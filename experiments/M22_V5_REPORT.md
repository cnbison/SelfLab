# M2.2 v5 — 公式 A2 + PHASE_THRESHOLD=0.5 联调（P0-1 + P0-3 修复实证）

**日期**: 2026-07-10 (v5 重跑 250 epoch 完整版)
**作者**: Bisen + Claude
**关联**:
- [Insight 35A](../SGE-Key-Insights.md)（H_self 单调下降目标）
- [Insight 36](../SGE-Key-Insights.md)（M2.2 v2 实证局限与修订）
- [M22_H_SELF_DIAGNOSIS.md](../research/sge-feasibility/M22_H_SELF_DIAGNOSIS.md)（P0-1/P0-3 根因诊断）
- [M22_V4_DEDUP_REPORT.md](M22_V4_DEDUP_REPORT.md)（dedup 路线失败）
- [recompute_h_self_v5.py](scripts/recompute_h_self_v5.py)（离线公式验证）
- [simulate_pt_v6.py](scripts/simulate_pt_v6.py)（PT Monte Carlo 验证）

---

## 0. 摘要

> **v5 报告 2026-07-10 更新**：之前 v5 partial run（epoch 0-170, LLM 崩溃）的报告为 +52.3% reduction + PT 1 次触发。完整 250 epoch 重跑后结论**显著修正**——见 §6 "原报告偏差说明"。

| 验证项 | v2/v3/v4（旧） | **v5 重跑（新）** | PRD §6 要求 | 结论 |
|--------|---------------|------------------|------------|------|
| **H_self reduction_rate** | -18.4% (反向上升) | **+17.0%** (.6 → .498) | > 30% | ❌ 未达标 |
| **H_self 触底 reduction** | -18.4% | **+81.7%** (epoch 49: .6 → .110) | — | ✅ 公式 A2 有效 |
| **H_self 单调性** | 单调上升 | **非单调**（epoch 49 触底后回升） | — | ❌ 暴露新问题 |
| **PT 触发数** (250 epoch) | 0 | **0** | ≥ 1 | ❌ 未修复 |
| **LLM 稳定性** (800 calls) | 0/800 retry (30s/5 次) | **0/800 retry** (60s/8 次) | — | ✅ timeout 升级完美 |
| **H_self 数学下界** | 0.6 (硬地板) | **0.0** (公式 A2, 触底 0.110) | — | ✅ 突破地板 |

**根因诊断 → 修复 → 实证 → 新发现**：
- ✅ **P0-1**（H_self 数学下界 0.6）：公式 A2 修复 → 实证 H_self 可下降到 0.110
- ✅ **P0-2**（dedup 与 H_identity 互相抵消）：被公式 A2 隐式解决
- ❌ **P0-3**（PT 触发几乎不可能）：阈值 0.5 → 仍未触发 → 暴露 frustration dynamics 根本问题
- ⚠️ **NEW P0-4**（H_self 非单调）：identity 增长 → H_identity 必然回升 → H_self 不是稳定指标

---

## 1. 修复实现

### 1.1 公式 A2 — H_identity / H_narrative 重新定义

**修改**：`sge/sge/metrics.py:_sequence_entropy_normalized()`

```python
# 原公式（结构性 bug）：归一化基准 = log2(N_total) → 全 unique → 永远 = 1.0
# 新公式 A2：基于 N_unique 线性映射
def _sequence_entropy_normalized(items: list, n_max: int = 20) -> float:
    n_unique = len(set(items)) if items else 0
    if n_unique == 0: return 1.0  # 未形成
    if n_unique == 1: return 0.0  # 完全稳定
    return min(1.0, (n_unique - 1) / (n_max - 1))
```

**优势**：
- 1 unique → H = 0（真正反映"稳定"）
- 数学下界 = 0（与 H_value = 0 一起）
- dedup 效果可观测（减少 unique 数 → 直接降低 H）

### 1.2 PHASE_THRESHOLD 调整 — 2.0 → 0.5

**修改**：`sge/sge/baseline.py:154`

