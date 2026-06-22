# 30 - A→B 学习状态迁移整合

> **状态**：📋 探索中（占位文件，Phase 3.1 实施期间可同步填充）
> **关联**：[README.md §5 个研究维度](../../README.md)、[01-applications.md §应用 2](../../00-overview/01-applications.md)
> **背景**：[research/cognitive-architecture/Cognitive-State-A-to-B-Research.md](../../../cognitive-architecture/Cognitive-State-A-to-B-Research.md) — A→B 项目核心文档

---

## 这个目录要做什么

A→B 项目（学习状态迁移）和 SGE（人格引擎）虽然目标不同，但有**强协同**：
- A→B：估计学生的认知状态（9D 向量），设计从 A 状态到 B 状态的迁移路径
- SGE：让学生数字孪生 / AI 教练"有持续自我"，能经历 1000 次对话成长
- **整合**：AI 教练用 SGE 的人格 + A→B 的状态估计，给学生个性化教学

## A→B 项目的核心概念

```
认知状态向量（9D）：
  - knowledge（知识掌握）
  - skill（技能熟练度）
  - comprehension（理解深度）
  - application（应用能力）
  - analysis（分析能力）
  - synthesis（综合能力）
  - evaluation（评估能力）
  - metacognition（元认知）
  - motivation（动机）

迁移路径 A→B：
  - A = 当前状态
  - B = 目标状态（教学目标）
  - 设计中间步骤（梯度难度 + 个性化）
```

## 与 SGE 的整合点

| A→B 概念 | SGE 对应 | 整合方式 |
|---------|---------|---------|
| 9D cognitive state | ValueLayer (6D) + DriveMetabolism (5D) | A→B state 可映射到 SGE value/drive |
| A→B 迁移路径 | Actor LLM 输出 | AI 教练设计转移步骤，Actor 输出建议 |
| 目标状态 B | Identity Layer | "学生应该成为什么样" |
| 元认知 | Identity crystallization | 学生意识到自己的学习状态 |

## 文件结构（待填充）

```
30-atoB/
├── README.md (本文件)
├── 01-state-mapping.md            # A→B 9D → SGE value/drive 映射
├── 02-transfer-design.md          # 从 A 状态设计到 B 状态的路径
├── 03-coach-integration.md        # AI 教练如何使用 A→B 状态
├── 04-atoB-sge-sync.md            # A→B 状态变化如何触发 SGE 事件
└── 05-evaluation-metrics.md       # 评估 A→B 迁移是否成功
```

## 关键问题（待研究）

1. **9D cognitive state 如何映射到 SGE 的 6D value + 5D drive？**
   - 候选映射：knowledge → safety, skill → creativity, motivation → connection
   - 需要实验验证

2. **A→B 状态变化如何注入 SGE？**
   - 作为 App 层 event（"math_score_increase"）
   - 还是作为 SubjectMasteryState 更新？
   - 还是作为 critic_context 注入？

3. **AI 教练如何用 A→B 设计转移？**
   - 知道学生当前 A → 推荐下一步 → B 渐进接近
   - 与 SGE Identity 配合：身份"我是数学不好的学生" vs "我正在变好"

4. **如何评价转移是否成功？**
   - 知识维度是否提升？
   - 学生主观感受（AI 教练的 frustration 是否下降）？
   - Identity 是否更新？

## 与现有 A→B 文档的关系

[research/cognitive-architecture/Cognitive-State-A-to-B-Research.md](../../../cognitive-architecture/Cognitive-State-A-to-B-Research.md) 是 A→B 项目核心文档。本目录（30-atoB/）专注于 **A→B 与 SGE 的整合**——A→B 内部逻辑以现有文档为准。

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-22
