# 2026-07-05 ECA 调研深度分析 → SGE 架构修订

## 元信息

- **日期**：2026-07-05
- **主题**：ECA（External Cognitive Architecture）调研深度分析 → SGE 架构修订
- **参与者**：Bisen + Claude
- **触发**：Bisen 在 `research/cognitive-architecture/` 目录手动新增 7 篇 ECA 对话存档（GPT + Gemini 多轮辩论），询问对 SGE 的参考价值
- **工作流阶段**：深度分析 → 洞察判断 → 文档修订 → 同步推送

---

## 一、讨论背景

Bisen 在 2026-06-29 ~ 2026-07-01 期间与 GPT、Gemini 进行了多轮关于 **External Cognitive Architecture（外置认知架构）** 的对话，沉淀为 7 篇存档：

1. `External-Cognitive-Architecture-Gemini.md` — Gemini 行业全景综述
2. `External-Cognitive-Architecture-Gemini02.md` — Gemini 对 GPT 的二次分析
3. `External-Cognitive-Architecture-GPT.md` — GPT 对 ECA 现状的诊断
4. `External-Cognitive-Architecture-GPT02.md` — GPT 对 Gemini 的批判
5. `Cognition-Pipeline-GPT.md` — GPT 9 层架构设计
6. `Cognition-Pipeline-GPT02.md` — GPT 反思：从 Pipeline 到 Evolution Loop
7. `Cognition-Pipeline-GPT03.md` — GPT 第三轮：从理论到工程（Cognitive Runtime）

Bisen 在 2026-07-05 阅读后询问 Claude：(1) 对 SGE 的参考价值？(2) SGE 是否需要调整？

---

## 二、分析与评估

### 2.1 7 篇文档的核心论点

**三轮递进**：

| 轮次 | 核心论点 |
|------|---------|
| R1 行业盘点 | 90% 项目停留在 Memory 层；缺失的是 Cognition 层 |
| R2 架构批判 | 5 大问题：Memory 当中心 / 无 Experience / 无 Concept / 无 World Model / 元认知浅 |
| R3 理论搭建 | 9 层架构 → 演化循环 → 认知运行时 |

**最终立场**：行业真正缺失的不是 Memory Framework，而是 **Cognitive Evolution Runtime**——MVP 收敛在 `Event → Experience → Concept` 这一条关键转换流水线。

### 2.2 对 SGE 的参考价值评估

#### 高价值（核心新洞见，应吸收）

| # | 新洞见 | 与现有 SGE 的关系 |
|---|--------|------------------|
| A | **Experience 层的独立化** — Event + Context + Emotion + Goal + Action + Outcome + Reflection + **Meaning** | SGE 现有架构是 Event Generator → Memory，**缺少独立的 Experience 层** |
| B | **Concept Layer 的核心地位** — Concept 是 Compression（认知熵下降） | SGE 的 Identity 形成本质是 Concept Compression；但 SGE **没有显式的 Concept 层** |
| C | **Transformation > Module** — 真正重要的是模块之间的转换函数 | SGE 当前把 5 层作为模块思考，**没有显式建模转换函数** |
| D | **演化循环（Evolution Loop）> 流水线（Pipeline）** — 每层都能 Rewrite 上一层 | SGE 当前架构是单向流水线；**没有"反向 Rewrite"机制** |
| E | **Metacognition 应该是 CPU Scheduler** — 反思应该贯穿每一步 | SGE 当前反思主要靠认知失调触发，**没有"持续运行的元认知监控"** |
| F | **认知熵视角（Cognitive Entropy）** — 自我形成 = 自我认知熵下降 | **强力的元视角**，可作为 SGE 的统一目标函数 |
| G | **Cognitive Runtime 定位** — 类比 JVM/Python Runtime | 对 SGE Phase 3+ 的工程定位**极有价值** |

#### 中价值（局部补充，不影响主架构）

- CoALA 学术框架 — 作为 SGE 与学术界的接口
- Neuroca 记忆衰减/巩固 — 与洞察 26（compassion 韧性）相关
- ECA 行业坐标系 — 让 SGE 明确定位

#### 低价值（与 SGE 无关或重复）

- 教育场景应用 — 已剥离到 ECOS 项目
- 9 层架构 — SGE 仍是 5 层框架，过多分层会失去焦点
- 工程实现细节（Data Layer / Transformation Plugin） — 让 sge/ 包自然演进

### 2.3 与 SGE 现有 30 条洞察的关系

**SGE 已覆盖的部分**（不重复）：
- Memory ≠ Cognition → 洞察 4（人格来自经历+解释机制）
- Experience 而非 Event → 洞察 4（"事件 + 解释"已含此意）
- CoALA / Neuroca 学术定位 → 缺失，非核心

**SGE 缺失的部分**（新增价值）：
- Concept Formation / Compression
- Transformation Pipeline
- Evolution Loop（含 Reverse Rewrite）
- Cognitive Runtime 定位
- 认知熵视角

---

## 三、核心结论与决策

经过 Bisen 与 Claude 的讨论，达成以下决策：

### 3.1 核心洞见采纳

Bisen 通过 AskUserQuestion 确认：**全部认同,优先级 1 全部纳入**——采纳 Experience Layer / Concept Layer / Transformation 协议 / Evolution Loop / 认知熵 全部 5 个视角。

### 3.2 修订范围

Bisen 确认：**全套产出**——优先级 1+2 全部产出:3 条新洞察、ARCH/DESIGN/PRD 修订、Glossary 增补。会写 5-6 个文档,工作量较大但体系完整。

