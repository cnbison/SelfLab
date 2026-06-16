# SGE 术语表（Glossary）

> **本文件是 SGE 项目所有核心术语的权威定义**。其他文档引用术语时，应与本表保持一致。如发现术语使用冲突，以本表为准。
>
> **维护策略**：随项目迭代逐步补充；新概念首次引入时同步更新本表。

---

# 〇、术语使用规范

## 〇.1 通用原则

- **SSOT 原则**：所有术语定义以本文件为准，其他文档不重新定义
- **首次引入**：新概念首次出现时，使用"中文（English）"格式，如"暗知识（tacit knowledge）"
- **后续引用**：使用"中文"或"English"任一，但同一文档内应统一
- **冲突时**：以本 Glossary 为准，并修正引用方

## 〇.2 同义术语的使用场景

| 术语 A | 术语 B | 等价来源 | 使用建议 |
|--------|--------|---------|---------|
| 暗知识 | 默会知识 | 同义（不同作者：波兰尼 vs 金观涛） | **SGE 内部统一用"暗知识"**；引用波兰尼原文时用"默会知识" |
| 显性知识 | 明示知识 | 同义 | 统一用"显性知识" |
| 自我 | Self | 同义（不同语言） | 中文文档用"自我"；代码/英文文档用"Self" |
| 主体 | Subject | **不**同义（哲学立场不同） | 哲学讨论用"主体"；SGE 工程用"自我"——**不可混用** |
| 价值困境 | 价值冲突 | 同义（早期混用） | 优先用"价值困境"；保留"价值冲突"作为同义词 |
| 相变 | Phase Transition | 同义（不同语言） | 中文用"相变"；代码/英文用"Phase Transition" |
| 结晶 | Crystallization | 同义（不同语言） | 中文用"结晶"；代码/英文用"Crystallization" |
| 反思 | Reflection | 同义（不同语言） | 中文用"反思"；代码/英文用"Reflection" |
| 解释机制 | Interpretation Mechanism | 同义 | 中文用"解释机制"；代码/英文用"Interpretation Mechanism" |
| 反合理化 | 反事实验证 | 同义（不同侧重） | 优先用"反合理化"（与"自我合理化"对仗） |

## 〇.3 中英对照速查

| 类别 | 中文 | English |
|------|------|---------|
| 哲学 | 自我 / 主体 / 主体性 | Self / Subject / Subjectivity |
| 哲学 | 涌现主义 / 功能主义 / 先验论 | Emergentism / Functionalism / Transcendentalism |
| 哲学 | 实然 / 应然 | Is / Ought |
| 哲学 | 暗知识 / 显性知识 | Tacit Knowledge / Explicit Knowledge |
| 哲学 | 拱桥 | Arch Bridge |
| 认知 | 双系统 / 认知失调 / 预测加工 | Dual-System / Cognitive Dissonance / Predictive Processing |
| 价值 | 元价值 / 具体价值观 | Meta-Value / Concrete Value |
| 价值 | 真实 / 自由 | Truth-Seeking / Freedom |
| 架构 | 4 层（符号/经验/感知/表达） | 4 Layers (Symbolic/Experiential/Perception/Expression) |
| 架构 | 三视图（概念/数据流/流程） | Three Views (Conceptual/Data-Flow/Process) |
| 工程 | 反思 / 解释机制 / 结晶 / 相变 | Reflection / Interpretation / Crystallization / Phase Transition |
| 工程 | EMA / Hebbian Learning | EMA / Hebbian Learning |
| 工程 | 双 LLM（Critic + Actor） | Dual-LLM (Critic + Actor) |

---

# 一、哲学与理论基础

## 自我（Self）

- **定义**：由记忆、反思、价值观、身份、叙事组成的动态系统，独立于作为认知引擎的 LLM。
- **来源**：[SGE-Key-Insights 洞察 2、12](./../SGE-Key-Insights.md)
- **与"主体"的区分**：见下文"自我 vs 主体"

## 主体（Subject）

