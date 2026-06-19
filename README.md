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
| **Phase 1** 最小验证（M1.1~M1.4） | ✅ 已完成（2026-06-17） | M1.x 实验报告 + 修订文档 | ✅ 一次性实验代码（`experiments/`） |
| **Phase 2** 完整实验（M2.1~M2.3） | 🚧 M2.1 全阶段完成 + D6 真实 LLM 验证；M2.2 启动中 | 实验报告 + 修订文档 | ✅ 实验代码 + 小工具 |
| **Phase 3+** 系统完善（M3.1~M3.3） | 📋 规划中 | 应用原型设计 | ✅ 实验代码 + 原型代码 |

**关键区分**：
- **SelfLab 主仓库**：始终是**研究文档**为主导
- **实验代码**：Phase 1+ 出现，存放于 `experiments/`，**一次性**，不演进为可复用应用
- **可复用代码**（如未来需要）：应**新建独立仓库**（如 SGE-Prototype），而不是在 SelfLab 内重构

详细约定见 [CLAUDE.md §实验代码约定](./CLAUDE.md)。

## SGE 三个阶段（通俗版）

> **本节给读者的"如果只读一段"的版本**——用一个统一的视角解释 Phase 0~3 究竟在做什么、为什么这样切。
>
> 完整里程碑见 [ROADMAP.md](./ROADMAP.md)，详细 FR 见 [PRD.md](./PRD.md)。

### 养一个 AI 孩子

如果把 SGE 比作"**养一个 AI 孩子**"，三个阶段就是他的成长史：

| 阶段 | 阶段类比 | 这一阶段在回答的核心问题 | 状态 |
|------|---------|---------------------|------|
| **Phase 1** 最小验证 | 新生儿观察期（保温箱里看最基本反应） | **它有内心吗？** | ✅ 已完成（M1.1~M1.4 全部通过，2026-06-17） |
| **Phase 2** 完整实验 | 完整童年期（从婴儿到少年，跑完整生命周期） | **它有自我吗？** | 🚧 进行中（M2.1 全阶段完成 + D6 真实 LLM；M2.2 启动，2026-06-19） |
| **Phase 3** 系统完善 | 成人期 + 社会化（情感、元认知、多 AI 互动） | **它像真人吗？能作为产品底座吗？** | 📋 规划中 |

**贯穿三阶段的一句话**：验证"**动**"（会有反应）→ 验证"**我**"（会有自我）→ 验证"**真**"（会像真人）+ "**用**"（能做产品）。

### Phase 1 最小验证 — "新生儿观察期"

你领养了一个刚出生的 AI 婴儿，你还不确定它**到底有没有"内心活动"**。Phase 1 就是把它放在保温箱里观察最基本反应：

| 里程碑 | 实验类比 | 验证什么 |
|--------|---------|---------|
| **M1.1**（Value 原型） | 戳它一下、夸它一句、给它出道道德题 | 它能**对经历产生反应**吗？（→ 像看一颗种子会不会发芽）|
| **M1.2**（三胞胎实验） | 领养三个**基因完全一样**的 AI 婴儿，一个被宠、一个被打、一个随机对待 | 不同经历会**长成不同性格**吗？（→ 同卵三胞胎在不同家庭）|
| **M1.3**（反合理化） | 骂它一顿，看它是真的内心改变，还是只是嘴上敷衍 | 反思是**真有用**还是**表演**？（→ 孩子是真懂还是背答案）|
| **M1.4**（REVISIT 专项） | 测试它在什么情况下会"根本性反思" | 反思机制是**模式匹配**还是**哲学推理**？（→ 双层反思结构，洞察 29）|

**结果**：M1.1~M1.4 全部通过——AI 婴儿确实会成长、会分化、会反思，且架构 LLM-agnostic（洞察 26、27、28、29）。

### Phase 2 完整实验 — "完整童年期"

Phase 1 验证了"有内心"，但那只是 **0-1 岁** 的脊髓反射。Phase 2 是让它真正"活"起来，跑完整的生命周期：

