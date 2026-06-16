# CLAUDE.md - SelfLab 项目指南

## 项目性质

**本项目是研究规划与技术探讨项目，不是代码实现项目。**

所有工作应围绕以下活动展开：
- 研究文档的撰写、评审与迭代
- 认知架构的设计与论证
- 技术路线的分析与比较
- 哲学与科学问题的探讨

不应产出可运行的应用代码。如需代码片段用于说明概念，以伪代码或示意性代码为主。

## 项目背景

SelfLab 探索"人工自我（Artificial Self）"——AI 能否形成持续存在的自我认同、价值观、人生叙事与成长轨迹。核心研究纲领见 `research/sge-core/` 目录，关键洞察见项目根目录 `SGE-Key-Insights.md`。

## 子项目：A→B 调研

> **A→B 是 SelfLab 的并行子项目**——与 SGE（人工自我）使用**相同的认知科学底层工具箱**，但目标不同。
>
> 当用户提及"A→B"、"认知状态向量"、"学习迁移"等关键词时，参考 [research/cognitive-architecture/](./research/cognitive-architecture/) 和 [research/sge-learning/SGE-Feasibility-Impact-on-AtoB.md](./research/sge-learning/SGE-Feasibility-Impact-on-AtoB.md)。

| 维度 | SGE（自我生成） | A→B（学习状态迁移） |
|------|----------------|---------------------|
| **目标** | AI 能否形成持续自我 | 人的学习状态如何估计与迁移 |
| **核心问题** | "AI 能否成为存在" | "如何从 A 状态迁移到 B 状态" |
| **状态语义** | 存在性身份（价值观、叙事） | 功能能力（9 维认知状态向量） |
| **应用** | 数字孪生、AI 陪伴、Personal AI | 自适应学习系统、教育 AI |
| **研究文档** | `research/sge-core/`、`research/sge-feasibility/` | `research/cognitive-architecture/` |

**为什么 A→B 调研放在 SelfLab**：
- 两者共享 7 个认知科学工具（贝叶斯更新、预测加工、双系统、记忆分层、BDI、元认知等）
- SGE 验证后可赋能 A→B 升级为"有灵魂的教育者"（[洞察 11](./SGE-Key-Insights.md)）
- 同一研究者（Bisen）关注这两个方向

**A→B 关键文档**：
- [Cognitive-State-A-to-B-Research.md](./research/cognitive-architecture/Cognitive-State-A-to-B-Research.md) — 完整调研
- [Cognitive-State-A-to-B-Distilled.md](./research/cognitive-architecture/Cognitive-State-A-to-B-Distilled.md) — 精要版
- [SGE-Feasibility-Impact-on-AtoB.md](./research/sge-learning/SGE-Feasibility-Impact-on-AtoB.md) — SGE 对 A→B 的影响

## 用户与协作

**项目发起人**：Bisen
- **背景**：关注 AI 认知架构与人工自我的研究者
- **专业领域**：哲学（现象学、金观涛真实性哲学）、认知科学、AI 架构
- **协作偏好**：
  - 深度讨论与跨工具协作（同时使用 ChatGPT、Gemini、Claude 等）
  - 重视哲学层面的硬问题（意识、主体性、自我与模拟的边界）
  - 倾向于结构化、可追溯的文档体系
  - 接受挑战既有框架的批判性思考

**AI 协作伙伴的预期角色**：
- 研究助手：协助文献调研、概念梳理
- 架构师：辅助认知架构的设计与论证
- 评审者：对设计决策提供批判性反馈
- 文档维护者：确保文档体系的一致性和可追溯性

**协作者背景假设**：当与 Bisen 协作时，默认对方熟悉金观涛真实性哲学、ACT-R/SOAR/LIDA 等经典认知架构、LLM 基础概念。可直接使用专业术语，无需展开基础解释。

## 协作规范

- 文档语言以中文为主，技术术语保留英文
- 研究纲领使用版本号管理（v0.1、v0.2 ...）
- 讨论记录应标注参与者和日期
- 引用外部理论时注明来源

## 核心工作流：探讨 → 洞察 → 修正

每次有价值的讨论应遵循以下闭环流程：

### 第一步：讨论存档

每次深度讨论结束后，将讨论内容保存到 `discussions/` 目录。文件命名格式：

```
discussions/YYYY-MM-DD-主题关键词.md
```

内容应包含：讨论背景、核心观点、论证过程、结论与开放问题。

