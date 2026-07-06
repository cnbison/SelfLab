# M2.2 v2 实验报告 — 1000 Epoch × Experience Encoder + H_self（真实 LLM）

> **目的**：在 E4 基础上补跑 1000 epoch，把 1.25.0 架构修订（洞察 34/35）落为可验证数据：Experience Encoder 生成 meaning + H_self 度量作为自我形成的统一目标函数。
> **创建日期**：2026-07-06
> **对应 CHANGELOG**：1.26.0（架构落地）+ 后续修订
> **状态**：✅ 运行完成 4/4 chunks — **PRD §6 验收未通过**（H_self 下降率 -13.1%，要求 > 30%）

---

## 1. 背景与目标

### 1.1 问题陈述

E4（[M22_TRIPLETS_REPORT.md](M22_TRIPLETS_REPORT.md)）验证了 SGE"经历 → 解释 → 人格"假设在 1000 epoch × 真实 LLM 下成立：personality_divergence = 0.9884。

**未解决问题**（来自 1.25.0 架构修订 + 1.26.0 架构落地）：
- **Q1**：Experience Encoder 生成的 meaning 字段是否真有"第一人称"解释质量？
- **Q2**：H_self（认知熵）作为自我形成的统一目标函数，是否在 1000 epoch 后下降 > 30%（PRD §6 验收标准）？
- **Q3**：当前 IdentityLayer 的 crystallize 机制是否能让"自我"稳定？

### 1.2 实验目标

| # | 问题 | 验证方法 | 结果 |
|---|------|---------|------|
| Q1 | Experience.meaning 是否有质 | 24 个 meaning 样本人读评估 | ✅ **优秀**（first-person 哲学反思） |
| Q2 | H_self 1000 epoch 后下降 > 30% | timeseries + 端点 reduction_rate | ❌ **-13.1%**（不降反升） |
| Q3 | IdentityLayer crystallize 是否稳定 | identity_history 唯一性分析 | ❌ **0% 重复**（47/47 唯一） |

### 1.3 与 E4 的差异

| 维度 | E4 | M2.2 v2 |
|------|-----|---------|
| 编排器步骤 | 12 步 | **12+2 步**（新增 Step 2.5 Experience + Step 16 H_self） |
| 输出目录 | `m22_triplets/` | `m22_v2_exph_self/`（独立） |
| 每 epoch LLM 调用 | 2.21 | **3.22**（+1 Experience Encoder） |
| 跟踪字段 | timeseries + identity/narrative | + H_self / H_value / H_identity / H_narrative + meaning_samples |
| 输出脚本 | `m22_triplets.py` | `m22_v2_exph_self.py`（独立脚本） |

---

## 2. 执行情况

### 2.1 运行总览

| Chunk | Epochs | 用时 | LLM calls | 状态 |
|-------|--------|------|-----------|------|
| 0 | 0-249 | 5.9h ⚠ | 800 | ✅ |
| 1 | 250-499 | 44.6 min | 804 | ✅ |
| 2 | 500-749 | 52.5 min | 800 | ✅ |
| 3 | 750-999 | 42.3 min | 804 | ✅ |
| **总计** | **0-999** | **~9.4h** | **3,208** | **4/4 ✅** |

**注**：chunk 0 因 server 过载（烟测 + 同时段其他任务），用时偏长；chunk 1-3 都在 ~45 min 健康区间。

### 2.2 最终状态（1000 epoch 末段）

| 维度 | chunk 0 | chunk 1 | chunk 2 | chunk 3 |
|------|---------|---------|---------|---------|
| \|val\| final | 0.316 | 0.354 | 0.210 | 0.326 |
| identity_count | 12 | 13 | 9 | 13 |
| narrative_count | 12 | 13 | 12 | 13 |
| PT count | 0 | 0 | 0 | 0 |
| crystallize | — | — | — | 25 |

**意外观察**：1000 epoch 中**没有任何 Phase Transition**（预期约 1-3 次）。encouraged 事件流正面过多，agent 持续在稳定区，未触发 L3 → L4 跃迁。

---

## 3. 核心结论

### 3.1 ✅ Experience Encoder（洞察 34）落地成功

