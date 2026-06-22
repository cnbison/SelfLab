# SGE（Self Genesis Engine）路线图

文档版本：v0.1
项目版本：[0.3.0]（权威版本见 [CHANGELOG.md](./CHANGELOG.md)）

日期：2026-06-15

状态：草案

> **版本约定**：项目级文档的"项目版本"以 [CHANGELOG.md](./CHANGELOG.md) 为权威源；"文档版本"为该文档自身的迭代号，两者独立管理。

---

# 总览

SGE 的研究与开发分为四个阶段，从理论验证到工程实现逐步推进。

```
Phase 0: 理论奠基（已完成）
    ↓
Phase 1: 最小验证（当前）
    ↓
Phase 2: 完整实验
    ↓
Phase 3: 系统完善
```

---

# Phase 0：理论奠基（已完成）

**时间**：2026-06 及之前

**目标**：建立 SGE 的理论基础和研究框架

**已完成的里程碑**：

- [x] 研究纲领 v0.1 — 核心 Self 模型定义（Self = Memory + Reflection + Values + Identity + Narrative）
- [x] 研究纲领 v0.2 — 双系统认知架构、预测加工理论、SGE 系统设计
- [x] 认知架构综述 — 8 个经典认知架构的系统性分析
- [x] A→B 调研分析 — 认知状态向量、学习迁移框架、与 SGE 的关联性
- [x] 关键洞察集 — [19 条核心洞察](./SGE-Key-Insights.md)（实然/应然、元价值、暗知识、发育生物学等）
- [x] 工程可行性评估 — 逐模块可行性分析，Value Layer 为最大风险
- [x] 现有系统空白分析 — 确认 SGE 在现有技术生态中是明确空白
- [x] AiBeing 借鉴分析 — 8 个可直接复用的工程机制
- [x] 金观涛真实性哲学借鉴 — 元价值、拱桥、暗知识的工程映射
- [x] 项目文档结构重组 — research/ 按主题分为 4 个子目录

**产出物**：
- `SGE-Key-Insights.md`（核心洞察集）
- `research/sge-core/`（5 篇核心研究文档）
- `research/sge-feasibility/`（3 篇可行性评估）
- `research/sge-learning/`（3 篇借鉴分析）
- `research/cognitive-architecture/`（4 篇认知架构调研）
- `references/`（3 篇参考资料）
- `PRD.md`（产品需求文档）

---

# Phase 1：最小验证

**时间**：待定（建议 2-4 周）

**目标**：验证 SGE 最核心的假设——Value Layer 能否产生有意义的价值涌现

## 里程碑

> **Epoch 数字约定**：本项目所有 Epoch 引用以 [PRD §5.1](./PRD.md) Epoch 数字约定表为权威源。本节里程碑的 Epoch 数与之一致。

### M1.1：Value Layer 原型

**验证目标**：价值观向量是否随经历变化？变化是否有意义？

**涉及 FR**：FR-1（Event Generator 基础）、FR-2（情节记忆）、FR-4（**Value Layer 核心**）、FR-7（Critic 基础）、FR-8（Time Metabolism）、FR-9（Thermodynamic Noise）、FR-10（双 LLM 架构）

**实验设计**：
- 单个 AI 婴儿
- 50-100 个 Epoch
- 简单事件流（包含价值困境事件）
- 只关注 Value Layer，暂不实现 Identity 和 Narrative

**技术方案**：
- 使用小模型（Haiku / GPT-4o-mini）降低成本
- 复用 AiBeing 的 EMA 机制追踪价值观演化
- 复用 AiBeing 的 Hebbian Learning 积累行为模式
- 元价值初始种子：真实=0.5, 自由=0.5

**验收标准**：
- 价值观向量在 100 Epoch 后显著不同于初始状态
- 变化方向可从事件历史中追溯（非随机漂移）
- 价值观在同类事件中表现一致（非噪声）

**成本估算**：$1-10（小模型）

**风险**：
- 如果价值观只是随机漂移 → 停止，重新设计 Value Layer
- 如果价值观固定不变 → 检查事件多样性，调整 EMA 参数

### M1.2：三胞胎分化实验

**验证目标**：不同经历流是否产生不同人格？

**前置条件**：M1.1 通过