### 第二步：洞察判断

讨论结束后，判断本次讨论是否产生了**关键洞察**。判断标准：

- 是否提出了新的核心概念或框架？
- 是否修正或推翻了之前的某个假设？
- 是否建立了新的理论映射或类比？
- 是否明确了项目的哲学立场或技术方向？

如果满足以上任一条件，将洞察添加到 `SGE-Key-Insights.md`，格式与现有洞察保持一致（一句话 + 完整论证 + 来源标注）。

### 第三步：项目文档修正

每条新洞察产生后，检查以下项目级文档是否需要修正：

| 文档 | 检查内容 |
|------|---------|
| PRD.md | 核心假设、功能需求、成功标准是否受影响 |
| ARCH.md | 设计哲学、模块架构、技术选型是否受影响 |
| DESIGN.md | 设计原则、算法设计、参数配置是否受影响 |
| ROADMAP.md | 阶段划分、里程碑、依赖关系是否受影响 |
| DEVELOP.md | 技术栈、测试策略是否受影响 |
| CHANGELOG.md | 记录本次变更 |

如果受影响，修正对应文档，并在 CHANGELOG.md 中记录。

### 第四步：自动同步推送

完成上述所有步骤后，执行 git add、commit 和 push。

### 流程示意

```
深度讨论 / 深度分析
    │
    ▼
【第 0 步】深度分析 → 存档到 research/ 对应子目录
    │
    ▼
【第 1 步】讨论存档 → discussions/YYYY-MM-DD-主题.md
    │
    ▼
【第 2 步】是否产生关键洞察？
    │
    ├── 否 → 继续
    │
    └── 是 → 添加到 SGE-Key-Insights.md
              │
              ▼
          【第 3 步】检查项目级文档是否需要修正
              │
              ├── 是 → 修正 PRD/ARCH/DESIGN/ROADMAP/DEVELOP
              │         更新 CHANGELOG.md
              │
              └── 否 → 仅更新 CHANGELOG.md
    │
    ▼
【第 4 步】会话记录 → 在 discussions/ 生成简要记录
    │          （包含日期、主题、核心结论、产出文件列表）
    │
    ▼
【第 5 步】git add + commit + push
```

## 目录约定

- `SGE-Key-Insights.md` — 关键洞察集（项目最重要的文件之一）
- `PRD.md` — 产品需求文档
- `ROADMAP.md` — 路线图
- `ARCH.md` — 架构文档
- `DESIGN.md` — 详细设计文档
- `DEVELOP.md` — 开发规范
- `CHANGELOG.md` — 变更日志
- `research/sge-core/` — SGE 核心研究（纲领、洞察、哲学基础）
- `research/sge-feasibility/` — SGE 可行性评估（工程、空白、关联性）
- `research/sge-learning/` — 借鉴分析（AiBeing、真实性哲学、对A→B的影响）
- `research/cognitive-architecture/` — 认知架构调研（经典架构、A→B、工具箱）
- `references/` — 参考资料（外部论文、引擎文档、哲学文献），含 `Glossary.md` 术语表
- `discussions/` — 讨论存档（每次深度讨论的完整记录）
- `prototypes/` — 架构原型设计图与系统描述（非可运行代码）

> **术语使用约定**：所有 SGE 文档涉及核心术语时，应与 [references/Glossary.md](./references/Glossary.md) 保持一致。如发现术语使用冲突，以 Glossary.md 为准。

## 深度分析存档策略

当用户说"深度分析"或"深度研究"时，默认将分析结果保存为 `research/` 对应子目录下的 MD 文件（sge-core / sge-feasibility / sge-learning / cognitive-architecture），而非仅在对话中输出。文件命名应体现主题，格式与现有研究文档保持一致。保存后告知用户文件路径。

当用户说"深度探讨"时，走完整闭环流程（见"核心工作流"章节）。

**会话记录**：无论"深度分析"还是"深度探讨"，每次对话结束时在 `discussions/` 目录生成一个简要的会话记录（`YYYY-MM-DD-主题.md`），包含日期、主题、核心结论、产出文件列表。

## 自动同步推送策略

每次完成内容或文件的增删改任务后，自动执行 git add、commit 和 push，无需用户手动触发。commit message 应简要概括变更内容。

## 讨论风格

鼓励批判性思考与深度追问。不回避哲学层面的硬问题（意识、主体性、自我与模拟的边界）。欢迎挑战既有框架，而非仅在框架内做修补。
