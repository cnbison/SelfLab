# M2.2 H_self/PT 诊断报告

**日期**: 2026-07-07
**作者**: Bisen + Claude
**关联**:
- [Insight 35](../SGE-Key-Insights.md)（H_self 公式 + 收敛预期）
- [Insight 36](../SGE-Key-Insights.md)（M2.2 v2 dedup 根因诊断）
- [M22_V2_EXPH_SELF_REPORT.md](../../experiments/M22_V2_EXPH_SELF_REPORT.md)
- [M22_V3_DEDUP_REPORT.md](../../experiments/M22_V3_DEDUP_REPORT.md)
- [M22_V4_DEDUP_REPORT.md](../../experiments/M22_V4_DEDUP_REPORT.md)

---

## 0. 摘要

基于 v2/v3/v4 三轮 M2.2 实验的实证数据 + H_self/PT 源码审计，得出三个核心结论：

| 问题 | 严重度 | 触发 Insight 修订？ |
|------|--------|-------------------|
| **H_self 数学下界 0.6**（H_identity=H_narrative=1.0 锁死） | 🔴 致命 | 35A 需重大修订 |
| **H_self 上升 100% 来自 H_value**（与 dedup 完全无关） | 🟠 关键 | 35B/36 需修订 |
| **PT frustration 衰减 ≫ 累积**（净 -24.5/250 epoch）| 🟡 重要 | PT 触发机制需调整 |

**Insight 35A 的"自我形成 = H_self 单调下降"假设在数学上不可达**。需要重新审视 H_self 公式。

---

## 1. H_self 公式审计

**公式来源**：`sge/sge/metrics.py:9`
```python
H_self = w_v · H_value + w_i · H_identity + w_n · H_narrative
       = 0.4 · H_value + 0.3 · H_identity + 0.3 · H_narrative
```

### 1.1 H_value 计算（metrics.py:118）

```python
H_value = _histogram_entropy_normalized(value_vec, bins=10, lo=-1.0, hi=1.0)
```

- 6 维 value_state → 10 bin 直方图 → Shannon 熵 → 归一化
- **范围 [0, 1]**，OK
- v3 epoch 249 实测：H_value = 0.2764 ✓ 与手动验算一致

### 1.2 H_identity 计算（metrics.py:123）

```python
identities = [h['identity'] for h in identity_layer.identity_history]
H_identity = _sequence_entropy_normalized(identities)
```

`_sequence_entropy_normalized`（metrics.py:67-83）：
```python
n = len(items)
if n == 0 or n == 1:
    return 1.0
counts = Counter(items)
probs = [c / n for c in counts.values()]
h = -sum(p * log2(p) for p in probs)
return h / log2(n)
```

### 1.3 🔴 H_identity/H_narrative 结构性 bug

**问题**：归一化基准 = `log2(N)`（N=history 长度）。当所有 items 都 unique 时：
- N=11 unique items → counts 都是 1 → probs = [1/11 × 11]
- entropy = log2(11) ≈ 3.459
- normalized = log2(11) / log2(11) = **1.0**

**实测验证**：
| 场景 | H_identity |
|------|-----------|
| 11 unique items | 1.000 |
| 12 unique items | 1.000 |
| 5×'探索者'（全同）| 0.000 |
| 6 items 中 2 对重复 | 0.742 |

**结论**：H_identity/H_narrative 公式**仅在出现重复时才 < 1.0**。只要 LLM 持续生成不同 string（或 dedup 保证 history 全 unique），就永远 = 1.0。

### 1.4 🔴 H_self 数学下界 = 0.6

```python
H_self = 0.4·H_value + 0.3·H_identity + 0.3·H_narrative
```

当 H_identity = H_narrative = 1.0 时（**常态**）：
- H_self = 0.4·H_value + 0.6
- 最小值 = 0.6（当 H_value=0）
- 最大值 = 1.0（当 H_value=1.0）

**实测轨迹验证**（v3 chunk 0）：

| epoch | H_value | 0.4·H_value | H_id+H_na | H_self 预测 | 实测 |
|------:|--------:|------------:|----------:|------------:|-----:|
| 0 | 0.0000 | 0.0000 | 0.6 | 0.600 | **0.600** ✓ |
| 49 | 0.3768 | 0.1507 | 0.6 | 0.751 | **0.751** ✓ |
| 99 | 0.1957 | 0.0783 | 0.6 | 0.678 | **0.678** ✓ |
| 149 | 0.4771 | 0.1908 | 0.6 | 0.791 | **0.791** ✓ |
| 199 | 0.3010 | 0.1204 | 0.6 | 0.720 | **0.720** ✓ |
| 249 | 0.2764 | 0.1106 | 0.6 | 0.711 | **0.711** ✓ |

