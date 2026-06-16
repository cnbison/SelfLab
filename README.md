# SelfLab

**Artificial Self（人工自我）研究与规划项目**

---

## 定位

本项目**是一个研究规划与技术探讨项目**，专注于人工自我的理论研究与实验验证。

我们关注的核心问题是：

> AI 如何形成持续存在的自我（Being），而非仅完成任务（Doing）

### 项目阶段与产物形态

| 阶段 | 状态 | 文档产出 | 代码产出 |
|------|------|---------|---------|
| **Phase 0** 理论奠基 | ✅ 已完成 | 全部项目级文档 | ❌ 无 |
| **Phase 1** 最小验证 | 🔜 即将开始 | 实验报告 + 修订文档 | ✅ 一次性实验代码（`experiments/`） |
| **Phase 2** 完整实验 | ⏳ 待 Phase 1 | 实验报告 + 修订文档 | ✅ 实验代码 + 小工具 |
| **Phase 3+** 系统完善 | ⏳ 待 Phase 2 | 应用原型设计 | ✅ 实验代码 + 原型代码 |

**关键区分**：
- **SelfLab 主仓库**：始终是**研究文档**为主导
- **实验代码**：Phase 1+ 出现，存放于 `experiments/`，**一次性**，不演进为可复用应用
- **可复用代码**（如未来需要）：应**新建独立仓库**（如 SGE-Prototype），而不是在 SelfLab 内重构

详细约定见 [CLAUDE.md §实验代码约定](./CLAUDE.md)。

## 核心命题

- LLM 是思维机器（Thinking Machine），不是自我（Living Self）—— 详见 [SGE-Key-Insights 洞察 2](./SGE-Key-Insights.md)
- 人格来自经历 + 解释机制，而非预设的 Prompt
- 自我 = 记忆 × 反思 + 价值观 + 身份 + 叙事 —— 详见 [SGE-Key-Insights 洞察 12](./SGE-Key-Insights.md)
- 对应然问题给出基于自身价值判断的回答，是"自我"的最小边界 —— 详见 [SGE-Key-Insights 洞察 1](./SGE-Key-Insights.md)
- **哲学立场**：涌现主义/功能主义 vs 金观涛先验论 —— 详见 [SGE-Key-Insights 洞察 18, 19](./SGE-Key-Insights.md)

## 子项目

| 子项目 | 目标 | 状态 |
|--------|------|------|
| **SGE（自我生成）** | 验证 AI 能否形成持续自我 | Phase 0 完成，Phase 1 待启动 |
| **A→B（学习状态迁移）** | 人的学习状态如何估计与迁移 | 调研完成（`research/cognitive-architecture/`） |

A→B 与 SGE 共享 7 个认知科学工具但目标不同，详见 [CLAUDE.md §子项目 A→B 调研](./CLAUDE.md)。

## 使用约定

与 Claude 协作时，使用以下关键词触发不同工作流：

| 关键词 | 工作流 | 结果存放 |
|--------|--------|---------|
| **"深度分析"** 或 **"深度研究"** | 对某个主题进行深入调研和分析 | 结果存到 `research/` 对应子目录 |
| **"深度探讨"** | 对某个话题进行对话式探讨 | 走完整闭环流程（见下方） |

**"深度探讨"闭环流程**（[CLAUDE.md §核心工作流](./CLAUDE.md) 6 步）：

```
深度探讨 / 深度分析
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
    │
    ▼
【第 5 步】git add + commit + push
```

**讨论文件模板**：[`discussions/_TEMPLATE.md`](./discussions/_TEMPLATE.md) 提供标准化结构。

**每次对话的记录**：无论"深度分析"还是"深度探讨"，每次结束时在 `discussions/` 目录生成一个简要的会话记录，包含日期、主题、核心结论、产出文件列表、是否产生关键洞察。命名格式：`YYYY-MM-DD-主题.md`。

