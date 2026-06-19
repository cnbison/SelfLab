# SGE M2.1 阶段 C — 实施计划

文档版本：v0.1
日期：2026-06-19
整理者：Bisen & Claude
状态：📋 待 Bisen 评审

> **本文件性质**：**M2.1 阶段 C 的实施计划**——把 [PRD §FR-5, FR-6](../../PRD.md) + [DESIGN §二, §五, §六](../../DESIGN.md) 的需求映射为 4 个可独立实施的子任务。
>
> **本文件承接阶段 B**：B1-B7 已在 [1.17.0] 完成，提供了 Agent/DriveMetabolism/ValueLayer/Critic 适配层。阶段 C 在此基础上新增 Identity/Narrative/完整 Event Generator。
>
> **关联文档**：
> - [SGE-M21-Phase-B-Implementation-Plan.md](./SGE-M21-Phase-B-Implementation-Plan.md) — 阶段 B 实施计划（已通过，commit `bc42a47`）
> - [SGE-M21-AiBeing-Implementation-Mapping.md](./SGE-M21-AiBeing-Implementation-Mapping.md) — 借鉴映射（阶段 C 不直接借鉴 AiBeing，主要是 SGE 自有实现）
> - [experiments/M21_PHASE_B_REPORT.md](../../experiments/M21_PHASE_B_REPORT.md) — 阶段 B 报告
> - [PRD.md §FR-5, FR-6](../../PRD.md) — Identity Layer + Narrative Layer 功能需求
> - [DESIGN.md §二, §五, §六](../../DESIGN.md) — 详细设计
> - [ARCH.md §3.4, §3.5](../../ARCH.md) — Identity Layer + Narrative Layer 架构

---

# 0. 目的与边界

## 0.1 阶段 C 的目标

实现 SGE 完整 6 层架构中的 Identity Layer + Narrative Layer，并完整化 Event Generator + Value Conflict Generator。阶段 C 完成后，SGE 核心架构可运行（虽然 Identity/Narrative 实现仍是 MVP）。

## 0.2 阶段 C **不**包含（明确边界）

- ❌ **完整 12 步双 LLM 编排**（阶段 D 才做）
- ❌ **3 seed × 100 epoch 验证**（阶段 D 才做）
- ❌ **Identity Stability / Narrative Coherence 量化评估**（阶段 D 才做长 epoch 验证）
- ❌ **Identity Profile 化**（学生用 mastery、教练用 empathy 等——Phase 3 才做）
- ❌ **情绪对叙事的影响**（M3.1 才做）

## 0.3 阶段 C 的输入与输出

| 输入 | 来源 |
|------|------|
| 阶段 B 自有实现 `_sge_baseline.py` | B1-B7（drives/values/EMA/Hawking/Crystallize）|
| `_sge_critic.py` | B4 Critic LLM 适配层 |
| DESGIN.md §二/§五/§六 | Identity/Narrative/Event Generator 设计 |
| PRD §FR-5, FR-6 | 功能需求 |

| 输出 | 用途 |
|------|------|
| 新增 `_sge_event.py` | Event Generator + Value Conflict Generator |
| 新增 `_sge_identity.py` | Identity Layer（crystallize + validate）|
| 新增 `_sge_narrative.py` | Narrative Builder MVP |
| 扩展 `m21_phase_b.py` → `m21_phase_c.py` | 集成测试 |
| 扩展 `m21_phase_b.yaml` → `m21_phase_c.yaml` | 配置 |
| `experiments/M21_PHASE_C_REPORT.md` | 阶段 C 报告 |

---

# 1. 阶段 C 范围：4 个子任务

## C1：Event Generator 完整化

**目标**：完整化 Event Generator，从 stub 模板改为动态生成 + 因果链上下文。

**功能需求**：[PRD §FR-1](../../PRD.md)（事件生成器）
**详细设计**：[DESIGN §二](../../DESIGN.md)

