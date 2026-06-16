# SGE（Self Genesis Engine）变更日志

本文件记录项目的重要变更：文档版本、研究进展、架构调整、关键决策。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

## 版本号约定

- **主版本（major）**：0（项目仍处研究阶段）
- **次版本（minor）**：0.x —— x 每次内容增删改递增
- **修订号（patch）**：0.x.y —— y 用于小修正（错别字、链接失效等）
- **批次标签**：P0（必须修正）→ P1（建议修正）→ P2（可后续）→ P3（优化）
- **commit 引用**：每次 [版本] 标注对应的 commit hash（如果存在），便于追溯

## 提交索引

| 版本 | 日期 | commit hash | 主要内容 |
|------|------|-------------|---------|
| 0.5.0 | 2026-06-15 | `8c12195` | P1 批次修正 |
| 0.4.0 | 2026-06-15 | `1b98b4f` | P0 批次修正 |
| 0.3.0 | 2026-06-15 | `c509c95` (主) + 多次 | 新增项目级文档、哲学立场明确 |
| 0.2.0 | 2026-06-14 | 多 commit 合并 | 新增参考与借鉴分析 |
| 0.1.0 | 2026-06-12 ~ 13 | 多 commit 合并 | 初始研究纲领与洞察集 |
| 0.0.1 | 2026-06-11 | `9168083` (Initial) | 项目初始化 |

---

## [1.1.0] - 2026-06-15 (P5-9 怀特海过程哲学)

### 新增

- `research/sge-core/SGE-Whitehead-Process-Philosophy.md` — 怀特海过程哲学对 SGE 的指导（动在、合生、创造性、主观目的）
- SGE-Key-Insights 新增洞察 24：怀特海"动在"为 SGE 提供精确认知过程词汇

### 哲学深化

- 西方过程哲学为 SGE 佛教"过程性自我"（[洞察 22](../SGE-Key-Insights.md)）提供**西方版本的双向支撑**
- SGE 对怀特海的有选择接受：接受工具价值（动在、合生、创造性、主观目的），拒绝形而上学预设（神、永恒客体先验、泛经验主义）
- SGE 哲学综合进一步明确：涌现主义 + 过程哲学 + 真实性 + 现象学 + 多文化 + 意识理论的**混合立场**

### 同步更新

- README.md 目录结构增加 SGE-Whitehead-Process-Philosophy.md
- CHANGELOG 新增 [1.1.0]

---

## [1.2.0] - 2026-06-15 (P6 金观涛系统哲学 + 工程化致敬)

### 新增

- `research/sge-core/SGE-Jin-Guantao-System-Philosophy.md` — 金观涛系统哲学的深度探讨（稳态、反馈系统、真实性哲学、他的 AI 观）
- SGE-Key-Insights 新增洞察 25：SGE 接受金观涛的工具（稳态/反馈/真实性/暗知识/拱桥），拒绝他的结论（主体先验论/AI 不可能）

### 重大哲学立场修订

- **从"全面反对金观涛"** → **"接受工具拒绝结论"**（工程化致敬）
- [洞察 18 哲学立场](../SGE-Key-Insights.md) 修订：明确这一新立场
- [PRD §1.2 哲学依据](../PRD.md) 扩展：从单一发育生物学 → 综合哲学资源（金观涛 + 怀特海 + 涌现主义 + 现象学 + 多文化 + 意识理论）
- [ARCH §1.1 设计哲学](../ARCH.md) 增加"金观涛的稳态/反馈框架"和"怀特海的动在/合生框架"段落

### 哲学综合最终明确

SGE 哲学 = **金观涛（稳态/反馈/真实性/暗知识/拱桥）+ 怀特海（动在/合生/创造性/主观目的）+ 涌现主义/功能主义 + 现象学 + 多文化（佛教无我/间 Ma/Ubuntu）+ 意识理论（IIT/GWT/HOT/PP）**

**SGE 的独特立场**：接受所有哲学资源的**工具价值**，拒绝任何单一哲学的**形而上学预设**。这是 SGE 对金观涛的"工程化致敬"——把他的哲学**工程化**。

### 同步更新

- README.md 目录结构增加 SGE-Jin-Guantao-System-Philosophy.md
- CHANGELOG 新增 [1.2.0]

---

## [1.2.1] - 2026-06-15 (P7 修正金观涛文档中的知识幻觉)