## 项目结构

```
SelfLab/
├── SGE-Key-Insights.md                    # 关键洞察集（19 条 + FR 双向追溯）
│
├── PRD.md                                 # 产品需求文档（FR-1~10 + 验收标准）
├── ROADMAP.md                             # 路线图（Phase 0~3 + M1.1~M3.3）
├── ARCH.md                                # 架构文档（4 层架构 + 三视图对照）
├── DESIGN.md                              # 详细设计文档（算法、数据结构、参数）
├── DEVELOP.md                             # 开发规范（技术栈 SSOT）
├── CHANGELOG.md                           # 变更日志（含版本号约定、提交索引）
│
├── research/                              # 研究文档
│   ├── sge-core/                          # SGE 核心研究
│   │   ├── Artificial-Self-Research-v0.1.md     # 研究纲领 v0.1
│   │   ├── Artificial-Self-Research-v0.2.md     # 研究纲领 v0.2（双系统+预测加工）
│   │   ├── SGE-Core-Insight-Is-vs-Ought.md      # 核心领悟：实然与应然的分野
│   │   ├── SGE-Corrected-Judgment-and-Application-Logic.md  # 修正判断与应用逻辑
│   │   ├── SGE_AI_Value_Emergence_Authenticity.md           # 金观涛真实性哲学与AI价值涌现
│   │   ├── SGE-Authenticity-vs-Simulation-Operationalization.md  # 真我 vs 精致模拟可操作化（P5-1）
│   │   ├── SGE-Phenomenology-Deep-Dive.md           # 现象学深度对接（P5-6）
│   │   ├── SGE-Cross-Cultural-Self-Views.md         # 多文化自我观（P5-7）
│   │   └── SGE-Consciousness-Theory-Mapping.md      # 意识理论对接（P5-8）
│   │
│   ├── sge-feasibility/                   # SGE 可行性评估
│   │   ├── SGE-Engineering-Feasibility-Analysis.md            # 工程实现可行性
│   │   ├── SGE-Existing-Attempts-and-Gap-Analysis.md          # 现有尝试与空白分析
│   │   ├── SGE-Technology-Stack-Overview.md                   # 技术栈全景（SSOT: DEVELOP.md）
│   │   ├── SGE-Experiment-Protocol.md                         # 实验运行与评估手册
│   │   ├── SGE-Memory-Layer-Design.md                         # 记忆层正式设计文档
│   │   ├── SGE-Failure-Mode-Deep-Analysis.md                  # 失败模式深度分析（P5-2）
│   │   ├── SGE-Alternative-Architectures.md                   # 替代架构探索（P5-3）
│   │   ├── SGE-M11-Experiment-Design.md                       # M1.1 实验详细设计（P5-5）
│   │   └── Analysis-Cognitive-State-A-to-B-Relevance-and-Feasibility.md  # A→B 关联性分析
│   │
│   ├── sge-learning/                      # 借鉴与学习
│   │   ├── SGE-Learning-from-AiBeing.md              # AiBeing 引擎借鉴分析
│   │   ├── SGE-Learning-from-Authenticity-Philosophy.md  # 金观涛真实性哲学借鉴
│   │   └── SGE-Feasibility-Impact-on-AtoB.md          # SGE 对 A→B 项目的影响
│   │
│   └── cognitive-architecture/            # 认知架构调研（A→B 子项目）
│       ├── Cognitive-Architectures-Overview.md        # 经典认知架构综述
│       ├── Cognitive-State-A-to-B-Research.md         # A→B 认知状态调研（完整版）
│       ├── Cognitive-State-A-to-B-Distilled.md        # A→B 调研（精要版）
│       ├── Shared-Cognitive-Science-Toolbox.md        # 认知科学底层工具箱
│       └── SGE-Cognitive-Tools-Application.md         # 7 个认知工具的具体应用（P5-4）
│
├── references/                            # 参考资料
│   ├── AiBeing-Core-Engine-Reference.md             # AiBeing Genome v10 引擎（16篇合并）
│   ├── Philosophy-of-Authenticity.md                # 金观涛真实性哲学
│   ├── LLM_and_Cognitive_Architecture_Complete_Discussion.md  # LLM与认知架构讨论
│   └── Glossary.md                                  # SGE 核心术语表（含使用规范）
│
├── discussions/                           # 讨论存档
│   ├── _TEMPLATE.md                                 # 标准化讨论文件模板
│   └── YYYY-MM-DD-主题.md                           # 每次对话的会话记录
│
├── prototypes/                            # 架构原型
│   ├── README.md                                    # 目录说明
│   └── sge-architecture-overview.md                 # SGE 4 层架构图（含跨层数据流 v2）
│
└── experiments/                           # 实验代码（Phase 1+，一次性）
    ├── README.md                                    # 实验代码约定与命名
    ├── notebooks/                                   # Jupyter notebooks
    ├── scripts/                                     # ad-hoc 脚本
    ├── analysis/                                    # 数据处理
    └── configs/                                     # 实验配置
```