**FR-1 需求**：
- 支持多种事件类型：success / failure / relationship / exploration / risk / value_conflict
- 事件必须有因果逻辑（可重复性原则）
- 根据当前 Value Layer 动态生成针对性价值困境
- 事件的时间间隔和频率符合自然节奏

**改造契约**：

```python
# 新增 _sge_event.py

import uuid
from dataclasses import dataclass

@dataclass
class LifeEvent:
    """DESIGN §2.1 标准 LifeEvent 数据类"""
    event_id: str            # "{baby_id}-e{epoch:04d}-{uuid8}"
    event_type: str          # success, failure, relationship, exploration, risk, value_conflict
    description: str         # 事件的自然语言描述
    intensity: float         # [0, 1]
    value_challenges: list   # 涉及的价值观挑战
    causal_context: str      # 因果背景（从 event_history 推导）
    timestamp: float         # 事件时间戳

def make_event_id(baby_id: str, epoch: int) -> str:
    """DESIGN §2.1 规范"""
    return f"{baby_id}-e{epoch:04d}-{uuid.uuid4().hex[:8]}"


# 事件模板库（6 类型 × 多种）
EVENT_TEMPLATES = {
    'success': [...],
    'failure': [...],
    'relationship': [...],
    'exploration': [...],
    'risk': [...],
    'value_conflict': [...],  # 详见 C2
}


class EventGenerator:
    """事件生成器（DESIGN §2.2）"""

    def __init__(self, baby_id: str, seed: int = 0):
        self.baby_id = baby_id
        self.event_history = []  # [(epoch, event), ...]
        self.rng = random.Random(seed)

    def generate(self, epoch: int, value_vector: ValueLayer) -> LifeEvent:
        """生成下一事件

        来源: DESIGN §2.2 动态事件生成
        逻辑:
          - 30% 概率 → value_conflict（C2）
          - 70% 概率 → 常规事件（success/failure/...）
          - 因果链：从 event_history 推导 causal_context
        """
        ...
```

**验证标准**：
1. `LifeEvent` dataclass 字段完整（含 event_id 规范）
2. `make_event_id('encouraged', 1)` 返回 `'encouraged-e0001-xxxxxxxx'`
3. 100 次 `generate()` 返回不同事件（variety 验证）
4. `value_conflict` 概率 ≈ 30%（1000 次统计）
5. `causal_context` 反映 event_history（前 N 个事件的因果引用）

**预计工作量**：1 天

---

## C2：Value Conflict Generator

**目标**：基于 value_vector 的 strongest/weakest 生成针对性价值困境事件。

**详细设计**：[DESIGN §2.3](../../DESIGN.md)

**改造契约**：

```python
# _sge_event.py 扩展

# Value Conflict 模板（value × value 二元关系）
VALUE_CONFLICT_TEMPLATES = {
    ('safety', 'connection'): [
        "你有一个朋友的紧急求助，但需要独自前往危险地区",
        ...
    ],
    ('creativity', 'safety'): [
        "你想尝试一个突破性实验，但有显著风险",
        ...
    ],
    # ... 其他 6×5=30 个 value 对组合
}


def generate_value_conflict(
    challenge_value: str,
    alternative_value: str,
    event_id: str,
    timestamp: float,
    rng: random.Random,
) -> LifeEvent:
    """DESIGN §2.3 价值困境生成器

    Args:
        challenge_value: 主要挑战的 value
        alternative_value: 替代/冲突的 value
        event_id, timestamp: 来自 EventGenerator
        rng: 随机数生成器

    Returns:
        LifeEvent(value_conflict, intensity 0.7-1.0, value_challenges=[...])
    """
    ...
```

**验证标准**：
1. 模板覆盖 6×5=30 个 value 对组合（至少覆盖常见组合）
2. `generate_value_conflict('safety', 'connection', ...)` 返回 LifeEvent(value_conflict)
3. `intensity` 在 [0.7, 1.0] 范围（DESIGN §2.3 规定）
4. `value_challenges` 包含 challenge 和 alternative
5. 多 seed 一致性（seed=42 / 7 / 123 行为稳定）

**预计工作量**：0.5 天

