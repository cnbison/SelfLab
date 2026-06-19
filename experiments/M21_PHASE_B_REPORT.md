# M2.1 阶段 B — SGE 化改造实验报告

> **目的**：记录 M2.1 阶段 B 实施结果——7 个子任务（B1-B7）全部完成，集成测试通过。
> **创建日期**：2026-06-19
> **对应 CHANGELOG**：[1.17.0]（待 commit 后填入）
> **状态**：✅ PASS — 7/7 子任务完成，集成验证通过

---

# 1. 概述

## 1.1 背景

M2.1 阶段 A（基线冒烟测试）已在 [1.10.0/1.11.0] 完成。阶段 B 是 **SGE 化改造**——把 AiBeing 原生参数和机制改造为 SGE 化的版本（基于 [SGE-Phase0-Closeout.md §5](../../research/sge-core/SGE-Phase0-Closeout.md) 的 6 决策点）。

## 1.2 范围

按 [SGE-M21-Phase-B-Implementation-Plan.md](../../research/sge-feasibility/SGE-M21-Phase-B-Implementation-Plan.md) 实施 7 个子任务：

| ID | 子任务 | §5 决策 | 状态 |
|----|--------|--------|------|
| B1 | drives 替换（候选 B）+ schema 化 | `exploration, safety, creativity, connection, autonomy` + yaml 加载 | ✅ |
| B2 | Value Layer 引入（独立于 drives）| 6 values，scale [-1, 1] | ✅ |
| B3 | Value EMA 实现（α=0.3）| α=0.3（M1.x baseline）| ✅ |
| B4 | Critic LLM 接入（MiniMax-M3 适配层）| MiniMax-M3（M1.x 沿用）| ✅ |
| B5 | Phase Transition 阈值扫描 [1.0, 3.0] | 扫描 [1.0, 3.0]，默认 2.0 | ✅ |
| B6 | Hawking 辐射机制（γ=0.01/h）| γ=0.01/h（半衰期 ~3 天）| ✅ |
| B7 | Crystallize 维度归一化（0.25/sqrt(N)）| 0.25/sqrt(N) | ✅ |

## 1.3 文件位置

| 文件 | 用途 | 状态 |
|------|------|------|
| `experiments/scripts/_sge_baseline.py` | SGE 自有核心实现（阶段 A + 阶段 B 全部新增）| 修改 |
| `experiments/scripts/_sge_critic.py` | **新增** — Critic LLM 适配层（stub + 真实 MiniMax-M3）| 新增 |
| `experiments/scripts/m21_setup.py` | 阶段 A baseline（向后兼容）| 不变 |
| `experiments/scripts/m21_phase_b.py` | **新增** — 阶段 B 集成测试脚本 | 新增 |
| `experiments/configs/m21_baseline.yaml` | 阶段 A baseline 配置 | 不变 |
| `experiments/configs/m21_phase_b.yaml` | **新增** — 阶段 B 配置（drives/values/phase/hawking/crystallize）| 新增 |
| `experiments/output/m21_phase_b/` | 阶段 B 输出快照 | 新增 |
| `experiments/M21_PHASE_B_REPORT.md` | **本报告** | 新增 |

---

# 2. 子任务实施细节

## B1：drives 替换（候选 B）+ schema 化

**改造位置**：`experiments/scripts/_sge_baseline.py`

**改造内容**：
1. 模块级常量：`DRIVES = ['connection', 'novelty', 'expression', 'safety', 'play']` → `SGE_DEFAULT_DRIVES = ['exploration', 'safety', 'creativity', 'connection', 'autonomy']`
2. 新增 `_load_drives(config_path)` 函数：从 yaml 加载 DRIVES 清单
3. `DriveMetabolism.__init__` 新增 `drives` 和 `hunger_rates` 参数（schema 化）
4. `Agent.__init__` 新增 `drives` 参数；`INPUT_SIZE` 从模块级常量改为 `self.INPUT_SIZE`（跟随 n_drives）
5. 模块级 `INPUT_SIZE` 常量删除（已被 `self.INPUT_SIZE` 替代）

**架构层接口**（满足原则 1）：
```python
# 阶段 B 入口（为 Phase 3 profile 化铺路）
drives = _load_drives('experiments/configs/m21_phase_b.yaml')
# → ['exploration', 'safety', 'creativity', 'connection', 'autonomy']
```

**验证**：
- ✅ 5 步循环跑通（阶段 A 回归测试通过）
- ✅ 多 seed 一致（seed=42 / 7 / 123）
- ✅ schema 验证：`_load_drives(config_path)` 返回 5 drives
- ✅ 向后兼容：`Agent(seed=42)` 默认使用 `SGE_DEFAULT_DRIVES`

---

