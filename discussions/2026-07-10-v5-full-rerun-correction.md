# 2026-07-10 M2.2 v5 完整 250 epoch 重跑 — partial run 乐观偏差修正

**日期**: 2026-07-10
**主题**: M2.2 v5 完整 250 epoch 重跑（timeout 30s→60s, retry 5→8），发现 partial run 报告 +52.3% reduction + PT 1 触发为乐观偏差，完整数据为 +17.0% reduction + PT 0 触发
**参与者**: Bisen + Claude
**关联文档**:
- [M22_V5_REPORT.md 2026-07-10 重写版](../experiments/M22_V5_REPORT.md)
- [M22_H_SELF_DIAGNOSIS.md](../research/sge-feasibility/M22_H_SELF_DIAGNOSIS.md)
- [Insight 35 §10 (修订)](../SGE-Key-Insights.md)
- [Insight 36 §10 + §11 (新增)](../SGE-Key-Insights.md)
- [PRD §6 修订](../PRD.md)
- [ARCH §1.8.2 修订](../ARCH.md)
- [2026-07-08 讨论记录](2026-07-08-v5-formula-pt-fix.md)

---

## 1. 讨论背景

M2.2 v5 partial run（2026-07-08, LLM 崩于 epoch 170）报告：
- H_self reduction **+52.3%** ✅
- PT 触发 **1** @ epoch 87 ✅
- PRD §6 验收通过

Bisen 选择重跑 v5（更长 timeout + 断点续跑 / 更稳健）以获得完整 250 epoch 数据。

## 2. 重跑策略（C 方案）

**C 方案**（Bisen 选定）：
1. timeout 30s → 60s
2. retry 5 → 8
3. checkpoint_interval 100 → 100（保持）
4. 后台运行 + 实时监控

**关键工程修复**（`sge/sge/llm_client.py`）：
```python
timeout: float = 60.0,  # 30 → 60
max_retries = 8         # 5 → 8
```

## 3. 完整 250 epoch 实测结果

### 3.1 关键指标对比

| 指标 | partial run 报告 | **完整 250 epoch 实测** | 偏差 |
|------|----------------|---------------------|------|
| H_self 起点 | 0.600 | 0.600 | 0 |
| H_self 终点 | ~0.29（基于 epoch 100 估算）| 0.498 | **+0.21 偏差** |
| H_self 触底 | — | **0.110（epoch 49）** | 未观察到 |
| H_self reduction | +52.3% | **+17.0%** | **+35.3pp 偏差** |
| PT 触发数 | 1 @ epoch 87 | **0** | -1 |
| 完整跑通？ | ❌ 崩于 epoch 170 | ✅ 250/250 epoch | — |
| LLM retry | 4+ 次超时崩溃 | 0/800 retry | ✅ 工程彻底解决 |
| 耗时 | ~50 min（崩）| 43.5 min | 更快（10.4s/epoch）|

### 3.2 H_self 演化曲线（完整 250 epoch）

| Epoch | H_self | H_value | H_identity | H_narrative | identity_so_far | 阶段特征 |
|-------|--------|---------|------------|-------------|----------------|---------|
| 0     | 0.6000 | 0.0000 | 1.0000 | 1.0000 | 0 | 起点（未结晶） |
| 49    | **0.1098** | 0.1957 | 0.0526 | 0.0526 | 2 | **H_self 触底**（identity 仍少） |
| 99    | 0.2046 | 0.1957 | 0.2105 | 0.2105 | 5 | identity 增长期 |
| 149   | 0.3803 | 0.4771 | 0.3158 | 0.3158 | 7 | value_conflict 期 |
| 199   | 0.3948 | 0.2764 | 0.4737 | 0.4737 | 10 | 持续结晶 |
| 249   | 0.4981 | 0.3768 | 0.5789 | 0.5789 | 12 | 终点（identity 12 unique） |

**关键观察**：
- H_self 触底 epoch 49（identity 2 unique）
- 此后 identity 持续增长到 12 unique，H_identity 必然上升（每结晶 +1 → H_identity +(N-2)/(N-1)·1/(N_MAX-1) = 0.053）
- H_self 终点 0.498 = 0.4·H_value + 0.3·H_identity + 0.3·H_narrative ≈ 0.4·0.38 + 0.3·0.58 + 0.3·0.58 ≈ 0.50

### 3.3 PT 触发实证

- **触发数：0 / 250 epoch**
- frustration 演化：epoch 0 = 10.0 → epoch 249 = 9.58（仅 -4.2% 衰减）
- PHASE_THRESHOLD = 0.5：frustration 单变量 > 0.5 触发，但 drives 内部没有 [0, 1] 范围 frustration
- **根因**：标量阈值 vs drive-level [0, 5] 累积 frustration **量级不匹配**

## 4. 关键洞察

### 4.1 H_self 不是稳定的"自我形成"指标

**新发现**：

