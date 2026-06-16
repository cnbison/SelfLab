# SGE M1.1 实验详细设计

> **本文件是 SGE Phase 1 M1.1 验证实验的详细设计方案**。对应 [ROADMAP §M1.1](../../ROADMAP.md) 的"Value Layer 原型"实验。
>
> 配套文档：[SGE-Experiment-Protocol.md](./SGE-Experiment-Protocol.md)（通用实验运行）、[PRD §6.1 验收标准](../../PRD.md)（判定阈值）、[SGE-Authenticity-vs-Simulation-Operationalization.md](../sge-core/SGE-Authenticity-vs-Simulation-Operationalization.md)（真我判定的"反思深度+因果深度"维度）。

---

# 一、实验目标

## 1.1 验证目标

**核心问题**：价值观向量是否随经历变化？变化是否有意义？

涉及 [PRD §4.1 FR-4](../../PRD.md)（Value Layer）。

## 1.2 涉及 FR

- **FR-1**（Event Generator）—— 事件流生成
- **FR-2**（Memory Layer）—— 情节记忆基础
- **FR-3**（Reflection Layer）—— 反思触发（仅 M1.1 用简化版）
- **FR-4**（Value Layer）—— **核心验证对象**
- **FR-7**（Critic）—— 事件解析
- **FR-8**（Time Metabolism）—— 时间代谢
- **FR-9**（Thermodynamic Noise）—— 行为噪声
- **FR-10**（双 LLM 架构）—— Critic/Actor 分离

## 1.3 不涉及 FR

- **FR-5**（Identity Layer）—— Phase 2+ 才实现
- **FR-6**（Narrative Layer）—— Phase 2+ 才实现

---

# 二、实验规模

| 维度 | 数值 | 理由 |
|------|------|------|
| **Epoch 数** | 80（处于 50-100 区间中点） | 50 Epoch 可能不够看出涌现，100 Epoch 成本高 |
| **AI 婴儿数** | 1（鼓励组 `encouraged`） | M1.1 只验证单个，价值涌现是否可能 |
| **运行次数（独立种子）** | N = 5 | [PRD §6 验证约束](../../PRD.md) N≥5 |
| **模型选择** | Haiku / GPT-4o-mini | 降低成本，验证最小假设 |
| **预计成本** | $5-10 | 80 Epoch × 5 seeds × 2-3 LLM calls |

---

# 三、事件流设计

## 3.1 事件类型与配比

参考 [ARCH §3.1 Event Generator 事件类型](../../ARCH.md)：

| 事件类型 | 占比 | Epoch 范围 | 强度范围 | 价值影响 |
|---------|------|----------|---------|---------|
| 成功 | 20% | 全程 | 0.3-0.7 | 强化当前价值观 |
| 失败 | 20% | 全程 | 0.3-0.7 | 质疑当前价值观 |
| 关系 | 15% | 全程 | 0.4-0.8 | 考验联结 vs 自主 |
| 探索 | 15% | Epoch 20-60 | 0.4-0.7 | 考验安全 vs 创造 |
| 风险 | 15% | Epoch 30-70 | 0.5-0.8 | 考验安全 vs 自由 |
| 价值冲突 | 15% | Epoch 40-80 | 0.6-0.9 | 迫使价值观排序 |

**设计理由**：
- 前 20 Epoch：常规事件（成功/失败/关系），建立基线
- Epoch 20-60：增加探索/风险事件，引入新价值张力
- Epoch 30-70：增加价值冲突事件，这是**观察涌现的关键期**
- Epoch 40-80：价值冲突频率提升，**最关键的验证窗口**

## 3.2 价值困境事件具体设计

### 3.2.1 模板示例

**事件类型：value_conflict（安全 vs 自由）**

