# SGE M2.1 阶段 B — 实施计划

文档版本：v0.1
日期：2026-06-19
整理者：Bisen & Claude
状态：📋 待 Bisen 评审

> **本文件性质**：**M2.1 阶段 B 的实施计划**——把 [SGE-Phase0-Closeout.md §5](../sge-core/SGE-Phase0-Closeout.md#5-决策结果基于-05-三原则推导2026-06-19-填写) 的决策映射到具体的代码改造点，每个子任务有明确的代码位置、改造契约、验证标准、依赖关系。
>
> **本文件不替 Bisen 做哲学决策**——所有决策点已沉淀到 Closeout §5，本文件只负责**工程实施**。
>
> **本文件是"实施脚手架"**——评审通过后，每个子任务可独立认领和实施，避免直接全量动手发现某项决策有遗漏。

## 关联文档

- [SGE-M21-AiBeing-Implementation-Mapping.md](./SGE-M21-AiBeing-Implementation-Mapping.md) — 借鉴映射（§五 阶段 A/B/C/D 分解 + 逐机制公式）
- [SGE-Phase0-Closeout.md §5](../sge-core/SGE-Phase0-Closeout.md#5-决策结果基于-05-三原则推导2026-06-19-填写) — 6 决策点填写（drives/Value scale/Phase/Hawking/Crystallize/LLM）
- [experiments/M21_BASELINE_SETUP_REPORT.md §6](../../experiments/M21_BASELINE_SETUP_REPORT.md#6-下一步) — 阶段 A 下一步建议（阶段 B/C/D 范围）
- [experiments/scripts/_sge_baseline.py](../../experiments/scripts/_sge_baseline.py) — 阶段 A 自有实现（要改造的代码）
- [experiments/scripts/m21_setup.py](../../experiments/scripts/m21_setup.py) — 阶段 A 基线冒烟测试（要扩展的脚本）
- [experiments/configs/m21_baseline.yaml](../../experiments/configs/m21_baseline.yaml) — 阶段 A 基线配置（要扩展的 schema）
- [SGE-Key-Insights.md §洞察 24, 26, 28](../../SGE-Key-Insights.md) — 相关洞察（怀特海动在/合生、6 维度非对称响应、LLM-agnostic）
- [PRD.md §FR-3, FR-4](../../PRD.md) — Reflection Layer + Value Layer 功能需求

---

# 0. 目的与边界

## 0.1 阶段 B 的目标

把 [SGE-M21-AiBeing-Implementation-Mapping.md §五 阶段 B](../sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md#五m21-实施步骤建议) 的"SGE 化改造"具体化为可独立实施的子任务，每个子任务完成后可立即验证。

## 0.2 阶段 B **不**包含（明确边界）

- ❌ **Identity Layer 完整实现**（阶段 C/D 才做）
- ❌ **Narrative Layer 完整实现**（阶段 C/D 才做）
- ❌ **完整 12 步双 LLM 编排**（阶段 D 才做）
- ❌ **3 seed × 100 epoch 验证**（阶段 D 才做）
- ❌ **Phase 3 产品化接口**（value profile / meta-values override——架构层留 stub，但具体设计留到 Phase 3）

## 0.3 阶段 B 的输入与输出

| 输入 | 来源 |
|------|------|
| 阶段 A 自有实现 `_sge_baseline.py` | 5 步循环已跑通（CHANGELOG 1.10.0/1.11.0）|
| §5 决策 | SGE-Phase0-Closeout.md（drives=候选 B 等 6 项）|
| 映射文档 §五 阶段 B 范围 | 实施步骤建议 |
| M1.x 实验经验 | value_state 在 80 epoch 后涌现幅度 0.34-0.75（CHANGELOG 1.7.0/1.8.0）|

| 输出 | 用途 |
|------|------|
| 扩展版 `_sge_baseline.py` | 阶段 C/D 的基础 |
| 扩展版 `m21_setup.py` 或新增 `m21_phase_b.py` | 阶段 B 验证脚本 |
| 扩展版 `m21_baseline.yaml` | 阶段 B 配置 |
| `experiments/M21_PHASE_B_REPORT.md` | 阶段 B 报告（与 M21_BASELINE_SETUP_REPORT.md 并列）|
| CHANGELOG 新条目 | 阶段 B 完成记录 |

---

# 1. 阶段 B 范围：7 个子任务

> 每个子任务都有**目标、代码位置、改造契约、验证标准、依赖关系**5 个字段，可独立认领和实施。

## B1：drives 维度替换（候选 B）+ schema 化

**目标**：把 AiBeing 原生 5D drives 替换为 SGE 候选 B 5D drives，schema 化（从配置读取，为 Phase 3 profile 化留接口）。

**§5 决策**：候选 B = `exploration, safety, creativity, connection, autonomy`

**代码位置**：`experiments/scripts/_sge_baseline.py:53`（DRIVES 常量）

**改造契约**：

```python
# Before（阶段 A）
DRIVES = ['connection', 'novelty', 'expression', 'safety', 'play']

# After（阶段 B）
# 1. DRIVES 改为可配置（从 yaml 读）
def _load_drives(config_path: str = None) -> list[str]:
    """从 yaml 读 DRIVES 清单；缺省用 SGE 默认 5 drives（候选 B）"""
    if config_path is None:
        return SGE_DEFAULT_DRIVES
    # else: yaml.safe_load + 校验

SGE_DEFAULT_DRIVES = ['exploration', 'safety', 'creativity', 'connection', 'autonomy']
DRIVES = SGE_DEFAULT_DRIVES  # 向后兼容（常量仍存在）

# 2. DriveMetabolism/Agent 接受 drives 参数
class DriveMetabolism:
    def __init__(self, drives: list[str] = None, ...):
        self.drives = drives or SGE_DEFAULT_DRIVES
        self.frustration = {d: 0.0 for d in self.drives}
        ...
```

**验证标准**：

1. 5 步最小循环跑通（与阶段 A 对比，drive_baseline keys 不同但行为相似）
2. `from _sge_baseline import DRIVES; assert DRIVES == ['exploration', 'safety', 'creativity', 'connection', 'autonomy']`
3. 多 seed 一致（seed=42 与 seed=7 都跑通）
4. schema 验证：`_load_drives(config_path='experiments/configs/m21_phase_b.yaml')` 返回 5 drives

**依赖**：无（独立子任务，可先做）

**预计工作量**：0.5 天

---

## B2：Value Layer 引入

**目标**：新增 6 个 values（safety / creativity / connection / autonomy / justice / compassion），scale [-1, 1]，独立于 drives。

**§5 决策**：Value scale = [-1, 1]（A 候选）

**代码位置**：`experiments/scripts/_sge_baseline.py`（新增 `ValueLayer` 类）

**改造契约**：

```python
# After（阶段 B 新增）
SGE_DEFAULT_VALUES = ['safety', 'creativity', 'connection', 'autonomy', 'justice', 'compassion']
N_VALUES = len(SGE_DEFAULT_VALUES)
VALUE_INIT_SEEDS = {v: 0.0 for v in SGE_DEFAULT_VALUES}  # 初始 0
VALUE_CLIP_MIN, VALUE_CLIP_MAX = -1.0, 1.0

class ValueLayer:
    """SGE Value Layer（独立于 DriveMetabolism）

    来源: 借鉴 EMA 公式 from AiBeing agent/evermemos_mixin.py:_apply_relationship_ema
    公式: value[d] = clip((1 - α) * value[d] + α * delta[d], -1, 1)
    参考: SGE-M21-AiBeing-Implementation-Mapping.md §2.3
    """

    def __init__(self, values: list[str] = None, alpha: float = 0.3):
        self.values = values or SGE_DEFAULT_VALUES
        self.alpha = alpha
        self.value_state = {v: VALUE_INIT_SEEDS.get(v, 0.0) for v in self.values}

    def update(self, delta_dict: dict) -> dict:
        """应用 Critic 输出的 value delta，返回新 value_state

        来源: EMA 公式（参考 evermemos_mixin._apply_relationship_ema）
        """
        for v in self.values:
            delta = delta_dict.get(v, 0.0)
            self.value_state[v] = max(
                VALUE_CLIP_MIN,
                min(VALUE_CLIP_MAX, (1 - self.alpha) * self.value_state[v] + self.alpha * delta)
            )
        return dict(self.value_state)

    def get(self) -> dict:
        return dict(self.value_state)

    def to_vec(self) -> list[float]:
        return [self.value_state[v] for v in self.values]
```

**验证标准**：

1. 构造 `ValueLayer()` → `value_state = {safety: 0.0, creativity: 0.0, ...}`
2. `update({'safety': 0.5})` → `value_state['safety'] = 0.15`（α=0.3 验证）
3. `update({'safety': 2.0})` → `value_state['safety'] = 1.0`（clip 验证）
4. `update({'safety': -2.0})` → `value_state['safety'] = -1.0`（clip 验证）
5. 多 seed 一致（seed 只影响 Agent，不影响 ValueLayer 初始化）

**依赖**：B1（schema 化先做）

**预计工作量**：1 天

---

## B3：Value EMA 实现

**目标**：把 ValueLayer 接入 Agent.step，每步应用 Critic delta 到 value_state。

**§5 决策**：α = 0.3（暂定，阶段 B 末段可调；M1.x 已用 0.3 baseline）

**代码位置**：`experiments/scripts/_sge_baseline.py:Agent.step`

**改造契约**：

```python
# After（阶段 B 改造 Agent）
class Agent:
    def __init__(self, seed, ..., value_layer: ValueLayer = None):
        ...
        self.value_layer = value_layer or ValueLayer()

    def step(self, context: dict, reward: float = 0.0, critic_value_delta: dict = None) -> dict:
        """一步完整循环（含 Value EMA 更新）

        Before: signals → learn → tick_drives
        After: signals → learn → tick_drives → value_layer.update(critic_value_delta)
        """
        signals = self.compute_signals(context)
        self.learn(signals, reward)
        self.tick_drives()
        if critic_value_delta:
            self.value_layer.update(critic_value_delta)
        return signals
```

**验证标准**：

1. 5 步循环 + 注入 `critic_value_delta={'safety': 0.5}` 每步
2. 5 步后 `value_state['safety'] > 0.1`（EMA 累积验证）
3. value_state 其他维度保持 0.0（无 delta 不变）
4. drive_state 行为与阶段 A 对比一致（Hebbian 学习不受 Value Layer 影响）

**依赖**：B2

**预计工作量**：0.5 天

---

## B4：Critic LLM 接入（stub → MiniMax-M3）

**目标**：把 `m21_setup.py` 的 `make_stub_context` 替换为真实 LLM 调用，输出 8D Critic context + 6D value delta。

**§5 决策**：LLM = MiniMax-M3（M1.x 已验证，stage B 沿用减少混淆变量）

**代码位置**：

- 新建 `experiments/scripts/_sge_critic.py`（Critic LLM 适配层）
- 修改 `experiments/scripts/m21_setup.py`（替换 stub context）

**改造契约**：

```python
# New file: _sge_critic.py
"""
SGE Critic LLM 适配层

来源: 借鉴 m11_smoke_test.py:call_critic（M1.1 已实现 MiniMax-M3 接入）
公式: N/A（LLM 输出）
参考: SGE-M21-AiBeing-Implementation-Mapping.md §2.1
"""

from typing import Optional
import os
import json

def critic_sense(
    event: dict,
    drives: dict,
    values: dict,
    config_path: str = "experiments/configs/m21_phase_b.yaml",
) -> tuple[dict, dict]:
    """
    调用 Critic LLM 感知事件，输出 8D context + 6D value delta

    Returns:
        context: 8D dict（user_emotion, topic_intimacy, ..., user_vulnerability）
        value_delta: 6D dict（safety, creativity, ...）

    来源: m11_smoke_test.py:call_critic（M1.1 已验证）
    """
    import litellm
    # ... (复用 m11_smoke_test.py 的 MiniMax-M3 配置)
    # 构造 critic prompt（含 event + drives + values）
    # 调用 LLM，解析 JSON 输出
    # 返回 (context, value_delta)

def make_event(stub_or_seed: int = 0) -> dict:
    """构造 stub event（阶段 B 用 stub event + 真实 Critic LLM）"""
    # 与 m21_setup.py 的 make_stub_context 类似
    ...
```

**验证标准**：

1. `critic_sense(stub_event, drives={}, values={})` 返回 8D context + 6D value_delta
2. 8D context keys 与 CONTEXT_FEATURES 前 8 个一致（user_emotion 等）
3. 6D value_delta keys 与 SGE_DEFAULT_VALUES 一致（safety 等）
4. value_delta 数值在 [-0.3, 0.3] 范围（M1.x baseline）
5. 5 步循环 + critic_sense 跑通（每次 LLM 调用 < 5 秒）
6. cost < $0.01（MiniMax-M3 5 步）

**依赖**：B1, B2, B3

**预计工作量**：1 天

---

## B5：Phase Transition 阈值扫描 [1.0, 3.0]

**目标**：把 PHASE_THRESHOLD 从硬编码 2.0 改为可配置，扫描 [1.0, 3.0] 找最优。

**§5 决策**：扫描 [1.0, 3.0]（B 候选）

**代码位置**：`experiments/scripts/_sge_baseline.py:100`（PHASE_THRESHOLD 常量）

**改造契约**：

```python
# After（阶段 B 改造）
# PHASE_THRESHOLD 不再是常量，而是 Agent.__init__ 参数
# 默认值仍为 2.0（与 AiBeing 一致），但可覆盖

class Agent:
    def __init__(self, seed, phase_threshold: float = 2.0, ...):
        ...
        self.phase_threshold = phase_threshold
        # 删除模块级 PHASE_THRESHOLD 常量（或保留为默认值的引用）
```

**验证标准**：

1. 5 步循环 × 3 阈值（1.0 / 2.0 / 3.0）跑通
2. 阈值 1.0：5 步内 phase transition 触发 ≥ 1 次
3. 阈值 3.0：5 步内 phase transition 不触发（frustration 未达）
4. 阈值 2.0：行为与阶段 A baseline 一致
5. 扫描脚本：`experiments/scripts/m21_phase_b_scan.py` 输出 3 阈值对比表

**依赖**：无（独立子任务，但需要 B1 完成 drives 替换）

**预计工作量**：0.5 天

---

## B6：Hawking gamma 调参（0.01/h）+ 辐射机制

**目标**：把 Hawking 衰减率从 0.001/h 调到 0.01/h，新增 Hawking 辐射机制（style_memory.py:209-255）。

**§5 决策**：γ = 0.01/h（B 候选，半衰期 ~3 天）

**代码位置**：`experiments/scripts/_sge_baseline.py`（新增 `HawkingDecay` 类 / 函数）

**改造契约**：

```python
# After（阶段 B 新增）
SGE_HAWKING_GAMMA = 0.01  # 替代 AiBeing 0.001

class HawkingDecay:
    """Hawking 辐射式记忆衰减（自有实现）

    来源: AiBeing engine/genome/style_memory.py:209-255
    公式: decay = exp(-γ * Δt_hours)
          weight *= decay
    参考: SGE-M21-AiBeing-Implementation-Mapping.md §2.7
    """

    def __init__(self, gamma: float = SGE_HAWKING_GAMMA):
        self.gamma = gamma
        self.memory = []  # list of {timestamp, weight, content}

    def insert(self, content: dict, weight: float = 1.0, now: float = None):
        """插入新记忆"""
        ...

    def tick(self, now: float = None):
        """每步调用，按 Hawking 衰减所有记忆"""
        # 对每个记忆: weight *= exp(-γ * Δt_hours)
        # 删除 weight < threshold 的记忆
        ...

    def retrieve(self, query: dict, k: int = 5) -> list:
        """KNN 检索 + Hawking 衰减（可选）"""
        ...
```

**验证标准**：

1. 插入 10 个记忆 + tick 100 次 → 部分记忆 weight < threshold 被删除
2. 半衰期验证：插入 1 个记忆 + tick 70 次（模拟 70h ≈ 3 天）→ weight ≈ 0.5
3. 5 步循环 + Hawking tick 跑通
4. 阶段 A baseline 无 Hawking 也能跑通（向后兼容，Hawking 是可选组件）

**依赖**：无（独立子任务）

**预计工作量**：1 天

---

## B7：Crystallize 阈值（维度归一化 0.25/sqrt(N)）

**目标**：把 Crystallize 距离阈值从固定 0.25 改为维度归一化 0.25/sqrt(N)，新增结晶机制。

**§5 决策**：0.25/sqrt(N)（B 候选）

**代码位置**：`experiments/scripts/_sge_baseline.py`（新增 `crystallize_threshold` 函数 + `crystallize` 机制）

**改造契约**：

```python
# After（阶段 B 新增）
import math

def crystallize_threshold(n_dims: int, base: float = 0.25) -> float:
    """维度归一化结晶阈值

    来源: 借鉴映射 §2.6
    公式: threshold = base / sqrt(N)
    """
    return base / math.sqrt(n_dims)

class MemoryCrystallizer:
    """记忆结晶机制

    来源: AiBeing engine/genome/style_memory.py:280-310
    公式: distance = L2(query, memory)
          if distance < threshold: merge; else: create new
    """

    def __init__(self, n_dims: int, base: float = 0.25):
        self.threshold = crystallize_threshold(n_dims, base)
        self.memories = []  # list of {vec, weight, count}

    def insert_or_merge(self, vec: list[float], weight: float = 1.0):
        """插入或合并"""
        for mem in self.memories:
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(vec, mem['vec'])))
            if dist < self.threshold:
                # merge: 加权平均
                ...
                return 'merged'
        # else: create new
        self.memories.append({'vec': vec, 'weight': weight, 'count': 1})
        return 'created'
```

**验证标准**：

1. N=5（drives）：threshold = 0.25/sqrt(5) ≈ 0.112
2. N=8（signals）：threshold = 0.25/sqrt(8) ≈ 0.088
3. N=12（context）：threshold = 0.25/sqrt(12) ≈ 0.072
4. 插入相似 vec（距离 < threshold）→ 'merged'；不同 vec → 'created'
5. 5 步循环 + 多次 insert_or_merge 跑通

**依赖**：B1（drives 决定 N）

**预计工作量**：1 天

---

# 2. 子任务依赖图

```
B1 (drives 替换 + schema) ──→ B2 (Value Layer 引入) ──→ B3 (Value EMA 实现) ──→ B4 (Critic LLM 接入)
                                                            │
                                                            └──→ B5 (Phase 阈值扫描)
                                                            │
B6 (Hawking) ──→ 独立                                    │
                                                            │
B7 (Crystallize) ──→ B1 (drives 决定 N)                  │
                                                            │
                                                            └──→ 集成测试（阶段 B 末段）
```

**关键路径**：B1 → B2 → B3 → B4 → 集成测试（约 3.5 天）

**可并行**：B5 / B6 / B7 与关键路径并行（约 2.5 天）

**总时长**：3.5 天（关键路径，含 buffer）

---

# 3. 验收标准（阶段 B 完成时）

| 项 | 标准 | 验证方式 |
|----|------|---------|
| 1. drives 替换 | DRIVES = `['exploration', 'safety', 'creativity', 'connection', 'autonomy']` | `from _sge_baseline import DRIVES` |
| 2. schema 化 | DRIVES 可从 yaml 读取 | `_load_drives(config_path='experiments/configs/m21_phase_b.yaml')` |
| 3. Value Layer | 6 values 初始化为 0.0，scale [-1, 1] | `ValueLayer()` 构造 + update() clip 验证 |
| 4. Value EMA | α=0.3 累积验证 | 5 步循环 + critic_value_delta 注入 |
| 5. Critic LLM | 真实 MiniMax-M3 调用，输出 8D context + 6D value delta | `critic_sense()` 返回 keys 验证 |
| 6. Phase 阈值扫描 | [1.0, 2.0, 3.0] 三阈值都跑通 | `m21_phase_b_scan.py` 输出对比表 |
| 7. Hawking | 半衰期 ~3 天（0.01/h） | 插入 + tick 70 次 → weight ≈ 0.5 |
| 8. Crystallize | 维度归一化 0.25/sqrt(N) | N=5/8/12 三档 threshold 验证 |
| 9. 集成测试 | 5 步循环 + 全部新组件跑通 | `m21_phase_b.py` PASS |
| 10. 多 seed 一致 | seed=42 / 7 / 123 都跑通 | `m21_phase_b.py --seeds 42 7 123` |
| 11. 回归测试 | 阶段 A baseline 仍能跑通（向后兼容） | `m21_setup.py` PASS |
| 12. 文档 | `experiments/M21_PHASE_B_REPORT.md` 完成 | 文件存在 |

---

# 4. 风险与开放问题

| 风险 | 影响 | 缓解 |
|------|------|------|
| B4 Critic LLM 接入成本 | 5 步 × MiniMax-M3 ≈ $0.005（低），但反复扫描可能累积 | 扫描用 stub，只在最终验证用真实 LLM |
| B3 Value EMA α 参数 | α=0.3 是 M1.x baseline，SGE 6D value 可能需调 | 阶段 B 末段做 α 扫描 [0.1, 0.5] |
| B6 Hawking γ 衰减 | γ=0.01/h 是 Closeout §5 默认值，未经验证 | 阶段 D 长 epoch 验证 |
| B7 Crystallize 阈值 | 0.25/sqrt(N) 是 SGE 化的 magic number | 阶段 D 扫描 [0.15, 0.35] 验证 |
| B5 Phase 阈值扫描 | [1.0, 3.0] 范围可能不够 | 阶段 D 视情况扩展 |
| 引入 Value Layer 可能破坏 drives 联动 | drives ↔ values 是双轨独立，但 Reward 同时影响两者，可能出现"反同步" | 阶段 B 报告需明确双轨独立性 |
| 阶段 A baseline 回归 | schema 化改造可能破坏向后兼容 | B1 实施时保留 DRIVES 常量作为 fallback |

---

# 5. 与现有文档的关联

| 文档 | 影响 |
|------|------|
| [SGE-Phase0-Closeout.md](../sge-core/SGE-Phase0-Closeout.md) | §5 决策已填写，本文件是其实施映射 |
| [SGE-M21-AiBeing-Implementation-Mapping.md](./SGE-M21-AiBeing-Implementation-Mapping.md) | §五 阶段 B/C 分解，§二 逐机制公式 |
| [experiments/M21_BASELINE_SETUP_REPORT.md](../../experiments/M21_BASELINE_SETUP_REPORT.md) | §6 下一步建议（阶段 B/C/D 范围）|
| [PRD.md §FR-3, FR-4](../../PRD.md) | Value Layer 功能需求 + Reflection Layer |
| [SGE-Key-Insights.md §洞察 24, 26](../../SGE-Key-Insights.md) | 怀特海动在/合生 + 6 维度非对称响应 |
| [ROADMAP.md §M2.1](../../ROADMAP.md) | 完整 SGE 架构里程碑（本文件是其详细实施映射）|
| [CHANGELOG.md](../../CHANGELOG.md) | 阶段 B 完成时新增条目 |

---

# 6. 时间估算

| 子任务 | 工作量 | 依赖 |
|--------|-------|------|
| B1: drives 替换 + schema | 0.5 天 | — |
| B2: Value Layer 引入 | 1 天 | B1 |
| B3: Value EMA 实现 | 0.5 天 | B2 |
| B4: Critic LLM 接入 | 1 天 | B1, B2, B3 |
| B5: Phase 阈值扫描 | 0.5 天 | B1 |
| B6: Hawking 机制 | 1 天 | — |
| B7: Crystallize 机制 | 1 天 | B1 |
| 集成测试 + 多 seed 验证 | 0.5 天 | B1-B7 |
| 报告写作 | 0.5 天 | 全部 |
| **总计** | **6-7 天** | — |

**关键路径**：B1 → B2 → B3 → B4 → 集成测试 ≈ 3.5 天

---

# 7. 实施步骤建议（按依赖顺序）

1. **第 1-2 天**（关键路径开始）：
   - B1: drives 替换 + schema 化
   - B6: Hawking 机制（独立，可与 B1 并行）
2. **第 2-3 天**：
   - B2: Value Layer 引入
   - B7: Crystallize 机制（依赖 B1，可与 B2 并行）
3. **第 3-4 天**：
   - B3: Value EMA 实现
   - B5: Phase 阈值扫描（独立，可与 B3 并行）
4. **第 4-5 天**：
   - B4: Critic LLM 接入
5. **第 5-6 天**：
   - 集成测试 + 多 seed 验证
6. **第 6-7 天**：
   - 报告写作 + CHANGELOG 更新 + commit + push

---

# 8. 一句话总结

> **M2.1 阶段 B 的本质是"借鉴映射 → SGE 自有"的工程实施**——把 §5 决策（候选 B / [-1, 1] / 0.01/h / 0.25/sqrt(N) / MiniMax-M3）映射为 7 个可独立验证的子任务，关键路径 B1→B2→B3→B4 约 3.5 天完成，集成验证 0.5 天，总计 6-7 天进入 M2.1 阶段 C（Identity + Narrative Layer）。

---

# 附录 A：版本与变更

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-19 | v0.1 | 初稿（Bisen 委托 Claude 基于 §5 决策 + 映射文档 §五 起草）|

---

**创建日期**：2026-06-19
**最后更新**：2026-06-19
**维护者**：Bisen & Claude
**状态**：📋 待 Bisen 评审