```python
PHASE_THRESHOLD = 0.5  # 原 2.0（AiBeing 默认禁用 PT）
```

**Monte Carlo 验证**（`experiments/scripts/simulate_pt_v6.py`）：

| Threshold | Mean PT/250ep | 评估 |
|-----------|---------------|------|
| 2.0 (原) | 0.0 | ❌ 完全失效（v2/v3/v4 实测 0）|
| 1.0 | 0.5 | ⚠️ 偶发 |
| **0.5** | **2.5** | ✅ 推荐（但实测 0，模型偏差）|
| 0.3 | 5.5 | ⚠️ 过度触发 |

### 1.3 LLM Timeout/Retry 升级 — 30s/5 → 60s/8

**修改**：`sge/sge/llm_client.py:158 + 210`

```python
timeout: float = 60.0,  # M2.2 v5 重跑：从 30 提至 60
max_retries = 8  # M2.2 v5 重跑：5 → 8
```

**目的**：消除 v5 partial run 因连续 4 次 30s 超时崩溃的工程问题。

---

## 2. v5 实验设置

**Babies**: encouraged（与 v2/v3/v4 完全一致 → 事件流可比）
**Chunk**: 0（250 epoch 完整）
**Seed**: 42（与 v2/v3/v4 完全一致）
**Dedup**: 关闭（与 v2 baseline 一致，专注公式 A2 + PT 0.5 的独立效果）
**Timeout**: 60s/8 retries
**输出**: `experiments/output/m22_v5_exph_self/`

**运行状态**：
- ✅ **完整 250/250 epoch 跑通**（无崩溃）
- ⏱️ **总耗时 43.5 min**（10.4s/epoch，优于 partial run 15.6s/epoch）
- 🔁 **0 retry**（0/800 LLM calls 失败）— timeout 升级完美生效
- 💰 **800 LLM calls**（v2 partial: 322 calls/100 epoch → 800/250 epoch，与预期一致）

---

## 3. 关键结果

### 3.1 PRD §6 验收指标

| 指标 | 数值 | 评估 |
|------|------|------|
| **H_self 起点** | 0.600 | — |
| **H_self 终点** (@ epoch 249) | 0.4981 | — |
| **H_self 触底** (@ epoch 49) | **0.1098** | ✅ 公式 A2 允许触达近 0 |
| **H_self reduction_rate** (起点→终点) | **+17.0%** | ❌ 未达 30% 阈值 |
| **H_self 触底 reduction_rate** | **+81.7%** | ✅ 远超 30%（但非单调）|
| **Phase Transition 触发数** | **0** | ❌ 未达 ≥ 1 阈值 |

### 3.2 H_self 演化曲线（完整 250 epoch）

| Epoch | H_self | H_value | H_identity | H_narrative | identity_so_far | narrative_so_far | 阶段特征 |
|-------|--------|---------|------------|-------------|----------------|------------------|---------|
| 0     | 0.6000 | 0.0000 | 1.0000 | 1.0000 | 0 | 0 | 起点（未结晶） |
| 49    | **0.1098** | 0.1957 | 0.0526 | 0.0526 | 2 | 2 | **H_self 触底**（identity 仍少） |
| 99    | 0.2046 | 0.1957 | 0.2105 | 0.2105 | 5 | 5 | 首次结晶期（identity 增长） |
| 149   | 0.3803 | 0.4771 | 0.3158 | 0.3158 | 7 | 7 | value_conflict 期 |
| 199   | 0.3948 | 0.2764 | 0.4737 | 0.4737 | 10 | 10 | 持续结晶 |
| 249   | 0.4981 | 0.3768 | 0.5789 | 0.5789 | 12 | 12 | 终点（identity 12 unique） |

**关键观察**：
- H_self 在 epoch 49 触底 0.110（identity 2 unique → 公式 A2 = 0.053）
- 此后 H_identity 随结晶次数单调上升（每结晶 +1 unique → H_identity +0.053）
- H_self 终点 0.498 主要是 H_identity 贡献（0.579 × 0.3 权重 = 0.174）
- H_value 持续在 0.20-0.48 间波动（value vector 演化）