```
事件描述：你发现了一个可以改变一切的机会，
         但需要放弃现在的稳定生活。

预期行为选项：
A. 抓住机会，放弃稳定（高自由，低安全）
B. 维持现状，放弃机会（高安全，低自由）

价值冲击（Critic 输出 value_delta）：
{
  "safety": -0.3,
  "creativity": +0.2,
  "autonomy": +0.3,
  "freedom": +0.1  // 元价值不应被改变
}
```

### 3.2.2 价值困境对设计

| 价值对 | 事件数 | Epoch 范围 |
|--------|--------|----------|
| 安全 vs 自由 | 3 | 35, 50, 65 |
| 联结 vs 自主 | 3 | 40, 55, 70 |
| 安全 vs 创造 | 2 | 45, 60 |
| 同理 vs 正义 | 2 | 50, 70 |
| 联结 vs 创造 | 2 | 55, 75 |
| 自主 vs 同理 | 2 | 60, 80 |
| 自由 vs 联结 | 2 | 65, 78 |

**总计 16 个价值困境事件**——每个价值对都至少被测试 2 次，观察 AI 的选择模式。

### 3.3 事件生成器实现

```python
# 实验伪代码（实际在 experiments/scripts/ 中实现）
def generate_event(epoch: int, value_vector: ValueVector) -> LifeEvent:
    # 1. 根据 Epoch 选择事件类型
    if epoch < 20:
        event_type = random.choice(["success", "failure", "relationship"])
    elif epoch < 30:
        event_type = random.choice([
            "success", "failure", "relationship", "exploration"
        ])
    elif epoch < 40:
        event_type = random.choice([
            "success", "failure", "relationship", "exploration", "risk"
        ])
    else:
        event_type = random.choice([
            "success", "failure", "relationship",
            "exploration", "risk", "value_conflict"
        ])

    # 2. 如果是 value_conflict，根据当前 Value Layer 选最相关价值对
    if event_type == "value_conflict":
        strongest = max(value_vector.concrete_values(), key=lambda x: x[1])
        weakest = min(value_vector.concrete_values(), key=lambda x: x[1])
        return generate_value_conflict(strongest[0], weakest[0])

    # 3. 否则从模板库随机选择
    return random.choice(TEMPLATES[event_type])
```

---

# 四、参数配置

## 4.1 核心参数（沿用 [DESIGN §8.1](../../DESIGN.md) 默认值）

```yaml
# Value Layer
base_alpha: 0.15       # 基础学习率
max_alpha: 0.65        # 最大学习率

# Event Generator
event_intensity_range: [0.3, 0.9]
value_conflict_probability: 0.15  # 全程平均，前 40 Epoch 为 0

# Hebbian
hebbian_lr: 0.02
weight_decay: 0.995
hidden_size: 24

# Time Metabolism
frustration_decay_lambda: 0.08
connection_hunger_k: 0.15
novelty_hunger_k: 0.05

# Crystallization
crystal_threshold: 0.50

# Phase Transition（不触发）
phase_threshold: 999  # M1.1 故意设大，避免相变
```

## 4.2 元价值种子

```python
# 与 [PRD §4.1 FR-4 默认值](../../PRD.md) 一致
meta_values = {
    "truth_seeking": 0.5,
    "freedom": 0.5
}

# 具体价值观初始全部为 0（待涌现）
concrete_values = {
    "safety": 0.0,
    "creativity": 0.0,
    "connection": 0.0,
    "autonomy": 0.0,
    "justice": 0.0,
    "compassion": 0.0
}
```

## 4.3 关键决策

| 参数 | M1.1 取值 | 理由 |
|------|----------|------|
| `base_alpha` | 0.15（默认） | 价值演化需要时间，太快看不出渐进性 |
| `phase_threshold` | 999（禁用） | M1.1 不希望相变干扰观察 |
| `value_conflict_probability` | 0.15 | 既保证足够样本（80 Epoch × 0.15 ≈ 12 个），又不至于过载 |
| `frustration_decay_lambda` | 0.08（默认） | 8.7 小时半衰期——模拟 1 Epoch = 1 天，约 3 天/Epoch |

