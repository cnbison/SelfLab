# 02 - sge/ 包架构 + 应用层边界

> **目的**：明确 SGE 引擎 vs App 应用层各自的责任，避免"什么在 SGE 里 / 什么在 App 里"的混乱

---

## 1. 架构总览

```
┌─ App 应用层（Phase 3 新增）────────────────────────────┐
│                                                            │
│  ┌─ 数字孪生 / AI 教练 / Personal AI / 协作 agent ─────┐ │
│  │                                                       │ │
│  │  - UI（chat / 语音 / 虚拟形象）                    │ │
│  │  - 数据采集（学校系统 / 日记 / 社交 API）          │ │
│  │  - 持久化（SQLite DB + save/load）                 │ │
│  │  - 会话管理（session state）                       │ │
│  │  - LLM cache / async                                │ │
│  │  - 用户上下文注入（StudentProfile → SGE context）  │ │
│  │  - 领域模型（SubjectMasteryState 学生领域特有）    │ │
│  │                                                       │ │
│  └────────────────────────────────────────────────────┘ │
│                                                            │
├─ SGE 引擎层（已有，pip install sge）──────────────────────┤
│                                                            │
│  - 12 步编排（Event → Critic → Value → ... → Narrative）│
│  - EventGenerator / Critic / Actor / Identity / Narrative│
│  - ValueLayer / HawkingDecay / MemoryCrystallizer      │
│  - SGEOrchestrator                                        │
│  - SGELLMClient                                            │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**关键原则**：**SGE 保持领域无关性**——SGE 处理"事件流 → 价值/记忆/身份/叙事"。学生/老人/历史人物各有自己的领域模型，但都用同一个 SGE personality engine。

---

## 2. 责任划分（详细）

| 概念 | SGE 包 | 应用层 | 理由 |
|------|--------|--------|------|
| 12 步编排 | ✅ | | 引擎核心 |
| EventGenerator（通用） | ✅ | | 引擎核心 |
| Critic / Actor / Identity / Narrative | ✅ | | 引擎核心 |
| Hawking / Crystallizer / Value / Drive | ✅ | | 引擎核心 |
| 4 层记忆系统 | ✅ | | 引擎核心 |
| LLM 适配（含 retry/warmup/timeout）| ✅ | | 引擎核心 |
| **持久化层** | ✅ 提供基础 API（save/load 4 层）| ✅ 决定 schema + 数据库 | App 知道数据布局 |
| **会话管理** | | ✅ TwinSession | App 决定 session 边界 |
| **用户上下文注入** | | ✅ TwinContextBuilder | App 构造 SGE 看的 context |
| **LLM cache** | ✅ 提供 hook | ✅ 决定 cache 策略 | 性能优化 |
| **领域模型** | | ✅ SubjectMasteryState（学生）| 领域特有 |
| **数据采集** | | ✅ SchoolSystem / Journal API | 数据源特有 |
| **UI** | | ✅ Chat / Voice / Avatar | 产品特有 |
| **多用户隔离** | | ✅ Per-user DB row | 产品架构 |

---

## 3. SGE 内部模块（M2.x 已有）

```
sge/
├── baseline.py        Agent, DriveMetabolism, ValueLayer, 
│                       HawkingDecay, MemoryCrystallizer
├── event.py           EventGenerator, LifeEvent
├── llm_client.py      SGELLMClient (retry/warmup/timeout)
├── critic.py          critic_sense (LLM 感知)
├── actor.py           actor_express (LLM 表达)
├── identity.py        IdentityLayer (自我概念)
├── narrative.py       NarrativeBuilder (自传叙事)
└── orchestrator.py    SGEOrchestrator (12 步编排)
```

**M2.x 验证状态**：
- ✅ M2.2 1000 epoch × 真实 LLM × 3 baby 跑通
- ✅ personality_divergence 0.9884
- ✅ Identity 50 次重写 + Narrative 50 次构建
- ✅ Hawking 衰减（M2.3 修复 unit bug 后 4/4 unit tests PASS）

---

## 4. Phase 3 新增模块（应用层）

```
sge/                  (扩展)
├── baseline.py
├── event.py
├── ...
├── persistence.py     # NEW (Phase 3.1 P0)
├── session.py         # NEW (Phase 3.1 P0)
├── context_injection.py  # NEW (Phase 3.1 P0)
├── llm_cache.py       # NEW (Phase 3.2 P1)
├── prompts/           # NEW (Phase 3.2 P2) - prompt 模板 + version
│   ├── critic/
│   └── actor/
└── tests/             # NEW (Phase 3.2 P1) - 单元测试覆盖 ≥80%
```

**关键设计决策**：

| 决策 | 选择 | 理由 |
|------|------|------|
| persistence 放 SGE 包还是 App？| **放 SGE 包** | 提供通用 TwinStateDB API，App 调用 |
| session 放 SGE 包还是 App？| **放 SGE 包** | 与 orchestrator 紧耦合 |
| context_injection 放 SGE 包还是 App？| **放 SGE 包** | SGE 提供 hook，App 构造内容 |
| llm_cache 放 SGE 包还是 App？| **放 SGE 包** | 性能优化，所有 App 都受益 |
| 领域模型放哪？| **App 层** | SubjectMasteryState 等是领域特有 |

---

## 5. 数据流（学生数字孪生示例）

```python
# 1. 数据采集（App 层）
math_test = school_api.get_test_score('stu_001', 'midterm_2026')
# → {'score': 65, 'prev_score': 90, 'subject': 'math', 'topic': 'algebra'}

