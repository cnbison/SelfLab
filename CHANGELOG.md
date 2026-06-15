# SGE（Self Genesis Engine）变更日志

本文件记录项目的重要变更：文档版本、研究进展、架构调整、关键决策。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

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