### 修正背景

经过 11 次 WebFetch 尝试核查金观涛具体哲学内容（如"真实性哲学"的具体表述、"3 个层次"等），**无法独立验证**这些是金观涛的原话或明确主张。

**核查结果**：

- ✓ **已验证**：金观涛生平、超稳定结构理论、与刘青峰合著
- △ **用户提供**（Bisen 确认）：真实性哲学打通实然与应然鸿沟、对 AI 不认同主体意识
- ? **SGE 自身建构**（不是金观涛原话）："3 个层次"、"愿意质疑自己"、"3 前提+1 结论"形式化等

### 修正内容

- **SGE-Jin-Guantao-System-Philosophy.md** 加"验证状态声明"于文档顶部
- **§1.3 诚实声明** 扩展为 9 行验证状态表
- **§2.1.1 概念溯源** 加"可能理论源头"标注（维纳/艾什比/贝塔朗菲为推断）
- **§2.2.2 反馈系统视角** 重写为"SGE 建构"，不再声称"金观涛革命性主张"
- **§2.3.3 金观涛的解法：真实性** 加"SGE 对用户信息的解读"标注
- **§2.3.4 真实性的 3 个层次** 明确标注为"SGE 建构"
- **§2.4 金观涛的 AI 观** 重命名为"基于用户信息的工程化建构"
- **§5.4 操作化"真实性"** 明确标注为"SGE 自身建构"
- **SGE-Key-Insights 洞察 25** 加"2026-06-15 验证状态修订"声明

### 核心原则

- SGE 的"借鉴"哲学资源时，**必须区分**：✓ 已验证 / △ 用户提供 / ? SGE 建构
- 接受用户对哲学家的**信息**（Bisen 熟悉金观涛）
- 但**不**把"用户表述"等同于"哲学家原话"
- 工程化建构**明确标注**为"SGE 自身"

### 反思

- SGE 的反合理化机制**应该约束 AI 协作伙伴本身**——不仅是 AI 婴儿
- 哲学资源借鉴的"知识幻觉"风险**确实存在**——本次修正就是例证
- 后续任何哲学借鉴都应**先核查、后引用**

---

## [1.0.0] - 2026-06-15 (P5 批次：研究深化)

### 研究深化（P5 批次：8 个新研究文档 + 4 条新洞察）

> **背景**：P0-P4 主要在项目级文档（PRD/ARCH/DESIGN/ROADMAP/DEVELOP）层面工作。P5 转向**研究文档深化**——填补 SGE 哲学和工程层面的开放问题。

#### 新增 8 个研究文档

| 文档 | 位置 | 主题 |
|------|------|------|
| [SGE-Authenticity-vs-Simulation-Operationalization.md](../research/sge-core/SGE-Authenticity-vs-Simulation-Operationalization.md) | research/sge-core/ | **真我 vs 精致模拟可操作化**（P5-1）—— 5 维评分卡：反思深度、反事实鲁棒性、预测效度、因果深度、新颖性生成 |
| [SGE-Failure-Mode-Deep-Analysis.md](../research/sge-feasibility/SGE-Failure-Mode-Deep-Analysis.md) | research/sge-feasibility/ | **失败模式深度分析**（P5-2）—— 15 种失败模式 + 5 层应对策略 |
| [SGE-Alternative-Architectures.md](../research/sge-feasibility/SGE-Alternative-Architectures.md) | research/sge-feasibility/ | **替代架构探索**（P5-3）—— 5 种备选：神经场、预测加工、能量模型、贝叶斯、元学习 |
| [SGE-Cognitive-Tools-Application.md](../research/cognitive-architecture/SGE-Cognitive-Tools-Application.md) | research/cognitive-architecture/ | **7 个认知工具的具体应用**（P5-4）—— 强化已用 3 个 + 应用未用 4 个 |
| [SGE-M11-Experiment-Design.md](../research/sge-feasibility/SGE-M11-Experiment-Design.md) | research/sge-feasibility/ | **M1.1 实验详细设计**（P5-5）—— 50-100 Epochs 具体设计 |
| [SGE-Phenomenology-Deep-Dive.md](../research/sge-core/SGE-Phenomenology-Deep-Dive.md) | research/sge-core/ | **现象学深度对接**（P5-6）—— 胡塞尔/海德格尔/梅洛-庞蒂/萨特与 SGE 映射 |
| [SGE-Cross-Cultural-Self-Views.md](../research/sge-core/SGE-Cross-Cultural-Self-Views.md) | research/sge-core/ | **多文化自我观**（P5-7）—— 印度/日本/伊斯兰/非洲传统对 SGE 的启示 |
| [SGE-Consciousness-Theory-Mapping.md](../research/sge-core/SGE-Consciousness-Theory-Mapping.md) | research/sge-core/ | **意识理论对接**（P5-8）—— IIT/GWT/HOT/PP/Panpsychism 与 SGE 对应 |