# 2. 构造 StudentEvent（App 层）
event = StudentEvent(
    event_type='mastery_drop', subject='math', topic='algebra',
    mastery_before=90, mastery_after=65, mastery_delta=-25,
    emotion='frustrated', emotion_intensity=4,
)

# 3. 更新 SubjectMasteryState（App 层）
mastery_state.update('math', MasteryChange(topic='algebra', score_delta=-25))

# 4. Adapter：StudentEvent → SGE event + 注入 mastery context（App 层）
sge_event = student_event_to_sge_event(event, mastery_state)
critic_context = inject_mastery_to_critic(mastery_state)

# 5. SGE 12 步编排（SGE 层，不知道是学生事件）
trace = sge_orchestrator.step(epoch=N, critic_context=critic_context)

# 6. 持久化（App 层 → DB）
twin_state_db.save_full_state('stu_001', sge_state, app_state, epoch=N, trigger='auto_100')

# 7. 渲染响应（App 层）
return render_chat_response(trace.actor_output, mastery_state)
# → "你最近数学好像不太顺利，要不要聊聊代数哪部分最吃力？"
```

---

## 6. SGE 与 AiBeing 的边界（应用层）

M2.1 mapping 已经借鉴了 AiBeing 的引擎内部 9 机制。Phase 3 应用层也借鉴（详见 [discussions/2026-06-22-...aibeing-reflection.md](../../../discussions/2026-06-22-sge-phase3-aibeing-reflection.md)）。

**SGE 与 AiBeing 的关键差异**：

| 差异 | AiBeing | SGE |
|------|---------|-----|
| 身份 | SOUL.md 预设 | Identity Layer 涌现 |
| 情感 | 模拟 | frustration 真实累积 |
| Phase | 预设状态切换 | frustration 阈值触发 |
| 4 层记忆 | 1-2 层 | 4 层（Hawking/Crystallizer/Identity/Narrative）|
| 长跑稳定性 | 单进程 | chunk 隔离（17h 验证）|
| 用户记忆 | EverMemOS | 持久化层（SQLite）|
| 应用领域 | AI 角色扮演 | 数字孪生 + AI 教练 + ... |

---

## 7. 关联文档

- [README.md](../README.md) — Phase 3 SSOT 入口
- [01-applications.md](./01-applications.md) — 4 应用详解
- [03-roadmap.md](./03-roadmap.md) — 时间线
- [04-risks.md](./04-risks.md) — 风险矩阵
- [10-engineering/](../10-engineering/) — Phase 3.1 工程实现细节
- [sge/README.md §Phase 3 路线图](../../../sge/README.md)

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-22