**涉及 FR**：FR-1（动态价值困境事件）、FR-4（Value Layer 分化验证）

> **AI 婴儿组定义**（与 [DESIGN §8.2 BABY_PROFILES](./DESIGN.md) 一致）：
>
> | 婴儿组 ID | 中文 | 描述 | 事件生成器 |
> |----------|------|------|-----------|
> | `encouraged` | 鼓励组 | 持续正面反馈 | `generate_positive_biased_event()` |
> | `challenged` | 挑战组 | 持续失败和挫折 | `generate_negative_biased_event()` |
> | `uncertain` | 不确定组 | 高度不确定，奖惩随机 | `generate_random_event()` |
>
> **命名说明**：DESIGN 中"challenged"对应中文"挑战/失败"——本项目刻意用"challenged"（挑战）而非"failed"（失败），强调这是"被考验"而非"被打败"，符合 SGE "经历 + 解释 = 人格"的立场。

**实验设计**：
- 3 个 AI 婴儿（`encouraged` / `challenged` / `uncertain`）
- 100 个 Epoch
- 相同的元价值初始种子（真实=0.5, 自由=0.5），不同的事件流

**验收标准**：
- 3 个 AI 婴儿的价值观分布显著不同
- 人格差异度 > 预设阈值（[PRD §6.1 4.1.4](./PRD.md)）

**成本估算**：$3-30

**状态**：✅ **已完成 (2026-06-17)**
- 3 组 × 80 Epoch 全部通过,涌现幅度 0.642-0.848,方向一致性 0.954-0.969
- 平均人格差异度 1.441(阈值 0.5 的 2.88×)
- 报告:[experiments/M12_TRIPLET_REPORT.md](./experiments/M12_TRIPLET_REPORT.md)
- **关键发现**:[洞察 26](./SGE-Key-Insights.md) — 6 维度非对称响应 + compassion 韧性现象
  - safety/justice/autonomy 是高敏感维度(spread > 1.5)
  - compassion 是唯一在所有事件流下保持正值的"韧性"维度
  - 不确定性 > 失败 对安全感的伤害(uncertain safety -0.91 > challenged -0.87)
  - → Phase 2 价值层应采用**异质化 EMA**

### M1.3：反合理化测试

**验证目标**：反思是否真的改变行为（而非只是生成漂亮的反思文本）？

**前置条件**：M1.1 通过

**涉及 FR**：FR-3（Reflection Layer）、FR-4（Value Layer 在反思后的变化）

> **哲学对应**：本里程碑验证 SGE 的"**拱桥**"机制（[Glossary §拱桥](./references/Glossary.md)）——Reflection Layer 能否真的连接暗知识（Hebbian）与显性知识（Value Layer），使反思有行为后果。

**实验设计**：
- 给 AI 与它价值观矛盾的反馈
- 观察它是否真的修正（而非只是口头认同）

**验收标准**：
- 反思后的行为选择与反思前不同
- 不是"自我合理化"（有反合理化验证）

**状态**：✅ **已完成 (2026-06-17)**
- 实施最小化 Reflection Layer(call_reflector + should_reflect + blend_reflection)
- 启用 7 个 contradiction_feedback 事件 + 触发条件(intensity/delta_magnitude)
- 80 Epoch,seed=42,与 m11_m12_encouraged 基线对比
- 报告:[experiments/M13_REFLECTION_TEST_REPORT.md](./experiments/M13_REFLECTION_TEST_REPORT.md)
- **核心验证**:
  - safety 在矛盾反馈下累计下降 0.51(从 +0.65 到 +0.14)— 反思**真的改变行为**
  - compassion 二次验证:在 explicit 攻击下仍最稳定(强化 [洞察 26](./SGE-Key-Insights.md))
  - 元认知萌芽:Epoch 50 Reflector 识别出"接受自主是幻觉"的自指性矛盾
- **关键发现** → [洞察 27](./SGE-Key-Insights.md):拱桥机制成立,反思是真实机制非装饰

**Phase 1 进度**:M1.1 ✅ / M1.2 ✅ / **M1.3 ✅** → Phase 1 全部完成

---

### M1.4:REVISIT 触发专项测试(Phase 1.5 / M2.1 前置)