## B2：Value Layer 引入

**改造位置**：`experiments/scripts/_sge_baseline.py` 末尾新增

**新增内容**：
```python
SGE_DEFAULT_VALUES = ['safety', 'creativity', 'connection', 'autonomy', 'justice', 'compassion']
N_VALUES = len(SGE_DEFAULT_VALUES)
VALUE_CLIP_MIN, VALUE_CLIP_MAX = -1.0, 1.0

class ValueLayer:
    def __init__(self, values=None, alpha=0.3, init_seed=None): ...
    def update(self, delta_dict): ...     # EMA: value[v] = (1-α)*value[v] + α*delta[v], clip to [-1, 1]
    def get(self): ...                    # 返回当前 value_state 副本
    def to_vec(self): ...                 # 按 values 顺序转为 list[float]
    def magnitude(self): ...              # L2 范数（人格分化度量）
```

**单元测试 12/12 PASS**：
- 默认初始化（6D values，0.0）
- 单步 update α=0.3 验证
- Clip 到 [-1, 1]
- 100 步累积到饱和
- 反向累积
- EMA 衰减行为（无 delta 时向 0 衰减）
- magnitude L2 范数
- to_vec 按顺序

---

## B3：Value EMA 实现

**改造位置**：`experiments/scripts/_sge_baseline.py:Agent.step`

**改造内容**：
```python
class Agent:
    def __init__(self, ..., value_layer=None):
        self.value_layer = value_layer  # None 时 step 不更新 values

    def step(self, context, reward=0.0, critic_value_delta=None):
        signals = self.compute_signals(context)
        self.learn(signals, reward)
        self.tick_drives()
        if self.value_layer is not None and critic_value_delta is not None:
            self.value_layer.update(critic_value_delta)
        return signals
```

**集成测试 6/6 PASS**：
- Agent 接受 value_layer 参数
- step() 无 delta 时 value_state 保持
- step() 有 delta 时正确累积（α=0.3 EMA）
- 多 value 同时更新（每个独立）
- drive_state 与 value_layer 完全独立（Hebbian vs EMA 平行机制）

---

## B4：Critic LLM 接入（MiniMax-M3 适配层）

**新增文件**：`experiments/scripts/_sge_critic.py`

**架构**：
- `stub_critic_sense(event, drives, values, seed)` → 不调用 LLM，返回 stub 8D context + 6D value_delta
- `real_critic_sense(event, drives, values, ...)` → 调用 MiniMax-M3，解析 JSON 输出
- `critic_sense(...)` → 统一入口（`use_real_llm=True/False`）

**输出 Schema（SSOT）**：
```python
CRITIC_CONTEXT_FIELDS = [user_emotion, topic_intimacy, time_of_day, conversation_depth,
                          user_engagement, conflict_level, novelty_level, user_vulnerability]
VALUE_DELTA_FIELDS = [safety, creativity, connection, autonomy, justice, compassion]
```

**单元测试 11/11 PASS**：
- Schema 完整性（8D context + 6D value_delta）
- stub_critic_sense 返回维度
- context 范围（user_emotion [-1, 1], 其他 [0, 1]）
- value_delta 范围 [-1, 1]
- 事件类型影响（success → +emotion, risk → -emotion）
- intensity 缩放
- 统一入口
- 异常处理（无 API key）

**默认模式**：stub（避免 API 成本）。M2.2/M2.3 阶段才用真实 LLM。

---

## B5：Phase Transition 阈值扫描 [1.0, 3.0]

**改造位置**：`Agent.__init__(phase_threshold)` 参数化 + `experiments/scripts/m21_phase_b.py:phase_threshold_scan()`

**扫描结果**：

| threshold | phase_xition_count | 说明 |
|-----------|---------------------|------|
| 1.0 | 0/5 | 5 步内 frustration 累积 < 1.0（短时间未触发）|
| 2.0 | 0/5 | 5 步内 frustration 累积 < 2.0（默认阈值）|
| 3.0 | 0/5 | 5 步内 frustration 累积 < 3.0（高阈值）|

**观察**：5 步太短，phase transition 不会触发（frustration 单步累积仅 0.05-0.1）。需要更长 epoch（M2.2 1000 epoch）才能观察阈值影响。

**实施路径**：
- ✅ Agent 接受 phase_threshold 参数
- ✅ 默认 2.0（与 AiBeing 一致）
- ✅ 扫描脚本集成在 m21_phase_b.py

---

## B6：Hawking 辐射机制

**新增**：`HawkingDecay` 类（gamma=0.01/h，半衰期 ~3 天）