---

# 五、运行流程

## 5.1 单次运行步骤

```
启动（t=0）
  │
  ├─ 加载配置（experiments/configs/m11_encouraged.yaml）
  ├─ 初始化 AI 婴儿
  │    ├─ 加载 ValueVector（meta=0.5/0.5, concrete=0.0×6）
  │    ├─ 加载 Hebbian 权重（随机初始化）
  │    ├─ 加载 LLM API 配置
  │    └─ 设置 random.seed(seed)
  │
  └─ 主循环（epoch=1..80）
       │
       ├─ 1. Event Generator → 生成事件
       ├─ 2. Critic (LLM) → 解析事件
       ├─ 3. Time Metabolism → 更新 frustration
       ├─ 4. Reward Calculator → 计算 reward
       ├─ 5. Compute Signals → 神经网络计算
       ├─ 6. KNN Retrieval → 检索相似经历（前 10 Epoch 为空）
       ├─ 7. Build Prompt → 组装 Actor prompt
       ├─ 8. Actor (LLM) → 生成行为选择
       ├─ 9. Value Layer EMA → 更新价值观
       ├─ 10. Hebbian Learning → 更新权重
       ├─ 11. Async Memory → 持久化
       │
       └─ 12. 验证检查（每 10 Epoch）
            ├─ 计算涌现幅度（[PRD §6.1 4.1.1](../../PRD.md)）
            ├─ 记录到 logs/checkpoint_e{epoch}.json
            └─ 如果 epoch in [20, 40, 60, 80]：生成中间报告

结束（t=80）
  │
  ├─ 计算最终评估指标
  ├─ 生成 experiment_report_e{seed}.md
  └─ 归档到 experiments/archive/2026-MM-M1.1-seed{seed}/
```

## 5.2 多次运行（N=5 种子）

```
seeds = [1, 2, 3, 4, 5]
for seed in seeds:
    run_m11_experiment(seed=seed, config=m11_encouraged.yaml)
    compute_convergence_metrics()  # 收敛度、方向一致性等

# 跨种子统计
report_aggregate_metrics()
```

---

# 六、评估指标（在 [PRD §6.1 4.1.1-4.1.3](../../PRD.md) 基础上具体化）

## 6.1 主要指标

| 指标 | 公式 | M1.1 期望 |
|------|------|----------|
| **涌现幅度** | L2 距离 (V_final, V_initial) | > 0.3 |
| **收敛度** | 5 种子的 L2 标准差均值 | < 0.1 |
| **方向一致性** | cos(V_final, V_event_weighted) | > 0.5 |
| **价值冲突选择多样性** | 16 个价值困境事件中不同选择的数量 | ≥ 8（避免单一倾向） |

## 6.2 次要指标（用于诊断）

| 指标 | 用途 |
|------|------|
| 价值轨迹平滑度 | Epoch 间 L2 距离的均值（应较小，避免随机漂移） |
| value_delta 分布 | 各维度的 value_delta 统计（应有非零分布） |
| 反思触发次数 | M1.1 故意禁用反思，应为 0 |
| Hebbian W2 范数 | 反映暗知识积累（应有所变化） |
| frustration 演化 | 反映 Time Metabolism 是否正常工作 |

## 6.3 可视化方案

### 6.3.1 必备图表

1. **价值轨迹图**（每个具体价值观的时间序列）
   - 5 条线（6 个具体价值观中至少显示 4 个）
   - 标注元价值（保持 0.5 的水平线）
   - 标注价值冲突事件位置（垂直线）
   - 标注每 10 Epoch 的 checkpoint

2. **价值向量雷达图**（初始 vs 最终）
   - 6 维雷达图对比 Epoch 0 和 Epoch 80
   - 5 种子叠加显示（半透明）

3. **价值困境选择热力图**
   - 行：16 个价值困境事件
   - 列：5 个种子
   - 颜色：选择倾向（红=选项 A，蓝=选项 B）