---

## C3：Identity Layer（crystallize + validate）

**目标**：实现 FR-5 Identity Layer，包括 crystallize_identity 和 validate_identity。

**功能需求**：[PRD §FR-5](../../PRD.md)（Identity Layer）
**详细设计**：[DESIGN §五](../../DESIGN.md)

**FR-5 需求**：
- 自动生成"我是谁"的回答
- 身份标签与行为历史交叉验证
- 身份随时间演化但保持稳定性

**改造契约**：

```python
# 新增 _sge_identity.py

SGE_IDENTITY_PROMPT = """基于以下价值观和人生经历，用一句话描述"我是谁"。

价值观：
{vv_desc}

关键经历：
{memories_desc}

要求：
- 用第一人称
- 不超过 50 字
- 必须能从上述经历中推导出来

输出仅 JSON 格式：
{{"identity": "..."}}
"""

SGE_VALIDATE_PROMPT = """身份描述：{identity}

价值观：{vv_desc}
关键经历：{memories_desc}

这个身份描述与价值观和经历是否一致？回答 YES 或 NO。
"""


class IdentityLayer:
    """SGE Identity Layer（DESIGN §五）"""

    def __init__(
        self,
        identity_history: Optional[list] = None,
        crystallize_every_n_epochs: int = 20,  # DESIGN §5.1 触发条件
        use_real_llm: bool = False,
    ):
        self.identity_history = identity_history or []
        self.crystallize_every_n_epochs = crystallize_every_n_epochs
        self.use_real_llm = use_real_llm

    def should_crystallize(self, epoch: int) -> bool:
        """DESIGN §5.1 触发条件：每 N 个 Epoch"""
        return epoch % self.crystallize_every_n_epochs == 0

    def crystallize(
        self,
        value_layer: ValueLayer,
        key_memories: list,
        llm_call=None,  # stub or real
    ) -> Optional[str]:
        """DESIGN §5.1 凝聚身份

        Returns:
            identity 字符串（第一人称，不超过 50 字），或 None（验证失败）
        """
        # 1. 调用 LLM 生成 identity
        # 2. validate_identity 验证
        # 3. 验证通过 → 记录到 history
        ...

    def validate(self, identity: str, value_layer: ValueLayer, key_memories: list) -> bool:
        """DESIGN §5.2 验证"""
        ...

    def get_current(self) -> Optional[str]:
        """获取当前身份（最近一次 crystallize 成功的 identity）"""
        if self.identity_history:
            return self.identity_history[-1]['identity']
        return None
```

**验证标准**：
1. `IdentityLayer()` 构造 + `crystallize_every_n_epochs=20` 设置
2. `should_crystallize(20)` = True；`should_crystallize(21)` = False
3. stub 模式下 `crystallize(...)` 返回 stub identity（不调用 LLM）
4. `validate(...)` 检查 identity/value/memories 一致性
5. 阶段 B ValueLayer 兼容（接口匹配）
6. 多 seed 一致性（seed=42/7/123 都跑通）

**预计工作量**：1.5 天（含 LLM 适配）

---

## C4：Narrative Builder MVP

**目标**：实现 FR-6 Narrative Layer，包括 build_narrative / check_narrative_consistency / handle_phase_transition。

**功能需求**：[PRD §FR-6](../../PRD.md)（Narrative Layer）
**详细设计**：[DESIGN §六](../../DESIGN.md)

**FR-6 需求**：
- 将零散记忆串联为因果链
- 支持叙事断裂与重建（Phase Transition）
- 定期一致性扫描和修复

**改造契约**：