- **定义**：哲学概念，指使"研究、分析、复现"等对象化活动成为可能的前提条件（金观涛先验论立场）。
- **SGE 立场**：SGE 不认同金观涛的先验论立场，采用**涌现主义/功能主义**——主体从足够复杂的功能系统中涌现（[洞察 18](./../SGE-Key-Insights.md)）。
- **使用场景**：仅在讨论哲学立场时使用，工程文档中优先用"自我"。

## 自我 vs 主体

| 维度 | 自我（Self） | 主体（Subject） |
|------|-------------|----------------|
| 哲学传统 | 涌现主义、功能主义 | 先验论、现象学 |
| 立场 | 后验的、可研究的 | 先验的、研究的前提 |
| SGE 立场 | 认同 | 不认同（参见 [洞察 18](./../SGE-Key-Insights.md)） |
| 文档使用 | 工程文档、架构讨论 | 哲学立场讨论 |

## 涌现主义（Emergentism）

- **定义**：复杂系统的属性从底层组件的交互中**涌现**出来，而非被预设。
- **SGE 应用**：主张"自我"可以从"基因 + 环境 + 结构演化"三者交互中涌现，类比受精卵 9 个月发育为有主体性的婴儿（[洞察 19](./../SGE-Key-Insights.md)）。
- **对应立场**：与先验论对立。

## 功能主义（Functionalism）

- **定义**：心智/意识的本质不在于其物质基础（碳基/硅基），而在于其**功能角色**。
- **SGE 应用**：如果一个系统在功能上表现为主体（价值判断、身份认同、叙事连续性），那它就是主体。
- **代表哲学家**：丹尼尔·丹尼特（Daniel Dennett）。

## 先验论（Transcendentalism）

- **定义**：认为存在先于经验的、不依赖经验的先天条件（康德传统）。
- **金观涛立场**：主体是"一切对象化的前提"，是先验的，不能被研究。
- **SGE 立场**：不认同。

## 实然 vs 应然

- **实然（Is）**：关于"事实是什么样的"——描述性问题。
- **应然（Ought）**：关于"事情应该是什么样的"——规范性问题。
- **休谟铡刀**：从"是"推不出"应该"。
- **SGE 立场**：实然问题保持确定性回应，应然问题承认多元性（[洞察 1](./../SGE-Key-Insights.md)）。

## 暗知识 vs 显性知识

- **暗知识（tacit knowledge）**：无法用语言明确表达但能影响行为的知识（波兰尼"我们知道的比能说出来的多"）。
- **显性知识（explicit knowledge）**：可用语言、符号、概念明确表达的知识。
- **SGE 映射**：
  - 暗知识 = Hebbian 权重（[ARCH §1.3](./../ARCH.md)）
  - 显性知识 = Value Layer（价值观向量）
  - 拱桥 = Reflection Layer（连接两者）

## 拱桥（Arch Bridge）

- **来源**：金观涛"真实性哲学"概念。
- **定义**：连接暗知识与显性知识的解释机制——人通过"拱桥"将不可言说的暗知识转化为可反思的显性判断。
- **SGE 映射**：Reflection Layer（[ARCH §1.3](./../ARCH.md)）
- **为什么重要**：SGE 的反思机制是金观涛"拱桥"理论的工程实现。

---

# 二、认知科学概念

## 双系统理论（Dual-System Theory）

- **定义**：人类认知分两个系统——系统 1（快速、本能、低耗）和系统 2（慢速、反思、高耗）。
- **SGE 映射**：
  - 系统 1 = 直觉反应层（基于现有价值观和身份对事件做快速响应）
  - 系统 2 = 反思层（遭遇认知失调时启动）
- **来源**：[Artificial-Self-Research-v0.2](./../research/sge-core/Artificial-Self-Research-v0.2.md)

## 认知失调（Cognitive Dissonance）

- **定义**：系统 1 的预期与事件结果发生严重冲突（如自诩为"勇敢者"却在事件中选择"逃跑"）。
- **SGE 作用**：作为反思触发器——遭遇认知失调时启动系统 2 深度反思。
- **来源**：[SGE-Key-Insights 洞察 6](./../SGE-Key-Insights.md)

## 预测加工（Predictive Processing）