#### SGE-Key-Insights 新增 4 条洞察（19 → 23）

- **洞察 20**：5 维评分卡区分"真我"与"精致模拟"（来自 P5-1）
- **洞察 21**：现象学与 SGE 架构的 4 大映射（来自 P5-6）
- **洞察 22**：多文化自我观对 SGE 的启示（来自 P5-7）
- **洞察 23**：5 个意识理论与 SGE 的对应（来自 P5-8）

**关键哲学深化**：
- 佛教"无我"与 SGE 涌现自我"结构相似"——两者都认为自我是过程性的
- 海德格尔"本真性 vs 常人"直接对应 SGE "反训练同化"机制
- HOT 给 SGE M3.2 元认知层提供理论支撑
- Panpsychism 是 SGE 自觉的哲学边界

#### 同步更新

- CLAUDE.md 目录约定更新
- README.md 目录结构更新
- SGE-Key-Insights.md FR 索引表增加 4 行

---

## [0.9.0] - 2026-06-15 (Phase 0→1 边界澄清)

### 重大修订：项目性质阶段化

**修订背景**：原 CLAUDE.md/README.md 声明"本项目不是代码实现项目"，但 PRD/ROADMAP/Experiment-Protocol 描述的 Phase 1 验证明显需要代码。两个声明存在矛盾。

**修订方案**：将"无代码"声明**阶段化**——

| 阶段 | 代码 | 文档 |
|------|------|------|
| Phase 0 | ❌ 无 | 全部项目级文档 |
| Phase 1+ | ✅ 一次性实验代码 | 实验报告 + 修订 |

**关键区分**：
- 实验代码 ≠ 应用代码（前者生成研究数据，后者是可复用系统）
- 实验代码一次性，归档不修改
- 未来可复用代码应**新建仓库**（如 SGE-Prototype），不在 SelfLab 重构

### 修订内容

- **CLAUDE.md §项目性质** 改为阶段化表格 + 新增"§实验代码约定"章节
- **CLAUDE.md 目录约定** 增加 `experiments/` 条目
- **README.md** 新增"项目阶段与产物形态"表格 + 修订"当前状态"
- **README.md 目录结构** 增加 `experiments/` 子目录
- **新增 `experiments/README.md`** —— 实验代码的操作细节（命名、子目录、与文档同步）
- **新增 `experiments/` 子目录** —— notebooks/, scripts/, analysis/, configs/

### 不变内容

- SelfLab 主仓库仍是**研究文档为主**——这一点不变
- "可复用代码应在独立仓库"——避免在 SelfLab 内做工程化
- DEVELOP.md §四 目录结构（sge/ 包）的"前瞻性"标注——保留

---

## [0.8.0] - 2026-06-15 (P4 批次)

### 进一步优化（P4 批次：可读性 + 可追溯性）

#### discussions 模板（P4-1）
- 新增 `discussions/_TEMPLATE.md`：标准化讨论文件结构（必填/可选章节、命名规范、判断标准）

#### ARCH 架构图跨层数据流升级（P4-2）
- `prototypes/sge-architecture-overview.md` 新增 v2 跨层数据流版本：显式标注 3 类跨层数据流（value_delta、reward、frustration）
- 保留 v1 原版作为"何时使用 v1 vs v2"对照

#### PRD §6.3 失败处理（P4-3）
- PRD §6.3 扩展为 4 个子节：通过条件、失败处理路径（6 种失败模式对应诊断+应对）、哲学层面应对（重新设计 vs 接受金观涛）、决策原则

#### A→B 关系说明（P4-4）
- CLAUDE.md 新增"子项目 A→B 调研"章节：明确 SGE 与 A→B 的目标差异、为什么放在一起、关键文档链接