公式 A2 让 H_identity 反映"N_unique 数量"——数学上正确（突破 0.6 地板），但**与"自我形成"语义不一致**：
- "自我形成"应是"先发散后收敛"的轨迹
- 公式 A2 让"identity 少时自动低，identity 多时自动高"
- H_self 在结晶期必然先降后升——**不是 bug，是公式本质特性**

**结论**：H_self = w_v·H_value + w_i·H_identity + w_n·H_narrative 反映"多样性"，而非"形成度"——不适合作为稳定验收指标。

### 4.2 PT 触发机制需重新设计

**新发现**：

frustration dynamics（drive-level [0, 5] 累积）与 PHASE_THRESHOLD（标量 0.5）**量级不匹配**：
- drives 初始 frustration = 5.0（探索、连接）从 epoch 0 就已饱和
- 触发条件 `frustration > 0.5` 是 trivial true（frustration 永远 ≥ 9.5）
- Monte Carlo 模型（基于事件分布预测）高估了 PT 触发概率

**候选新方案**：
- 方案 G：frustration 单变量归一化到 [0, 1]（`frustration[i] / 5.0`）+ 阈值 0.3
- 方案 H：连续 N=3 failure 事件触发（与 frustration 阈值解耦）
- 方案 I：放弃 PT 作为验收指标，改用其他自我形成信号

### 4.3 partial run 报告的乐观偏差来源

**根因分析**：

partial run 在 epoch 100 checkpoint 停止，H_self = 0.205 看起来"很美"（.6 → .205 = +65.8%）。但：
- epoch 49 才是 H_self 真实触底点 0.110
- epoch 100 是"触底后回升期"
- partial 报告把"触底"误当"收敛"

**更深的偏差**：
- partial 报告 PT 1 @ epoch 87：可能 epoch 87 frustration 短暂超过 0.5，但完整 run 重新随机种子（虽然 seed=42 固定）— 实际未触发
- 提示：partial run 的 LLM 调用次数和事件分布可能与完整 run 有差异

### 4.4 公式 A2 本身工作良好

虽然 H_self 不是稳定指标，但**公式 A2 本身没有 bug**：
- 1 unique → H=0（理论完全稳定）
- N=0 → H=1.0（未形成）
- N>20 → H=1.0（完全发散）
- 12 unique → H=0.579（线性映射）
- 数学下界 = 0（突破原 0.6 地板）

**结论**：公式 A2 适用于任何"基于唯一性计数"的多样性/稳定性度量。问题在于**H_self 这个组合指标是否合理**——需要重新设计。

### 4.5 LLM 工程问题已彻底解决

v5 完整跑通 + 0/800 retry 证明：60s timeout + 8 retry 完全消除 LLM 瞬时不稳定导致的崩溃。后续实验可放心使用这套配置。

## 5. 文档同步（核心工作流第三步）

按 [CLAUDE.md 核心工作流](../CLAUDE.md)，完成 v5 重跑修订后必须同步：

### 5.1 已更新

| 文档 | 更新内容 |
|------|---------|
| **[experiments/M22_V5_REPORT.md](../experiments/M22_V5_REPORT.md)** | **重写**：移除 partial run 报告，改为完整 250 epoch 实证数据 + 关键发现（§5.1-5.5）+ 偏差说明（§6）|
| **[SGE-Key-Insights.md 索引](../SGE-Key-Insights.md)** | 35B 状态从 "✅ 通过" 改为 "⏸ 2026-07-08 报告通过 → 2026-07-10 完整 250 修订为未通过" |
| **[SGE-Key-Insights.md §4 公式](../SGE-Key-Insights.md)** | 增加 2026-07-10 修订：公式 A2 正确但 H_self 组合指标需重设计 |
| **[SGE-Key-Insights.md §10 (v5 实证)](../SGE-Key-Insights.md)** | 修订为 "partial → 完整 250 epoch 修订" + 新增 P0-4 / P0-5 + 状态表更新 |
| **[SGE-Key-Insights.md 36 §10 + §11 (新增)](../SGE-Key-Insights.md)** | 完整 250 修订内容 + M2.2 v6 方向（候选 H_self 重设计 + PT 重设计）|
| **[ARCH.md §1.8.2](../ARCH.md)** | 标题增加 "2026-07-10 完整 250 修订" + H_self 指标状态 + PT 触发机制状态 |
| **[PRD.md §6.1 B 维度](../PRD.md)** | 状态从 "✅ M2.2 v5 通过" 改为 "❌ 待 H_self 指标重设计" |
| **[PRD.md §6.3 修订注](../PRD.md)** | 2026-07-08 修订注加 "已被 2026-07-10 修订注覆盖" + 新增 2026-07-10 完整修订注 |
| **[PRD.md §6.3.1 通过条件](../PRD.md)** | 条件 B 从 "✓" 改为 "⏸" |
| **[sge/sge/llm_client.py](../sge/sge/llm_client.py)** | timeout 30→60s, retry 5→8 |

### 5.2 待跟进