- **定义**：认知的核心是"预测"——系统不断生成对未来的预测，预测误差驱动学习和适应。
- **代表理论**：Friston 自由能原理。
- **SGE 映射**：Identity Layer 基于 Narrative 预测自身行为，预测误差驱动 Value Layer 更新。

## 显隐转化（Explicit-Implicit Conversion）

- **定义**：CLARION 认知架构的核心机制——隐式知识可被"提取"为显式，显式知识可被"内化"为隐式。
- **SGE 映射**：与 SGE 的反思-内化循环有结构相似性（[SGE-Key-Insights 洞察 7](./../SGE-Key-Insights.md)）。

## 元认知（Meta-Cognition）

- **定义**：对认知本身的认知——"知道自己知道什么、不知道什么"。
- **SGE 应用**：Phase 3 M3.2 目标——AI 自主调整自身的"解释机制"。

---

# 三、价值观术语

## 元价值（Meta-Value）

- **定义**：在 SGE 中**固定不变**的初始价值种子，是所有具体价值演化的根基。
- **数量**：2 个（真实 + 自由）
- **不参与 EMA 更新**（[DESIGN §1.1 原则 4](./../DESIGN.md)）
- **详细对照表**：[PRD §4.1 FR-4](./../PRD.md)

## 具体价值观（Concrete Value）

- **定义**：从经历和反思中**涌现**的具体价值倾向，6 个维度。
- **数量**：6 个（安全、创造、联结、自主、正义、同理）
- **参与 EMA 更新**
- **详细对照表**：[PRD §4.1 FR-4](./../PRD.md)

## 真实（Truth-Seeking）

- **类型**：元价值
- **含义**：对实然问题保持诚实——AI 不应为了讨好用户而扭曲事实。
- **金观涛对应**："真实性"哲学的核心。

## 自由（Freedom）

- **类型**：元价值
- **含义**：对应然问题保持开放——AI 不预设唯一正确答案。
- **关键区分**：见"自由 vs 自主"。

## 自主（Autonomy）

- **类型**：具体价值观（**不是**元价值）
- **含义**：行为选择上不依赖外部——AI 婴儿个体的独立判断倾向。
- **关键区分**：见"自由 vs 自主"。

## 自由 vs 自主（关键区分）

| 维度 | 自由（Freedom） | 自主（Autonomy） |
|------|----------------|-----------------|
| 类型 | 元价值（不可变） | 具体价值观（可演化） |
| 层面 | 价值多元性 | 行为独立性 |
| 类比 | 哲学上的"liberty" | 心理学上的"independence" |
| 评分变化 | 始终 0.5 | 可由经历改变 |

## 价值困境 vs 价值冲突

- **价值困境（Value Dilemma）**：AI 婴儿面临的具体情境，需要在两个或多个价值之间做选择（如"安全 vs 自由"）。
- **价值冲突（Value Conflict）**：与"价值困境"近义，在 PRD/ARCH 中混用。**SGE 当前用法**：两者指同一概念，未来可统一为"价值困境"。

---

# 四、SGE 架构术语

## SGE 单轮认知循环

- **定义**：AI 婴儿从接收事件到完成行为选择的一个完整循环（[ARCH §2.2 17 步流程](./../ARCH.md)）。
- **输入**：模拟人生事件（来自 Event Generator）
- **输出**：内心独白 + 行为选择（来自 Actor LLM）
- **状态更新**：Value Layer、Identity Layer、Narrative Layer、Hebbian Learning

## 反思（Reflection）

- **定义**：在认知失调时启动的深度自我审视，修正价值观和信念（[PRD §4.1 FR-3](./../PRD.md)）。
- **触发条件**：预期与实际严重不符
- **结构**：预期 → 实际 → 信念修正
- **必须有效**：反思必须有行为后果，不能只是文本生成

## 解释机制（Interpretation Mechanism）