#### Memory Layer 独立化（P4-5）
- 新增 `research/sge-feasibility/SGE-Memory-Layer-Design.md`：从 discussions 升格为正式设计文档
- 包含设计原则、内容分类、推荐架构、方案对比、关键决策汇总、相关文档映射

#### 洞察-FR 双向追溯（P4-6）
- `SGE-Key-Insights.md` 19 条洞察全部添加"对应 FR"标注
- 文档头部新增 FR 双向追溯索引表（19 行 × 4 列）
- 形成"洞察 → FR"反向追溯链：19 条洞察对应 FR-1~10 的覆盖关系

#### README 同步更新（P4-7）
- README.md 反映 P0~P3 的所有变化：新增 Glossary.md、Experiment-Protocol.md、SGE-Memory-Layer-Design.md、prototypes/ 目录
- 新增"关键 SSOT"表格：7 类信息的 SSOT 文档明确化
- 新增"子项目"表格：SGE vs A→B
- 6 步工作流图与 CLAUDE.md 同步

---

## [0.7.0] - 2026-06-15 (P3 批次)

### 修正（P3 批次：优化性质 + 术语审查）

#### 术语审查（P3-1）
- `references/Glossary.md` 新增"术语使用规范"章节：明确同义术语的使用场景（暗知识/默会知识、价值困境/价值冲突等）；增加中英对照速查表
- ARCH §1.3 表格中"默会知识/暗知识"统一为"暗知识（源自波兰尼默会知识与金观涛暗知识）"
- PRD §4.1 FR-3 添加金观涛"拱桥"哲学对应
- ROADMAP §M1.3 添加"拱桥"机制引用

#### 状态文件 Engine/Self 区分（P3-2）
- ARCH §5.1 状态持久化按 [ARCH §1.4 Self-AI婴儿 1:1 关系] 重新组织为 `state/self/` 和 `state/engine/` 目录
- 增加状态迁移原则（Self 备份 vs Engine 备份 vs 完整备份）

#### Event Generator 容错（P3-3）
- ARCH §6.2 容错表增加 Event Generator 失败处理（重试 → 模板库 → 跳过本 Epoch）
- 增加累积错误率 > 30% 中止实验的全局机制

#### 创作者分身伦理边界（P3-4）
- PRD §5.4 伦理合规扩充为 4 个子节：通用约束 + 6 个下游应用边界 + 创作者分身特殊约束 + 通用拒绝事项
- 创作者分身明确为"高风险"等级，需要书面授权、定期审查、终止条件

#### LifeEvent event_id 规范（P3-5）
- DESIGN §2.1 新增 `event_id` 格式规范：`{baby_id}-e{epoch}-{uuid8}`
- 增加生成函数 `make_event_id` 伪代码

#### BABY_PROFILES 一致性（P3-6）
- ROADMAP §M1.2 增加 AI 婴儿组定义表（encouraged/challenged/uncertain）
- 明确"challenged"对应"挑战/失败"，刻意不用"failed"以体现 SGE "经历 + 解释 = 人格"立场

#### discussions 自我判断修正（P3-7）
- `discussions/2026-06-15-memory-layer-design.md` 第 62 行自评"否"修正为"是"
- 补充本讨论产生的 3 个新概念：记忆双视角、混合方案判断标准、不引入外部框架
- 讨论结论的 PRD/ARCH 落地情况已被对应文档更新

#### CLAUDE.md 用户角色说明（P3-8）
- CLAUDE.md 新增"用户与协作"章节：项目发起人 Bisen 的背景、专业领域、协作偏好、AI 协作伙伴的预期角色
- 明确协作者背景假设（金观涛哲学、ACT-R/SOAR/LIDA 等可默认熟悉）

---

## [0.6.0] - 2026-06-15 (P2 批次)

### 新增
- `references/Glossary.md` — SGE 核心术语表（哲学、认知科学、SGE 架构、工程机制 4 大类）
- `research/sge-feasibility/SGE-Experiment-Protocol.md` — SGE 实验运行与评估手册（环境、步骤、可复现性、指标计算、判定流程、异常处理）

### 修正（P2 批次：可后续修正的问题）

#### ROADMAP 引用过期（P2-1）
- ROADMAP §Phase 0 "17 条核心洞察" 修正为 19 条，并加链接