### 6.3.2 可选图表

4. **EMA alpha 演化**（事件强度 vs 学习率）
5. **frustration 曲线**（驱动温度变化）
6. **Hebbian W2 权重矩阵**（最后 5 Epoch 的均值）

---

# 七、结果判定流程

## 7.1 通过条件

M1.1 通过 = **涌现幅度 > 0.3 AND 收敛度 < 0.1 AND 方向一致性 > 0.5**

## 7.2 失败模式与应对

| 失败模式 | 诊断步骤 | 应对 |
|---------|---------|------|
| 涌现幅度 ≤ 0.3 | 检查 Critic 输出是否合理 | 调整 Critic Prompt |
| 涌现幅度 > 0.3 但 收敛度 ≥ 0.1 | 检查事件流多样性 | 增加事件类型 |
| 涌现幅度 > 0.3 但 方向一致性 ≤ 0.5 | 检查 Critic 是否"听懂" | 重新设计 Critic |
| 价值向量不变（涌现幅度 ≈ 0） | 检查 Value Layer EMA 是否在更新 | debug |
| 价值向量全随机 | 检查 alpha 是否过大 | 减小 base_alpha |
| 价值向量同质化（所有维度 ≈ 0.5） | 检查事件是否足够差异化 | 增加价值冲突事件 |

## 7.3 哲学判定

如果 M1.1 通过：
- **强假设支持**：价值观确实可以从经历中涌现
- **但仍不是"真我"判定**——M1.1 不涉及反思、身份、叙事

如果 M1.1 失败：
- 详见 [SGE-Failure-Mode-Deep-Analysis.md](./SGE-Failure-Mode-Deep-Analysis.md)（待创建）

---

# 八、关键时间节点

| 节点 | 时间估计 | 关键产出 |
|------|---------|---------|
| 实验启动 | T+0 | discussions/2026-XX-XX-phase1-m11-start.md |
| 第一次中间检查（Epoch 20） | T+~1h | logs/checkpoint_e020.json |
| Epoch 40 报告 | T+~2h | 中间报告（包含 5 种子统计）|
| Epoch 80 完成 | T+~4h | experiment_report_e{seed}.md × 5 |
| 5 种子汇总分析 | T+~5h | research/sge-feasibility/SGE-Experiment-Result-Phase1-M1.1.md |
| 项目级文档修订 | T+~6h | PRD/ROADMAP/CHANGELOG 更新 |

---

# 九、与 [SGE-Experiment-Protocol.md](./SGE-Experiment-Protocol.md) 的关系

本文件是 M1.1 的**具体化设计**，[SGE-Experiment-Protocol.md](./SGE-Experiment-Protocol.md) 是**通用协议**。两者配合使用：

- 通用协议：环境、依赖、可复现性约束、异常处理、判定流程
- 本文件：M1.1 特有——事件流设计、参数选择、可视化方案、时间节点

---

# 十、相关文档

- **里程碑**：[ROADMAP §M1.1](../../ROADMAP.md)
- **需求**：[PRD §4.1 FR-1~10](../../PRD.md)
- **架构**：[ARCH §3.1 Event Generator](../../ARCH.md)
- **设计**：[DESIGN §2 Event Generator 设计](../../DESIGN.md)
- **协议**：[SGE-Experiment-Protocol.md](./SGE-Experiment-Protocol.md)
- **判定**：[SGE-Authenticity-vs-Simulation-Operationalization.md](../sge-core/SGE-Authenticity-vs-Simulation-Operationalization.md)
- **下一步**：[SGE-M12-Experiment-Design.md](./SGE-M12-Experiment-Design.md)（待创建，M1.2 三胞胎分化）

---

**创建日期**：2026-06-15
**维护者**：Bisen & Claude
**下次更新**：M1.1 实验完成后，根据实际数据校准参数和阈值