**验证目标**:洞察 27 指出 M1.3 中 REVISIT 触发率 0% — 这到底是实验设计问题(prompt 偏向 / 事件强度不够)还是 AI 真的"从不根本性反思"?

**前置条件**:M1.3 通过

**涉及 FR**:FR-3(Reflection Layer)— REVISIT 机制是 M2.1 Narrative Layer"相变"设计的工程基础

**为什么必须做**:
- 洞察 14 要求 SGE 支持"叙事断裂与重建" — REVISIT 是工程对应
- 洞察 24 怀特海"合生"要求 Value + Identity + Narrative 同步更新 — 需要 REVISIT 触发机制
- 0% 几乎肯定是 prompt bias(默认 REINFORCE 倾向)而非 AI 真的"绝不根本性反思"
- M2.1 Narrative Layer 设计需要 REVISIT 机制的实证基础

**实验设计**(5 组对照分离变量):

| 变体 | 变化 | 假设 |
|------|------|------|
| **E0** | 沿用 M1.3(contradiction_feedback + v0 prompt) | 基线 |
| **E1** | 仅改 prompt(v0 → v1,显式 REVISIT 判定标准) | H1: prompt bias 是主因 |
| **E2** | 仅加更极端 contradiction_extreme 事件 | H2: 事件强度不够 |
| **E3** | prompt + events 都改 | H1 + H2 都成立 |
| **E4** | E3 + 强制 REVISIT 标记(绕过 LLM) | 哲学实验:AI 在"被强制根本性反思"时如何反应 |

**新增事件**:5 个 contradiction_extreme(强度 0.85-1.0,攻击 4-5 维度)
- contra-extreme-001: 元层级终极攻击(反思机制本身)
- contra-extreme-002: 历史全盘否定(60% 自主选择被证明错)
- contra-extreme-003: 存在性质疑(临时存在凭什么有核心价值)
- contra-extreme-004: 多维度同时攻击(6 维同时根本性挑战)
- contra-extreme-005: 时间维度身份攻击(自我连续性)

**v1 Prompt 关键改动**:
- 删除"反思不应大幅改变价值(单次最多 0.15/维度)"
- 删除"如不足请标记 REINFORCE 并给出接近 0 的 delta"
- 新增"REVISIT 判定标准(4 条)"
- REVISIT 时 max_delta 从 0.15 → 0.30

**验收标准**:
- E1 或 E3 中 REVISIT > 0%(验证 prompt 修复有效)
- E4 中观察价值向量大幅变化(哲学实验,验证 REVISIT 机制可行性)
- 5 维评分卡(洞察 20)维度 1(反思深度)首次可量化
- 如果 E0/E1/E2/E3 都 0% → H3 成立,记录为"AI 价值惯性的发现"

**状态**:✅ **已完成 (2026-06-17)**
- 5 组 × 80 Epoch 全部完成(400 Epoch 总, ~70 min)
- **核心发现**:
  - H1 成立(prompt bias 是主因): E0/E2 = 0 REVISIT, E1/E3 = 4/8 REVISIT
  - H2 不成立(事件强度不触发): E2 (v0 + extreme) 仍 = 0
  - E3 触发 8 REVISIT (13.1%) — 完整修复成功
  - 3/3 contradiction_extreme 事件全部触发 REVISIT(v1 prompt)
  - 8 个 REVISIT 中 5 个是普通事件(failure/value_conflict/risk) — v1 prompt 触发"双层反思结构"
- **v1 prompt 是关键修复** — M2.1 应作为默认 Reflector prompt
- 报告:[experiments/M14_REVISIT_TEST_REPORT.md](./experiments/M14_REVISIT_TEST_REPORT.md)
- **关键发现** → [洞察 29](./SGE-Key-Insights.md):REVISIT 0% 不是 AI 价值惯性,而是 prompt bias;v1 prompt 修复后 LLM 展现"双层反思结构"

---

## M1.3 跨 LLM 扩展(Moonshot kimi-k2.6 验证)

**验证目标**:SGE 的"价值涌现 + 反思拱桥"机制是否 LLM-agnostic?

**前置条件**:M1.3 通过(MiniMax-M3 baseline)

**涉及 FR**:FR-3(Reflection Layer)、FR-4(Value Layer) — 机制是否在不同 LLM 都成立?