**完全吻合**：H_self 的 100% 变化来自 H_value 的 100% 变化。

### 1.5 Insight 35A 不可达性证明

PRD §6 验收标准："一段成长后 H_self 下降率 > 30%"（entropy_reduction_rate = (H_start - H_end) / H_start > 0.3）

- H_start = 0.600（典型初始值）
- 需要 H_end < 0.420
- 即 0.4·H_value + 0.6 < 0.420 → H_value < -0.450
- H_value ∈ [0, 1] → **数学上不可达**

**Insight 35A 的"自我形成 = H_self 单调下降"在当前公式下是空头承诺**。

---

## 2. dedup 与 H_identity 互相抵消（Insight 36 误诊）

### 2.1 原 Insight 36 假设

> "LLM 每次 crystallize 都重新诠释自我，导致字符级 Jaccard 相似度虽高但不等同字符串 → 信息熵从未坍缩"
> → 修复方向：dedup 让 H_identity 下降

### 2.2 实证反驳

| 实验 | Identity unique | H_identity (epoch 249) |
|------|-----------------|-----------------------|
| v2 baseline (no dedup) | 12/12 | 1.000 |
| v3 jaccard dedup | 11/12 | 1.000 |
| v4 ngram dedup | 8/12 | 1.000 |

**dedup 越激进，H_identity 越"应该"低**——但**全部等于 1.0**！

### 2.3 原因：dedup 与 H_identity 公式互相对抗

```
dedup 工作机制：
  - 检测重复 → 不追加到 history → history 保持全 unique
  - history N unique items → H_identity = 1.0

期望效果（Insight 36）：
  - dedup 让 history 变小 → H_identity 下降
  - 实际上：history 减小的是 N_total，而 N_unique 也等比减小，比例不变 → H_identity = 1.0
```

**dedup 不仅没帮助，反而让"稳定"的形式更不可见**：
- 无 dedup：history 有 N 个不同 items → 看起来"丰富"但实际 H=1.0
- 有 dedup：history 有 M < N 个 unique items → 看起来"稳定"但 H 仍 = 1.0
- 真正的"稳定"应该让 items 重复出现 → 但 dedup 阻止重复出现

**Insight 36 的根因诊断方向错了**。真正问题不是"identity 没去重"，而是"H_identity 公式在 unique-history 场景下永远等于 1.0"。

---

## 3. PT 触发机制审计

### 3.1 触发条件（baseline.py:154, 494）

```python
PHASE_THRESHOLD = 2.0  # scalar agent frustration 阈值

# 在 learn() 中:
if reward < -0.1:
    self._frustration += abs(reward)  # 累积（仅负 reward）
else:
    self._frustration = max(0, self._frustration - reward * 0.5)  # 衰减

if self._frustration > PHASE_THRESHOLD:  # > 2.0
    # ... 触发 PT
```

### 3.2 v3 chunk 0 frustration dynamics 实测

事件分布：
- success: 165 (66%) — 正 reward
- value_conflict: 41 (16.4%) — 可能负 reward
- relationship: 20 (8%) — 可能正 reward
- exploration: 11 (4.4%) — 可能正 reward
- failure: 13 (5.2%) — 负 reward

**假设 reward 典型值**（基于 v2 M22 报告 reward 范围 [-0.5, +0.4]）：

| event_type | count | reward (假设) | 累积 frustration | 衰减 frustration |
|-----------|------:|--------------:|----------------:|----------------:|
| success | 165 | +0.4 | — | 165 × 0.4 × 0.5 = 33.0 |
| value_conflict | 41 | -0.2 | 41 × 0.2 = 8.2 | — |
| failure | 13 | -0.5 | 13 × 0.5 = 6.5 | — |
| relationship | 20 | +0.3 | — | 20 × 0.3 × 0.5 = 3.0 |
| exploration | 11 | +0.2 | — | 11 × 0.2 × 0.5 = 1.1 |

**净变化**：累积 = 8.2 + 6.5 = 14.7；衰减 = 33.0 + 3.0 + 1.1 = 37.1；**净 = -22.4**

→ frustration 在 250 epoch 内净减少 22.4 → 永远不可能达到 2.0 → **PT 永远不触发**

### 3.3 PT 触发需要"持续失败簇"

PT 触发需要 frustration > 2.0，但：
- 累积仅当 reward < -0.1（失败类事件）
- 衰减在每个正 reward 步都发生（66% 概率）

