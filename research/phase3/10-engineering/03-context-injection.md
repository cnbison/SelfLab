# 10-03 - 用户上下文注入（TwinContextBuilder）

> **目的**：让 SGE 知道在跟谁对话（学生/老人/历史人物），而不需要 SGE 内部写领域代码
> **来源**：借鉴 AiBeing EverMemOS 的"user profile 注入到 LLM prompt"模式

---

## 1. 为什么需要 Context Injection

```
SGE 的 Critic LLM 看到的是：
  - event（事件）
  - drives（5 drives 当前状态）
  - values（6 values 当前状态）
  - agent.drive_state
  
但 SGE 不知道：
  - 这个学生叫什么名字
  - 他现在数学学得怎么样
  - 他最近有没有和父母吵架
  - 他是初几的
  
→ 如果不注入这些 context，SGE 生成的 Identity / Narrative 是"通用 AI 婴儿"，不是"这个学生"
```

**Solution：TwinContextBuilder**

App 层构造"丰富 context"，SGE 通过 hook 接收。

---

## 2. 设计

```python
class TwinContextBuilder:
    """构造注入到 SGE 各层的 context"""
    
    def __init__(self, app_state: dict):
        self.app_state = app_state
    
    def build_critic_context(
        self,
        student_event: StudentEvent,
        mastery_state: SubjectMasteryState,
        extra: Optional[dict] = None,
    ) -> dict:
        """构造注入到 SGE Critic 的 context（替换默认 8D）"""
        ctx = {
            # SGE 原生 8D（必须保留）
            'user_emotion': self._infer_emotion_from_event(student_event),
            'topic_intimacy': self._infer_intimacy(student_event),
            'conversation_depth': self._compute_depth(),
            'user_engagement': self._infer_engagement(),
            'conflict_level': self._infer_conflict(student_event),
            'novelty_level': self._infer_novelty(student_event),
            'user_vulnerability': self._infer_vulnerability(student_event),
            'time_of_day': self._infer_time_of_day(),
            
            # App 层注入（学生特有 — SGE 不知道这些字段含义）
            'student_name': self.app_state.get('student_name'),
            'student_grade': self.app_state.get('grade'),
            'current_mastery_overview': mastery_state.summary(),
            'recent_struggle': mastery_state.most_recent_struggling(),
            'learning_pace': mastery_state.learning_velocity(),
            
            # 可选扩展
            **(extra or {}),
        }
        return ctx
    
    def build_actor_prompt_context(
        self,
        student_event: StudentEvent,
        mastery_state: SubjectMasteryState,
    ) -> str:
        """构造 Actor 的 prompt context（注入到 system prompt）"""
        return f"""
[学生信息]
姓名: {self.app_state.get('student_name', 'unknown')}
年级: {self.app_state.get('grade', 'unknown')}
当前优势学科: {mastery_state.get_mastering_subjects() or '无'}
当前挑战学科: {mastery_state.get_struggling_subjects() or '无'}

[本次事件]
{student_event.to_human_readable()}

[回复要求]
- 用学生名字称呼（如果已知）
- 根据当前挑战学科给具体建议（不是泛泛而谈）
- 避免评判性语言（"你太差了"），用建设性语言（"这块有挑战"）
"""
```

---

## 3. 集成到 SGEOrchestrator

### 3.1 改造 Orchestrator 接受外部 context

```python
class SGEOrchestrator:
    def step(
        self, 
        epoch: int, 
        extra_critic_context: Optional[dict] = None,  # NEW: App 层注入
        extra_actor_context: Optional[str] = None,   # NEW: App 层注入
    ) -> OrchestratorStep:
        ...
        
        # Step 3: Critic（用 App 注入的 context 覆盖默认）
        critic_context, value_delta = critic_sense(
            event=event.to_dict(),
            drives=self.agent.drive_state,
            values=self.value_layer.value_state,
            use_real_llm=self.use_real_llm,
            llm=self.llm,
            seed=hash((epoch, 'critic')) % (2**31),
            extra_context=extra_critic_context,  # NEW
        )
        
        ...
        
        # Step 11: Actor（用 App 注入的 system prompt 增强）
        actor_output = actor_express(
            signals=noisy_signals,
            value_vector=self.value_layer.value_state,
            retrieved_memories=retrieved_memories,
            current_narrative=self.narrative_builder.get_current(),
            use_real_llm=self.use_real_llm,
            llm=self.llm,
            seed=hash((epoch, 'actor')) % (2**31),
            extra_system_prompt=extra_actor_context,  # NEW
        )
```