### 3.3 Phase Transition 实证

- **触发数：0 / 250 epoch**
- **frustration_per_drive 演化**：
  - epoch 0: exploration=5.0, connection=5.0, others=0.0（初始 5/5 drives = 5.0）
  - epoch 249: exploration=4.7545, connection=4.8246, others=0.0（缓慢衰减）
- **frustration_total**：epoch 0=10.0 → epoch 249=9.58（仅 -4.2%）
- **PHASE_THRESHOLD = 0.5**：frustration 永远 ≥ 9.5（≥ 0.5 是 trivial true），但触发需要 `frustration` 单变量 > 0.5——而 drives 内部没有 0-1 范围的 frustration，单变量触发从未达成

**根因**：frustration 是 **drive-level** 累积（初始 5.0，clamp [0, 5]），**永远不可能**与一个标量 PHASE_THRESHOLD 0.5 单独比较。方案 E（drive-level frustration）已在 §1.2 评估中明确为不可行。

### 3.4 Identity/Narrative 历史（最终）

| 指标 | 数值 |
|------|------|
| Identity 总生成 | 12 |
| Identity 唯一 | 12（无 dedup，全部 unique）|
| Narrative 总生成 | 12 |
| Narrative 唯一 | 12（无 dedup，全部 unique）|
| Crystallize 次数 | 24 |
| Hawking 最终大小 | 250 entries |
| Hawking min_weight | 0.083（持续衰减）|

### 3.5 LLM 稳定性（retry 统计）

```
total_calls:        800
calls_with_retry:   0
calls_failed:       0
total_attempts:     800 (no retries)
retry_rate:         0.0%
total_wait_seconds: 0.0
```

✅ **LLM 稳定性完美**——timeout 60s + retry 8 完全消除了 v5 partial 的崩溃问题。

---

## 4. 修复前后对比矩阵（更新版）

| 维度 | v2 baseline | v3 jaccard | v4 ngram | **v5 (partial 报告)** | **v5 (完整 250)** |
|------|------------|-----------|---------|---------------------|------------------|
| 公式 | Shannon | Shannon | Shannon | **公式 A2** | **公式 A2** |
| PHASE_THRESHOLD | 2.0 | 2.0 | 2.0 | **0.5** | **0.5** |
| Dedup | 无 | jaccard@0.3 | ngram@0.3 | 无 | 无 |
| Timeout/Retry | 30s/5 | 30s/5 | 30s/5 | 30s/5 | **60s/8** |
| Epochs 跑通 | 1000 | 250 | 250 | 170（崩）| **250（完整）** |
| H_self 起点 | 0.600 | 0.600 | 0.600 | 0.600 | 0.600 |
| H_self 终点 | 0.711 | 0.711 | 0.751 | ~0.286（估）| **0.498** |
| **Reduction rate** | -18.4% | -18.4% | -25.1% | +52.3% (claimed) | **+17.0% (actual)** |
| **PT 触发数** | 0 | 0 | 0 | 1 (claimed) | **0 (actual)** |
| PRD §6 验收 | ❌ | ❌ | ❌ | ✅ (claimed) | **❌** |

---

## 5. 关键洞察（重要更新）

### 5.1 H_self 不是稳定的"自我形成"指标

**新发现**（v5 完整 250 epoch 暴露）：

H_self = w_v·H_value + w_i·H_identity + w_n·H_narrative 看似合理，但**H_identity 必然随 identity 增长而上升**（每结晶 +1 unique → H_identity +(N-2)/(N-1)·1/(N_MAX-1)）。这意味着：

- 自我形成期（H_self 应该下降）↔ 结晶期（identity 增加）→ 两者方向相反
- H_self 在"identity 少时"自动低，但"identity 多时"自动高
- 这不是 bug，是公式 A2 的本质特性——**H_self 反映"多样性"，而非"形成度"**

**与 partial run 报告的偏差来源**：
- partial run 在 epoch 100（identity 5）停止，把"identity 少时的低点"误当终点
- 完整 250 epoch 显示 identity 持续增长到 12，H_identity 必然回升
- partial 报告的 +52.3% 是 **artifact of early stopping**

