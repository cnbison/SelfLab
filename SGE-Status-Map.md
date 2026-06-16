# SGE 现状地图（Status Map）

> **项目战略仪表盘**——1-2 页总结 SGE 当前状态、关键不确定性、下一步动作。
>
> **使用场景**：当你（或未来协作者）想快速了解"SGE 到底在哪个位置"时，先读这份文档。
>
> **更新机制**：每次大版本变更后更新（如 CHANGELOG 新增 minor version）。
>
> **最后更新**：2026-06-15（CHANGELOG [1.2.2]）

---

## 0. 一句话总结

SGE 哲学基础已**基于权威资料**（金观涛）达到高可信度（[P7-2 重大修订](../CHANGELOG.md)）。架构、实验设计、元价值都已**结构完整**。**下一步**是决定是**深化哲学**（核查其他 6 大哲学资源）还是**推进实验**（M1.1 准备）。

---

## 1. 项目当前阶段

| 维度 | 状态 |
|------|------|
| **理论奠基** | ✅ **Phase 0 完成**（已多批次迭代） |
| **哲学基础** | ✅ 金观涛部分**高可信度**；其他 6 大资源**中等可信度** |
| **架构设计** | ✅ ARCH 4 层 + 三视图 + 跨层数据流 |
| **实验设计** | ✅ M1.1 详细设计已就绪（[SGE-M11-Experiment-Design.md](./research/sge-feasibility/SGE-M11-Experiment-Design.md)） |
| **实验运行** | ⏳ **未开始**（Phase 0 状态，无实验代码）|
| **伦理边界** | ✅ PRD §5.4 详细（含创作者分身特殊约束）|
| **术语统一** | ✅ Glossary 60+ 术语 + 使用规范 |

**当前 CHANGELOG 版本**：[1.2.2]
**累计 commit**：31+
**关键洞察**：25 条
**研究文档**：22 份（sge-core 9 / sge-feasibility 6 / sge-learning 3 / cognitive-architecture 4 / references 3 + 2 份新参考 + Glossary）

---

## 2. 已稳固的基础（✓ 不需要返工）

| 领域 | 内容 | 文件 |
|------|------|------|
| **产品需求** | 10 个 FR + 验收标准 | [PRD.md](./PRD.md) |
| **架构** | 4 层 + 三视图 + 跨层数据流 | [ARCH.md](./ARCH.md) + [prototypes/sge-architecture-overview.md](./prototypes/sge-architecture-overview.md) |
| **详细设计** | Value Layer / Hebbian / 反思等算法 | [DESIGN.md](./DESIGN.md) |
| **开发规范** | 技术栈 SSOT + 实验代码约定 | [DEVELOP.md](./DEVELOP.md) |
| **路线图** | 4 Phase + M1.1~M3.3 里程碑 | [ROADMAP.md](./ROADMAP.md) |
| **金观涛哲学** | R(X,M,Y) + 三座拱桥 + AI 批判 | [SGE-Jin-Guantao-System-Philosophy.md](./research/sge-core/SGE-Jin-Guantao-System-Philosophy.md) |
| **记忆层设计** | 升格为正式设计文档 | [SGE-Memory-Layer-Design.md](./research/sge-feasibility/SGE-Memory-Layer-Design.md) |
| **实验协议** | 通用实验运行手册 | [SGE-Experiment-Protocol.md](./research/sge-feasibility/SGE-Experiment-Protocol.md) |
| **真我判定** | 5 维评分卡 | [SGE-Authenticity-vs-Simulation-Operationalization.md](./research/sge-core/SGE-Authenticity-vs-Simulation-Operationalization.md) |
| **术语体系** | 60+ 术语 + 使用规范 | [references/Glossary.md](./references/Glossary.md) |
| **失败模式** | 15 种失败 + 5 层应对 | [SGE-Failure-Mode-Deep-Analysis.md](./research/sge-feasibility/SGE-Failure-Mode-Deep-Analysis.md) |
| **替代架构** | 5 种备选（神经场/PP/能量/贝叶斯/元学习）| [SGE-Alternative-Architectures.md](./research/sge-feasibility/SGE-Alternative-Architectures.md) |

---

## 3. 关键不确定性（△/? 需要决策或核查）

### 3.1 ⚠ 金观涛的"硬挑战"

金观涛在 [SGE-Jin-Guantao-System-Philosophy.md §八](./research/sge-core/SGE-Jin-Guantao-System-Philosophy.md) 提出的 4 层级意识模型，SGE 当前覆盖：