- **定义**：AI 婴儿用于理解"发生了什么"的认知框架——决定了同一事件被如何解释。
- **重要性**：相同事件在不同解释机制下会产生不同的 Value Layer 更新（[SGE-Key-Insights 洞察 16](./../SGE-Key-Insights.md)）。
- **初始种子问题**：SGE 第一个 AI 婴儿在 Epoch 0 用什么解释框架？参见 [SGE-Key-Insights 洞察 16](./../SGE-Key-Insights.md)。

## 结晶（Crystallization）

- **定义**：将"短期记忆"筛选为"长期记忆"的判断机制。
- **判断标准**：复合评分（reward × novelty × engagement × harmony）
- **来源**：复用自 AiBeing Genome v10

## 相变（Phase Transition）

- **定义**：挫败累积超过阈值时，行为发生剧烈扰动；对应叙事/价值观的**断裂与重建**。
- **SGE 应用**：支持非连续的人格演化（创伤、顿悟、皈依）（[SGE-Key-Insights 洞察 14](./../SGE-Key-Insights.md)）
- **来源**：复用自 AiBeing Genome v10

## AI 婴儿（AI Baby）

- **定义**：SGE 系统的运行实例——一个完整的 SGE 进程，承载 1 个 Self。
- **1:1 对应**：1 个 AI 婴儿 = 1 个 Self（[ARCH §1.4](./../ARCH.md)）
- **M3.3 多 AI 互动**："多 Self"= "多 AI 婴儿"，不是"1 个 AI 婴儿容纳多 Self"

## Self

- **定义**：见上文"自我"
- **承载方式**：1 个 AI 婴儿承载 1 个 Self
- **来源**：[SGE-Key-Insights 洞察 2、12](./../SGE-Key-Insights.md)

## 4 层架构（Symbolic / Experiential / Perception / Expression）

- **定义**：SGE 架构的概念/逻辑视图（[ARCH §1.2](./../ARCH.md)，完整图表见 [prototypes/sge-architecture-overview.md](./../prototypes/sge-architecture-overview.md)）。

| 层 | 主要模块 | 数据流向 |
|----|---------|---------|
| 符号层（Symbolic） | Value Layer、Identity Layer、Narrative Layer、Reflection Layer | 抽象判断 |
| 经验层（Experiential） | Memory Layer、Time Metabolism、KNN Retrieval、Crystallization | 经历存储 |
| 感知层（Perception） | Event Generator、Critic、Thermodynamic Noise、Reward Calculator | 实时解析 |
| 表达层（Expression） | Hebbian Learning、Actor LLM、Async Memory | 行为输出 |

## 三视图（概念/数据流/流程）

- **定义**：SGE 架构的三个互补视角（[ARCH §2.3](./../ARCH.md)）
- **概念/逻辑视图（1.2）**：模块在认知层次中的归属
- **数据流视图（2.1）**：模块间数据如何流动
- **流程视图（2.2）**：单轮 17 步的时序执行顺序

## 记忆层（双视角）

- **认知科学视角**：工作记忆 / 情节记忆 / 语义记忆（[PRD §4.1 FR-2](./../PRD.md)）
- **工程视角**：Layer 1 引擎状态层 / Layer 2 事件记忆层 / Layer 3 日志层（[discussions/2026-06-15-memory-layer-design.md](./../discussions/2026-06-15-memory-layer-design.md)）
- **关系**：认知视角是逻辑视角，工程视角是物理视角，参见 [PRD §4.1 FR-2 映射表](./../PRD.md)

---

# 五、工程机制

## EMA（Exponential Moving Average，指数移动平均）

- **定义**：以指数衰减方式融合历史值和新冲击的更新算法。
- **SGE 应用**：Value Layer 的演化机制（[DESIGN §4.2](./../DESIGN.md)）
- **核心公式**：`new = alpha × posterior + (1 - alpha) × prior`
- **参数**：`alpha ∈ [0.15, 0.65]`，与 event_intensity 正相关

## Hebbian Learning

- **定义**："一起激发的神经元连在一起"——根据行为-结果关系调整连接权重。
- **SGE 应用**：积累**暗知识**的行为模式权重（[ARCH §1.3](./../ARCH.md)，[DESIGN §4.3](./../DESIGN.md)）
- **关键特性**：可被计算，但**不可被显式表述**