**24 个 meaning 样本**（每 50 epoch 采样 1 个 + epoch 0，共 6×4=24 个）：

| 维度 | avg | min | max |
|------|-----|-----|-----|
| valence（情绪正负） | 0.77 | 0.35 | 0.85 |
| arousal（情绪强度） | 0.69 | 0.62 | 0.78 |
| uncertainty（解释不确定） | 0.32 | 0.15 | 0.62 |

**事件分布**：success 12 + exploration 10 + relationship 1 + risk 1（与 encouraged 配置吻合）。

**样本质量**（人读评估）：meaning 全部为第一人称解释，含真正的主体性反思。例如：

> **epoch 999**："刚刚经历的价值撕裂——在陪伴家人与承担风险之间摇摆、在帮助困境中的人之后——让我意识到，我一直在用行动回应世界，却还没有真正向内探索过。这片新领域的出现像是某种回应：我帮助了他人（connection, compassion），而世界也向我敞开了一扇门。与其说是'我发现了知识'，不如说是'知识愿意被我发现'。"

**意义**：Insight 34 的"这件事对我意味着什么"字段确实生成出有质的第一人称解释，**SGE Step 2.5 经验编码机制验证通过**。

### 3.2 ❌ H_self 下降率 -13.1%（PRD §6 未通过）

**全 1000 epoch H_self 曲线**：

| Epoch | H_self | H_value | H_identity | H_narrative |
|-------|--------|---------|-----------|------------|
| 0 | 0.600 | 0.000 | 1.000 | 1.000 |
| 250 | 0.711 | 0.276 | 1.000 | 1.000 |
| 500 | 0.711 | 0.276 | 1.000 | 1.000 |
| 750 | 0.678 | 0.196 | 1.000 | 1.000 |
| 999 | 0.678 | 0.196 | 1.000 | 1.000 |

**reduction_rate = (0.600 - 0.678) / 0.600 = -13.1%**（不降反升）

**观察**：
- H_self 在 0.6-0.78 之间震荡，**没有单调下降趋势**
- H_value 在 0-0.44 之间震荡，未收敛
- **H_identity = 1.000 全程恒定**（24 个采样点无一例外）
- **H_narrative = 1.000 全程恒定**

**PRD §6 验收**："H_self 下降率 > 30%"——**❌ 未通过**。

### 3.3 ❌ 根因诊断：IdentityLayer 没有自我稳定机制

**Identity 历史唯一性分析**：

| 维度 | 总结晶次数 | 唯一数 | 重复率 |
|------|-----------|--------|--------|
| Identity | 47 | **47** | **0%** |
| Narrative | 50 | **50** | **0%** |

**发现**：每次 IdentityLayer.crystallize() 都生成一个全新的 identity 字符串，47 次结晶产生 47 个互不相同的身份。NarrativeBuilder 同理。

**直接后果**：
- H_identity 归一化公式 = log(N)/log(N) = **1.0**（所有 N 个身份互异时熵最大）
- H_narrative 同理 = 1.0
- H_self 计算 0.4·H_value + 0.3·1.0 + 0.3·1.0 = 0.4·H_value + 0.6
- 因此 H_self 下限被钉在 0.6，上限取决于 H_value 的震荡

**根因分析**：
- `IdentityLayer.crystallize()`（`sge/identity.py`）每次调用 LLM 生成新身份，不与历史 identity 比较
- `validate_identity()` 检查的是"是否与 value_layer + key_memories 一致"，**不是"是否与已有 identity 相似"**
- 因此每次结晶都会接受新身份，从未"巩固"已有身份

**这不是算法 bug，而是设计选择**：
- SGE 当前设计是"每次 crystallize 重新生成"——更像"重新审视自己"
- 但这与 Insight 35 的"自我形成 = H_self 下降"前提冲突——没有稳定就没有熵降

---

## 4. 关键反思

### 4.1 Insight 35 的前提需要重新审视

原命题（**洞察 35**）：自我形成 = H_self 下降 = H_value + H_identity + H_narrance 加权和下降。