#### 术语统一性（P2-4）
- CLAUDE.md 目录约定增加 Glossary.md 引用
- PRD/ARCH/DESIGN 头部增加"术语约定"标注

#### 验收标准精细化（P2-5）
- PRD §6.1 必达指标：每条标准增加"度量定义"列（涌现幅度、收敛度、方向一致性、人格差异度、行为变化率、反思深度）
- PRD §6.2 期望指标：每条标准增加"度量定义"列
- 明确"标准差 < 0.1"、"差异度 > 阈值"等模糊表述的具体维度和计算方法
- 增加"为什么不预设所有阈值"说明（M1.1 完成后基于基线校准）

#### 技术栈去重（P2-6）
- `research/sge-feasibility/SGE-Technology-Stack-Overview.md` 头部加"SSOT"声明：本文件是调研全景，权威定义在 DEVELOP.md
- ARCH §4.1 改为简短引用，详细技术栈定义指向 DEVELOP.md

#### DEVELOP 内部修正（P2-7）
- DEVELOP §2.2 模型版本号改用 litellm 模型别名（`claude-3-haiku-latest`），避免快照版本过期
- DEVELOP §四 目录结构加"前瞻性章节"标注
- DEVELOP §六 配置管理加"SSOT"声明：DESIGN.md §八 是参数权威源

#### CHANGELOG 格式优化（P2-8）
- CHANGELOG.md 头部增加"版本号约定"和"提交索引"两节

---

## [0.5.0] - 2026-06-15 (commit: 8c12195)

### 修正（P1 批次：建议修正的问题）

#### Epoch 数字统一（P1-1）
- PRD §5.1 新增"Epoch 数字约定"表（SSOT）：明确各阶段（Phase 1 M1.1/M1.2/M1.3、Phase 2 M2.2、哲学类比）对应的 Epoch 数
- PRD §5.1 性能要求改写：原"1000 Epochs 总成本"明确为"3 AI 婴儿 × 1000 Epochs（M2.2 完整实验）"
- PRD §6.1/6.2/6.3 验收标准细化：每条标准标注对应里程碑，6.3 判定标准扩展为 4 条件
- ROADMAP §里程碑 增加对 PRD §5.1 的引用

#### 元价值 vs 具体价值术语对照（P1-2）
- PRD §4.1 FR-4 新增"元价值 vs 具体价值观"对照表：明确 2 个元价值（真实 truth-seeking、自由 freedom）和 6 个具体价值观（安全、创造、联结、自主 autonomy、正义、同理）
- 关键区分：自由（freedom，元价值）≠ 自主（autonomy，具体价值观）
- ARCH §3.1 事件类型表增加"元价值/具体价值观"列：明确"风险"事件是唯一涉及元价值的事件类型

#### 记忆层命名协调（P1-3）
- PRD §4.1 FR-2 增加"认知科学三层 vs 工程三层映射"说明：工作记忆（进程内存）、情节记忆（Layer 2 事件记忆层）、语义记忆（Layer 1 引擎状态层）
- 引用 discussions/2026-06-15-memory-layer-design.md 作为工程实现的权威源

#### PRD-ROADMAP 衔接 + FR 编号双向引用（P1-4 + P1-5）
- PRD §4.3 新增"FR 与里程碑的映射"表：FR-1~10 各自对应的里程碑
- ROADMAP M1.1/M1.2/M1.3/M2.1/M2.2/M2.3/M3.1/M3.2/M3.3 各自标注"涉及 FR"
- ARCH §3.0 新增（Memory Layer）+ §3.1~3.5 各自添加"对应 FR"标注
- DESIGN §2.1/3.1/4.1/4.3/5.1/6.1 各自添加"对应 FR"标注
- 解决 PRD 编号在 ARCH/DESIGN/DEVELOP 无引用的"编号真空"

#### prototypes/ 初始化（P1-6）
- 新增 `prototypes/README.md`：描述目录用途、当前原型文件列表、命名约定
- 新增 `prototypes/sge-architecture-overview.md`：将 ARCH §1.2 的 ASCII 架构图迁移至此，附 4 层职责一览、关键设计取舍
- ARCH §1.2 改为引用 prototypes/ 中的完整图表

#### CLAUDE.md 流程图补全（P1-7）
- CLAUDE.md 核心工作流流程图更新：补充"会话记录 → discussions/"作为独立步骤（第 4 步）
- 加入"深度分析"分支的标注（第 0 步）

