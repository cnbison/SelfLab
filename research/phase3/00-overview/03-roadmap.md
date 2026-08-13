# 03 - Phase 3 时间线

> **目的**：Phase 3.1 / 3.2 / 3.3 时间线 + 里程碑 + 依赖图
> **基础**：基于 chat 讨论 + M2.3 实施计划 + Phase 3 AiBeing 反思
> **2026-08-13 收窄决策**：Phase 3.3 从"PoC 验证"重定义为"Runtime 可加载性验证"，详见 [§10 Phase 3.3 收窄决策](#10-phase-33-收窄决策2026-08-13)

---

## 1. Phase 3 整体时间线

```
Phase 3.1 (P0: 应用基础)        Phase 3.2 (P1: 性能 + 测试)        Phase 3.3 (P2: Runtime 验证)
─────────────────────         ─────────────────────          ─────────────────────────
Week 1-3 (3 周) ✅              Week 4-6 (2-3 周)                Week 7-8 (2 周) ✅
- persistence.py ✅            - llm_cache.py ❌ [1]             - student-digital-twin
- session.py ✅                - 单元测试覆盖 ≥80% ✅ [2]         Runtime Demo ✅
- context_injection.py ✅      - prompt 版本管理 ❌ [1]           - teaching-ai-coach M4+ 延后
                               - (可选) async/streaming
                               - (可选) M2.2 重跑 ✅

并行：20-domain-k12 + 30-atoB 探索 → 暂停（Phase 3 收窄决策）
```

**关键节点**：
- **Phase 3.1** ✅ 完成（CHANGELOG 1.32-1.36）
- **Phase 3.2 pytest 部分** ✅ 完成（1.37-1.39，14 模块 86% 覆盖）
- **Phase 3.2 工程缺口** [1]（llm_cache + prompts）❌ 未完成 → 划为"Phase 3.2 收尾"任务，下次启动
- **Phase 3.3 student-digital-twin Runtime Demo** ✅ 完成（1.40.0 + 1.40.1）
- **Phase 3.3 teaching-ai-coach PoC** ⏸ M4+ 延后（2026-08-13 决策）

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

| Week | 任务 | 工作量 | 状态（2026-08-13）|
|------|------|--------|-------------------|
| W4 | `sge/llm_cache.py` (SGELLMCache + hash 策略 + 失效检测) | 0.5 天 | ❌ [1] 划为"Phase 3.2 收尾" |
| W4 | 单元测试覆盖：HawkingDecay (4/4 already)、Crystallizer、Value、Drive、Agent | 1.5 天 | ✅ [2] 实际由三批 pytest 框架化完成（1.37-1.39）|
| W5 | `sge/prompts/` 目录 + version 管理 | 1 天 | ❌ [1] 划为"Phase 3.2 收尾" |
| W5 | async/streaming 支持（如果学生 chat 应用需要）| 1 天 | ⏸ 暂停（Phase 3 收窄，无需）|
| W5-6 | M2.2 重跑（验证 Hawking 修复后真实衰减）| 2 天（执行）+ 1 天（分析）| ✅ 完成（M2.2 v6 长程验证，1.31.0）|
| W6 | 集成测试 + e2e smoke test | 1 天 | ✅ 完成（persistence 集成 + student-digital-twin 端到端 demo）|

> **[1] Phase 3.2 收尾待办**（下次启动）：
> - `sge/llm_cache.py` 实施 + 单元测试（0.5 天）
> - `sge/prompts/` 目录 + version 管理（1 天）
> - 详见 [§10 Phase 3.3 收窄决策](#10-phase-33-收窄决策2026-08-13) §"Phase 3.2 缺口划分"

> **[2] Phase 3.2 pytest 框架化实际完成度**：14 模块累计 442 tests，86% 平均覆盖率（详见 [sge/README.md §测试](../../../sge/README.md)）

---

## 4. Phase 3.3 详细时间线（P2 Runtime 可加载性验证）

> **2026-08-13 收窄后定义**：从"PoC 验证"重命名为"Runtime 可加载性验证"——证明 sge/ 包可被外部项目加载调用，不是应用可行性验证。

| Week | 任务 | 工作量 | 状态（2026-08-13）|
|------|------|--------|-------------------|
| W7-8 | [student-digital-twin.md](../90-applications/student-digital-twin.md) Runtime Demo（学生事件 schema + adapter + 端到端 demo）| 2 周 | ✅ 完成（CHANGELOG 1.40.0 + 1.40.1）|
| ~~W9-10~~ | ~~[teaching-ai-coach.md](../90-applications/teaching-ai-coach.md) PoC 实现（含 A→B 整合）~~ | ~~2 周~~ | ⏸ M4+ 延后（2026-08-13 决策，仍为 21 行占位）|
| W11-12 | **Phase 3 Runtime 收尾报告**（总结"包已可调用"而非"应用可行"）| 2 周 | ⏸ 待写 |

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

| Milestone | 截止 | 验收 | 状态（2026-08-13）|
|-----------|------|------|-------------------|
| **M1**: persistence.py + 单元测试 | W1 末 | SQLite schema 落地 + save/load 4 层可工作 | ✅ |
| **M2**: session.py + 单元测试 | W2 始 | TwinSession 类可加载完整状态、跑 N epoch、保存 | ✅ |
| **M3**: context_injection.py + 集成测试 | W2 末 | 学生上下文注入 SGE Critic，verified | ✅ |
| **M4**: Phase 3.1 集成（orchestrator hook）| W3 末 | 端到端：student event → SGE 处理 → DB 保存 → chat 输出 | ✅ |
| **M5**: Phase 3.2（性能 + 测试）| W6 末 | LLM cache 节省调用，单元测试 ≥ 80% | ⚠️ pytest 部分 ✅（86% 覆盖），llm_cache + prompts 划收尾 |
| **M6**: Phase 3.3（Runtime 验证）| W12 末 | sge/ 包可被外部项目加载调用 + Runtime Demo + 收尾报告 | ⚠️ student-digital-twin Runtime Demo ✅，teaching-ai-coach M4+ 延后，收尾报告待写 |

---

## 7. Phase 3 与其他维度并行

| 维度 | Phase 3 时间 | 工作量 | 状态（2026-08-13）|
|------|------------|--------|-------------------|
| **20-domain-k12** | W4-W6 并行 | 1 周（探索 K12 认知发展 + 学科结构 + 教学法）| ⏸ 暂停（Phase 3 收窄决策）|
| **30-atoB** | W4-W8 并行 | 2 周（A→B 状态映射 + 转移设计 + 与 SGE 整合）| ⏸ 暂停（洞察 32 否决 SGE value/drive 建模他人）|
| **90-applications** | W7-W8（Runtime Demo 实施期间）| 2 周 | ✅ student-digital-twin Runtime Demo 完成；⏸ teaching-ai-coach M4+ 延后 |

并行 ≠ 多人同时做（假设还是 Bisen + Claude 2 人），而是**写文档和写代码可以错开**——比如 W4-W6 写 domain-k12 文档时，llm_cache.py 也在写。

> **2026-08-13 收窄决策**：20-domain-k12 与 30-atoB **暂停**，不再作为 Phase 3 并行任务。理由：Phase 3 边界收紧在"Runtime 工程化"，不再做新应用探索或跨项目调研。

---

## 8. 优先级矩阵

| 任务 | 价值 | 工作量 | ROI | 优先级 | 状态（2026-08-13）|
|------|------|--------|-----|--------|-------------------|
| persistence.py | 高 | 1.5 天 | 高 | **P0** | ✅ 完成 |
| session.py | 高 | 1.5 天 | 高 | **P0** | ✅ 完成 |
| context_injection.py | 高 | 1.5 天 | 高 | **P0** | ✅ 完成 |
| 单元测试覆盖 | 中 | 1.5 天 | 中 | **P1** | ✅ 完成（86% 覆盖，442 tests）|
| llm_cache.py | 中 | 0.5 天 | 极高（省 API 成本）| **P1** | ❌ 划为"Phase 3.2 收尾" |
| prompts/ 版本管理 | 中 | 1 天 | 中 | P2 | ❌ 划为"Phase 3.2 收尾" |
| async/streaming | 低 | 1 天 | 低 | P2 | ⏸ 暂停（无需）|
| M2.2 重跑 | 低 | 3 天 | 低（数据已存在）| P2 | ✅ 完成（M2.2 v6）|
| 学生数字孪生 Runtime Demo | 高 | 2 周 | 中 | Phase 3.3 | ✅ 完成（重命名为 Runtime Demo）|
| AI 教练 PoC | 高 | 2 周 | 中 | Phase 3.3 | ⏸ M4+ 延后 |
| K12 认知研究 | 中 | 1 周 | 中 | 并行 | ⏸ 暂停 |
| A→B 整合 | 中 | 2 周 | 中 | 并行 | ⏸ 暂停 |

---

## 9. 关联文档

- [README.md](../README.md) — Phase 3 SSOT 入口
- [02-architecture.md](./02-architecture.md) — sge/ 包架构
- [04-risks.md](./04-risks.md) — 风险矩阵
- [10-engineering/](../10-engineering/) — 各工程文件详情
- [sge/README.md §Phase 3 路线图](../../../sge/README.md)
- [research/sge-feasibility/SGE-M23-Implementation-Plan.md](../../sge-feasibility/SGE-M23-Implementation-Plan.md) — M2.3 计划（已合并到此）

---

## 10. Phase 3.3 收窄决策（2026-08-13）

### 决策背景

Bisen 在 Phase 3.3 student-digital-twin 完成（CHANGELOG 1.40.0 + 1.40.1）后，反思当前 SGE 走向：

> "先暂停一下，梳理总结一下 SGE 开发到现在，是个什么状况？我咋感觉越来越像在做类似 ECOS 项目的事情了呢？会不会方向偏移了？"

**核心担忧**：Phase 3.3 的两个 PoC（`student-digital-twin` + `teaching-ai-coach`）虽然在防火墙之内（洞察 31/32/33），但**名称与 ECOS（学生数字孪生 + AI 教学教练）高度重叠**，做下去感觉"像在给 ECOS 打前站"。

### 决策内容

**采用选项 A：保留 Phase 3 路线但收窄 PoC 范围**

| 原 Phase 3.3 | 收窄后 |
|-------------|--------|
| **PoC 验证**（应用原型） | **Runtime 可加载性验证**（证明 sge/ 包可被外部项目加载调用）|
| student-digital-twin PoC | student-digital-twin Runtime Demo |
| teaching-ai-coach PoC | M4+ 延后（占位文档保留）|
| Phase 3.3 评估 + 总结报告 | **Phase 3 Runtime 收尾报告**（总结"包已可调用"而非"应用可行"）|

**核心边界**：Phase 3.3 收尾 = 把 1.40.0/1.40.1 的成果**定性归档**，不再往前推。

### Phase 3.2 缺口划分

`llm_cache.py` + `prompts/` 不在本次收窄范围内，划为"Phase 3.2 收尾"任务，下次启动：

| 任务 | 工作量 | 说明 |
|------|--------|------|
| `sge/llm_cache.py` 实施 + 单元测试 | 0.5 天 | hash 策略 + 失效检测，省 API 成本 |
| `sge/prompts/` 目录 + version 管理 | 1 天 | Prompt 版本化（洞察 33 Runtime 抽象完整性的待验证问题）|

### 与已有洞察的关系

| 洞察 | 关系 |
|------|------|
| 30（SGE 三原则锚点）| **强化** —— 原则 1（"SGE 是根"）边界更清晰 |
| 31（ECOS 独立项目）| **强化** —— 通过收窄避免 PoC 被误读为 ECOS 前站 |
| 32（SGE value/drive 不适合建模他人）| **支撑** —— Runtime Demo 只调 duck typing mastery_state，不涉及 SGE 建模学生 |
| 33（Self Evolution Runtime 定位）| **强化** —— Runtime Demo 直接证明 sge/ 包可作为外部 Runtime 被加载调用 |

### 详细讨论记录

完整决策讨论（含 Bisen 担忧的逐条分析 + 3 选项对比 + 推荐理由）：

- [discussions/2026-08-13-phase3-narrowing-decision.md](../../../discussions/2026-08-13-phase3-narrowing-decision.md)

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-22
**最后更新**：2026-08-13（Phase 3.3 收窄决策）