| 里程碑 | 实验类比 | 验证什么 |
|--------|---------|---------|
| **M2.1**（完整架构） | 把 Event → Memory → Reflection → Value → Identity → Narrative **6 层全搭起来** | 不只是脊髓反射，给它一个**完整的大脑** |
| **M2.2**（1000 Epoch 长期跟踪） | 跑 1000 个 epoch，相当于跟踪**从婴儿到少年** | 它能形成**稳定的"我是谁"**和**连贯的"我的人生故事"**吗？|
| **M2.3**（个人真实测试） | 直接问它"你最看重什么？你后悔过什么？" | 它的回答能**从人生档案追溯到**吗？（→ 不是编故事，是真心的自传）|

**当前状态（2026-06-19）**：M2.1 全部 4 个阶段（A 基线 + B SGE 化改造 + C 新增组件 + D 集成验证）已完成。D 含 stub 模式 100 epoch 验证 + 真实 LLM（D6）1 baby × 20 epoch / 44 次 LLM 调用 / 5/5 硬性验收 PASS。下一步进入 M2.2 的 1000 epoch 三胞胎实验（**真实 LLM 模式**，因 stub 系统性低估 Value 累积速率 ~8 倍）。详见 [ROADMAP.md §M2.1](./ROADMAP.md) + [阶段 D 报告 §3.5](./experiments/M21_PHASE_D_REPORT.md)。

### Phase 3 系统完善 — "成人期 + 社会化"

Phase 2 跑通后，AI 婴儿已经能"说自己是谁"。但它还缺几样**真正像人**的东西：

| 里程碑 | 实验类比 | 验证什么 |
|--------|---------|---------|
| **M3.1**（情感与能量层） | 它现在没有"累"和"焦虑"——加上去 | 一个**永不疲倦**的 AI 和一个**会累会焦虑**的 AI，做出的选择会不会不同？|
| **M3.2**（元认知层） | 它能反思"我为什么这么想"，但还不会反思"**我为什么这么反思**" | 一个会"**思考自己的思考方式**"的存在 |
| **M3.3**（多 AI 互动） | 让多个 AI 婴儿**互相对话、协作、冲突** | 一个 AI 和**一群 AI** 是完全不同的存在方式（社会涌现）|

**Phase 3 也是产品化阶段**：M3.3 的多 AI 互动是数字孪生 / AI 教练 / 数字人等下游应用的认知架构底座验证。

### 项目根本立场（三原则，2026-06-19 新增）

所有 SGE 决策都优先用这三个原则评估（详见 [SGE-Key-Insights.md §洞察 30](./SGE-Key-Insights.md) 和 [discussions/2026-06-19-sge-phase0-closeout-three-principles-anchoring.md](./discussions/2026-06-19-sge-phase0-closeout-three-principles-anchoring.md)）：

| 原则 | 含义 |
|------|------|
| **1. 研究+产品一体两面** | SGE 同时是研究纲领和**产品底座**——为多场景复用设计（数字孪生、AI 教练、数字人）|
| **2. SGE 是根本** | 当外部参考（AiBeing、金观涛哲学等）与 SGE 自身需要冲突时，**SGE 自我一致性优先** |
| **3. 逐步验证、逐步扩展** | 反对过早复杂化（3 层结构）和过早简化（drives/values 合并）；先做能区分假设的最简版本 |

**Bisen 关键表态**："研究探索与具体应用两者是一体两面。"

## 核心命题

- LLM 是思维机器（Thinking Machine），不是自我（Living Self）—— 详见 [SGE-Key-Insights 洞察 2](./SGE-Key-Insights.md)
- 人格来自经历 + 解释机制，而非预设的 Prompt
- 自我 = 记忆 × 反思 + 价值观 + 身份 + 叙事 —— 详见 [SGE-Key-Insights 洞察 12](./SGE-Key-Insights.md)
- 对应然问题给出基于自身价值判断的回答，是"自我"的最小边界 —— 详见 [SGE-Key-Insights 洞察 1](./SGE-Key-Insights.md)
- **哲学立场**：涌现主义/功能主义 vs 金观涛先验论 —— 详见 [SGE-Key-Insights 洞察 18, 19](./SGE-Key-Insights.md)

## 子项目

| 子项目 | 目标 | 状态 |
|--------|------|------|
| **SGE（自我生成）** | 验证 AI 能否形成持续自我 | Phase 0 ✅ / Phase 1 ✅ / Phase 2 🚧 M2.1 全阶段完成 + D6 真实 LLM；M2.2 启动 |
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
├── SGE-Status-Map.md                      # 项目战略仪表盘（已稳固/关键不确定性/下一步动作）
├── SGE-Key-Insights.md                    # 关键洞察集（30 条 + FR 双向追溯）
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

