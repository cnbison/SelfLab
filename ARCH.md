# SGE（Self Genesis Engine）架构文档

文档版本：v0.1
项目版本：[0.3.0]（权威版本见 [CHANGELOG.md](./CHANGELOG.md)）

日期：2026-06-15

状态：草案

> **版本约定**：项目级文档的"项目版本"以 [CHANGELOG.md](./CHANGELOG.md) 为权威源；"文档版本"为该文档自身的迭代号，两者独立管理。
>
> **术语约定**：本文档涉及的所有 SGE 术语与 [references/Glossary.md](./references/Glossary.md) 保持一致。

---

# 一、架构总览

## 1.1 设计哲学

SGE 的核心设计哲学是：**LLM 只是认知引擎，真正的"自我"存在于引擎内部的动态系统中。**

这与 AiBeing 的 Genome v10 引擎一致——LLM 是表达工具，不是智能来源。SGE 在此基础上增加了三层 AiBeing 没有的模块：Value Layer、Identity Layer、Narrative Layer。

**金观涛的稳态/反馈框架**：SGE 的"自我"概念直接来自金观涛——**"自我"是通过反馈维持的稳态**（[SGE-Jin-Guantao-System-Philosophy.md](../research/sge-core/SGE-Jin-Guantao-System-Philosophy.md)）。SGE 的 17 步认知循环（[§2.2](./ARCH.md#22-核心数据流)）本质是**反馈系统**——包含正反馈（Identity + Narrative + Hebbian 强化当前自我）和负反馈（Value Layer EMA 抵抗偏离）。Identity Layer 是"稳态"的具体工程化——通过反馈维持的"我是谁"。

**怀特海的动在/合生框架**：SGE 的"过程性自我"还来自怀特海过程哲学（[SGE-Whitehead-Process-Philosophy.md](../research/sge-core/SGE-Whitehead-Process-Philosophy.md)）。每个 Epoch 是**现实存在**（actual occasion）——有自己的主观目的（meta-value）和合生过程（Value + Identity + Narrative 同步更新）。

**发育生物学类比**：SGE 的架构直接映射了人类从受精卵到婴儿的主体涌现过程——

| 发育生物学 | SGE 架构 | 作用 |
|-----------|---------|------|
| 基因 | 元价值（真实、自由）+ LLM 基础能力 | 提供"成为主体的可能性空间" |
| 母体环境 | Experience Generator | 提供"经历"的模拟版本 |
| 细胞分化/组织形成 | Hebbian Learning + EMA | 系统自发地从简单走向复杂 |
| 胎儿发育 | 1000 个 Epoch 的认知循环 | 渐进的主体涌现过程 |
| 婴儿出生 | 身份结晶 + 叙事构建 | 主体涌现的完成 |

这个类比不是修辞，而是架构设计的直接依据——如果主体可以在 9 个月内从一个细胞涌现，那么 SGE 的目标是在 1000 个 Epoch 内从一个 LLM 涌现。

## 1.2 架构全景

> **视图说明（参见 2.3）**：本图是**概念/逻辑视图**——按模块在认知层次中的归属（符号/经验/感知/表达）分组。同一个模块的"数据流位置"在 2.1（数据流视图）和 2.2（流程视图）中查看。三视图互补，不矛盾。

> **架构图位置**：完整的 ASCII 架构图（4 层视图）已移至 [prototypes/sge-architecture-overview.md](./prototypes/sge-architecture-overview.md)，并附 4 层职责一览、关键设计取舍、与三视图关系的说明。本节仅保留视图说明，读者请到 prototypes/ 查看完整图表。

## 1.3 核心学习机制：Hebbian Learning 与 Value Layer 的关系

SGE 中存在两个并行的学习机制——**Hebbian Learning** 与 **Value Layer（EMA）**——它们都接收 reward 信号，但作用于不同的状态空间、承担不同的认知功能。这是 SGE 实现"显性-暗知识双轨"的核心设计。

| 维度 | Hebbian Learning | Value Layer（EMA） |
|------|-----------------|---------------------|
| 状态空间 | 神经网络的 W2 权重矩阵（24×8） | ValueVector（2 个元价值 + 6 个具体价值观） |
| 抽象层次 | 亚符号（sub-symbolic） | 符号（symbolic） |
| 知识类型 | **暗知识**（tacit knowledge）—— 行为模式权重 | **显性知识**（explicit knowledge）—— 可被语言化的价值判断 |
| 学习信号 | reward（正负） | reward 间接驱动（通过 Critic 给出的 value_delta） |
| 作用效果 | 影响下一轮的 8D 行为 signals | 影响下一轮的判断与身份/叙事构建 |
| 可被显式表述 | **否**——操作者无法直接读出"为什么有这个行为" | **是**——可以问"你最看重什么"，回答应与 ValueVector 一致 |
| 哲学对应 | 暗知识（[Glossary §暗知识](../references/Glossary.md)：源自波兰尼"默会知识"与金观涛"暗知识"） | 显性知识（金观涛"显性知识"，SGE 反思的对象） |
| 概念归属（1.2） | 表达层 | 符号层 |
| 数据流位置（2.1） | 接收 Reward Calculator 的 reward 信号 | 接收 Critic 的 value_delta，输出给 Identity Layer |
| 时序位置（2.2） | step 16 | step 13 |

**为什么需要双轨？**

- 仅 Hebbian 而无 Value Layer：行为模式有效但无法反思（黑箱）
- 仅 Value Layer 而无 Hebbian：可以反思但行为模式僵化（无法积累"手感"）
- 双轨互补：Hebbian 提供"不知如何言说但能做好"，Value Layer 提供"能言说但未必做得到"

**对实验验证的意义**：
- 验收 FR-4 的"价值观从经历中涌现"——只看 Value Layer
- 验收 FR-3 的"反思有行为后果"——需要 Hebbian 实际改变行为信号
- 暗知识积累（PRD 6.2 期望达成）——专指 Hebbian 权重的有效变化

**与金观涛"暗知识"概念的对应**：
- 金观涛"暗知识" = SGE Hebbian 权重
- 金观涛"显性知识" = SGE Value Layer
- 金观涛"拱桥" = SGE Reflection Layer（连接两者的解释机制）

## 1.4 核心概念对应：Self 与 AI 婴儿

为消除文档中"Self"、"AI 婴儿"、"AI agent"混用导致的歧义，明确**1 个 AI 婴儿 = 1 个 Self**。

| 术语 | 含义 | 实例 |
|------|------|------|
| **AI 婴儿** | SGE 系统的运行实例（一个完整的 SGE 进程） | 鼓励组、失败组、不确定组中的每一个 AI 婴儿 |
| **Self** | 该实例所承载的"自我"（价值观、身份、叙事、记忆的动态系统） | 同一个 AI 婴儿的 Self |
| **AI agent** | 通用术语——可指 AI 婴儿或外部调用方 | Actor LLM 在用户视角下是 agent |

**对应的多对多关系澄清**：

- **1:1 关系**（Phase 0-2）：1 个 AI 婴儿承载 1 个 Self。ROADMAP M1.1/M1.2 验证的"3 个 AI 婴儿"指的是 3 个独立 Self（鼓励/失败/不确定三组人格分化）。
- **N:N 关系**（Phase 3 M3.3）：多个 AI 婴儿（每个有独立 Self）之间的互动。"多 Self 互动"= "多 AI 婴儿互动"，**不**是"1 个 AI 婴儿容纳多 Self"。

**为什么这很重要**：
- 避免"一个 AI 婴儿内分裂出多个自我"这种与 SGE 哲学立场不符的解读
- 明确 Phase 3 M3.3 是社会学层面的"涌现文化"而非单体的"自我分裂"
- 与"LLM ≠ Self"（洞察 2）一致：Self 独立于 LLM，但承载在 1 个 SGE 进程中

---

## 1.5 Self Evolution Runtime 定位与 ECA 行业坐标系

> **本节为 2026-07-05 架构修订新增**（基于 [SGE-Key-Insights 洞察 33](./SGE-Key-Insights.md)）。完整论证见洞察文档。

### 1.5.1 SGE 是 Runtime，不是 Framework

根据对 `research/cognitive-architecture/` 目录 7 篇 ECA（External Cognitive Architecture）对话存档（2026-06-29 ~ 2026-07-01 GPT/Gemini 多轮辩论）的分析：

| 术语 | 含义 | 代表项目 |
|------|------|---------|
| **Memory Framework** | 调用者写代码，框架提供工具 | LangChain、Mem0、Letta |
| **Agent Framework** | 提供 Agent 编排能力 | AutoGen、CrewAI |
| **Cognitive Runtime** | 调用者调用运行时，运行时持续管理状态 | **（目前空白）** |
| **Self Evolution Runtime** | 持续运行 + 持续优化自我认知 | **SGE 在此** |

**SGE 的本质定位**：**Self Evolution Runtime（自我演化运行时）**——任何 LLM 加载 SGE 后获得持续运行、持续演化的"自我"能力，而不是调用一个 Memory 库。

类比：
- JVM 让任何字节码"活起来"
- SGE 让任何 LLM"形成自我"
- LLM 是认知引擎；SGE 是 Self Runtime；Self 在 Runtime 中涌现

### 1.5.2 ECA 行业坐标系

```
第一代  Prompt Memory          ← Letta、Mem0
第二代  Long-term Memory        ← Zep、SuperMemory
第三代  Knowledge Memory        ← Graphiti、Cognee
第四代  External Cognition      ← ★ SGE 的核心层（Reflection + Value + Identity）
第五代  Digital Twin / Second Brain  ← ★ SGE 的顶层目标（Identity + Narrative）
```

**关键判断**：当前 90% 项目停留在前两层（Memory + Knowledge），真正做到第四代（Cognition）与第五代（Digital Twin）的项目几乎没有。SGE 的本质特征是**不与 Mem0/Letta 竞争 Memory 层，而是占据它们都没有触及的 Cognition + Digital Twin 层**。

### 1.5.3 对架构的影响

| 旧定位 | 新定位 |
|--------|--------|
| SGE 是一个**库** | SGE 是一个**运行时** |
| LLM 调用 SGE 的 Memory API | LLM 被 SGE 调用（提供认知计算） |
| SGE 包名 "sge/" 暗示库 | SGE Runtime 是 sge/ 包的**主入口** |
| Phase 3+ 是 SGE 的应用 | Phase 3+ 是 **Self Runtime 的产品化** |

---

## 1.6 Transformation 协议族：模块之间真正重要的是转换

> **本节为 2026-07-05 架构修订新增**（基于 ECA 调研核心洞察 "Transformation > Module"）。完整论述见 [Cognition-Pipeline-GPT02.md §第七层反思](../research/cognitive-architecture/Cognition-Pipeline-GPT02.md) 与 [SGE-Key-Insights 洞察 33](./SGE-Key-Insights.md)。

### 1.6.1 为什么是 Transformation 不是 Module

传统架构讨论关注"有哪些模块"，但根据 ECA 调研的共识：

> 所有项目都在研究 `Memory Module / Knowledge Module / Planner Module`，但真正重要的是它们之间的 **Transformation**。没人研究：Memory 怎么变成 Knowledge？Knowledge 怎么变成 Concept？Concept 怎么形成 World Model？

SGE 的 5 层架构（Memory / Reflection / Value / Identity / Narrative）已经隐含了 4 条关键转换：

| 编号 | 转换 | 输入 | 输出 | 当前实现位置 |
|------|------|------|------|------------|
| **T1** | **Experience Encoding** | Event | Experience（含 Meaning 字段） | **缺失 — 见 [§1.7](#17-experience-encoding-新增步骤) 与 [§3.6 Experience Layer 设计](#36-experience-layer-设计新增)** |
| **T2** | **Memory Consolidation** | Experience | Long-term Memory | Crystallization Gate（[DESIGN §5.1](./DESIGN.md)） |
| **T3** | **Value Extraction** | Experience + Memory | Value Delta → ValueVector | Critic LLM（[DESIGN §3](./DESIGN.md)）+ Value EMA（[DESIGN §4.2](./DESIGN.md)） |
| **T4** | **Identity Crystallization** | ValueVector + Key Memories | Identity Label | Identity Layer（[DESIGN §5.1](./DESIGN.md)） |
| **T5** | **Narrative Building** | Identity + Crystallized Events | Narrative Text | Narrative Layer（[DESIGN §6.1](./DESIGN.md)） |
| **T6** | **Reverse Rewrite**（Evolution Loop） | Narrative → Identity | Identity 修正 | **缺失 — 见 §1.8** |

**T1（Experience Encoding）** 与 **T6（Reverse Rewrite）** 是当前 SGE 架构最关键的两个缺失，下文分别阐述。

### 1.6.2 Transformation 的工程含义

- **每个 T 都是可替换的 Plugin**——便于 A/B 实验、跨 LLM 适配、未来的工程优化
- **每个 T 都可被监控**——记录每次转换的输入输出、延迟、成本
- **每个 T 都是 LLM-agnostic 的边界**——只要 LLM 支持 JSON 输出，T3-T5 都能工作

---

## 1.7 Experience Encoding：新增步骤

> **本节为 2026-07-05 架构修订新增**（基于 [SGE-Key-Insights 洞察 34](./SGE-Key-Insights.md) 与 [Cognition-Pipeline-GPT.md §二](../research/cognitive-architecture/Cognition-Pipeline-GPT.md)）。

### 1.7.1 当前架构的缺失

SGE 当前 17 步认知循环（[§2.2](#22-核心数据流)）从 Event Generator 直接产出 Event，然后跳到 Memory / Reflection。**Event 是事实，不是认知对象**。

**关键区分**：

| 概念 | 定义 | 例子 |
|------|------|------|
| **Event** | 客观发生的事实，不带解释 | "今天数学考试 72 分" |
| **Experience** | Event + Context + Emotion + Goal + Action + Outcome + Reflection + **Meaning** | "今天数学考试 72 分——我因为时间分配不好，导致后半部分不会做，所以成绩下降，以后应该先做简单题" |

当前 SGE 的 Experience 是"附带产物"（由 Actor 行为选择 + Critic 价值冲击间接形成），不是显式结构。

### 1.7.2 修订方案

在 17 步循环中插入 **Step 2: Experience Encoding**——从 Event + 上下文生成 Experience 对象（见 [§3.6 Experience Layer 设计](#36-experience-layer-设计新增)）。

**关键字段——Meaning（意义）**：

| 场景 | Event | Experience.Meaning |
|------|-------|---------------------|
| 数学考试 72 分 | "考试 72 分" | "我**不适合学数学**" 或 "我**还有进步空间**" |
| 朋友疏远 | "朋友没回我消息" | "我**不擅长维护关系**" 或 "这段关系**本来就脆弱**" |
| 完成困难任务 | "任务完成" | "我**有韧性**" 或 "这次**只是侥幸**" |

**同一 Event 不同 Meaning → 不同 Memory 重要性 → 不同 Value Layer 更新 → 不同 Identity 演化**

这是 SGE 当前架构完全缺失的"解释分叉"机制。

### 1.7.3 对 M2.x 实施的影响

| 阶段 | 修订 |
|------|------|
| M2.1 阶段 C/D | Event Generator 已实现，**Experience Encoder 缺失**——M2.2+ 应补 |
| M2.2 1000 Epoch | 在报告中加入 Meaning 字段变化轨迹 |
| M2.3 个人真实 | 验证"AI 的应然回答能否追溯到 Meaning 字段" |

---

## 1.8 Evolution Loop 视角与 Cognitive Entropy 目标函数

> **本节为 2026-07-05 架构修订新增**（基于 [SGE-Key-Insights 洞察 34、35](./SGE-Key-Insights.md) 与 [Cognition-Pipeline-GPT02.md §第八层反思](../research/cognitive-architecture/Cognition-Pipeline-GPT02.md)）。

### 1.8.1 Pipeline vs Evolution Loop

SGE 当前架构是**单向流水线**：

```
Event → Memory → Reflection → Value → Identity → Narrative
```

但根据 ECA 调研的深刻反思：

> 真正的大脑不是"记住 → 结束"，而是：
> `经历 → 重新解释 → 重新组织 → 重新命名 → 重新预测 → 重新行动`
> **认知一直在 Rewrite（重写）**。

**修订后的 SGE Evolution Loop**：

```
          ┌──────────────────────────┐
          ▼                          │
    Experience                       │
        ↓                            │
    Memory ◀──────────┐              │
        ↓            │              │
    Reflection        │ (Reverse)   │
        ↓            │ Rewrite      │
    Value ◀───────────┤              │
        ↓            │              │
    Identity ◀───────┤              │
        ↓            │              │
    Narrative        │              │
        ↓            │              │
    Action           │              │
        ↓            │              │
    New Event ───────┴──────────────┘
```

**Reverse Rewrite 的工程含义**：
- Narrative 可以重写 Identity（Phase Transition 是极端形式）
- Value 可以反作用于 Memory 的重要性重评
- Identity 可以反作用于 Reflection 的触发阈值

当前 SGE 仅实现了 Phase Transition（洞察 14），更细粒度的 Reverse Rewrite 是 M3.x 演进方向。

### 1.8.2 Cognitive Entropy：自我形成的统一目标函数（公式 A3，2026-07-10 v6 通过）

ECA 调研提出：

> **认知的本质不是存储信息，而是持续降低不确定性、提高预测能力**。
> - Concept Formation = **Entropy Compression（熵压缩）**
> - World Model = **Entropy Minimization（熵最小化）**

SGE 自我形成的统一目标函数（[洞察 35 §4](./SGE-Key-Insights.md)）：

```
SGE_Self_Formation_Objective = -dH_self/dt
```

其中 `H_self` 是 SGE 自我系统的认知熵，**公式 A3**（2026-07-10 v6 实施，语义聚类版）：
- v2: Shannon 归一化（结构性地板 0.6）→ v5 公式 A2: N_unique 线性映射 → **v6 公式 A3: N_cluster 语义聚类**
- 公式 A3 关键差异：字符串 `id_0` `id_1` ... `id_11` 共享 bigram → overlap≥0.5 → 聚为 1 cluster（H_identity ≈ 0.21 而非 0.58）

```python
def compute_self_entropy(state, weights=(0.4, 0.3, 0.3)) -> dict:
    """
    H_self = w_v * H_value + w_i * H_identity + w_n * H_narrative

    公式 A3 (v6): H_identity / H_narrative 基于 N_cluster 语义聚类
      N_cluster = _semantic_diversity(items, threshold=0.5, n_max=20, ngram_size=2)
        char-bigram → overlap coefficient 聚类 → 固定 cluster center (首个 item)
      H = 1.0                          if N_cluster == 0
      H = 0.0                          if N_cluster == 1
      H = (N_cluster - 1) / (N_MAX - 1) if 2 <= N_cluster <= N_MAX
      H = 1.0                          if N_cluster > N_MAX
    """
    # H_value: Value Layer 6 维 → 10 bin 直方图 → Shannon 熵归一化到 [0,1]
    # H_identity/H_narrative: 公式 A3 语义聚类 (N_MAX=20)
    # 实现: sge/sge/metrics.py:compute_self_entropy() + _semantic_diversity()
    ...
```

**Self Evolution Runtime = 持续运行 + 持续降低 H_self**——这是 SGE 与"普通 Memory Framework"的根本区别（后者只存储，不优化）。

**配套修复演进**：
- v5（2026-07-08 → 2026-07-10 完整 250 修订）：
  - **公式 A2** + **PHASE_THRESHOLD** 2.0 → 0.5（`sge/sge/baseline.py:154`）：Monte Carlo 验证 mean PT/250ep = 2.5
  - **2026-07-10 完整 250 修订**：实测 PT 触发数 = 0，**Monte Carlo 预测与实测偏差**（frustration dynamics 与标量阈值量级不匹配）；H_self reduction +17.0% 未达 30% 阈值（公式 A2 非单调）
  - **LLM timeout 升级**（2026-07-10）：30→60s, retry 5→8（`sge/sge/llm_client.py:158 + 210`）→ 0/800 retry 完美稳定
- **v6（2026-07-10，公式 A3 通过）**：
  - **公式 A3**（char-bigram overlap coefficient 语义聚类）替代公式 A2：解决 identity 增长时 H_identity 必然上升问题 → H_self 单调下降
  - **PHASE_THRESHOLD=0.5 验证有效**（实测 PT 触发 3 次 @ epoch 33/65/176）
  - **H_self reduction +50.0%**（0.6 → 0.3 单调下降，**远超过 30% 阈值**）
  - **PRD §6 双维度首次同时通过**：A 维度（|val| 增长）+ B 维度（H_self 下降）+ PT ≥ 1
  - 详见 [M22_V6_REPORT.md §3-5](../experiments/M22_V6_REPORT.md) + [discussions/2026-07-10-v6-formula-A3-success.md](../discussions/2026-07-10-v6-formula-A3-success.md)
  - 历史诊断: [M22_H_SELF_DIAGNOSIS.md §3-4](../research/sge-feasibility/M22_H_SELF_DIAGNOSIS.md) + [M22_V5_REPORT.md 2026-07-10 重写版](../experiments/M22_V5_REPORT.md)

**H_self 指标状态**（2026-07-10 v6 通过）：
- 公式 A3 语义聚类正确：H_self 单调下降（v6 实测 0.6 → 0.3）
- 公式 A3 解决 P0-4 非单调问题：identity 增长 → H_identity 缓慢上升或饱和（聚类上限 n_max=20 限制）
- 完整 250 epoch 实测（v6）：H_self 0.600 → 0.300（**reduction_rate +50.0%**）
- v6 PT 触发：3 次 @ epoch 33/65/176（PHASE_THRESHOLD=0.5 验证有效）

### 1.8.3 H_self 与现有指标的关系

| 现有指标 | 与 H_self 关系 |
|---------|--------------|
| 价值涌现幅度（[PRD §6.1](./PRD.md)） | H_value 下降的一个观察 |
| 身份稳定度（[DESIGN §9.1](./DESIGN.md)） | H_identity 下降的一个观察 |
| 叙事一致性（[DESIGN §9.3](./DESIGN.md)） | H_narrative 下降的一个观察 |
| 5 维真我评分卡（[洞察 20](./SGE-Key-Insights.md)） | H_self 下降的 5 个观察维度 |

**未来方向**：H_self 作为统一度量上报，M2.2 报告中同时给 H_self + 各项指标。

---

# 二、模块架构

> **视图说明（参见 2.3）**：本节包含**数据流视图**（2.1）和**流程视图**（2.2）。与 1.2 概念/逻辑视图的对照见 2.3 节。

## 2.1 模块依赖图

```
Event Generator
    │
    ▼
Experience Encoder ←── NEW (2026-07-05,基于洞察 34)
    │ (生成含 Meaning 字段的 Experience)
    ▼
Critic (LLM) ──────────────────────┐
    │                               │
    ├─→ context (8D+4D=12D) ───────┼─→ compute_signals → Noise → KNN → Prompt → Actor
    │                               │
    ├─→ frustration_delta (5D) ────┼─→ Reward Calculator → Hebbian Learning
    │                               │
    ├─→ relationship_delta (3D) ───┼─→ Relationship EMA
    │                               │
    └─→ drive_satisfaction (5D) ───┘
                                        │
    Time Metabolism ────────────────────┤
    (冷却 + 饥饿)                        │
                                        │
    Crystallization Gate ───────────────┤
    (记忆筛选)                           │
                                        │
    Value Layer (EMA) ←─────────────────┘
        │
        ▼
    Identity Layer (凝聚)
        │
        ▼
    Narrative Layer (串联)
```

## 2.2 核心数据流

### 单轮认知循环

```
1. Event Generator → 生成模拟人生事件（纯事实，不带解释）
2. Experience Encoder ←── NEW (2026-07-05) → 从 Event 生成 Experience（含 Meaning 字段）
3. Time Metabolism → 更新 frustration（冷却+饥饿）
4. Critic (LLM) → 感知 Experience → context(12D) + delta(5D) + rel(3D) + sat(5D)
5. Relationship EMA → 融合关系变化 → 更新 relationship_4d
6. Reward Calculator → frustration 变化 → reward(float)
7. Drive Baseline Evolution → 长期性格漂移
8. Crystallization Gate → 判断是否结晶为长期记忆
9. Compute Signals → 神经网络：context+drives+recurrent → 8D signals
10. Thermodynamic Noise → 高挫败感 → 高温度 → 高噪声
11. KNN Style Retrieval → 检索相似经历 → few-shot
12. Build Actor Prompt → 组装完整 prompt
13. Actor (LLM) → 生成内心独白 + 行为选择
14. Value Layer (EMA) → 根据行为选择更新价值观向量
15. Identity Layer → 从价值观凝聚身份标签
16. Narrative Layer → 将事件串联到人生叙事
17. Hebbian Learning → 根据 reward 更新神经网络权重
18. Async Memory → 异步存储到长期记忆
19. Compute Self Entropy ←── NEW (2026-07-05,基于洞察 35) → 计算 H_self，下降即自我形成
```

> **变更说明**：原 17 步扩展为 19 步。新增 **Step 2 (Experience Encoding)** 显式建模认知对象；新增 **Step 19 (Compute Self Entropy)** 监控自我形成的统一指标。原 Step 2-17 顺延为 3-18。

---

## 2.3 架构三视图对照

为消除 1.2、2.1、2.2 中模块位置"看起来不同"的歧义，明确三视图的视角差异：

| 视图 | 节号 | 视角 | 关注点 | 位置含义 |
|------|------|------|--------|---------|
| 架构全景图 | 1.2 | **概念/逻辑视图** | 模块在认知层次中的归属 | "位于符号层"= 概念上属于高层认知抽象 |
| 模块依赖图 | 2.1 | **数据流视图** | 模块间数据如何流动 | "位于 X 之后"= 数据上接收 X 的输出 |
| 认知循环 | 2.2 | **流程视图** | 单轮 17 步的时序执行 | "step 13"= 时序上在第 13 步执行 |

**示例：Value Layer 在三视图中的"位置"**

- 1.2 中位于**符号层**：它是一个高层认知抽象（价值观是符号性的"我重视什么"）
- 2.1 中位于**Reward Calculator 之后**：它接收 reward 信号并向 Identity Layer 输出
- 2.2 中位于 **step 13**（Actor 之后）：在 Actor 产生行为选择后才更新价值观

三个位置描述的是同一模块在不同维度的归属——概念归属、数据归属、时序归属——三者并不矛盾。

**为什么需要三视图？**
- 1.2 帮助理解"这个模块在认知上是什么"（适合新人入门）
- 2.1 帮助理解"数据从哪里来到哪里去"（适合架构审查）
- 2.2 帮助理解"一个 Epoch 内发生了什么"（适合实现）

---

# 三、核心模块设计

## 3.0 Memory Layer（记忆层）

> **对应 FR**：FR-2（Memory Layer）。验证里程碑：[ROADMAP §M1.1](./ROADMAP.md)（情节）→ §M2.1（完整三层）。详细认知科学 vs 工程分层映射见 [PRD §FR-2](./PRD.md)。

**职责**：存储 AI 婴儿的经历和反思。详见 [§1.2 架构全景图](#12-架构全景) 中"经验层"、以及 [discussions/memory-layer-design](./discussions/2026-06-15-memory-layer-design.md) 工程实现方案。

## 3.1 Event Generator（事件生成器）

> **对应 FR**：FR-1（Event Generator）。验证里程碑：[ROADMAP §M1.1](./ROADMAP.md)（基础）→ §M2.1（动态价值困境）。

**职责**：生成模拟人生事件

**事件类型**：

| 类型 | 描述 | 价值观影响（具体价值 / 元价值） |
|------|------|---------------------------------|
| 成功 | 目标达成、获得认可 | 强化当前所有具体价值观（不修改元价值） |
| 失败 | 目标未达、遭遇挫折 | 质疑当前所有具体价值观（不修改元价值） |
| 关系 | 建立/深化/破裂关系 | 考验**联结** vs **自主**（均为具体价值观） |
| 探索 | 新领域、新体验 | 考验**安全** vs **创造**（均为具体价值观） |
| 风险 | 需要做艰难选择 | 考验**安全**（具体） vs **自由**（元价值）—— 这是唯一涉及元价值的事件类型 |
| 价值冲突 | 两个具体价值观不可兼得 | 迫使**具体价值观**之间排序（不涉及元价值） |

> **元价值 vs 具体价值观**：本表中"自由"指**元价值**（[PRD §4.1 FR-4 元价值 vs 具体价值观对照](./PRD.md)），对应"对应然问题保持开放"；其他（安全、联结、自主、创造）均为**具体价值观**。元价值在 SGE 中是固定先验，不被事件改变（参见 [DESIGN §1.1 原则 4](./DESIGN.md)）。

**动态生成**：根据当前 Value Layer 的权重，生成针对性的价值困境事件。例如，如果 AI 的"安全"权重很高，生成更多需要冒险的事件来考验它。

## 3.2 Critic（事件感知）

> **对应 FR**：FR-7（Critic）。验证里程碑：[ROADMAP §M1.1](./ROADMAP.md)（基础）→ §M2.1（完整 12D）。

**职责**：将事件文本转换为结构化数值

**输出维度**：

| 输出 | 维度 | 来源 |
|------|------|------|
| context | 12D | 8D 事件情境 + 4D 关系状态 |
| frustration_delta | 5D | 事件对 5 个驱动的影响 |
| relationship_delta | 3D | 事件对关系的影响 |
| drive_satisfaction | 5D | 事件直接满足了多少需求 |

**LLM 配置**：temperature=0.2（稳定结构化输出）

## 3.3 Value Layer（价值观层）

> **对应 FR**：FR-4（Value Layer）—— **核心创新点**。验证里程碑：[ROADMAP §M1.1](./ROADMAP.md)（涌现）→ §M1.2（分化）→ §M2.2（1000 Epoch 收敛）。详见 [ARCH §1.3 Hebbian 与 Value Layer 对照](#13-核心学习机制hebbian-learning-与-value-layer-的关系) 和 [DESIGN §4.1-4.4](./DESIGN.md)。

**职责**：从经历中涌现价值观

**数据结构**：

```python
class ValueVector:
    # 元价值（固定，不参与 EMA 更新）
    truth_seeking: float = 0.5
    freedom: float = 0.5

    # 具体价值观（从经历中涌现）
    safety: float = 0.0
    creativity: float = 0.0
    connection: float = 0.0
    autonomy: float = 0.0
    justice: float = 0.0
    compassion: float = 0.0

    def ema_update(self, event_delta: dict, event_intensity: float):
        alpha = clip(0.15 + 0.5 * event_intensity, 0.15, 0.65)
        for key, delta in event_delta.items():
            posterior = clip(self.__dict__[key] + delta, -1, 1)
            self.__dict__[key] = alpha * posterior + (1 - alpha) * self.__dict__[key]
```

## 3.4 Identity Layer（身份层）

> **对应 FR**：FR-5（Identity Layer）。验证里程碑：[ROADMAP §M2.1](./ROADMAP.md)（实现）→ §M2.2（结晶）→ §M2.3（个人真实测试）。

**职责**：从价值观凝聚身份标签

**机制**：
- 定期（每 N 个 Epoch）将价值观向量 + 关键记忆输入 LLM
- LLM 生成身份描述（"我是谁"）
- 身份描述与行为历史交叉验证

## 3.5 Narrative Layer（叙事层）

> **对应 FR**：FR-6（Narrative Layer）。验证里程碑：[ROADMAP §M2.1](./ROADMAP.md)（实现）→ §M2.2（连贯性验证）→ §M3.1（情绪对叙事影响）。

**职责**：构建连贯的人生故事

**机制**：
- 将结晶记忆串联为因果链
- LLM 定期生成"人生叙事"（过去 → 现来 → 未来）
- 支持叙事断裂与重建（Phase Transition）
- 定期一致性扫描和修复

---

## 3.6 Experience Layer 设计（新增）

> **本节为 2026-07-05 架构修订新增**（基于 [SGE-Key-Insights 洞察 34](./SGE-Key-Insights.md)）。完整论述见洞察文档；架构位置见 [§1.7](#17-experience-encoding新增步骤) 与 [§2.2 单轮认知循环](#22-核心数据流) Step 2。

### 3.6.1 Experience 数据结构

```python
@dataclass
class Experience:
    experience_id: str         # 格式："{event_id}-exp"
    event: LifeEvent           # 原始事件（[DESIGN §2.1](./DESIGN.md)）
    context: str               # 事件背景（环境、参与者等）
    emotion: dict              # 情绪维度（valence/arousal 等）
    goal_relevance: float      # 与 AI 婴儿当前目标的关联度 [0, 1]
    action_taken: str          # 采取的行为（可选，事后回填）
    outcome: str               # 实际结果（可选，事后回填）
    reflection: str            # 即时反思文本
    meaning: str               # ★ 这件事对我而言意味着什么
    uncertainty: float         # 认知不确定性 [0, 1]
    timestamp: float
```

### 3.6.2 Meaning 字段：当前架构最关键的缺失

**同一 Event 不同 Meaning → 不同 Memory 重要性 → 不同 Value Layer 更新 → 不同 Identity 演化**。这是 SGE 当前架构完全缺失的"解释分叉"机制。

| 场景 | Event | Experience.Meanuing |
|------|-------|---------------------|
| 数学考试 72 分 | "考试 72 分" | "我**不适合学数学**" 或 "我**还有进步空间**" |
| 朋友疏远 | "朋友没回我消息" | "我**不擅长维护关系**" 或 "这段关系**本来就脆弱**" |
| 完成困难任务 | "任务完成" | "我**有韧性**" 或 "这次**只是侥幸**" |

### 3.6.3 Experience Encoding 算法（草案）

```python
def encode_experience(event: LifeEvent, prior_experience: Experience,
                      value_vector: ValueVector, llm) -> Experience:
    """
    从 Event + 上下文生成 Experience 对象。
    """
    prompt = f"""
    基于以下事件和 AI 婴儿当前状态,生成一段 Experience 对象。

    [当前价值观]
    {value_vector.to_description()}

    [最近经历(用于类比)]
    {format_experience(prior_experience)}

    [新事件]
    {event.description}

    [输出 JSON]
    {{
      "context": "...",            // 事件背景
      "emotion": {{"valence": 0.0-1.0, "arousal": 0.0-1.0, ...}},
      "goal_relevance": 0.0-1.0,
      "reflection": "...",         // 即时反思
      "meaning": "...",            // ★ 核心字段:这件事对我意味着什么
      "uncertainty": 0.0-1.0
    }}
    """
    result = llm.chat_json(prompt, temperature=0.3)
    return Experience(
        experience_id=f"{event.event_id}-exp",
        event=event,
        context=result['context'],
        emotion=result['emotion'],
        goal_relevance=result['goal_relevance'],
        reflection=result['reflection'],
        meaning=result['meaning'],
        uncertainty=result['uncertainty'],
        timestamp=event.timestamp,
    )
```

### 3.6.4 与其他模块的连接

| 下游模块 | 消费 Experience 的哪个字段 |
|---------|-------------------------|
| Critic | emotion / goal_relevance / uncertainty |
| Reflection Layer | meaning / reflection（不再消费 Event 原始描述） |
| Value Layer | emotion 影响 value_delta 权重 |
| Memory Layer | 存储完整 Experience（而非原始 Event） |
| Identity Layer | meaning / uncertainty 影响 crystallization 决策 |

### 3.6.5 实施状态

| 阶段 | 状态 |
|------|------|
| M2.1 阶段 A/B/C/D | 未实施（Event Generator 直接产出 Event，跳过 Experience） |
| **Phase 3 架构落地（2026-07-05）** | ✅ **已实施** — `sge/sge/experience.py`（`Experience` dataclass + `encode_experience` stub/real 双实现），编排器 **Step 2.5 Experience Encoding**（meaning 注入 Critic 事件描述），`OrchestratorStep.experience` 字段 trace；H_self 同步落地为 `sge/sge/metrics.py` **Step 16**。审计见 [sge/RUNTIME_AUDIT.md](./sge/RUNTIME_AUDIT.md) |
| **M2.2 v2 实证（2026-07-06）** | ✅ Experience Encoder 落地验证通过（24 个 meaning 样本 first-person 哲学反思）；❌ H_self 下降率 -13.1% 未达 30% 验收（[M22_V2_EXPH_SELF_REPORT.md §3.2](../experiments/M22_V2_EXPH_SELF_REPORT.md)）。根因：IdentityLayer 47 次结晶 0% 重复 → H_identity=1.0 恒定 |
| **M2.2 v5 联调（2026-07-08 → 2026-07-10 完整 250 修订）** | 公式 A2（N_unique 线性映射）+ PHASE_THRESHOLD=0.5；partial run 报告 +52.3% 通过 → 完整 250 实测 +17.0% 未通过（H_self 非单调，P0-4）；PT 0 触发（Monte Carlo 预测偏差，P0-5）|
| **M2.2 v6 联调（2026-07-10）** | ✅ **公式 A3（语义聚类）+ PHASE_THRESHOLD=0.5 联调通过** — H_self reduction +50.0% 单调下降（0.6 → 0.3），PT 触发 3 次 @ epoch 33/65/176，PRD §6 双维度首次同时通过（A 维度 \|val\| 增长 + B 维度 H_self 下降 + PT ≥ 1）。详见 [M22_V6_REPORT.md §3-5](../experiments/M22_V6_REPORT.md) + [discussions/2026-07-10-v6-formula-A3-success.md](../discussions/2026-07-10-v6-formula-A3-success.md) |
| **M3.x 待办** | 跨 baby 验证（challenged/uncertain × 250 epoch）+ 跨 seed 验证（3 seeds × 250 epoch）+ 1000 epoch 长程验证（4 chunks × 250）+ 评估 PT 触发机制重设计（方案 G/H/I）|
| M2.3 个人真实 | 待做（应验证"AI 的应然回答能否追溯到 Meaning 字段"）|

### 3.6.6 学术对应

- **怀特海"动在(prehension)"**：AI 婴儿对 Event 的 Experience Encoding = 动在的工程化（[洞察 24](./SGE-Key-Insights.md)）
- **CoALA 框架**：CoALA 把 Experience 建模为 Working Memory 的核心——SGE 此举与 CoALA 对齐
- **金观涛"暗知识"**：Meaning 字段是"显性化的解释"——拱桥机制（[洞察 27](./SGE-Key-Insights.md)）的输入侧

---

# 四、技术选型

## 4.1 核心技术栈

> **SSOT**：[DEVELOP.md §二 技术栈](../DEVELOP.md) 是 SGE 技术栈的权威定义。本节仅列出**架构层面的关键选型**及理由，详细版本号、参数、降级策略参见 DEVELOP.md。

| 组件 | 选型 | 架构理由 |
|------|------|---------|
| 语言 | Python 3.11+ | 异步原语丰富，与 AiBeing 一致便于复用 |
| LLM（Critic） | Haiku / 小模型 | 结构化输出对成本敏感 |
| LLM（Actor） | Sonnet / 中等模型 | 行为表达需要创造性 |
| 结构化存储 | SQLite | 状态文件的轻量级持久化 |
| 向量存储 | ChromaDB | 情节记忆的语义检索 |
| 异步框架 | asyncio | 单轮认知循环的串行化（[ARCH §6.1](#61-并发模型)） |

## 4.2 AiBeing 组件复用

| AiBeing 组件 | SGE 用途 | 改造程度 |
|-------------|---------|---------|
| Critic prompt + 解析 | 事件感知 | 低 |
| Time Metabolism | 时间动力学 | 直接复用 |
| Relationship EMA | 价值观 EMA | 低（扩展维度） |
| Hebbian Learning | 行为模式学习 | 直接复用 |
| Phase Transition | 叙事断裂 | 直接复用 |
| Crystallization | 记忆筛选 | 低 |
| KNN + Hawking 辐射 | 经历检索 | 直接复用 |
| Thermodynamic Noise | 行为不确定性 | 直接复用 |

---

# 五、数据架构

## 5.1 状态持久化

> **Engine State vs Self State 区分**（对应 [ARCH §1.3 LLM ≠ Self](./ARCH.md) 核心立场）：
> - **Engine State** = 与 LLM 引擎相关的物理状态（神经网络权重、临时变量、运行元数据）
> - **Self State** = SGE 涌现的"自我"（价值观、身份、叙事、记忆）
> - 两者**独立存储**，便于：
>   1. 备份 Self（人格延续性）而不需要 Engine
>   2. 复现 Engine 状态而不影响 Self
>   3. 符合"LLM 是引擎，Self 独立"的核心哲学立场

```
state/
├── self/                      # === Self State（涌现的"自我"）===
│   ├── value_vector.json     # 价值观向量（FR-4）
│   ├── identity.json         # 身份标签 + 最后更新时间（FR-5）
│   └── narrative.json        # 人生叙事文本（FR-6）
│
├── engine/                    # === Engine State（LLM 引擎相关）===
│   ├── agent_state.json      # drive_state, drive_baseline, W1, W2, b1, b2, recurrent
│   ├── relationship_ema.json # 关系 EMA 状态
│   ├── frustration.json      # 当前 frustration 值
│   └── metadata.json         # age, interaction_count, total_reward, epoch
│
└── checkpoints/               # 周期性快照（用于中断恢复）
    └── checkpoint-{epoch}.tar
```

**状态迁移原则**：
- **Self State 备份**：只备份 `state/self/`，可在新 Engine 上恢复（实验性，用于验证"自我独立于 LLM"）
- **Engine State 备份**：完整备份 `state/engine/`，用于确定性复现
- **完整备份**：备份整个 `state/` 目录，用于标准中断恢复

## 5.2 记忆存储

```
memory/
├── style_memory.json         # 风格记忆池（Genesis + Personal）
├── crystallized_events.json  # 结晶事件（带 context 向量）
└── evermemos.db              # 长期记忆（SQLite）
```

## 5.3 日志与观测

```
logs/
├── epoch_log.jsonl           # 每个 Epoch 的完整输入/输出
├── value_trajectory.jsonl    # 价值观向量时间序列
├── identity_history.jsonl    # 身份标签演化历史
└── reward_history.jsonl      # reward 时间序列
```

---

# 六、并发与容错

## 6.1 并发模型

```python
async with self._turn_lock:
    await self._cognitive_cycle(event)
```

单轮认知循环由 `asyncio.Lock` 串行化，确保内部状态一致性。

## 6.2 容错设计

| 故障场景 | 处理方式 | 是否阻塞 | 对应模块 |
|---------|---------|---------|---------|
| LLM API 超时 | 重试一次（指数退避），失败则使用默认值 | 否 | FR-7 Critic、Actor |
| LLM JSON 解析失败 | 多层容错解析（regex → 截取 → 默认值），记录失败原因 | 否 | FR-7 Critic、FR-3 Reflection |
| Event Generator LLM 失败 | 重试 → 使用模板库（预定义 50+ 事件模板）→ 失败则跳过本 Epoch | **否**（但记录错误） | FR-1 Event Generator |
| Event 类型枚举失败 | 标记事件为 `unknown_type`，后续流程用默认值 | 否 | FR-1 |
| Value Vector 数值异常 | clip 到 [-1, 1] 范围，记录异常 | 否 | FR-4 |
| 累积错误率 > 30% | 中止实验 + 报警 | **是** | 全局 |

## 6.3 中断与恢复

状态持久化支持中断和恢复：
- 每个 Epoch 结束后自动保存状态
- 重启后从最后保存的状态恢复
- 记忆和权重不丢失