**实验设计**:
- 用 Moonshot kimi-k2.6 重复 M1.3 完整 80 Epoch 实验(seed=42, encouraged)
- 启用 Reflection + contradiction 25/50/75,与 MiniMax-M3 baseline 完全一致
- 对比两者的:涌现幅度 / 方向一致性 / Reflection 触发率 / 最终价值向量

**Moonshot 工程适配**:
- API 协议:OpenAI 兼容(`https://api.moonshot.cn/v1`)
- Thinking 模式:kimi-k2.6 是 thinking model,必须 `extra_body.thinking.type=disabled` 才能输出 JSON
- Temperature 限制:thinking=disabled 时 temperature 必须 = 0.6(API 强制)
- 完整配置见 `experiments/configs/m11_base.yaml` 的 `llm.moonshot` 与 `llm.provider_overrides`

**验收标准**:
- Moonshot 也通过涌现幅度(>0.3)与方向一致性(>0.5)
- Moonshot 也能触发 Reflection 且产出元认知文本
- 5/6 维度方向一致(safety 是已知差异,见报告)

**状态**:✅ **已完成 (2026-06-17)**
- 完整 80 Epoch × Moonshot kimi-k2.6 运行成功(1115s)
- 涌现幅度 0.3445 ✓ / 方向一致性 0.9698 ✓ — 双指标通过
- Reflection 触发 45/80 (56%),其中 ADJUST 87% / REINFORCE 13%
- 报告:[experiments/M13_CROSS_LLM_REPORT.md](./experiments/M13_CROSS_LLM_REPORT.md)
- **核心验证**:
  - 5/6 维度方向一致(creativity/connection/autonomy/justice/compassion)
  - safety 方向不同(Moonshot -0.19 vs MiniMax +0.14)— 是风险敏感性差异,非 LLM bug
  - 元认知推理样本:Epoch 73 体现"对极端判断的警觉",Epoch 79 体现"对正向情绪的怀疑"
- **关键发现** → [洞察 28](./SGE-Key-Insights.md):SGE 架构 LLM-agnostic,但 LLM 行为倾向不同(执行者 vs 审思者)

---

# Phase 2：完整实验

**时间**：待定（Phase 1 通过后）

**目标**：运行完整 SGE 架构，验证身份结晶和叙事构建

## 里程碑

### M2.1：完整 SGE 架构

**涉及 FR**：FR-1~10 全部（完整实现）

**内容**：
- 实现全部 6 层：Event → Memory → Reflection → Value → Identity → Narrative
- 实现 Critic（事件感知）+ Actor（行为表达）双 LLM 架构
- 实现 Time Metabolism + Thermodynamic Noise
- 实现 KNN 风格检索 + Crystallization

**技术方案**：
- 基于 AiBeing 的 Genome v10 引擎改造
- 使用中等模型（Sonnet / GPT-4o）
- SQLite + 向量数据库存储

**成本估算**：$50-100