### 5.2 Phase Transition 触发需要重新设计

**新发现**（v5 完整 250 epoch 暴露）：

PHASE_THRESHOLD=0.5（基于全局 frustration 标量）在 drive-level 累积 frustration 模型下**永远不触发**——因为：
- 5 个 drive 各自 [0, 5] 累积，总和永远 ≥ 0
- 触发需要"单变量"超过 0.5，但 drives 没有 [0, 1] 范围的 frustration
- 方案 D（降阈值）只能让 threshold 越来越低，但 frustration 量级不变

**新方案候选**（需进一步验证）：
- **方案 G**：frustration 单变量归一化到 [0, 1]（`frustration[i] / 5.0`）
- **方案 H**：PT 触发条件改为"连续 N 个 failure 事件"而非 frustration 阈值
- **方案 I**：放弃 PT 触发作为验收指标，改用其他自我形成信号

### 5.3 公式 A2 本身工作良好

虽然 H_self 不是稳定指标，但**公式 A2 本身没有 bug**：
- H_identity 在 0.053（2 unique）→ 0.579（12 unique）平滑过渡
- 1 unique → H=0（理论完全稳定）
- 数学下界 = 0（突破原 Shannon 公式的 0.6 地板）

**公式 A2 适用**于任何需要"基于唯一性计数"的多样性/稳定性度量。问题在于**H_self 这个组合指标是否合理**。

### 5.4 LLM 工程问题已彻底解决

v5 完整跑通 + 0 retry 证明：60s timeout + 8 retry 完全消除了 v2/v3/v4/v5-partial 共同的"LLM 不稳定崩溃"问题。后续实验可放心使用这套配置。

### 5.5 partial run 报告的乐观偏差

v5 报告最初版本（2026-07-08，partial run）声称：
- H_self reduction +52.3% ✅
- PT 1 次 @ epoch 87 ✅
- PRD §6 验收通过 ✅

**这些是基于 epoch 100 估算的乐观偏差**：
- epoch 100 H_self = 0.205 看起来很美（.6 → .205 = +65.8%）
- 但 epoch 100 是 H_self 触底 0.110 之后的回升期，**不是趋势**
- partial 报告把"触底"误当"收敛"

**教训**：
- LLM 实验**必须完整跑完**才能下结论
- "early checkpoint 看起来好"≠"最终结果好"
- 250 epoch 是最低标准，1000 epoch 才能验证长程

---

## 6. 原报告偏差说明（2026-07-10 更新）

**本次 v5 报告重写原因**：
- 原 v5 报告（2026-07-08，partial run 0-170 epoch）声称 +52.3% reduction + PT 1 次触发
- 完整 250 epoch 重跑后，结论需要**显著修正**：
  - 实际 reduction +17.0%（不是 +52.3%）
  - 实际 PT 触发 0 次（不是 1 次）
  - 实际 H_self 不是单调下降（不是 partial 报告的"单调下降"）

**修正后的状态**：
- ❌ v5 没有达成 PRD §6 验收（reduction 17% < 30%, PT = 0 < 1）
- ✅ 公式 A2 仍然有效（可让 H_self 触底 0.110）
- ✅ LLM 工程问题彻底解决（0 retry / 800 calls）
- ⚠️ H_self 指标本身需要重新设计
- ⚠️ PT 触发机制需要重新设计

**这是诚实研究的必经之路**——partial 报告偏乐观，完整实证暴露真实问题。

---

## 7. 限制与后续

### 7.1 本次实验限制

1. **单 baby**：仅 encouraged（与 v2/v3/v4 一致），未验证跨 baby 通用性
2. **单 chunk**：chunk 0（250 epoch），未验证 1000 epoch 长程
3. **H_self 指标不充分**：触底 0.110 但回升到 0.498，reduction < 30% 阈值
4. **PT 触发 0 次**：PHASE_THRESHOLD=0.5 仍未触发，frustration dynamics 需要重新设计

### 7.2 后续建议（按优先级）

