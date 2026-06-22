# 03 - Phase 3 时间线

> **目的**：Phase 3.1 / 3.2 / 3.3 时间线 + 里程碑 + 依赖图
> **基础**：基于 chat 讨论 + M2.3 实施计划 + Phase 3 AiBeing 反思

---

## 1. Phase 3 整体时间线

```
Phase 3.1 (P0: 应用基础)        Phase 3.2 (P1: 性能 + 测试)     Phase 3.3 (P2: PoC 验证)
─────────────────────         ─────────────────────         ──────────────────
Week 1-3 (3 周)                Week 4-6 (2-3 周)             Week 7-12 (6 周)
- persistence.py              - llm_cache.py                 - 90-applications/
- session.py                  - 单元测试覆盖 ≥80%             - student-digital-twin PoC
- context_injection.py        - prompt 版本管理              - teaching-ai-coach PoC
                              - (可选) async/streaming
                              - (可选) M2.2 重跑（Hawking 修复后验证衰减）

并行：20-domain-k12 + 30-atoB 探索
```

---

## 2. Phase 3.1 详细时间线（P0 应用基础）

| Week | 任务 | 工作量 | 依赖 |
|------|------|--------|------|
| W1 Day 1-2 | `sge/persistence.py` (TwinStateDB + SQLite schema) | 1.5 天 | schema 设计（已 v1.5 §9）|
| W1 Day 3 | persistence 单元测试 | 0.5 天 | TwinStateDB |
| W1 Day 4-5 | `sge/session.py` (TwinSession) | 1.5 天 | persistence |
| W2 Day 1 | session 单元测试 | 0.5 天 | TwinSession |
| W2 Day 2-3 | `sge/context_injection.py` (TwinContextBuilder) | 1.5 天 | session |
| W2 Day 4-5 | context_injection 单元测试 + 集成测试 | 1 天 | context_injection |
| W3 | SGEOrchestrator 集成 hook（_save_checkpoint 等）| 1 周 | 上面 3 个模块 |
| W3 | 文档 + 示例（[90-applications/student-digital-twin.md](../90-applications/student-digital-twin.md) PoC 设计）| 1 周 | 双轨并行 |

---

## 3. Phase 3.2 详细时间线（P1 性能 + 测试）

| Week | 任务 | 工作量 |
|------|------|--------|
| W4 | `sge/llm_cache.py` (SGELLMCache + hash 策略 + 失效检测) | 0.5 天 |
| W4 | 单元测试覆盖：HawkingDecay (4/4 already)、Crystallizer、Value、Drive、Agent | 1.5 天 |
| W5 | `sge/prompts/` 目录 + version 管理 | 1 天 |
| W5 | async/streaming 支持（如果学生 chat 应用需要）| 1 天 |
| W5-6 | M2.2 重跑（验证 Hawking 修复后真实衰减）| 2 天（执行）+ 1 天（分析）|
| W6 | 集成测试 + e2e smoke test | 1 天 |

---

## 4. Phase 3.3 详细时间线（P2 PoC 验证）

| Week | 任务 | 工作量 |
|------|------|--------|
| W7-8 | [student-digital-twin.md](../90-applications/student-digital-twin.md) PoC 实现（学生事件 schema + adapter + UI 原型）| 2 周 |
| W9-10 | [teaching-ai-coach.md](../90-applications/teaching-ai-coach.md) PoC 实现（含 A→B 整合）| 2 周 |
| W11-12 | PoC 评估 + Phase 3 总结报告 | 2 周 |

---

## 5. 依赖图

```
                    persistence.py
                         │
                         ▼
                    session.py
                         │
                         ▼
                 context_injection.py
                         │
                         ▼
            SGEOrchestrator hook 集成
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
    llm_cache.py   prompts/          单元测试覆盖
        │                │                │
        └────────────────┼────────────────┘
                         │
                         ▼
              Phase 3.1 集成测试
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   student-digital-   teaching-ai-      M2.2 重跑验证
       twin PoC         coach PoC        Hawking 衰减
```

---

## 6. 里程碑

| Milestone | 截止 | 验收 |
|-----------|------|------|
| **M1**: persistence.py + 单元测试 | W1 末 | SQLite schema 落地 + save/load 4 层可工作 |
| **M2**: session.py + 单元测试 | W2 始 | TwinSession 类可加载完整状态、跑 N epoch、保存 |
| **M3**: context_injection.py + 集成测试 | W2 末 | 学生上下文注入 SGE Critic，verified |
| **M4**: Phase 3.1 集成（orchestrator hook）| W3 末 | 端到端：student event → SGE 处理 → DB 保存 → chat 输出 |
| **M5**: Phase 3.2（性能 + 测试）| W6 末 | LLM cache 节省调用，单元测试 ≥ 80% |
| **M6**: Phase 3.3（PoC 验证）| W12 末 | 2 个 PoC 跑通，写总结报告 |

---

## 7. Phase 3 与其他维度并行

| 维度 | Phase 3 时间 | 工作量 |
|------|------------|--------|
| **20-domain-k12** | W4-W6 并行 | 1 周（探索 K12 认知发展 + 学科结构 + 教学法）|
| **30-atoB** | W4-W8 并行 | 2 周（A→B 状态映射 + 转移设计 + 与 SGE 整合）|
| **90-applications** | W7-W12（Phase 3.3 实施期间）| 4 周 |

并行 ≠ 多人同时做（假设还是 Bisen + Claude 2 人），而是**写文档和写代码可以错开**——比如 W4-W6 写 domain-k12 文档时，llm_cache.py 也在写。

---

## 8. 优先级矩阵

| 任务 | 价值 | 工作量 | ROI | 优先级 |
|------|------|--------|-----|--------|
| persistence.py | 高 | 1.5 天 | 高 | **P0** |
| session.py | 高 | 1.5 天 | 高 | **P0** |
| context_injection.py | 高 | 1.5 天 | 高 | **P0** |
| 单元测试覆盖 | 中 | 1.5 天 | 中 | **P1** |
| llm_cache.py | 中 | 0.5 天 | 极高（省 API 成本）| **P1** |
| prompts/ 版本管理 | 中 | 1 天 | 中 | P2 |
| async/streaming | 低 | 1 天 | 低 | P2 |
| M2.2 重跑 | 低 | 3 天 | 低（数据已存在）| P2 |
| 学生数字孪生 PoC | 高 | 2 周 | 中 | Phase 3.3 |
| AI 教练 PoC | 高 | 2 周 | 中 | Phase 3.3 |
| K12 认知研究 | 中 | 1 周 | 中 | 并行 |
| A→B 整合 | 中 | 2 周 | 中 | 并行 |

---

## 9. 关联文档

- [README.md](../README.md) — Phase 3 SSOT 入口
- [02-architecture.md](./02-architecture.md) — sge/ 包架构
- [04-risks.md](./04-risks.md) — 风险矩阵
- [10-engineering/](../10-engineering/) — 各工程文件详情
- [sge/README.md §Phase 3 路线图](../../../sge/README.md)
- [research/sge-feasibility/SGE-M23-Implementation-Plan.md](../../sge-feasibility/SGE-M23-Implementation-Plan.md) — M2.3 计划（已合并到此）

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-22