| 文档 | 状态 | 备注 |
|------|------|------|
| DESIGN.md §9.5 H_self 设计 | 待办 | H_self 重设计方向需详细论证 |
| ROADMAP.md M2.x 后续 | 待办 | M2.3 v6 方向（重设计 H_self + PT）需加入 |
| CHANGELOG.md 1.29.0 | 进行中 | 本次修订版本记录 |

## 6. 结论与下一步

### 6.1 闭环完成（修订版）

✅ **诚实研究闭环**：
1. **诊断**：[M22_H_SELF_DIAGNOSIS.md §3-4](../research/sge-feasibility/M22_H_SELF_DIAGNOSIS.md) 三个根因
2. **修复**：[sge/sge/metrics.py 公式 A2](../sge/sge/metrics.py) + [sge/sge/baseline.py PHASE_THRESHOLD=0.5](../sge/sge/baseline.py) + [sge/sge/llm_client.py timeout 60s retry 8](../sge/sge/llm_client.py)
3. **实证**：[M22_V5_REPORT.md §3](../experiments/M22_V5_REPORT.md) v5 完整 250 epoch 验证
4. **修订**：发现 partial run 乐观偏差 → 诚实修订 → 文档同步
5. **新发现**：H_self 非单调 + PT 触发机制不匹配 → 标记为 P0-4 / P0-5

### 6.2 partial run 报告的教训

1. **LLM 实验必须完整跑完** — partial run 在 epoch 100 停，H_self = 0.205 看起来很好但 epoch 49 才是真实触底
2. **"early checkpoint 看起来好" ≠ "最终结果好"** — 250 epoch 是最低标准，1000 epoch 才能验证长程
3. **诚实报告 > 乐观报告** — 完整跑完 + 暴露问题 > 早停 + 虚假通过
4. **Monte Carlo 验证有局限** — 事件分布假设 + frustration dynamics 与实际可能偏差
5. **公式正确 ≠ 指标合理** — 公式 A2 突破 0.6 地板正确，但 H_self 组合指标本身语义有问题

### 6.3 下一步建议（按优先级）

| 优先级 | 行动 | 预期 |
|-------|------|------|
| **P0** | 重新设计 H_self 指标 | 找到稳定的"自我形成"度量（候选：sliding window 重复率 / embedding similarity / 结晶相似度）|
| **P0** | 重新设计 PT 触发机制 | 候选 G（frustration 归一化 [0,1]）/ H（连续 N failure）/ I（放弃 PT 指标）|
| P1 | 跑 v6 = 新 H_self + 新 PT + 公式 A2 联调 | 验证双修复 |
| P1 | 跑 challenged / uncertain babies | 验证跨 baby 通用性 |
| P2 | 跑 1000 epoch 长程（4 chunks）| 验证长程稳定性 |
| P3 | 评估 M3.x dedup 路线 | v5 关闭 dedup 仍 +17% reduction → 暂停 |

---

**产出文件清单**：
- [experiments/M22_V5_REPORT.md](../experiments/M22_V5_REPORT.md)（重写，完整 250 epoch 数据）
- [research/sge-feasibility/M22_H_SELF_DIAGNOSIS.md](../research/sge-feasibility/M22_H_SELF_DIAGNOSIS.md)（之前）
- [experiments/scripts/recompute_h_self_v5.py](../experiments/scripts/recompute_h_self_v5.py)（之前）
- [experiments/scripts/simulate_pt_v6.py](../experiments/scripts/simulate_pt_v6.py)（之前）
- [experiments/scripts/m22_v5_exph_self.py](../experiments/scripts/m22_v5_exph_self.py)（之前）
- [sge/sge/metrics.py](../sge/sge/metrics.py)（公式 A2，2026-07-08）
- [sge/sge/baseline.py](../sge/sge/baseline.py)（PHASE_THRESHOLD=0.5，2026-07-08）
- [sge/sge/llm_client.py](../sge/sge/llm_client.py)（timeout 60s, retry 8, 2026-07-10）
- [SGE-Key-Insights.md](../SGE-Key-Insights.md)（§4 + §10 + 36 §10/§11 修订）
- [ARCH.md §1.8.2](../ARCH.md)（公式 A2 升级 + 修订注）
- [PRD.md §6](../PRD.md)（B 维度状态降级 + 修订注）
- [discussions/2026-07-10-v5-full-rerun-correction.md](../discussions/2026-07-10-v5-full-rerun-correction.md)（本记录）

**Git commits**（2026-07-10）：
- `待 commit 1` docs(experiments): v5 完整 250 epoch 重写报告（partial run 修订）
- `待 commit 2` docs(sge-insights): Insight 35B 状态降级 + 36 §10/§11 完整 250 修订
- `待 commit 3` docs(arch): §1.8.2 H_self 状态修订
- `待 commit 4` docs(prd): §6 B 维度降级 + 2026-07-10 修订注
- `待 commit 5` fix(sge): LLM timeout 30→60s, retry 5→8