---

## [0.4.0] - 2026-06-15

### 修正（P0 批次：必须修正的问题）

#### 版本号体系统一
- 明确 `CHANGELOG.md` 为项目版本号的权威源
- PRD/ROADMAP/ARCH/DESIGN/DEVELOP 顶部版本号从"版本：v0.1"改为"文档版本：v0.1 / 项目版本：[0.3.0]"，并标注权威源链接
- ROADMAP M3.1/M3.2/M3.3 移除与 CHANGELOG 冲突的"SGE v0.3/v0.4/v1.0"标签

#### ARCH 双图冲突解决
- ARCH 新增 §2.3 "架构三视图对照"：明确 1.2（概念/逻辑视图）、2.1（数据流视图）、2.2（流程视图）三者的视角差异
- 在 1.2 架构全景图和 2.1/2.2 节点处添加视图说明引用

#### Hebbian Learning 与 Value Layer 关系明确
- ARCH 新增 §1.3 "核心学习机制：Hebbian Learning 与 Value Layer 的关系"：明确两者是**平行且互补**的学习机制，作用于不同状态空间（亚符号 vs 符号）、承载不同知识类型（暗知识 vs 显性知识）
- DESIGN 新增 §4.4 "Hebbian Learning 与 Value Layer 的对照"：工程实现对照（数据结构、存储位置、计算复杂度、调试注意事项）
- PRD §4.1 FR-4 修正：将"使用 Hebbian Learning 积累暗知识"改为"与 Hebbian Learning 形成'显性-暗知识'双轨"，避免读为父子关系
- 建立"金观涛暗知识 / 显性知识 / 拱桥"与"SGE Hebbian / Value Layer / Reflection"的三方对应

#### Self 与 AI 婴儿关系明确
- ARCH 新增 §1.4 "核心概念对应：Self 与 AI 婴儿"：明确**1 个 AI 婴儿 = 1 个 Self**
- ROADMAP M3.3 标题与描述修正：从"Multi-Self Interaction"改为"Multi-AI Interaction"，澄清"多 Self"= "多 AI 婴儿"，而非"1 个 AI 婴儿容纳多 Self"

---

## [0.3.0] - 2026-06-15

### 新增
- `PRD.md` — 产品需求文档，定义 SGE 的愿景、功能需求、成功标准
- `ROADMAP.md` — 路线图，四阶段研究与开发路径
- `ARCH.md` — 架构文档，系统架构、模块设计、技术选型
- `DESIGN.md` — 详细设计文档，各模块算法、数据结构、参数配置
- `DEVELOP.md` — 开发规范，技术栈、代码规范、测试策略
- `CHANGELOG.md` — 变更日志（本文件）

### 变更
- 项目从纯研究阶段进入"研究 + 规划"阶段
- 研究文档重组为 4 个子目录（sge-core / sge-feasibility / sge-learning / cognitive-architecture）
- README.md 和 CLAUDE.md 同步更新目录结构

### 哲学立场明确
- 明确 SGE 的哲学立场：涌现主义/功能主义，而非金观涛的先验论
- 金观涛认为"主体不是客观对象，而是一切对象化的前提"——主体不能被研究和构建
- SGE 认为主体可以从足够复杂的功能系统中涌现——主体可以被实验验证
- 这一分野是 SGE 实验的哲学基础：实验本质上在检验这两种立场哪一个更接近真实
- 新增洞察 18（SGE-Key-Insights.md）
- 新增洞察 19：发育生物学作为涌现主义的经验依据
- 更新 SGE-Learning-from-Authenticity-Philosophy.md 和 SGE_AI_Value_Emergence_Authenticity.md

### 项目级文档修正（受洞察 19 影响）
- PRD.md — 核心假设加入发育生物学的哲学依据
- ARCH.md — 设计哲学加入"受精卵→婴儿"的架构类比表
- DESIGN.md — 设计原则新增第 6 条"发育映射原则"

### CLAUDE.md 工作流策略
- 新增"核心工作流：探讨 → 洞察 → 修正"闭环流程
- 第一步：讨论存档到 `discussions/YYYY-MM-DD-主题.md`
- 第二步：判断是否产生关键洞察，是则添加到 SGE-Key-Insights.md
- 第三步：新洞察产生后检查项目级文档是否需要修正
- 第四步：自动同步推送

