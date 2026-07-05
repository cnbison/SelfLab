# SGE Python Package

Self-Generating Engine — 通过"经历 → 解释 → 人格"形成 AI 持续自我认同。

## 状态

**Phase 3 Alpha** — 从 M2.x 实验脚本演化而来。包化目标：让 SGE 核心组件可被其他项目 import、可 pip install、可单元测试。

## 历史

| 阶段 | 里程碑 | 数据 |
|------|--------|------|
| M2.1 A/B/C/D | 完整架构实现 | stub + real LLM 混合验证 |
| M2.1 D6 | 真实 LLM 单 baby 验证 | 5/5 PASS |
| M2.2 E1-E6 | 三胞胎 1000 epoch × 真实 LLM | 12/12 chunks, personality_divergence 0.9884 |
| M2.3 | 个人真实测试 | challenged 一致性 6.00, L4 identity 9.0/10 |
| M2.3 fix | Hawking unit mismatch bug | 4/4 unit tests PASS |
| **Phase 3** | **sge/ 包化** | ← 当前 |

## 公开 API

```python
from sge import (
    # 核心机制
    Agent, DriveMetabolism, ValueLayer, MemoryCrystallizer, HawkingDecay,
    # 事件生成
    EventGenerator, LifeEvent,
    # 经验编码（洞察 34）
    Experience, encode_experience,
    # 自我熵度量（洞察 35）
    compute_self_entropy, entropy_reduction_rate,
    # LLM 适配层
    SGELLMClient, make_llm_client,
    # Critic / Actor
    critic_sense, actor_express, ActorOutput, BEHAVIOR_LABELS,
    # Identity / Narrative
    IdentityLayer, NarrativeBuilder,
    # Orchestrator
    SGEOrchestrator, OrchestratorStep,
)
```

## 安装

```bash
# Editable install（推荐 for development）
pip install -e sge/

# 运行测试
cd sge
pytest tests/
```

## 快速使用

```python
from sge import (
    Agent, DriveMetabolism, ValueLayer, HawkingDecay, MemoryCrystallizer,
    EventGenerator, SGELLMClient, SGEOrchestrator,
    IdentityLayer, NarrativeBuilder,
)

# 初始化核心组件
drives = ['exploration', 'safety', 'creativity', 'connection', 'autonomy']
agent = Agent(seed=42, drives=drives)
value_layer = ValueLayer()
hawking = HawkingDecay(gamma=0.01)
crystallizer = MemoryCrystallizer(n_dims=11)

# LLM
llm = make_llm_client(provider='minimax')
llm.warmup(n_calls=2)

# 12 步编排器
orchestrator = SGEOrchestrator(
    agent=agent, value_layer=value_layer,
    drive_metabolism=DriveMetabolism(drives=drives),
    event_generator=EventGenerator(baby_id='demo', seed=42),
    identity_layer=IdentityLayer(),
    narrative_builder=NarrativeBuilder(),
    hawking=hawking, crystallizer=crystallizer,
    use_real_llm=True, llm=llm,
)

# 跑 N epoch
traces = orchestrator.run(n_epochs=1000)
```

## 架构

```
sge/
├── __init__.py            # 公开 API
├── RUNTIME_AUDIT.md       # Self Evolution Runtime 定位审计（洞察 33）
├── baseline.py            # Agent / DriveMetabolism / ValueLayer / HawkingDecay / MemoryCrystallizer
├── event.py               # EventGenerator + LifeEvent
├── experience.py          # Experience + encode_experience（Step 2.5，洞察 34）
├── metrics.py             # compute_self_entropy / H_self（Step 16，洞察 35）
├── llm_client.py          # SGELLMClient (含 retry/warmup/timeout)
├── critic.py              # Critic LLM 适配
├── actor.py               # Actor LLM 适配
├── identity.py            # IdentityLayer
├── narrative.py           # NarrativeBuilder
├── orchestrator.py        # 12+3 步编排器（含 Step 2.5 Experience + Step 16 H_self）
└── tests/                 # 单元测试
```

> **Runtime 定位**：SGE 是 **Self Evolution Runtime**（自我演化运行时），而非 Memory Framework——
> 编排器提供受控时钟、单步执行、组件可插拔、逐步 trace。Step 2.5 把裸 Event 编码为含
> **meaning** 的 Experience（"这件事对我意味着什么"），Step 16 计算 **H_self**（自我认知熵）
> 作为自我形成的统一目标函数。详见 [RUNTIME_AUDIT.md](./RUNTIME_AUDIT.md) 与
> [SGE-Key-Insights 洞察 33-35](../SGE-Key-Insights.md)。

## Phase 3 路线图

- **3.1 Reflection Layer** — 让 SGE 能回答"后悔/感谢"类反思问题（M2.3 验证需要）
- **3.2 Multi-AI 互动** — 多 baby 之间对话、互相影响
- **3.3 长期人格稳定性测试** — 10000+ epoch 验证人格不"漂移过度"
- **3.4 应用原型** — Multi-AI 在真实场景的应用（如：个人助手、协作 agent）

## 关联文档

- [SelfLab README](../../README.md)
- [SGE-Memory-Layer-Design.md](../../research/sge-core/SGE-Memory-Layer-Design.md)
- [DESIGN.md](../../DESIGN.md)
- [M22_TRIPLETS_REPORT.md](../../experiments/M22_TRIPLETS_REPORT.md) — M2.2 验证
- [M23_PERSONAL_REALITY_REPORT.md](../../experiments/M23_PERSONAL_REALITY_REPORT.md) — M2.3 验证