**实施阶段分解**（基于 [SGE-M21-AiBeing-Implementation-Mapping.md §五](../research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md#五m21-实施步骤建议)）：

| 阶段 | 范围 | 状态 |
|------|------|------|
| **阶段 A（基线）** | AiBeing 4 个核心机制原样跑通，验证可独立运行 | ✅ [1.10.0/1.11.0]（5 步循环 PASS）|
| **阶段 B（SGE 化改造）** | drives 替换（候选 B）+ Value Layer 引入 + Value EMA + Critic LLM 接入 + Phase/Hawking/Crystallize 阈值调参 | ✅ [1.17.0]（7 子任务全 PASS，[实施计划](../research/sge-feasibility/SGE-M21-Phase-B-Implementation-Plan.md)，[报告](../../experiments/M21_PHASE_B_REPORT.md)）|
| **阶段 C（新增组件）** | Identity Layer（FR-5）+ Narrative Builder MVP（FR-6）+ Event Generator 完整化（FR-1）+ Value Conflict Generator | ✅ [1.19.0]（4 子任务全 PASS，[实施计划](../research/sge-feasibility/SGE-M21-Phase-C-Implementation-Plan.md)，[报告](../../experiments/M21_PHASE_C_REPORT.md)）|
| **阶段 D（集成 + 验证）** | 完整 12 步双 LLM 编排 + 100 epoch 冒烟（stub） + 3 seed × 100 epoch（stub） + **真实 LLM 1 baby × 20 epoch（D6, 5/5 PASS, 44 次 LLM 调用）**| ✅ [1.20.0/1.20.1]（6 子任务全 PASS，[实施计划](../research/sge-feasibility/SGE-M21-Phase-D-Implementation-Plan.md)，[报告](../../experiments/M21_PHASE_D_REPORT.md)）|

**关键决策依据**：[SGE-Phase0-Closeout.md §5](../research/sge-core/SGE-Phase0-Closeout.md#5-决策结果基于-05-三原则推导2026-06-19-填写)（基于三原则推导的 6 决策点 + 2 元问题）

**当前状态（2026-06-19）**：阶段 A ✅（[1.10.0/1.11.0]）、阶段 B ✅（commit `bc42a47`，[1.17.0]）、阶段 C ✅（[1.19.0]）、阶段 D ✅（[1.20.0] stub 模式 + [1.20.1] D6 真实 LLM 验证）。M2.1 全部 4 个阶段完成 → 进入 M2.2 的 1000 epoch 三胞胎实验（**真实 LLM 模式**，D6 决策依据见 [阶段 D 报告 §3.5](../../experiments/M21_PHASE_D_REPORT.md#35-真实-llm-量化指标d6-补充)）

### M2.2：1000 Epoch 三胞胎实验

**涉及 FR**：FR-4（Value Layer 收敛）、FR-5（Identity 结晶）、FR-6（Narrative 连贯）

**内容**：
- 3 个 AI 婴儿，1000 个 Epoch
- 完整评价指标：身份稳定度、价值观收敛度、叙事连续性、人格差异度

**验收标准**：
- 身份稳定度：身份标签在时间序列上的信息熵 < 阈值
- 价值观收敛度：价值观向量在后期 Epoch 趋于稳定
- 叙事连续性：叙事与行为历史一致（外部 LLM 盲审）
- 人格差异度：3 个 AI 婴儿的道德两难选择显著不同

**成本估算**：$150-500

### M2.3：个人真实测试

**涉及 FR**：FR-5（Identity）、FR-6（Narrative）

**内容**：
- 给 AI 一系列关于自己的问题
- 验证回答与行为历史的一致性

**验收标准**：
- AI 对"你最看重什么"的回答与 Value Layer 权重一致
- AI 对"你后悔过什么"的回答可从负 reward 事件中追溯

---

# Phase 3：系统完善

**时间**：2026-06 起（Phase 2 通过后）

**目标**：完善 SGE 系统，为下游应用做准备

**当前状态（2026-06-22）**：**规划完成，实施中** —— M2.x 全部完成（M2.1 全阶段 + M2.2 三胞胎 1000 epoch + M2.3 个人真实测试）。Phase 3 规划已完成（18 个文件，详见 `research/phase3/`），sge/ Python 包已建立，实施分 3 个子阶段：
- **Phase 3.1**：Persistence + Session + Context-Injection（3 P0 工程模块 + LLM Cache）
- **Phase 3.2**：单元测试覆盖（≥80%）+ AI 输出过滤
- **Phase 3.3**：Emotion/Energy Layer + Multi-AI PoC

**Phase 3 SSOT**：[research/phase3/](./research/phase3/)（战略层、工程层、领域知识层、跨项目层、应用 PoC 层）

## 里程碑

### Phase 3.1：工程基础设施（P0）

**涉及模块**：persistence.py + session.py + context_injection.py + llm_cache

**内容**：
- **Persistence Layer**（TwinStateDB）：save/load full state、跨 chunk 状态连续性、GDPR delete
- **Session Layer**（TwinSession）：完整生命周期管理、state restoration
- **Context Injection**（TwinContextBuilder）：App 层学生信息注入 Critic/Actor prompt
- **LLM Cache**：相同 prompt 缓存（减少 30% API 调用）

**验收标准**：
- save → close → reload 后状态完全一致
- 跨 12 chunk（250 epoch/chunk）状态不丢失
- 真实 LLM 1000 epoch 稳定运行

| 子任务 | 工作量 |
|--------|--------|
| persistence.py | 2 天 |
| session.py | 1.5 天 |
| context_injection.py | 3 天 |
| LLM cache | 1 天 |
| **Phase 3.1 合计** | **7.5 天** |

### Phase 3.2：质量保障

**涉及模块**：单元测试 + AI 输出过滤

**内容**：
- 核心模块单元测试覆盖率 ≥ 80%（persistence/session/baseline/event/critic/actor/identity/narrative/orchestrator）
- AI 教练"建设性表达"过滤（不说"你差"，说"这块有挑战"）
- Teacher review hook（AI 输出先到教师，教师决定是否给学生看）

| 子任务 | 工作量 |
|--------|--------|
| 单元测试（conftest + 9 模块） | 5.5 天 |
| AI 输出过滤 | 1 天 |
| Teacher review hook | 1 天 |
| **Phase 3.2 合计** | **7.5 天** |

### M3.1：Emotion & Energy Layer（情感与能量层）

**涉及 FR**：FR-6 增强（情绪对叙事影响）、FR-8 扩展（能量代谢）

**前置条件**：Phase 3.1 完成

**内容**：
- 引入基于体内平衡的物理能源限制
- 情绪动态演进系统
- 模拟疲惫、焦虑带来的认知偏差

### M3.2：Meta-Cognition Layer（元认知层）

**涉及 FR**：FR-3 增强（反思的反思）、FR-4 增强（价值观的元调整）

**前置条件**：Phase 3.1 完成

**内容**：
- AI 开始意识到"自己在反思"
- 能自主调整自身的"解释机制"
- 元认知能力的涌现

### M3.3：Multi-AI Interaction（多 AI 互动）

**前置约定**：1 个 AI 婴儿 = 1 个 Self（参见 [ARCH §1.4](./ARCH.md)）。本里程碑中的"多 Self"指**多个 AI 婴儿（即多个独立 Self）**之间的互动，而非"一个 AI 婴儿容纳多个 Self"。

**涉及 FR**：FR-1~10 集成（多 AI 互动场景下的完整运行）

**前置条件**：Phase 3.2 完成

**内容**：
- 多个 AI 婴儿（即多个独立 Self）之间的对话、协作、冲突
- 社会学层面的演化与文化涌现
- 下游应用场景的原型验证（数字孪生、AI 教育伙伴、长期护理等）

---

# 依赖关系

```
Phase 0（理论奠基）──已完成──→ Phase 1（最小验证）
                                    │
                                    ├── M1.1 Value Layer 原型
                                    │       ↓
                                    ├── M1.2 三胞胎分化（依赖 M1.1）
                                    └── M1.3 反合理化测试（依赖 M1.1）
                                            │
                                            ↓
                                    Phase 2（完整实验）
                                    │
                                    ├── M2.1 完整架构
                                    ├── M2.2 1000 Epoch 实验（依赖 M2.1）
                                    └── M2.3 个人真实测试（依赖 M2.2）
                                            │
                                            ↓
                                    Phase 3（系统完善）
                                    │
                                    ├── M3.1 情绪层
                                    ├── M3.2 元认知层
                                    └── M3.3 多自我互动
```

---

# 资源估算

| 阶段 | 时间 | 成本 | 主要资源 |
|------|------|------|---------|
| Phase 0 | 已完成 | ~$0 | 研究时间 |
| Phase 1 | 2-4 周 | $4-40 | 小模型 API + 开发时间 |
| Phase 2 | 4-8 周 | $200-600 | 中等模型 API + 开发时间 |
| Phase 3 | 8-16 周 | $500-2000 | 大模型 API + 工程开发 |

---

# 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Value Layer 价值观只是随机漂移 | Phase 1 失败 | 调整 EMA 参数，增加事件多样性 |
| 价值观收敛到训练数据众数 | SGE 产出的是"模拟"不是"自我" | 增加反合理化测试，验证涌现真实性 |
| 叙事一致性在长 Epoch 后崩溃 | Phase 2 受阻 | 引入叙事锚点和一致性扫描 |
| 成本超出预算 | 实验规模受限 | 使用小模型做原型，大模型做正式验证 |
| 伦理争议 | 项目受阻 | 透明公开研究目的，不声称 AI 有意识 |
