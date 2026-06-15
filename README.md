# SelfLab

**Artificial Self（人工自我）研究与规划项目**

---

## 定位

本项目**不是一个代码实现项目**，而是一个专注于**项目规划与技术探讨**的研究实验室。

我们关注的核心问题是：

> AI 如何形成持续存在的自我（Being），而非仅完成任务（Doing）

## 核心命题

- LLM 是思维机器（Thinking Machine），不是自我（Living Self）
- 人格来自经历 + 解释机制，而非预设的 Prompt
- 自我 = 记忆 + 反思 + 价值观 + 身份 + 叙事
- 对应然问题给出基于自身价值判断的回答，是"自我"的最小边界

## 使用约定

与 Claude 协作时，使用以下关键词触发不同工作流：

| 关键词 | 工作流 | 结果存放 |
|--------|--------|---------|
| **"深度分析"** 或 **"深度研究"** | 对某个主题进行深入调研和分析 | 结果存到 `research/` 对应子目录 |
| **"深度探讨"** | 对某个话题进行对话式探讨 | 走完整闭环流程（见下方） |

**"深度探讨"闭环流程**：

```
深度探讨
    │
    ▼
存档到 discussions/YYYY-MM-DD-主题.md
    │
    ▼
是否产生关键洞察？
    │
    ├── 否 → 仅记录讨论概要
    │
    ├── 是 → 添加到 SGE-Key-Insights.md
    │           │
    │           ▼
    │       检查项目级文档是否需要修正
    │           │
    │           ├── 是 → 修正 PRD/ARCH/DESIGN/ROADMAP/DEVELOP
    │           │
    │           └── 否 → 仅更新 CHANGELOG.md
    │
    ▼
自动 git add + commit + push
```

**每次对话的记录**：无论"深度分析"还是"深度探讨"，每次结束时在 `discussions/` 目录生成一个简要的会话记录，包含日期、主题、核心结论、产出文件列表。命名格式：`YYYY-MM-DD-主题.md`。

## 项目结构

```
SelfLab/
├── SGE-Key-Insights.md                    # 关键洞察集（本项目最重要的文件之一）
│
├── PRD.md                                 # 产品需求文档
├── ROADMAP.md                             # 路线图
├── ARCH.md                                # 架构文档
├── DESIGN.md                              # 详细设计文档
├── DEVELOP.md                             # 开发规范
├── CHANGELOG.md                           # 变更日志
│
├── research/                              # 研究文档
│   ├── sge-core/                          # SGE 核心研究
│   │   ├── Artificial-Self-Research-v0.1.md     # 研究纲领 v0.1
│   │   ├── Artificial-Self-Research-v0.2.md     # 研究纲领 v0.2（双系统+预测加工）
│   │   ├── SGE-Core-Insight-Is-vs-Ought.md      # 核心领悟：实然与应然的分野
│   │   ├── SGE-Corrected-Judgment-and-Application-Logic.md  # 修正判断与应用逻辑
│   │   └── SGE_AI_Value_Emergence_Authenticity.md           # 金观涛真实性哲学与AI价值涌现
│   │
│   ├── sge-feasibility/                   # SGE 可行性评估
│   │   ├── SGE-Engineering-Feasibility-Analysis.md            # 工程实现可行性
│   │   ├── SGE-Existing-Attempts-and-Gap-Analysis.md          # 现有尝试与空白分析
│   │   ├── SGE-Technology-Stack-Overview.md                   # 技术栈全景
│   │   └── Analysis-Cognitive-State-A-to-B-Relevance-and-Feasibility.md  # A→B 关联性分析
│   │
│   ├── sge-learning/                      # 借鉴与学习
│   │   ├── SGE-Learning-from-AiBeing.md              # AiBeing 引擎借鉴分析
│   │   ├── SGE-Learning-from-Authenticity-Philosophy.md  # 金观涛真实性哲学借鉴
│   │   └── SGE-Feasibility-Impact-on-AtoB.md          # SGE 对 A→B 项目的影响
│   │
│   └── cognitive-architecture/            # 认知架构调研
│       ├── Cognitive-Architectures-Overview.md        # 经典认知架构综述
│       ├── Cognitive-State-A-to-B-Research.md         # A→B 认知状态调研（完整版）
│       ├── Cognitive-State-A-to-B-Distilled.md        # A→B 调研（精要版）
│       └── Shared-Cognitive-Science-Toolbox.md        # 认知科学底层工具箱
│
├── references/                            # 参考资料
│   ├── AiBeing-Core-Engine-Reference.md             # AiBeing Genome v10 引擎（16篇合并）
│   ├── Philosophy-of-Authenticity.md                # 金观涛真实性哲学
│   └── LLM_and_Cognitive_Architecture_Complete_Discussion.md  # LLM与认知架构讨论
│
├── discussions/                           # 讨论存档（每次对话的会话记录）
└── prototypes/                            # 架构原型设计（待使用）
```

## 参与者

- Bisen（项目发起人）
- AI 协作伙伴（ChatGPT、Gemini、Claude 等）

## 当前状态

Phase 0（理论奠基）已完成：研究纲领 v0.2、认知架构调研、工程可行性评估、AiBeing 借鉴分析、金观涛真实性哲学借鉴分析。项目级文档（PRD、ROADMAP、ARCH、DESIGN、DEVELOP、CHANGELOG）已建立。下一步：Phase 1 最小验证——Value Layer 原型实验（50-100 Epochs）。