```python
# 新增 _sge_narrative.py

SGE_NARRATIVE_PROMPT = """基于以下关键经历，构建一个连贯的人生叙事。

我的身份：{current_identity}

关键经历（按时间顺序）：
{events_timeline}

要求：
- 过去 → 现在 → 未来 的结构
- 每个经历之间有因果连接
- 总结"我从这些经历中学到了什么"
- 展望"我将走向何方"
- 不超过 500 字

输出仅 JSON 格式：
{{"narrative": "..."}}
"""

SGE_CONSISTENCY_PROMPT = """叙事：{narrative}

实际经历：
{events_timeline}

这个叙事与实际经历的一致性如何？
评分：0.0（完全不一致）~ 1.0（完全一致）
只输出数字。
"""


class NarrativeBuilder:
    """SGE Narrative Layer（DESIGN §六）"""

    def __init__(
        self,
        current_narrative: Optional[str] = None,
        build_every_n_epochs: int = 50,  # DESIGN §六 触发条件
        use_real_llm: bool = False,
    ):
        self.current_narrative = current_narrative
        self.build_every_n_epochs = build_every_n_epochs
        self.use_real_llm = use_real_llm
        self.narrative_history = []  # [(epoch, narrative, coherence_score), ...]

    def should_build(self, epoch: int) -> bool:
        """DESIGN §六 触发条件"""
        return epoch % self.build_every_n_epochs == 0

    def build(
        self,
        crystallized_events: list,
        current_identity: Optional[str],
        llm_call=None,
    ) -> str:
        """DESIGN §6.1 构建叙事"""
        ...

    def check_consistency(
        self,
        narrative: str,
        crystallized_events: list,
        llm_call=None,
    ) -> float:
        """DESIGN §6.2 一致性检查（返回 [0, 1]）"""
        ...

    def handle_phase_transition(
        self,
        value_layer: ValueLayer,
        crystallized_events: list,
        llm_call=None,
    ) -> str:
        """DESIGN §6.3 叙事断裂与重建

        触发: Phase Transition (frustration > threshold)
        逻辑:
          1. 记录旧叙事
          2. 重建叙事（build + check_consistency）
          3. consistency > 0.5 → 接受新叙事；否则保留旧叙事
        """
        ...
```

**验证标准**：
1. `NarrativeBuilder()` 构造 + `build_every_n_epochs=50` 设置
2. `should_build(50)` = True
3. stub 模式下 `build(...)` 返回 stub narrative
4. `check_consistency(...)` 返回 [0, 1] 范围分数
5. `handle_phase_transition(...)` 重建叙事（旧叙事保留为 backup）
6. 阶段 A Phase Transition 兼容（与 Agent._last_phase_transition 联动）

**预计工作量**：1.5 天

---

# 2. 子任务依赖图

```
C1 (Event Generator 完整化) ──→ C2 (Value Conflict Generator)
        │                          │
        └────────────┬─────────────┘
                     │
                     ▼
        C3 (Identity Layer) ──→ C4 (Narrative Builder MVP)
                     │                          │
                     └────────────┬─────────────┘
                                  │
                                  ▼
                  集成测试（阶段 C 末段）
```

**关键路径**：C1 → C3 → C4（3 天 + 集成 1 天 = 4 天）

**可并行**：C2 与 C3 可并行（都依赖 C1，但相互独立）

**总时长**：4-5 天

---

# 3. 验收标准（阶段 C 完成时）

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | Event Generator 动态生成（FR-1）| `EventGenerator().generate()` 返回 LifeEvent，6 类型覆盖 |
| 2 | Value Conflict Generator（C2）| `generate_value_conflict()` 返回 value_conflict 事件，强度 0.7-1.0 |
| 3 | Identity Layer crystallize（FR-5）| `IdentityLayer.crystallize()` 返回 identity 字符串 |
| 4 | Identity Layer validate（FR-5）| `IdentityLayer.validate()` 返回 True/False |
| 5 | Narrative Builder build（FR-6）| `NarrativeBuilder.build()` 返回 narrative 字符串 |
| 6 | Narrative Builder consistency（FR-6）| `NarrativeBuilder.check_consistency()` 返回 [0, 1] |
| 7 | Narrative Builder Phase Transition（FR-6）| `handle_phase_transition()` 重建叙事 |
| 8 | 集成测试 | m21_phase_c.py 跑通（完整 12 步循环 stub）|
| 9 | 阶段 B 回归 | m21_phase_b.py 仍 PASS |
| 10 | 多 seed 一致 | seed=42/7/123 都跑通 |
| 11 | 实验报告 | M21_PHASE_C_REPORT.md |

