# 90 - 4 个应用 PoC 设计（具体场景）

> **状态**：📋 设计中（占位文件，Phase 3.3 实施期间填充）
> **关联**：[README.md §4 个应用方向](../../README.md)、[01-applications.md](../../00-overview/01-applications.md)

---

## 4 个具体应用 PoC

每个应用一个详细设计文档：
1. `student-digital-twin.md` — 学生数字孪生 PoC
2. `teaching-ai-coach.md` — 教学 AI 教练 PoC
3. `personal-ai.md` — Personal AI PoC
4. `multi-ai-collaboration.md` — 协作 agent PoC

## 优先级

| 应用 | 优先级 | 工作量 |
|------|--------|--------|
| **学生数字孪生** | **P0**（最先实现）| 2 周 |
| **教学 AI 教练** | **P0** | 2 周 |
| Personal AI | P1 | 1.5 周 |
| 协作 agent | P2 | 1.5 周 |

## PoC 设计通用模板

每个 PoC 文件应包含：

1. **场景描述**（具体使用故事）
2. **数据 schema**（App 层定义）
3. **数据流**（采集 → SGE → 响应 → 持久化）
4. **关键技术点**（哪些 Phase 3 模块被使用）
5. **UI 原型**（chat / 报告 / 可视化）
6. **验收标准**（怎么算 PoC 成功）
7. **风险 + 缓解**

## 文件状态

| 文件 | 状态 |
|------|------|
| README.md（本文件）| ✅ |
| student-digital-twin.md | 📋 占位 |
| teaching-ai-coach.md | 📋 占位 |
| personal-ai.md | 📋 占位 |
| multi-ai-collaboration.md | 📋 占位 |

## 依赖关系

```
学生数字孪生 PoC
  ├─ 依赖: persistence + session + context_injection (Phase 3.1)
  ├─ 依赖: SubjectMasteryState (07-domain-student.md)
  └─ 输出: 1 个学生 twin 可跑通

教学 AI 教练 PoC
  ├─ 依赖: 学生数字孪生 PoC 基础架构
  ├─ 依赖: A→B 状态映射 (30-atoB/01)
  └─ 输出: 1 个 AI 教练 + 学生 twin 可交互

Personal AI PoC
  └─ 依赖: 学生数字孪生架构（简化版）

协作 agent PoC
  └─ 依赖: 多个 SGE 实例协同
```

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-22
