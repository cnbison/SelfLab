# 10-02 - 会话管理（TwinSession）

> **目的**：管理单次学生与 twin 交互的 session 生命周期（加载 → 跑 N events → 保存）
> **来源**：借鉴 AiBeing `chat_agent._chat_inner()` 的 session 模式

---

## 1. 为什么需要 Session

```
当前 SGEOrchestrator：
  orchestrator = SGEOrchestrator(agent, ...)
  traces = orchestrator.run(n_epochs=1000)
  
问题：
  - state 在 orchestrator 实例内驻留
  - 跨进程/重启 = state 丢失（除非有 persistence）
  - 多用户场景：每个用户一个 orchestrator 实例？太重
  - 没法"加载上次对话状态继续聊"
```

**Solution：TwinSession class**

```python
session = TwinSession(student_id='stu_001', twin_db=twin_state_db)
# 自动从 DB 加载完整状态
session.process_event(student_event)  # 一个 epoch
session.process_event(student_event)
session.close()  # 保存到 DB
```

---

## 2. TwinSession 设计

```python
class TwinSession:
    """单次学生与 twin 交互的 session
    
    生命周期：
    1. __init__: 从 DB 加载完整 state
    2. process_event: 处理一个学生事件（SGE step + 持久化增量）
    3. close: 保存完整 state 到 DB
    """
    
    def __init__(
        self,
        student_id: str,
        twin_db: TwinStateDB,
        sge_state: Optional[dict] = None,
        app_state: Optional[dict] = None,
        current_epoch: Optional[int] = None,
    ):
        self.student_id = student_id
        self.db = twin_db
        
        # 从 DB 加载（如未提供）
        if sge_state is None:
            sge_state, app_state, current_epoch = twin_db.load_full_state(student_id)
        
        self.sge_state = sge_state or {}
        self.app_state = app_state or {}
        self.current_epoch = current_epoch or 0
        
        # 构造 SGEOrchestrator（无 LLM，先 stub 模式）
        self.orchestrator = self._build_orchestrator_from_state(
            self.sge_state
        )
    
        # 设置当前 epoch
        self.orchestrator._n_epochs_hint = self.current_epoch
    
    def process_event(self, student_event: StudentEvent, 
                      mastery_state: SubjectMasteryState) -> dict:
        """处理一个学生事件，返回 AI 响应"""
        
        # 1. App 层：更新 SubjectMasteryState
        mastery_state.update(student_event)
        
        # 2. App 层：构造 SGE event + context
        sge_event = student_event_to_sge_event(
            student_event, mastery_state
        )
        critic_context = build_critic_context(
            student_event, mastery_state
        )
        
        # 3. SGE 12 步编排
        trace = self.orchestrator.step(
            epoch=self.current_epoch,
            extra_critic_context=critic_context,
        )
        
        # 4. App 层：保存到对话历史
        self.app_state.setdefault('conversations', []).append({
            'epoch': self.current_epoch,
            'student_event': student_event.to_dict(),
            'actor_output': trace.actor_output.to_dict() if trace.actor_output else None,
        })
        
        # 5. 增量持久化（每 10 epoch 才全量）
        self.current_epoch += 1
        if self.current_epoch % 10 == 0:
            self._save_incremental()
        
        return {
            'epoch': self.current_epoch - 1,
            'actor_output': trace.actor_output,
            'mastery_summary': mastery_state.summary(),
        }
    
    def close(self):
        """关闭 session：保存完整 state 到 DB"""
        # 1. 从 orchestrator 提取最新 state
        self._sync_state_from_orchestrator()
        
        # 2. 保存到 DB
        self.db.save_full_state(
            self.student_id,
            self.sge_state,
            self.app_state,
            epoch=self.current_epoch,
            trigger='on_close',
        )
    
    def _build_orchestrator_from_state(self, sge_state: dict) -> SGEOrchestrator:
        """从持久化 state 重建 orchestrator"""
        # 复杂的 state restoration 逻辑
        # 详见 §4
        ...
    
    def _sync_state_from_orchestrator(self):
        """从 orchestrator 提取最新 state 到 self.sge_state"""
        ...
    
    def _save_incremental(self):
        """增量保存（每 10 epoch）"""
        self._sync_state_from_orchestrator()
        self.db.save_full_state(
            self.student_id,
            self.sge_state, self.app_state,
            epoch=self.current_epoch,
            trigger='auto_10',
        )
```

---

## 3. Session 生命周期图

```
┌─────────────────────────────────────────┐
│ TwinSession.__init__(student_id, db)    │
│                                          │
│ 1. db.load_full_state(student_id)       │
│    ├─ Found → sge_state 加载           │
│    └─ Not found → 创建新 student row     │
│ 2. 重建 SGEOrchestrator（无 LLM）       │
│ 3. self.current_epoch = db.last_epoch    │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ session.process_event(event) × N         │
│                                          │
│ 每 event:                                │
│  1. App 层：更新 SubjectMasteryState    │
│  2. App 层：构造 SGE event + context    │
│  3. SGE：step(epoch) → trace            │
│  4. App 层：保存对话历史                │
│  5. 每 10 epoch：增量 save_full_state  │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ session.close()                          │
│                                          │
│ 1. 从 orchestrator 提取最新 state        │
│ 2. db.save_full_state(trigger='on_close') │
│ 3. 删除临时缓存                         │
└─────────────────────────────────────────┘
```