> **关于 experiments/**：本目录用于 Phase 1+ 的实验代码，遵循 [CLAUDE.md §实验代码约定](./CLAUDE.md)——**一次性、不演进为应用、归档不修改**。Phase 0 阶段此目录为空（仅 README）。

## 关键 SSOT（Single Source of Truth）

| 主题 | SSOT 文档 | 其他文档 |
|------|----------|---------|
| **项目版本号** | [CHANGELOG.md](./CHANGELOG.md) | 各项目级文档头部"项目版本"字段 |
| **Epoch 数字约定** | [PRD §5.1](./PRD.md) | [ROADMAP §里程碑](./ROADMAP.md) 引用 |
| **技术栈选型** | [DEVELOP.md §二](./DEVELOP.md) | [SGE-Technology-Stack-Overview.md](./research/sge-feasibility/SGE-Technology-Stack-Overview.md) 调研 |
| **参数默认值** | [DESIGN.md §八](./DESIGN.md) | [DEVELOP.md §六 配置管理](./DEVELOP.md) 引用 |
| **核心术语定义** | [references/Glossary.md](./references/Glossary.md) | 所有文档引用 |
| **架构图** | [prototypes/sge-architecture-overview.md](./prototypes/sge-architecture-overview.md) | [ARCH.md §1.2](./ARCH.md) 引用 |
| **关键洞察** | [SGE-Key-Insights.md](./SGE-Key-Insights.md) | 各项目级文档交叉引用 |

## 参与者

- Bisen（项目发起人，关注 AI 认知架构与人工自我的研究者）
- AI 协作伙伴（ChatGPT、Gemini、Claude 等）

## 当前状态

**Phase 0（理论奠基）已完成**：
- 研究纲领 v0.2、认知架构调研、工程可行性评估、AiBeing 借鉴分析、金观涛真实性哲学借鉴分析
- 项目级文档（PRD、ROADMAP、ARCH、DESIGN、DEVELOP、CHANGELOG）已建立
- 4 批次文档优化完成（P0~P3）：版本号统一、术语规范、验收标准精细化、技术栈去重、伦理边界细化、Memory Layer 独立化等
- 进一步优化（P4 批次）：模板化、架构图升级、Memory Layer 独立化、洞察-FR 追溯、README 同步

**下一步**：Phase 1 最小验证——Value Layer 原型实验（M1.1，50-100 Epochs，单个 AI 婴儿）。
- 实验代码将存放在 `experiments/` 目录（一次性，不演进为应用）
- 实验运行参见 [research/sge-feasibility/SGE-Experiment-Protocol.md](./research/sge-feasibility/SGE-Experiment-Protocol.md)
- 实验结果将记录在 `discussions/` 或 `research/sge-feasibility/` 下的报告中
