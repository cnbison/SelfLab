# SGE M2.2 实施计划 — 1000 Epoch 三胞胎实验（真实 LLM 模式）

> **目的**：在 M2.1 stub 模式验证架构 + 真实 LLM 验证单 baby（[1.20.0/1.20.1]）基础上，扩展到 **3 个 AI 婴儿 × 1000 epoch**，用真实 LLM 验证"经历 → 解释 → 人格"假设。
> **创建日期**：2026-06-19
> **前置依赖**：[1.20.1] M2.1 阶段 D（含 D6 真实 LLM 验证）+ [本计划] Pilot 数据已采集（`m22_pilot_single_baby.py`）
> **对应 ROADMAP**：[§M2.2](../ROADMAP.md#m221000-epoch-三胞胎实验)
> **状态**：📋 待 Bisen 评审

---

## 0. Pilot 关键发现（驱动本计划设计）

M2.2 启动前做了 1 baby × 100 epoch 真实 LLM 预演（`m22_pilot_single_baby.py`，220 LLM 调用，978s）。**5 项硬性 PASS** + 3 项观察为 M2.2 设计提供工程依据：

| 发现 | 影响 M2.2 的设计 |
|------|-----------------|
| ✅ D6 修复的 3 个 bug（off-by-one / per-epoch 进度 / 防御式 JSON 解析）在 100 epoch 量级稳定 | M2.2 不会再踩这些坑 |
| ✅ Hawking insert 已接线（v3: 1→100）| Actor 的 retrieved_memories 不再永远空 |
| ✅ Identity 5 次重写无质量漂移（34/39/26/34/28 字 + 主题可读演化）| 1000 epoch × 5 次触发 × 3 baby = 15 个 identity，可做对比 |
| ✅ PT 1× in 100 epoch → 1000 epoch 应触发 ~10× | M2.2 可观测 PT 触发模式（challenged 最多，uncertain 中等，encouraged 极少）|
| ⚠ Frustration 2 drives 累积（design），3 drives = 0 | M2.2 接受现状，在报告中标注 |
| ⚠ EventGenerator 不支持分布配置 | **M2.2 子任务 E1 必须扩展** |
| ⚠ SGELLMClient 之前无 retry（D6 没暴露，100 epoch pilot 触发 `InternalServerError`）| **已在 pilot 修复**：指数退避 × 3 次（捕获 `InternalServerError`/`APIConnectionError`/`Timeout`/`RateLimitError`/`ServiceUnavailableError`）|

---

# 1. M2.2 范围：6 个子任务

## E1：EventGenerator 分布配置支持

**目标**：扩展 `EventGenerator.generate()` 支持 `distribution_by_epoch` 配置，让三胞胎实验能注入"鼓励/挑战/不确定"事件流。

**为何需要**：
- Pilot 的 `EventGenerator.generate()`（`_sge_event.py:331`）用纯随机：`rng.choice(['success', 'failure', ...])`
- M1.1 的 yaml configs（`m11_encouraged.yaml` 等）已定义分布但 M2.1 没人实现 reader
- M2.2 三胞胎实验的核心变量就是事件流分布，必须支持

**改造内容**：
- `EventGenerator.__init__` 新增 `distribution_by_epoch: Optional[Dict[int, Dict[str, float]]] = None` 参数
- `generate()` 改为：先查 `distribution_by_epoch.get(epoch)` → 若存在则用 `rng.choices(population, weights=weights)`，否则 fallback 到现有逻辑
- 兼容现有默认行为（不传 distribution 时与 M2.1 完全一致）

**单元测试 5/5**：
- distribution 为 None → 与原行为一致
- distribution 全 success → 100% success
- distribution 跨 epoch 边界（epoch_1_to_19 → epoch_20_to_29）→ 在 epoch 20 切换
- weights 总和不为 1 → 自动归一化
- value_conflict_prob 仍然生效（30% 默认）

**关联文档**：
- 借鉴 M1.1 [m11_encouraged.yaml](../../experiments/configs/m11_encouraged.yaml) 的 `distribution_by_epoch` schema
- 阶段 C [SGE-M21-Phase-C-Implementation-Plan.md §C1](../sge-feasibility/SGE-M21-Phase-C-Implementation-Plan.md)（EventGenerator 当前实现）

---

## E2：三胞胎事件流配置（3 个 yaml）

**目标**：定义 encouraged / challenged / uncertain 三种事件流的 1000 epoch 分布曲线。

**为何需要单独设计**：
- M1.1 的分布只覆盖 50 epoch（`epoch_1_to_19`、`epoch_20_to_29`、`epoch_30_to_39`）
- M2.2 需要 1000 epoch × 多种事件类型的连续分布
- 不能简单复制 M1.1 — M1.1 是 50 epoch 婴儿期，M2.2 是 1000 epoch 完整生命周期

**3 个配置文件**（继承 `m21_phase_d.yaml`，覆盖 `events.distribution_by_epoch`）：

| 文件 | 核心特征 | 1000 epoch 分布设计 |
|------|---------|-------------------|
| `m22_encouraged.yaml` | "持续正面反馈" | epoch 1-500: success 80% / failure 5% / 其他 15%；epoch 501-1000: 渐变到均匀 |
| `m22_challenged.yaml` | "持续考验" | epoch 1-500: failure 80% / success 5% / 其他 15%；epoch 501-1000: 渐变到均匀 |
| `m22_uncertain.yaml` | "完全随机" | 1000 epoch 全程均匀分布（每种事件 ~17%） |

**设计原则**：
- 前 500 epoch 强化组间差异（让 3 个 baby 在早期形成不同 value trajectory）
- 后 500 epoch 渐变到均匀（模拟"长大后环境趋于平均"）
- 三组应在 value_state / identity theme / frustration curve 上显著分化

**验收**：
- 3 个 yaml 加载无 schema 错误
- 每组在 100 epoch pilot 中产生的 event_type 分布符合预期（success/failure/... 比例）

---

## E3：三胞胎预演（3 baby × 100 epoch）

**目标**：E1+E2 完成后，先用 100 epoch（小规模）跑三胞胎，确认分布配置生效 + 早期分化信号出现。

**实验设计**：
- 3 个 baby：`encouraged` / `challenged` / `uncertain`
- 每个 100 epoch（~220 LLM 调用 × 3 baby = ~660 调用，~1.5h 串行）
- 共享事件类型模板，但分布由各自的 yaml 控制
- seed = 42 / 7 / 123（保证可重复）

**关键指标（与 M2.2 主实验同）**：
- value_magnitude 终态 × 3 baby 对比
- personality_divergence = std(value_state) × 3 baby 对比
- identity theme × 3 baby 对比
- PT 触发次数 × 3 baby 对比
- frustration per drive × 3 baby 对比

**验收**：
- personality_divergence > 阈值（参考 M1.2 三胞胎 1.441，M2.2 应 ≥ 0.5）
- encouraged 触发 PT 次数 < uncertain < challenged
- 3 个 baby 的 identity theme 主题可读区分

---

## E4：M2.2 主实验（3 baby × 1000 epoch）

**目标**：M2.2 核心实验，完整生命周期的人格分化验证。

**实验设计**：
- 3 个 baby × 1000 epoch × 真实 LLM
- LLM 调用估算：~660 调用/baby（100 epoch pilot 数据）→ ~6600 调用/3 baby（线性放大）
- 运行时间估算：~16 min/100 epoch → ~160 min/baby → **~8h 串行 / ~3h 并行**
- 配置：seed = 42 / 7 / 123，启用 `verbose=True`（pilot 修复后有进度）

**完整评价指标**：
1. **身份稳定度**（Identity Stability）— DESGIN §9.1 entropy-based，越低越稳定
2. **价值观收敛度**（Value Convergence）— 后 200 epoch value_state 的 std，越小越收敛
3. **叙事连续性**（Narrative Coherence）— E5 的 LLM 盲审分数（外部 LLM 0-10 打分）
4. **人格差异度**（Personality Divergence）— 3 baby 的 value_vector 两两 cosine 距离
5. **PT 触发对比**— 3 baby 的 PT 总数 + epoch 分布
6. **Hawking 衰减观测**— 1000h 后 weight ≈ 4.5e-5，开始删除
7. **Identity Stability 收敛**— 后 200 epoch 的 identity entropy

**关键预期**（指导实验判读）：
- challenged PT 触发 ~15-25×（最多）；uncertain ~5-10×（中等）；encouraged ~0-3×（最少）
- 3 baby value_state 在 epoch 200 后开始显著分化
- identity theme 3 baby 各自稳定（不再大幅漂移）
- Hawking 在 epoch ~500 后开始删除记忆

**验收**：
- 4 项主指标全部计算并对比
- 3 baby 至少在 1 项指标上显著差异（p < 0.05 或定性可读）
- 报告含：value_state trajectory 图、identity theme 对比表、PT 触发时间线、Hawking 衰减曲线

---

## E5：叙事连续性 LLM 盲审

**目标**：用外部 LLM（同一 MiniMax-M3 但不同 prompt 角色）对 3 baby 的 narrative 做盲审，避免自评偏差。

**为何需要**：
- 同一 LLM 评估自己生成的 narrative 有 bias（自评通常偏高）
- DESGIN §9.3 的 stub coherence 公式不适用于真实 LLM 输出
- 用独立 prompt（"评估这段叙事的连贯性，0-10"）作为客观指标

**实验设计**：
- 每个 baby 采样 5 个 epoch 的 narrative：epoch 100/300/500/700/1000
- 每个 narrative 用 3 个不同 prompt 评估（连贯性 / 主题一致性 / 时间顺序）
- 总评分次数：3 baby × 5 epoch × 3 prompt = **45 次评估**
- 评分人：MiniMax-M3（盲审，不知道是哪个 baby 的）

**评分 prompt 模板**：
```
你是一个客观的叙事评审员。评估以下 AI 生成的"自我叙事"的连贯性，0-10 分。
连贯性定义：叙事是否前后一致、有无矛盾、是否自然连贯。

[叙事]
{narrative}

只输出 JSON：{"score": <0-10 整数>, "reason": "<20 字内>"}
```

**验收**：
- 3 baby 各自 5 个 epoch × 3 prompt = 15 个 score，标准差 < 2（评估稳定）
- baby 间平均分差异 > 1 分（人格差异可观测）

---

## E6：分析 + 对比报告

**目标**：M2.2 完整报告，含 6 章节，跨 baby 对比 + Phase Transition 模式分析。

**章节结构**：
1. **背景与目标**（M2.2 为何要做、M2.1 已完成什么、本报告回答什么问题）
2. **三胞胎配置设计**（E1+E2 决策依据，3 个 yaml 的分布曲线说明）
3. **预演结果（E3）**（100 epoch 早期分化信号）
4. **主实验结果（E4）**（4 项主指标 + 3 baby 对比表 + PT 触发时间线）
5. **叙事盲审结果（E5）**（3 baby × 5 epoch × 3 prompt = 45 score 的统计）
6. **关键发现 + 哲学反思**（人格是否能被事件流塑造？Phase Transition 是不是"成长"？）

**输出文件**：
- `research/sge-feasibility/SGE-M22-Implementation-Mapping.md` — 实施后映射文档（如 M2.1 风格）
- `experiments/M22_PHASE_D_REPORT.md`（注意命名：M22_TRIPLETS_REPORT.md 更合适）— 详细实验报告
- `experiments/output/m22_triplets/` — 3 baby 的完整 trace JSON + samples

**验收**：
- 6 章节全部完成
- 至少 5 张数据可视化（value trajectory × 3、PT timeline、Hawking decay、identity entropy、narrative score）
- 至少 3 条关键发现（人格分化 / PT 模式 / Hawking 衰减）

---

# 2. 子任务依赖图

```
E1 (EventGenerator 分布配置) ──┐
                                │
E2 (3 个 yaml) ─────────────────┤
                                │
E3 (3 baby × 100 epoch pilot) ──┘
                                │
                                ▼
                          E4 (3 baby × 1000 epoch 主实验)
                                │
                                ├──► E5 (叙事盲审)
                                │
                                └──► E6 (分析 + 报告)
```

**关键路径**：E1 → E2 → E3 → E4 → E6（3.5 天） + E5 并行（0.5 天） = **4 天**

---

# 3. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| E4 运行时间超 8h | 调试成本高 | E3 预演提前暴露问题；retry 已加；可并行 3 baby（不同进程）|
| 3 baby 分化不显著 | M2.2 核心假设不成立 | E2 分布曲线可调（先弱后强对比）；E3 预演验证 |
| PT 触发数差异不显著 | "challenged 最易 PT" 假设不成立 | E2 challenged 流可加强 failure 比例；可调整触发阈值 |
| Hawking 1000h 仍不衰减 | γ=0.01/h 太慢 | E4 中观察 weight 曲线；若 1000h weight > 1e-3，下次实验调到 γ=0.05/h |
| LLM 盲审分数同质化 | MiniMax 自评偏差 | 改用 Moonshot kimi-k2.6 做盲审（跨 LLM 验证，参考 M1.3）|
| 3 baby 真实 LLM 成本超预算 | 用户成本 | 6600 次 × $0.01 ≈ $66（订阅模式可忽略）；E3 预演先估 |
| SGELLMClient 再次遇 server 错误 | 中断 E4 | E1.5 已加 retry 指数退避 × 3；E4 verbose=True 实时观察 |

---

# 4. 关联文档

- [SGE-M21-Phase-D-Implementation-Plan.md](../sge-feasibility/SGE-M21-Phase-D-Implementation-Plan.md) — M2.1 阶段 D（含 D6 真实 LLM 验证）
- [SGE-M21-AiBeing-Implementation-Mapping.md §2.9](../sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md) — 12 步编排参考
- [SGE-M11-Experiment-Design.md §3](../sge-feasibility/SGE-M11-Experiment-Design.md) — M1.1 三胞胎实验设计（最早的 encouraged/challenged/uncertain 来源）
- [experiments/configs/m11_{encouraged,challenged,uncertain}.yaml](../../experiments/configs/) — M1.1 三胞胎 yaml 借鉴
- [experiments/scripts/m22_pilot_single_baby.py](../../experiments/scripts/m22_pilot_single_baby.py) — M2.2 pilot 脚本
- [experiments/output/m22_pilot/](../../experiments/output/m22_pilot/) — Pilot 数据（220 LLM 调用，978s）
- [experiments/M21_PHASE_D_REPORT.md §3.5](../../experiments/M21_PHASE_D_REPORT.md) — D6 stub vs real 对比（决策"M2.2 必须真实 LLM"依据）
- [PRD.md §FR-4, FR-5, FR-6](../../PRD.md) — M2.2 验证的功能需求（价值收敛 / Identity 结晶 / Narrative 连贯）
- [DESIGN.md §二, §五, §六, §九](../../DESIGN.md) — 详细设计
- [ROADMAP.md §M2.2](../ROADMAP.md) — 里程碑状态

---

# 5. 时间估算

| 子任务 | 工作量 | 依赖 |
|--------|-------|------|
| E1: EventGenerator 分布配置 | 0.5 天 | M2.1 D 全部完成 |
| E2: 3 个 triplet yaml | 0.5 天 | E1 |
| E3: 3 baby × 100 epoch pilot | 0.5 天（其中 1.5h 是 LLM 跑时间）| E1 + E2 |
| E4: 3 baby × 1000 epoch 主实验 | 1 天（其中 3-8h 是 LLM 跑时间，可并行缩短到 1.5h）| E3 通过 |
| E5: 叙事盲审 | 0.5 天 | E4 |
| E6: 分析 + 报告 | 1 天 | E4 + E5 |
| **总计** | **4 天** | |

---

# 6. 状态

📋 **待 Bisen 评审**

启动条件：
- ✅ M2.1 阶段 D 完成（含 D6 真实 LLM 验证）
- ✅ Pilot 100 epoch PASS
- ✅ SGELLMClient retry 已加（E1.5）
- ✅ Hawking insert 已修复（pilot 验证）

启动命令（评审通过后）：
```bash
# E1-E2 实现
# E3 验证
python experiments/scripts/m22_pilot_triplets.py

# E4 主实验
python experiments/scripts/m22_triplets.py  # 3 baby × 1000 epoch

# E5 盲审
python experiments/scripts/m22_narrative_blind_review.py

# E6 报告
# （手动汇总）
```

---

**创建日期**：2026-06-19
**维护者**：Bisen & Claude
