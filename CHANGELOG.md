# SGE（Self Genesis Engine）变更日志

本文件记录项目的重要变更：文档版本、研究进展、架构调整、关键决策。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

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
