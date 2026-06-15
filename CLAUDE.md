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

## 协作规范

- 文档语言以中文为主，技术术语保留英文
- 研究纲领使用版本号管理（v0.1、v0.2 ...）
- 讨论记录应标注参与者和日期
- 引用外部理论时注明来源

## 自动同步推送策略

每次完成内容或文件的增删改任务后，自动执行 git add、commit 和 push，无需用户手动触发。commit message 应简要概括变更内容。

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
- `references/` — 参考资料（外部论文、引擎文档、哲学文献）
- `discussions/` — 技术讨论与头脑风暴记录
- `prototypes/` — 架构原型设计图与系统描述（非可运行代码）

## 深度分析存档策略

当用户对某个主题进行深度分析时，默认将分析结果保存为 `research/` 对应子目录下的 MD 文件（sge-core / sge-feasibility / sge-learning / cognitive-architecture），而非仅在对话中输出。文件命名应体现主题，格式与现有研究文档保持一致。保存后告知用户文件路径。

## 讨论风格

鼓励批判性思考与深度追问。不回避哲学层面的硬问题（意识、主体性、自我与模拟的边界）。欢迎挑战既有框架，而非仅在框架内做修补。