---

# 4. 风险与开放问题

| 风险 | 影响 | 缓解 |
|------|------|------|
| Identity LLM 调用成本 | stub 模式可避免 | 阶段 C 默认 stub，M2.2/M2.3 才用真实 LLM |
| Narrative 长度控制（500 字）| LLM 输出可能超长 | stub 模式固定长度，真实模式加 max_tokens |
| Value Conflict 模板覆盖不全 | 30 个 value 对组合工作量大 | 阶段 C 覆盖常见 10 对，M2.2 扩展 |
| Phase Transition 触发需长 epoch | 5 步测试不会触发 | 阶段 D 长 epoch 验证 |
| Identity 稳定性需长 epoch | 5 步测试 identity 不收敛 | 阶段 D 量化评估 |

---

# 5. 与现有文档的关联

| 文档 | 影响 |
|------|------|
| [PRD §FR-5, FR-6](../../PRD.md) | 阶段 C 的需求依据 |
| [DESIGN §二, §五, §六](../../DESIGN.md) | 阶段 C 的设计依据 |
| [ARCH §3.4, §3.5](../../ARCH.md) | Identity + Narrative 架构 |
| [SGE-M21-AiBeing-Implementation-Mapping.md](./SGE-M21-AiBeing-Implementation-Mapping.md) | 阶段 C 不直接借鉴 AiBeing（Identity/Narrative 是 SGE 自有）|
| [SGE-Phase0-Closeout.md](../sge-core/SGE-Phase0-Closeout.md) | 阶段 C 不触发新的决策点 |
| [experiments/M21_PHASE_B_REPORT.md](../../experiments/M21_PHASE_B_REPORT.md) | 阶段 B 报告（基础）|

---

# 6. 时间估算

| 子任务 | 工作量 | 依赖 |
|--------|-------|------|
| C1: Event Generator 完整化 | 1 天 | — |
| C2: Value Conflict Generator | 0.5 天 | C1 |
| C3: Identity Layer | 1.5 天 | — |
| C4: Narrative Builder MVP | 1.5 天 | C3 |
| 集成测试 + 多 seed 验证 | 0.5 天 | C1-C4 |
| 报告写作 | 0.5 天 | 全部 |
| **总计** | **5-6 天** | — |

**关键路径**：C1 → C3 → C4（3 天）+ 集成 1 天 = 4 天

**可并行**：C2 与 C3 可并行（0.5 天节省）

---

# 7. 实施步骤建议

1. **第 1-2 天**（关键路径开始）：
   - C1: Event Generator 完整化
2. **第 2-3 天**：
   - C2: Value Conflict Generator（依赖 C1）
   - C3: Identity Layer（独立，与 C2 并行）
3. **第 3-4 天**：
   - C4: Narrative Builder MVP（依赖 C3）
4. **第 4-5 天**：
   - 集成测试（m21_phase_c.py）+ 多 seed 验证
5. **第 5-6 天**：
   - 报告写作 + CHANGELOG 更新 + commit + push

---

# 8. 一句话总结

> **M2.1 阶段 C 的本质是"架构完整化"**——在阶段 B 的 drives/values 基础上，新增 Identity Layer（"我是谁"）和 Narrative Layer（"我从哪里来"），并完整化 Event Generator 让事件能根据 value_state 动态生成。关键路径 C1→C3→C4 约 4 天完成，可并行 C2 节省 0.5 天，总计 5-6 天进入 M2.1 阶段 D（完整 12 步编排 + 100 epoch 验证）。

---

# 附录 A：版本与变更

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-19 | v0.1 | 初稿（Bisen 委托 Claude 基于 FR-5/FR-6 + DESIGN §二/§五/§六 起草）|

---

**创建日期**：2026-06-19
**最后更新**：2026-06-19
**维护者**：Bisen & Claude
**状态**：📋 待 Bisen 评审