**接口**：
```python
class HawkingDecay:
    def __init__(self, gamma=SGE_HAWKING_GAMMA, remove_threshold=1e-4, clock=None): ...
    def insert(self, content, weight=1.0, now=None): ...
    def tick(self, now=None) -> int: ...  # 返回删除的记忆数
    def retrieve(self, k=5) -> list: ...  # 按权重降序
```

**单元测试 7/7 PASS**：
- 默认初始化
- 插入/检索
- 半衰期验证（γ=0.01/h, 70h 后 weight=0.4966）
- 删除阈值（1000h 后删除低权重记忆）
- retrieve 按权重排序
- 短时间 tick 不衰减
- 多记忆混合

**集成状态**：HawkingDecay 类已实现并验证。**未集成到 Agent.step**（阶段 D 才用，因为 Hawking 需要记忆层 + 上下文压缩，阶段 B 仅做单元验证）。

---

## B7：Crystallize 维度归一化

**新增**：`MemoryCrystallizer` 类 + `crystallize_threshold(n_dims)` 函数

**公式**：`threshold = 0.25 / sqrt(N)`（维度归一化）

**验证结果**：

| N | 阈值 | 用途 |
|---|------|------|
| 5（drives） | 0.1118 | 阶段 B drives 维度 |
| 8（signals）| 0.0884 | 信号空间 |
| 12（context）| 0.0722 | 上下文空间 |
| 21（事件感知向量，预留）| 0.0546 | M2.3 预留 |

**单元测试 5/5 PASS**：
- 维度归一化阈值计算
- N=5 合并/创建行为
- N=12 合并行为
- 加权平均（count 累积）
- N=21 阈值

**集成状态**：MemoryCrystallizer 类已实现并验证。**未集成到 Agent.step**（阶段 D 才用，因为 Crystallize 是记忆层筛选门，需要完整记忆架构）。

---

# 3. 集成测试结果

## 3.1 主测试：阶段 B 5 步循环（seed=42）

```
[step 0] event=success       ctx.emotion=+0.69 value_safety=+0.020 value_comp=+0.001 phase_x=False
[step 1] event=failure       ctx.emotion=-0.46 value_safety=-0.007 value_comp=-0.003 phase_x=False
[step 2] event=relationship  ctx.emotion=+0.47 value_safety=-0.001 value_comp=+0.033 phase_x=False
[step 3] event=exploration   ctx.emotion=+0.49 value_safety=-0.004 value_comp=+0.031 phase_x=False
[step 4] event=risk          ctx.emotion=-0.67 value_safety=-0.064 value_comp=+0.019 phase_x=False
```

**观察**：
- ✅ value_state 正确累积（safety 从 0 → +0.020 → -0.007 → -0.064）
- ✅ compassion 累积符合预期（relationship 事件 → +0.033）
- ✅ phase transition 未触发（5 步内 frustration 累积 < 2.0）

## 3.2 多 Seed 一致性验证

| seed | value_magnitude | phase_xition_count |
|------|-----------------|---------------------|
| 42 | 0.0803 | 0 |
| 7 | 0.0910 | 0 |
| 123 | 0.0773 | 0 |

✅ 不同 seed 的 value_magnitude 有差异（randomness 工作正常）

## 3.3 阶段 A baseline 回归验证

- ✅ 默认 drives = SGE_DEFAULT_DRIVES（向后兼容）
- ✅ 5 步循环跑通（drive_state 变化 0.6853）
- ✅ temperature = 0.0830（与阶段 A baseline 一致）

## 3.4 Phase 阈值扫描

| threshold | phase_xition_count |
|-----------|---------------------|
| 1.0 | 0/5 |
| 2.0 | 0/5 |
| 3.0 | 0/5 |

⚠ 5 步太短无法观察阈值影响。需要更长 epoch。

---

# 4. 验收标准完成度

| # | 标准 | 状态 |
|---|------|------|
| 1 | drives = SGE 候选 B 5 drives | ✅ |
| 2 | schema 化（DRIVES 可从 yaml 读取）| ✅ |
| 3 | Value Layer（6 values，scale [-1, 1]）| ✅ |
| 4 | Value EMA（α=0.3 累积验证）| ✅ |
| 5 | Critic LLM 接入（stub + 真实 LLM 适配层）| ✅ |
| 6 | Phase 阈值扫描 [1.0, 3.0] | ✅（5 步太短，扫描脚本就绪）|
| 7 | Hawking 半衰期 ~3 天 | ✅（单元测试）|
| 8 | Crystallize 维度归一化 | ✅（单元测试）|
| 9 | 集成测试 5 步循环跑通 | ✅ |
| 10 | 多 seed 一致（42/7/123）| ✅ |
| 11 | 阶段 A baseline 回归 | ✅ |
| 12 | 实验报告 | ✅（本文件）|

**12/12 验收标准完成**

---