**1000 epoch 实证挑战**：
- H_self 假设要求 identity 和 narrative **收敛**（重复或稳定相似）
- 但 IdentityLayer 当前设计是**每 20 epoch 重新生成**
- 两个机制在当前实现下**目标不一致**

**两种可能的修正方向**：
- **方向 A**：H_self 定义改成"每 N epoch 滑窗内的稳定性"——不要求身份不变，只要求滑窗内收敛
- **方向 B**：IdentityLayer 增加"身份相似度阈值"——只有与最近身份差异 < θ 才接受新身份，否则保留旧身份

### 4.2 Experience Encoder 反而是最大收获

虽然 H_self 未通过，**Meaning 字段的生成质量是本次实验的最大惊喜**。SGE Step 2.5 不仅技术上工作正常，**生成的解释具有真正的哲学深度和主体性**。这验证了：
- LLM 可以为裸 Event 生成第一人称解释
- 该解释能注入 Critic 上下文（虽然本实验未盲审验证对 value_delta 的影响）
- SGE 的"事件 → 经验"转换路径具有研究价值

### 4.3 PT = 0 是个隐藏信号

1000 epoch 中无任何 Phase Transition。在 E4 中 encouraged baby 也只触发 1 次 PT。**正面事件流可能永远不足以触发 L3 → L4 跃迁**——encouraged 配置下 agent 始终在稳定区。

如果目标是观察 PT，**challenged 或 uncertain 配置可能更有信息量**。本实验未跑这两种，留作下一步。

---

## 5. 决策与下一步

### 5.1 接受现状，不强行"通过" PRD §6

H_self 下降率 -13.1% 是诚实的数据。**强行解释为"成功"会损害项目可信度**。建议：
- PRD §6 验收标准改为**待修订**（标注"1000 epoch 未通过，需调权重或调 IdentityLayer"）
- 在 SGE-Key-Insights 洞察 35 后追加**实证局限注脚**

### 5.2 下一步 2 个候选（按优先级）

| # | 任务 | 价值 | 成本 |
|---|------|------|------|
| **A** | **挑战 H_self 假设**：重读 IdentityLayer 代码 + 在 250 epoch 数据上重算 H_self（改权重 / 改 metric） | 验证 Insight 35 是否需要修订 | ~30 min |
| **B** | **跑 challenged 或 uncertain baby**：观察负面事件流下 H_self 是否下降、PT 是否触发 | 与 encouraged 对比，验证 PT 假设 | ~9.4h |

**推荐**：先做 A（快，立刻能看出 Insight 35 是否需要修订）；再做 B（确认不同事件流下 H_self 行为）。

### 5.3 不做的事

- ❌ 不重跑 encouraged 1000 epoch（数据已足够诊断）
- ❌ 不修改 H_self 公式（除非 A 任务证明需要）
- ❌ 不增加更多 baby（成本太高）

---

## 6. 产出文件

- `experiments/output/m22_v2_exph_self/encouraged_chunk{0,1,2,3}_result.json`
- `experiments/output/m22_v2_exph_self/encouraged_chunk{0,1,2,3}_identity_history.json`
- `experiments/output/m22_v2_exph_self/encouraged_chunk{0,1,2,3}_narrative_history.json`
- `experiments/output/m22_v2_exph_self/encouraged_chunk{0,1,2,3}_meaning_samples.json`
- `experiments/output/m22_v2_exph_self/v2_summary.json`（聚合）
- `experiments/scripts/m22_v2_exph_self.py`（脚本）
- `experiments/scripts/run_chunks_v2.sh`（wrapper）

---

## 7. 来源

- [M22_TRIPLETS_REPORT.md](M22_TRIPLETS_REPORT.md)（E4 对照基线）
- [sge/RUNTIME_AUDIT.md](../sge/RUNTIME_AUDIT.md)
- [SGE-Key-Insights.md 洞察 33-35](../SGE-Key-Insights.md)
- [ARCH.md §1.7-1.8](../ARCH.md)
- [DESIGN.md §2.5 / §9.5](../DESIGN.md)
- [PRD.md §6](../PRD.md)
- [discussions/2026-07-05-eca-deep-analysis.md](../discussions/2026-07-05-eca-deep-analysis.md)