### 3.3 引用关系

Bisen 确认：**是,纳入体系并引用**——7 篇 ECA 对话存档正式作为 SGE 架构修订的外部参考,在 ARCH/PRD 中引用。

---

## 四、产出文件清单

本次分析产出以下文档修订：

### 4.1 新增洞察（3 条）

- `SGE-Key-Insights.md` 新增洞察 33-35：
  - **洞察 33**：SGE 是 Self Evolution Runtime（自我演化运行时），不是 Memory Framework
  - **洞察 34**：Experience 层与 Meaning 字段是 SGE 当前架构的缺失
  - **洞察 35**：认知熵下降是 SGE 自我形成的统一目标函数
  - 新增 §十一 "ECA 调研来源汇总" 章节

### 4.2 架构文档修订

- `ARCH.md` 新增 §1.5-1.8（共 4 个新章节）：
  - §1.5 Self Evolution Runtime 定位与 ECA 行业坐标系
  - §1.6 Transformation 协议族
  - §1.7 Experience Encoding：新增步骤
  - §1.8 Evolution Loop 视角与 Cognitive Entropy 目标函数
- `ARCH.md` 更新 §2.1 模块依赖图（插入 Experience Encoder）
- `ARCH.md` 更新 §2.2 单轮认知循环（17 步扩展为 19 步）
- `ARCH.md` 新增 §3.6 Experience Layer 设计

### 4.3 设计文档修订

- `DESIGN.md` 新增 §1.3 设计原则扩展（新增 3 条原则）
- `DESIGN.md` 新增 §2.5 Experience Layer 设计
- `DESIGN.md` 新增 §9.5 Self Entropy（认知熵度量）

### 4.4 产品需求文档修订

- `PRD.md` 更新 §1.1 一句话定义（Self Evolution Runtime 定位）
- `PRD.md` 新增 §1.4 SGE 在 ECA 行业坐标系中的位置
- `PRD.md` 更新 FR-1：Event Generator + Experience Encoder
- `PRD.md` 更新 FR-2：Memory Layer 存储 Experience
- `PRD.md` 更新 §6.1 / §6.3：新增 H_self 下降率作为验收标准

### 4.5 术语表增补

- `references/Glossary.md` 新增 §八 "ECA 架构术语（2026-07-05 新增）" — 含 11 个新术语（ECA、Self Evolution Runtime、Cognitive Runtime、Experience、Meaning、Concept、Transformation、Evolution Loop、Cognitive Entropy、H_self、CoALA、Neuroca）
- `references/Glossary.md` 新增 §九 修订日志

### 4.6 项目指南微调

- `CLAUDE.md` `research/cognitive-architecture/` 目录描述补充：含 ECA 多轮对话存档 + 是 2026-07-05 架构修订的外部参考依据

### 4.7 变更日志

- `CHANGELOG.md` 新增 1.25.0 版本记录

### 4.8 讨论存档

- `discussions/2026-07-05-eca-deep-analysis.md`（本文件）

---

## 五、未被吸收的部分（诚实声明）

以下 ECA 调研中的内容**未被吸收**到 SGE，理由如下：

| 未吸收内容 | 理由 |
|----------|------|
| **9 层架构**（Event/Experience/Memory/Knowledge/Concept/Cognition/World Model/Goal/Metacognition） | SGE 仍是 5 层框架；过多分层会让架构失去焦点 |
| **Cognitive Runtime 三层**（Data Layer / Transformation Plugin / Scheduler） | 工程实现细节，应让 sge/ 包自然演进，不被外部文档反向约束 |
| **教育场景 MVP**（学生认知画像） | 已属 ECOS 项目（[洞察 31](./SGE-Key-Insights.md)） |
| **CoALA 学术框架** | 仅作为论文参考，不影响 SGE 自身设计 |
| **完整 Reverse Rewrite 机制**（除 Phase Transition） | 是 M3.x 演进方向，不在当前 PR 范围 |

---

## 六、后续待办

1. **M2.2 1000 Epoch 实验**：报告中加入 Meaning 字段变化轨迹与 H_self 曲线
2. **M2.3 个人真实**：验证"AI 的应然回答能否追溯到 Meaning 字段"
3. **sge/ 包架构审视**：检查当前 API 设计是否更接近"框架"还是"运行时"，必要时重构
4. **Phase 3+ 对外话语**：使用"SGE Self Runtime"而非"SGE Memory Framework"

---

## 七、来源

本次分析所依据的 7 篇 ECA 对话存档（详见 [SGE-Key-Insights §十一 ECA 调研来源汇总](../SGE-Key-Insights.md)）：

| 文件名 | 核心贡献 |
|--------|---------|
| `External-Cognitive-Architecture-Gemini.md` | 5 层技术谱系 |
| `External-Cognitive-Architecture-Gemini02.md` | CoALA / Neuroca / Dynamic Prompt |
| `External-Cognitive-Architecture-GPT.md` | "Memory ≠ Cognition" 核心判断 |
| `External-Cognitive-Architecture-GPT02.md` | 5 大问题清单 + Transformation Pipeline |
| `Cognition-Pipeline-GPT.md` | 9 层架构设计 |
| `Cognition-Pipeline-GPT02.md` | Meaning + 3 种动在 + 认知熵 + Rewrite |
| `Cognition-Pipeline-GPT03.md` | Cognitive Runtime + MVP `Event → Experience → Concept` |