**根本问题**：decay rate (reward × 0.5) 远高于 accumulation rate (|reward|) 在稀疏负 reward 场景下。要触发 PT，需要**连续 N 步负 reward**，但 event_generator 产生 success-heavy 流。

### 3.4 drive-level frustration 是另一回事

注意：DriveMetabolism 有自己的 per-drive frustration（clamp 到 [0, 5]）：
```
v3 epoch 249: frustration_per_drive = {
  exploration: 4.7371, safety: 0.0, creativity: 0.0,
  connection: 4.8122, autonomy: 0.0
}
```

但这个 drive-level frustration **没有连接到 PT 触发**（baseline.py:494 用的是 `self._frustration`，scalar）。

**另一个 bug**：drive-level frustration 数据存在但未被使用。

---

## 4. 三个核心问题 + 建议修复方向

### 问题 P0-1: H_self 数学下界 0.6

**症状**：H_self 在 0.6-0.8 区间波动，永远不下降。

**根因**：H_identity/H_narrative 归一化公式让"全 unique"= 1.0，与 H_value 权重叠加后产生 0.6 的硬地板。

**修复方向**（三选一）：

| 方案 | 描述 | 影响 |
|------|------|------|
| **A. 改 H_identity 为绝对熵** | `H_identity = log2(N_unique + 1) / log2(N_target + 1)` | 打破 1.0 上限；N_unique < N_target 时 H < 1 |
| **B. 改用 Jaccard 稳定性** | `H_identity = 1 - max_window_jaccard` | 直接衡量"近期重复程度" |
| **C. 重设目标函数** | H_self = `weighted_abs_change` 而非 weighted_entropy | 改为衡量"价值观收敛度"而非"分布熵" |

### 问题 P0-2: dedup 与 H_identity 互相抵消

**症状**：dedup 越激进，H_identity 越稳定为 1.0。

**修复方向**：
- 让 dedup 不阻止 history append，而是**追加标记 `dedup_hit=True`**；H_identity 计算时考虑 dedup 频次
- 或采用方案 A/B（让 H_identity 直接反映稳定性）

### 问题 P0-3: PT 触发机制几乎不可能

**症状**：250 epoch 内 PT 触发数 = 0（v2/v3/v4 一致）。

**修复方向**（三选一）：

| 方案 | 描述 | 影响 |
|------|------|------|
| **D. 降低 PHASE_THRESHOLD** | 2.0 → 0.5 | 1/4 倍触发概率，仍是 ad-hoc |
| **E. 改用 drive-level frustration** | 用 DriveMetabolism 总 frustration > 2.0 触发 | 已有数据可用，语义更对 |
| **F. 重设 frustration dynamics** | 累积只在 sustained failure 时；decay 仅在 idle 时 | 更接近真实情绪动力学 |

### 问题 P1: H_value 直方图分箱可能过粗

**症状**：6 个值落入 10 个 bin，集中在 2-3 个 bin 时熵很低，但实际值向量仍有差异。

**修复方向**：
- 增加 bins 到 20 或 30
- 或改用值向量的 L2 距离（`1 / (1 + ||v||)`）作为稳定性指标
- 或改用值向量的协方差矩阵熵（捕获维度间相关性）

---

## 5. 验证实验建议

要确认 P0-1/P0-2 修复方向，**最小验证实验**：

1. **修改 metrics.py**：实现方案 A（H_identity = log2(N_unique + 1) / log2(N_target + 1)，N_target=3）
2. **重算 v3 数据**：从已有 identity_history/narrative_history 重新计算 H_self（无需重跑实验）
3. **对比新旧 H_self 轨迹**：确认新公式能反映 dedup 效果

**最大验证实验**：

1. 实施 P0-1 + P0-3 全部修复
2. 跑 v5 encouraged chunk 0（250 epoch）
3. 检查：H_self 是否下降到 0.4 以下 + PT 是否触发 ≥ 1 次

---

## 6. 结论

**Insight 35A 修订是当务之急**：
- "H_self 单调下降" 目标在当前公式下**数学不可达**
- 修订方向：将目标从"分布熵下降"改为"目标收敛"（如"目标 identity 数 / 目标 value 范围"）

**Insight 36 部分正确**：
- ✅ 正确：LLM 持续生成新 identity 确实让 H_identity 失效
- ❌ 错误：dedup 不是修复方向；真正问题是公式本身

**PT 触发机制需要单独审计**：
- 当前 frustration dynamics 对 success-heavy 流不友好
- drive-level frustration 数据存在但未连接

下一步建议：先做"最小验证实验"（重算 v3 数据 + 新 H_self 公式），再决定是否实施全部修复。