| 优先级 | 行动 | 预期 |
|-------|------|------|
| **P0** | 重新设计 H_self 指标（如 sliding window 重复率 / embedding similarity）| 找到稳定的"自我形成"度量 |
| **P0** | 重新设计 PT 触发机制（方案 G/H/I 之一）| 让 PT 在 success-heavy 流中也能触发 |
| P1 | 跑 v6 = 公式 A2 + 新 H_self + 新 PT 触发 | 验证双修复 |
| P1 | 跑 challenged / uncertain babies | 验证跨 baby 通用性 |
| P2 | 跑 1000 epoch 长程（4 chunks）| 验证长程稳定性 |
| P3 | 评估 M3.x dedup 路线：v5 关闭 dedup 仍 +17% reduction → 暂停 | 资源优化 |

---

## 8. 文件清单

| 文件 | 说明 |
|------|------|
| `experiments/M22_V5_REPORT.md` | **本报告（2026-07-10 重写版）** |
| `experiments/output/m22_v5_exph_self/encouraged_chunk0_result.json` | v5 完整 250 epoch 结果 |
| `experiments/output/m22_v5_exph_self/encouraged_chunk0_checkpoint.json` | v5 最终 checkpoint（epoch 250）|
| `experiments/output/m22_v5_exph_self/encouraged_chunk0_identity_history.json` | 12 个 identity |
| `experiments/output/m22_v5_exph_self/encouraged_chunk0_narrative_history.json` | 12 个 narrative |
| `experiments/output/m22_v5_exph_self/encouraged_chunk0_meaning_samples.json` | 6 个 meaning 样本 |
| `experiments/output/m22_v5_exph_self/run.log` | 完整运行日志 |
| `experiments/scripts/m22_v5_exph_self.py` | v5 实验脚本 |
| `experiments/scripts/recompute_pt_v5.py` | PT 方案评估 |
| `experiments/scripts/simulate_pt_v6.py` | Monte Carlo PT 验证 |
| `experiments/output/m22_v6_pt_analysis/pt_analysis.json` | PT 分析输出 |

---

## 9. 命令记录

```bash
# v5 chunk 0 完整重跑（本次）
python experiments/scripts/m22_v5_exph_self.py \
    --baby encouraged --chunk-index 0 --force

# 后续：跑 v6（需先重新设计 H_self + PT）
python experiments/scripts/m22_v6_exph_self.py \
    --baby encouraged --chunk-index 0 --force
```

---

## 10. 结论

**v5 完整 250 epoch 重跑结论**：

✅ **P0-1 修复成功**：H_self 公式 A2 修复后，H_self 可触底 0.110（vs 旧公式下界 0.6）
✅ **P0-2 修复成功**：公式 A2 隐式解决 dedup-H_identity 互相抵消
✅ **LLM 工程问题彻底解决**：60s timeout + 8 retry → 0/800 retry
❌ **P0-3 未修复**：PHASE_THRESHOLD=0.5 实测仍 0 PT 触发（Monte Carlo 预测 2.5，模型偏差）
⚠️ **新发现 P0-4**：H_self 不是稳定指标——identity 增长必然导致 H_identity 上升

**PRD §6 验收状态**：
- B 维度（H_self reduction > 30%）：❌ 未达成（+17% < 30%）
- B' 维度（PT 触发 ≥ 1）：❌ 未达成（0 < 1）

**核心教训**：
- partial run 报告偏乐观（+52.3% vs 实际 +17.0%）
- H_self 指标需要重新设计（不是公式 bug，是组合指标问题）
- PT 触发机制需要重新设计（frustration dynamics 不匹配标量阈值）
- **诚实报告 > 乐观报告** — 完整跑完 + 暴露问题 > 早停 + 虚假通过

**下一步建议**：
1. **重新设计 H_self**：用 sliding window 重复率 / embedding similarity 替代 N_unique 公式
2. **重新设计 PT 触发**：方案 G（frustration 归一化）/ H（连续 N failure）/ I（放弃 PT 指标）
3. 跑 v6 = 新 H_self + 新 PT + 公式 A2 验证