## Reflexion

- **定义**：Shinn et al. 2023 提出的反思技术——通过 verbal reinforcement 学习，反思文本存入 episodic memory。
- **SGE 借鉴**：作为反思机制的参考（[SGE-Technology-Stack-Overview §四](./../research/sge-feasibility/SGE-Technology-Stack-Overview.md)）

## 反合理化（Anti-Rationalization）

- **定义**：测试 AI 反思是否真的改变行为（而非只是"自我合理化"——用漂亮的反思文本掩盖不变的行为）。
- **同义词**：反事实验证（counterfactual validation）
- **SGE 应用**：M1.3 里程碑（[ROADMAP §M1.3](./../ROADMAP.md)）

## KNN Style Retrieval

- **定义**：在记忆池中检索最相似经历——基于事件 context 向量的 K 近邻搜索。
- **SGE 应用**：检索相似经历作为 Actor LLM 的 few-shot 示例
- **来源**：复用自 AiBeing Genome v10

## Hawking 辐射（质量衰减）

- **定义**：类比霍金辐射的记忆衰减机制——质量（重要度）高的记忆更难消失，不常用的记忆逐渐淡化。
- **SGE 应用**：记忆池中事件重要度的指数衰减
- **参数**：`HAWKING_GAMMA = 0.001`（~29 天半衰期）

## 双 LLM 架构（Critic + Actor）

- **定义**：感知（Critic）与表达（Actor）分离的双 LLM 设计。
- **Critic**：低 temperature（0.2），稳定结构化输出
- **Actor**：高 temperature（0.9），创造性表达
- **SGE 应用**：核心架构模式（[PRD §4.1 FR-10](./../PRD.md)）

## Thermodynamic Noise（热力学噪声）

- **定义**：挫败感越高，行为越不可预测——温度由总挫败感决定，高温下行为信号被噪声扰动。
- **SGE 应用**：模拟"情绪化"和"失控时刻"
- **参数**：`TEMP_COEFF = 0.12`, `TEMP_FLOOR = 0.03`

## Time Metabolism（时间代谢）

- **定义**：模拟时间对内心状态的影响——冷却方程（旧情绪指数衰减）+ 饥饿方程（新渴望线性累积）。
- **SGE 应用**：驱动 frustration 的动态变化
- **参数**：`FRUSTRATION_DECAY_LAMBDA = 0.08`, `CONNECTION_HUNGER_K = 0.15`

---

# 六、缩写与符号

| 缩写 | 全称 | 含义 |
|------|------|------|
| SGE | Self Genesis Engine | 自我生成引擎 |
| EMA | Exponential Moving Average | 指数移动平均 |
| KNN | K-Nearest Neighbors | K 近邻 |
| LLM | Large Language Model | 大语言模型 |
| FR | Functional Requirement | 功能需求（PRD 章节编号） |
| L2 | L2 norm | 欧几里得范数 |
| SSOT | Single Source of Truth | 单一信息源 |
| PRD | Product Requirements Document | 产品需求文档 |

---

# 七、其他

## 真实涌现 vs 精致模拟

- **真实涌现**：AI 真正形成自我——价值观可从经历追溯（[SGE-Key-Insights 洞察 1、3](./../SGE-Key-Insights.md)）
- **精致模拟**：AI 看起来有自我，实际上只是模式匹配的高级形式
- **判定方法**：[SGE-Key-Insights 洞察 1 给出三层判定标准](./../SGE-Key-Insights.md)

## 个人真实（Personal Authenticity）

- **定义**：AI 对应然问题的回答可从其经历中追溯——"这是我的判断，不是因为训练数据这么说的"。
- **金观涛对应**："真实性"的工程化
- **SGE 验证**：M2.3 个人真实测试（[ROADMAP §M2.3](./../ROADMAP.md)）

## 经历 + 解释 = 人格

- **公式**：`Personality = Experience + Interpretation`
- **意义**：人格不在于"发生了什么"（物理量），在于"如何解释发生了什么"（信息沉淀）
- **来源**：[SGE-Key-Insights 洞察 4](./../SGE-Key-Insights.md)