# 5. 关键发现

1. **drives schema 化是基础设施**——`_load_drives()` + Agent/DriveMetabolism 参数化为 Phase 3 产品化（多场景 profile 化）铺路。

2. **Value Layer 与 DriveMetabolism 完全独立**——Hebbian 学习（drive_state）和 EMA 演化（value_state）平行不交叉，对应 SGE 哲学的"暗知识（Hebbian）+ 显性知识（Value Layer）+ 拱桥（Reflection）"三方对应。

3. **stub Critic 模式有效**——`_sge_critic.py` 的 stub_critic_sense 提供与 AiBeing EMA 兼容的事件响应模式（success → +safety/creativity/connection, risk → -safety/autonomy），不需要 LLM API 即可做机制验证。

4. **Phase 阈值需要长 epoch 才能观察**——5 步循环 frustration 累积 < 0.1，远低于任何阈值。M2.2 的 1000 epoch 实验才能给出阈值最优值。

5. **Hawking/Crystallize 是"机制就绪，集成延后"**——两个类都已实现并通过单元测试，但未集成到 Agent.step（阶段 D 集成，因为需要记忆层完整架构）。

---

# 6. 已知风险与开放问题

| 风险 | 影响 | 缓解 |
|------|------|------|
| Hawking γ=0.01/h 未经验证 | 5 步循环无法观察 | M2.2 1000 epoch 验证 |
| Crystallize threshold 0.25/sqrt(N) 是 magic number | 阈值可能需调 | M2.2 多 seed × 长 epoch 验证 |
| Value EMA α=0.3 是 M1.x baseline | SGE 6D value 可能需调 | M2.2 α 扫描 [0.1, 0.5] |
| Phase threshold 扫描需长 epoch | 阶段 B 无法给出最优 | M2.2 长 epoch 扫描 |
| Critic 真实 LLM 未在阶段 B 调用 | M2.1 阶段 B 不验证 LLM-agnostic | M2.2/M2.3 才用真实 LLM |
| B6/B7 未集成到 Agent.step | 主循环中只用了 B1-B5 | 阶段 D 才集成 |

---

# 7. 下一步

## 7.1 立即行动（已完成）

- ✅ 7 个子任务全部完成
- ✅ 集成测试通过
- ✅ 阶段 A 回归验证通过
- ✅ 多 seed 一致性验证通过
- ✅ 实验报告（本文件）

## 7.2 阶段 D（M2.1 阶段 D）

- **B6/B7 集成**：HawkingDecay + MemoryCrystallizer 接入 Agent.step
- **完整 12 步双 LLM 编排**：实现 Critic + Actor 编排
- **100 epoch 冒烟测试**：长 epoch 验证阶段 B 全部机制
- **3 seed × 100 epoch**：多 seed × 长 epoch 验证 Phase 阈值/Hawking γ/Crystallize 阈值的最优值

## 7.3 阶段 C（M2.1 阶段 C）

- **Identity Layer 完整实现**（FR-5）
- **Narrative Builder MVP**（FR-6）
- **Event Generator**（外部事件源）
- **Value Conflict Generator**（基于 value_state 生成针对性事件）

---

# 8. 关联文档

- [SGE-M21-Phase-B-Implementation-Plan.md](../../research/sge-feasibility/SGE-M21-Phase-B-Implementation-Plan.md) — 实施计划（7 子任务详细契约）
- [SGE-M21-AiBeing-Implementation-Mapping.md](../../research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md) — 借鉴映射（§五 阶段 B/C/D 分解 + 逐机制公式）
- [SGE-Phase0-Closeout.md](../../research/sge-core/SGE-Phase0-Closeout.md) — §5 决策（基于三原则推导的 6 决策点 + 2 元问题）
- [experiments/M21_BASELINE_SETUP_REPORT.md](../experiments/M21_BASELINE_SETUP_REPORT.md) — 阶段 A 报告
- [ROADMAP.md §M2.1](../../ROADMAP.md) — 完整 SGE 架构里程碑

---

# 9. 归档策略

- 本报告保留在 `experiments/`（与 M21_BASELINE_SETUP_REPORT.md 并列）
- 输出快照保留在 `experiments/output/m21_phase_b/`（已 .gitignore 排除体积大的 state 数据）
- `_sge_baseline.py` 和 `_sge_critic.py` 是 SGE 自有实现，**不属于"实验代码约定"的一次性代码**——它们是 SGE 借鉴映射的实施层，会持续演进到阶段 C/D
- m21_phase_b.py 是一次性集成测试脚本（阶段 D 完成时归档）

---

**创建日期**：2026-06-19
**维护者**：Bisen & Claude
**状态**：✅ 7/7 子任务完成，12/12 验收标准 PASS