---

## 4. 从 State 重建 Orchestrator（难点）

```python
def _build_orchestrator_from_state(self, sge_state: dict) -> SGEOrchestrator:
    """从持久化 state 重建 SGEOrchestrator"""
    
    # 1. 重建基础组件
    drives = ['exploration', 'safety', 'creativity', 'connection', 'autonomy']
    agent = Agent(seed=42, drives=drives)
    
    # 2. 恢复 value_state
    if 'value_state' in sge_state:
        for k, v in sge_state['value_state'].items():
            agent.value_layer.value_state[k] = v
    
    # 3. 恢复 drive_state + frustration
    if 'drive_state' in sge_state:
        for k, v in sge_state['drive_state'].items():
            metabolism.drive_state[k] = v
    if 'frustration' in sge_state:
        for k, v in sge_state['frustration'].items():
            metabolism.frustration[k] = v
    
    # 4. 恢复 Hawking memory
    hawking = HawkingDecay(gamma=0.01)
    for mem_dict in sge_state.get('hawking_memory', []):
        hawking.memory.append(mem_dict)
    
    # 5. 恢复 Crystallizer clusters
    crystallizer = MemoryCrystallizer(n_dims=11)
    for cluster in sge_state.get('crystallizer_clusters', []):
        crystallizer.clusters.append(cluster)
    
    # 6. 恢复 Identity history
    identity_layer = IdentityLayer()
    identity_layer.identity_history = sge_state.get('identity_history', [])
    
    # 7. 恢复 Narrative history
    narrative_builder = NarrativeBuilder()
    narrative_builder.narrative_history = sge_state.get('narrative_history', [])
    
    # 8. 构造 orchestrator
    return SGEOrchestrator(
        agent=agent,
        value_layer=agent.value_layer,
        drive_metabolism=metabolism,
        event_generator=EventGenerator(baby_id=self.student_id, seed=42),
        identity_layer=identity_layer,
        narrative_builder=narrative_builder,
        hawking=hawking,
        crystallizer=crystallizer,
        crystallize_every=10,
        use_real_llm=False,  # session 默认 stub 模式
    )
```

---

## 5. 与 Persistence 的关系

```
Persistence (sge/persistence.py)         Session (sge/session.py)
  │                                          │
  ├─ load_full_state(student_id)           ◄──┤ session 启动时调用
  ├─ save_full_state(...)                  ◄──┤ session close + 每 10 epoch
  ├─ save_incremental(layer, data, epoch)  ◄──┤ 单层增量（Identity/Narrative/Hawking）
  └─ delete_student(student_id)            ◄──┤ GDPR right-to-deletion
    
Session 调用 Persistence，但不依赖其具体实现
→ 可独立测试 Session（用 mock Persistence）
```

---

## 6. 与 Orchestrator 的关系

```
SGEOrchestrator（已有）
  - 12 步循环
  - state 在内部驻留
  
TwinSession（新）
  - 包一层 orchestrator
  - 加 persistence 集成
  - 加 App 层数据流（SubjectMasteryState, conversation history）
  - 加 session lifecycle（load → run → save）

→ SGEOrchestrator 不变
→ TwinSession 是"App-friendly"包装
```

---

## 7. 多 Session 并发

```python
# 同一学生不能开多个 session（数据竞争）
class SessionLock:
    def __init__(self, student_id: str, db: TwinStateDB):
        # INSERT INTO session_locks (student_id, started_at) VALUES (...)
        # 如果已存在 → raise SessionLockedError
        ...

# 不同学生可以并发
session_a = TwinSession('stu_001', db)  # 学生 A
session_b = TwinSession('stu_002', db)  # 学生 B（并发 OK）
```

---

## 8. 实施清单

| 子任务 | 工作量 |
|--------|--------|
| `sge/session.py` (TwinSession) | 1.5 天 |
| _build_orchestrator_from_state 单元测试 | 0.5 天 |
| Session lifecycle 集成测试 | 0.5 天 |
| 文档 + 示例 | 0.5 天 |
| **总计** | **3 天** |

---

## 9. 关联文档

- [README.md §P0 任务](../README.md)
- [01-persistence.md](./01-persistence.md) — Session 依赖 persistence
- [03-context-injection.md](./03-context-injection.md) — Session 内的 context 注入
- [02-architecture.md §应用层边界](../../00-overview/02-architecture.md)
- [discussions/2026-06-22-...-aibeing-reflection.md §2.1](../../../discussions/2026-06-22-sge-phase3-aibeing-reflection.md) — AiBeing session 模式借鉴

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-22