### 3.2 Critic LLM 接口改造

```python
# sge/critic.py
def critic_sense(
    event: dict,
    drives: Optional[dict] = None,
    values: Optional[dict] = None,
    use_real_llm: bool = False,
    llm=None,
    seed: int = 0,
    extra_context: Optional[dict] = None,  # NEW
    **kwargs,
):
    # 构造 critic context
    ctx = {
        'user_emotion': 0.5,
        'topic_intimacy': 0.5,
        ...
    }
    
    # App 层注入的 context 覆盖默认
    if extra_context:
        ctx.update(extra_context)
    
    # 构造 prompt（含 ctx 所有字段）
    prompt = SGE_CRITIC_PROMPT.format(
        event=event,
        vv_str=vv_str,
        drv_str=drv_str,
        extra_ctx_str=json.dumps(extra_context) if extra_context else '',
    )
    
    # ...
```

---

## 4. 数据流示例

```
App 层：
  event = StudentEvent(...)
  mastery_state = SubjectMasteryState(...)
  
  # 构造 context
  context_builder = TwinContextBuilder(app_state)
  critic_ctx = context_builder.build_critic_context(event, mastery_state)
  # → {
  #     'student_name': 'Alice',
  #     'student_grade': 8,
  #     'current_mastery_overview': 'math: 65, english: 82',
  #     'recent_struggle': 'math/algebra',
  #     ...
  #   }
  
  actor_ctx = context_builder.build_actor_prompt_context(event, mastery_state)
  # → "[学生信息] 姓名: Alice 年级: 8 当前优势: english ..."

# SGE 层：
  trace = sge_orchestrator.step(
      epoch=N,
      extra_critic_context=critic_ctx,
      extra_actor_context=actor_ctx,
  )

# SGE 不知道这是学生事件，sge 看到的只是"有 rich context 的事件"
# 但 LLM 知道："我是 Alice 的数字孪生"
```

---

## 5. 不同应用的注入差异

| 应用 | critic_context 关键字段 | actor_system_prompt |
|------|----------------------|---------------------|
| **学生数字孪生** | student_name, grade, mastery_state | "你是{name}的数字孪生，熟悉他的学习状态" |
| **教学 AI 教练** | student_state, learning_goals | "你是{name}的教练，目标是帮助他达到学习目标 B" |
| **Personal AI** | user_name, relationship_history | "你是{name}的私人助手，理解他的偏好" |
| **历史人物数字孪生** | person_name, era, historical_context | "你是{era}的{name}，按当时价值观回答" |

**关键**：SGE 不知道这些字段含义，App 层负责构造完整 prompt。

---

## 6. 边界：什么不该注入

| ❌ 不该注入 | 理由 |
|-----------|------|
| 完整学生档案（成绩单、家长信息）| 隐私 + context window 限制 |
| 实时聊天历史（每轮都注入）| 应让 Hawking 检索而不是直接注入 |
| 敏感数据（医疗、宗教、政治）| FERPA + 隐私法规 |
| 实时事件流（>100 events）| 应让 Crystallizer 提取模式 |

**注入原则**：**注入"AI 不知道的领域知识"，不是"所有信息"**。

---

## 7. 实施清单

| 子任务 | 工作量 |
|--------|--------|
| `sge/context_injection.py` (TwinContextBuilder) | 1 天 |
| SGEOrchestrator 接受 extra_critic_context / extra_actor_context | 0.5 天 |
| Critic / Actor LLM 接口扩展 | 0.5 天 |
| 单元测试（context_builder）| 0.5 天 |
| 集成测试（end-to-end context 注入）| 0.5 天 |
| **总计** | **3 天** |

---

## 8. 关联文档

- [README.md §P0 任务](../README.md)
- [02-session.md](./02-session.md) — Session 内调用 context builder
- [02-architecture.md §应用层边界](../../00-overview/02-architecture.md)
- [discussions/2026-06-22-...-aibeing-reflection.md §2.2](../../../discussions/2026-06-22-sge-phase3-aibeing-reflection.md) — AiBeing EverMemOS 借鉴

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-22