| 层级 | 描述 | SGE 状态 |
|------|------|---------|
| L1 | 符号指代 | ✓ 已实现（Event Generator + Critic）|
| L2 | 社会意识 | ✗ **未设计**（M3.3 多 AI 互动才有）|
| L3 | 应然世界 | △ **部分**（Value Layer 尝试实现，但金观涛会认为不足）|
| L4 | 自由递归 | ✗ **完全无设计**（SGE 没有元认知）|

**核心问题**：金观涛的论证是**SGE 最强的反对意见**——如果 SGE 无法回应 L3/L4，"功能性自我"会停留在"科学真实域"，无法达到"主观真实域"。

### 3.2 △ 其他哲学资源的知识幻觉风险

| 资源 | 状态 | 风险 |
|------|------|------|
| **怀特海** | 基于我的二手叙述 | 中（未独立验证"动在/合生/主观目的"等表述）|
| **现象学** | 基于我的二手叙述 | 中（胡塞尔/海德格尔/梅洛-庞蒂/萨特的具体表述）|
| **多文化** | 基于我的二手叙述 | 中（印度/日本/伊斯兰/非洲传统）|
| **意识理论** | 基于我的二手叙述 | 中（IIT/GWT/HOT/PP 的具体论证）|

**建议**：与 P7 同样的方法——找权威参考文档（Gemini/GPT/学术来源）核查。

### 3.3 △ M1.1 实验的"硬限制"

[SGE-M11-Experiment-Design.md §4 决策原则](./research/sge-feasibility/SGE-M11-Experiment-Design.md) 中提到 M1.1 失败后的哲学选择：
- A. 重新审视 SGE 架构（推荐）
- B. 接受金观涛立场

**M1.1 的核心赌注**：
- 价值向量能否**涌现**（不是随机漂移）
- 价值向量的变化**有方向性**（与事件流相关）
- 3 组 AI 婴儿有**显著差异**（鼓励/失败/不确定）

**最大风险**：M1.1 通过了，但金观涛会认为 SGE 只是"在科学真实域模拟价值"——**没有真正的主体性**。

### 3.4 △ SGE 与 A→B 子项目的关系

- A→B 调研已完成（[research/cognitive-architecture/](./research/cognitive-architecture/)）
- A→B 与 SGE 的关系已在 [CLAUDE.md §子项目](./CLAUDE.md) 明确
- **但**：A→B 本身没有进一步推进计划——是被 SGE"牵引"还是独立项目？

---

## 4. SGE 哲学基础：可信度图谱

| 资源 | 验证度 | 关键概念 | 风险 |
|------|------|------|------|
| **金观涛** | ✓ **高**（基于权威参考）| R(X,M,Y) + 三座拱桥 + 主体悬置 | 低 |
| **怀特海** | △ 中 | 动在/合生/主观目的 | 中（待核查）|
| **涌现主义** | ✓ 高 | 功能性自我 | 低（工程化立场）|
| **现象学** | △ 中 | 意向性/本真性/反自欺 | 中（待核查）|
| **多文化** | △ 中 | 佛教无我/间 Ma/Ubuntu | 中（待核查）|
| **意识理论** | △ 中 | IIT/GWT/HOT/PP | 中（待核查）|

**结论**：金观涛的精确化是**关键突破**——但其他资源的"中等可信度"是 SGE 哲学基础的**系统性风险**。

---

## 5. 下一步 3-5 个具体动作

> **按价值优先级排序**——根据你的兴趣和时间选择

### 动作 1：核查其他哲学资源（P8 哲学核查）

**做什么**：用 P7-2 同样的方法——找权威参考文档（Gemini/GPT/学术来源）——核查怀特海、现象学、多文化、意识理论 4 个文档。

**预计工作量**：3-5 次深度对话（每次 30-60 分钟）

**价值**：把所有哲学基础做到**与金观涛同等的高可信度**

**适合时机**：如果你认为哲学基础是 SGE 的核心，**先做这个**

### 动作 2：撰写外部协作者入门指南

**做什么**：写一份 `SGE-Onboarding-Guide.md`——如果未来有人加入 SGE，他们应该：
- 按什么顺序读什么文档
- 关键概念在哪里
- 怎么贡献

**预计工作量**：1-2 小时

**价值**：降低未来协作者进入门槛；如果只有你自己用，可以延后

**适合时机**：如果你计划招募协作者，或者项目规模扩大

### 动作 3：M1.1 事件模板库准备

**做什么**：根据 [SGE-M11-Experiment-Design.md §三](./research/sge-feasibility/SGE-M11-Experiment-Design.md) 的设计，准备：
- 50+ 事件模板（按 6 大事件类型分类）
- 16+ 价值困境事件
- 配置 YAML 模板