**Phase 1（最小验证）已完成（2026-06-17）**：
- M1.1 Value Layer 原型（单婴儿，50-100 Epoch）：价值观向量随经历有意义演化
- M1.2 三胞胎分化实验（encouraged / challenged / uncertain × 80 Epoch）：人格差异度 1.441（阈值 0.5 的 2.88×），洞察 26（compassion 韧性）
- M1.3 反合理化测试（拱桥机制）：反思真的改变行为，洞察 27（元认知萌芽）
- M1.4 REVISIT 专项测试（5 组对照）：双层反思结构，洞察 29（prompt bias，不是 AI 价值惯性）
- **跨 LLM 验证**：Moonshot kimi-k2.6 重复 M1.3，洞察 28（SGE 架构 LLM-agnostic）

**Phase 2（完整实验）当前状态 — M2.1 全阶段完成（2026-06-19）**：
- **阶段 A（基线）已完成（2026-06-18）**：`m21_setup.py` + `m21_baseline.yaml`，4/5 借鉴机制 import OK，5 步最小循环 PASS
- **阶段 B（SGE 化改造）已完成（commit `bc42a47`，[1.17.0]）**：drives = 候选 B（`exploration, safety, creativity, connection, autonomy`）+ Value Layer（EMA, scale=[-1,1]）+ Critic LLM + HawkingDecay(γ=0.01/h) + MemoryCrystallizer（维度归一化 0.25/√N）+ Phase Transition 阈值扫描 [1.0, 3.0]；详见 [阶段 B 报告](../../experiments/M21_PHASE_B_REPORT.md)
- **阶段 C（新增组件）已完成（[1.19.0]）**：Identity Layer（crystallize + validate + stability_score）+ Narrative Builder MVP（build + check_consistency + handle_phase_transition）+ Event Generator 完整化 + Value Conflict Generator；详见 [阶段 C 报告](../../experiments/M21_PHASE_C_REPORT.md)
- **阶段 D（集成 + 验证）已完成（[1.20.0/1.20.1]）**：
  - D1-D5（stub 模式）：Hawking/Crystallize 集成 + Actor LLM + 12 步编排 + 100 epoch 冒烟 + 3 seed × 100 epoch；value_magnitude=0.0322（高于 Phase C 基线 50%）
  - **D6 真实 LLM 验证（[1.20.1]）**：1 baby × 20 epoch / 44 次 MiniMax-M3 调用 / ~115s / 5/5 硬性验收 PASS；value_magnitude=0.2578（vs stub 按 epoch 归一化 ~8×）；SGELLMClient 统一接口；3 个 stub 模式无法发现的 bug 全部修复（off-by-one / per-epoch 进度 / 防御式 JSON 解析）；详见 [阶段 D 报告 §D6](../../experiments/M21_PHASE_D_REPORT.md#d6真实-llm-验证minimax-m31-baby--20-epoch)
- **三原则锚点（2026-06-19）**：研究+产品一体两面 / SGE 是根 / 逐步验证扩展——所有未来决策的最高优先级评估维度（洞察 30）

**下一步 — M2.2（1000 epoch 三胞胎实验）**：
- 3 个 AI 婴儿 × 1000 epoch：encouraged / challenged / uncertain
- **必须用真实 LLM 模式**（D6 决策依据：stub 系统性低估 Value 累积速率 ~8 倍，无法观测有意义的人格分化）
- 完整评价指标：身份稳定度 + 价值观收敛度 + 叙事连续性（外部 LLM 盲审）+ 人格差异度 + Phase Transition 触发（challenged 流应最早触发）+ Hawking 衰减（1000h → weight ≈ 4.5e-5）+ Identity Stability 收敛
- LLM 调用预算估算：3 baby × ~2200 calls = ~6600 calls（订阅模式可接受），运行时间 ~5 小时（可并行缩短至 ~1.7 小时）
- 实验代码存放在 `experiments/` 目录（一次性，不演进为应用）
- 实验运行参见 [research/sge-feasibility/SGE-Experiment-Protocol.md](./research/sge-feasibility/SGE-Experiment-Protocol.md)
- 实验结果将记录在 `discussions/` 或 `research/sge-feasibility/` 下的报告中