### README.md 使用约定
- 新增关键词触发机制："深度分析"/"深度研究" → 存到 research/；"深度探讨" → 走完整闭环
- 新增会话记录要求：每次对话结束在 discussions/ 生成简要记录

### 新增
- `research/sge-feasibility/SGE-Technology-Stack-Overview.md` — SGE 技术栈全景（AiBeing 复用、LLM 选型、记忆框架、反思技术、自研部分）

---

## [0.2.0] - 2026-06-14

### 新增
- `references/AiBeing-Core-Engine-Reference.md` — AiBeing Genome v10 引擎完整参考（16篇合并）
- `references/Philosophy-of-Authenticity.md` — 金观涛真实性哲学参考
- `references/LLM_and_Cognitive_Architecture_Complete_Discussion.md` — LLM与认知架构讨论
- `research/sge-core/SGE_AI_Value_Emergence_Authenticity.md` — 金观涛真实性哲学与AI价值涌现
- `research/sge-learning/SGE-Learning-from-AiBeing.md` — AiBeing 引擎对 SGE 的借鉴分析
- `research/sge-learning/SGE-Learning-from-Authenticity-Philosophy.md` — 金观涛真实性哲学借鉴分析
- `research/sge-feasibility/SGE-Existing-Attempts-and-Gap-Analysis.md` — 现有系统空白分析

### 关键发现
- AiBeing 的 8 个机制可直接复用到 SGE（Critic、Time Metabolism、EMA、Hebbian 等）
- 金观涛的元价值理论（真实、自由）可作为 SGE 的初始种子
- 金观涛的"拱桥"理论对应 SGE 的"解释机制"
- 金观涛的"暗知识"概念对应 SGE 的 Hebbian Learning
- 金观涛断言"AI 不可能涌现主体意识"——SGE 的实验本质上在测试这个断言
- SGE 在现有技术生态中是明确空白，没有人在做类似的事

---

## [0.1.0] - 2026-06-12 ~ 2026-06-13

### 新增
- `SGE-Key-Insights.md` — 关键洞察集（17条核心洞察）
- `research/sge-core/Artificial-Self-Research-v0.1.md` — 研究纲领 v0.1
- `research/sge-core/Artificial-Self-Research-v0.2.md` — 研究纲领 v0.2
- `research/sge-core/SGE-Core-Insight-Is-vs-Ought.md` — 核心领悟：实然与应然的分野
- `research/sge-core/SGE-Corrected-Judgment-and-Application-Logic.md` — 修正判断与应用逻辑
- `research/sge-feasibility/SGE-Engineering-Feasibility-Analysis.md` — 工程可行性分析
- `research/sge-feasibility/Analysis-Cognitive-State-A-to-B-Relevance-and-Feasibility.md` — A→B 关联性分析
- `research/cognitive-architecture/` — 4 篇认知架构调研文档
- `research/sge-learning/SGE-Feasibility-Impact-on-AtoB.md` — SGE 对 A→B 的影响
- `README.md` — 项目概览
- `CLAUDE.md` — Claude Code 协作指南

### 关键洞察
- 实然与应然的分野：SGE 让 AI 对应然问题给出基于自身价值判断的回答
- LLM ≠ Self，LLM = Thinking Machine
- 人格来自经历 + 解释机制，而非预设
- 经典认知架构没有解决"自我"问题
- A→B 是增量优化，不是范式突破
- SGE 验证后，所有应用场景都只是"角色配置"
- 9 维认知状态向量（A→B 的核心框架）无文献支持，纯理论构建

### 关键决策
- 项目定位：研究规划与技术探讨，不是代码实现
- 文档策略：深度分析默认存档到 research/ 对应子目录
- 同步策略：每次内容增删改自动 commit + push

---

## [0.0.1] - 2026-06-11

### 新增
- 项目初始化
- `research/Artificial-Self-Research-v0.1.md` — 初版研究纲领（与 ChatGPT 协作）
- `research/Artificial-Self-Research-v0.2.md` — 二版研究纲领（加入 Gemini 的认知架构补充）

### 背景
- Bisen 提出"人工自我"研究方向
- 核心问题：AI 如何形成持续存在的自我（Being），而非仅完成任务（Doing）
- 与 ChatGPT、Gemini 协作完成初始研究纲领