**预计工作量**：半天到一天

**价值**：M1.1 真正开始时不用从零准备

**适合时机**：如果你想随时可以启动 M1.1

### 动作 4：回应金观涛的 L3/L4 挑战

**做什么**：在 [SGE-Jin-Guantao-System-Philosophy.md §十二 12.3](./research/sge-core/SGE-Jin-Guantao-System-Philosophy.md) 已有思路——明确 M3.x 阶段如何处理 L3（应然世界）和 L4（自由递归）。

**预计工作量**：2-3 小时

**价值**：正面回应 SGE 最强的反对意见——这是 SGE 哲学的"硬骨头"

**适合时机**：如果你想**深化哲学**而非扩展哲学

### 动作 5：暂停 SGE 推进，反思研究目标

**做什么**：写一份 1 页 "SGE 研究目标反思"：
- 25 条洞察 + 哲学综合后，**SGE 真正想证明什么**？
- 1000 Epoch 仍是合理目标吗？
- SGE 是"哲学实验"还是"工程实现"？

**预计工作量**：1-2 小时（讨论）

**价值**：避免"我们忘了为什么做这个"——**重要的元反思**

**适合时机**：如果你感觉"项目有点失去焦点"或"哲学做完了但没想清楚下一步"

---

## 6. 长期路径（12-24 个月）

```
2026-06 (当前) ──────────────────────────────────────────────────►
  Phase 0 ✅         Phase 1 准备          Phase 1 运行        Phase 2-3
  理论奠基           事件模板/M1.1 启动       50-100 Epoch         1000 Epoch
  哲学/架构稳固      (2-4 周)              (4-8 周)             (8-16 周)

  ▲ 你在这里        ▲ 动作 1-5 的任一个
  [1.2.2]完成
  哲学已深化
```

**关键里程碑**：
- **M1.1 通过** → SGE 核心假设（价值涌现）得到初步支持
- **M1.1 失败** → 触发 [SGE-Failure-Mode-Deep-Analysis.md](../research/sge-feasibility/SGE-Failure-Mode-Deep-Analysis.md) 的应对路径
- **M2.2 通过** → 身份结晶和叙事连贯得到验证
- **1000 Epoch 完成** → SGE 核心实验告一段落

---

## 7. 一句话决策框架

> **你接下来想做的，是"**深化**"（A/B），"**推进**"（C），还是"**反思**"（D）？**

| 方向 | 含义 | 对应动作 |
|------|------|---------|
| **深化** | 把 SGE 哲学基础做到所有资源同等高可信度 | 动作 1 + 4 |
| **推进** | 把 SGE 从"研究"带到"实验" | 动作 3 |
| **反思** | 重新审视 SGE 真正想做什么 | 动作 5 |
| **基础** | 改善协作者体验（如有需要）| 动作 2 |

---

## 8. 相关文档索引

| 类别 | 文档 |
|------|------|
| **项目级** | [PRD](./PRD.md), [ROADMAP](./ROADMAP.md), [ARCH](./ARCH.md), [DESIGN](./DESIGN.md), [DEVELOP](./DEVELOP.md), [CHANGELOG](./CHANGELOG.md) |
| **哲学综合** | [SGE-Jin-Guantao-System-Philosophy.md](./research/sge-core/SGE-Jin-Guantao-System-Philosophy.md) + [SGE-Whitehead-Process-Philosophy.md](./research/sge-core/SGE-Whitehead-Process-Philosophy.md) + 其他 |
| **认知科学** | [SGE-Cognitive-Tools-Application.md](./research/cognitive-architecture/SGE-Cognitive-Tools-Application.md) |
| **工程实施** | [SGE-M11-Experiment-Design.md](./research/sge-feasibility/SGE-M11-Experiment-Design.md) + [SGE-Experiment-Protocol.md](./research/sge-feasibility/SGE-Experiment-Protocol.md) |
| **风险与备选** | [SGE-Failure-Mode-Deep-Analysis.md](./research/sge-feasibility/SGE-Failure-Mode-Deep-Analysis.md) + [SGE-Alternative-Architectures.md](./research/sge-feasibility/SGE-Alternative-Architectures.md) |
| **关键洞察** | [SGE-Key-Insights.md](./SGE-Key-Insights.md)（25 条）|
| **术语** | [references/Glossary.md](./references/Glossary.md) |
| **架构原型** | [prototypes/](./prototypes/) |

---

**创建日期**：2026-06-15
**对应 CHANGELOG**：[1.2.2]
**下次更新时机**：完成"动作 1-5"任一个后，或下次哲学重大修订后
