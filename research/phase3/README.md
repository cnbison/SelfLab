# SGE Phase 3 — SSOT 入口

> **Phase 3 = SGE 从研究到应用的重大转折点**
> **目标**：把 M2.x 验证过的 personality engine 落地为可被 4 类应用直接调用的基础设施

## 决策摘要（5 分钟读这一节就够）

### Phase 3 是什么

```
M2.x：SGE 引擎已验证（1000 epoch × 真实 LLM × 3 baby，personality_divergence 0.9884）
Phase 3：把 SGE 变成可 pip install、可被生产应用调用的 personality engine
```

### 4 个应用方向

| 应用 | SGE 核心作用 | 详见 |
|------|-------------|------|
| **学生数字孪生** | SubjectMasteryState + 12 步编排 | [00-applications.md §应用 1](./00-overview/01-applications.md) |
| **教学 AI 教练** | 长期会话 + frustration 累积 | [00-applications.md §应用 2](./00-overview/01-applications.md) |
| **Personal AI** | Hawking 衰减 + 4 层记忆 | [00-applications.md §应用 3](./00-overview/01-applications.md) |
| **协作 agent** | 多 SGE 实例各自不同人格 | [00-applications.md §应用 4](./00-overview/01-applications.md) |

### 当前状态（2026-06-22）

| 层级 | 状态 |
|------|------|
| 引擎层（sge/ 包）| ✅ M2.3 完成，pip install 可用 |
| 应用层 | 📋 设计中（本目录就是 SSOT） |
| 数字孪生 PoC | ❌ 未开始 |
| AI 教练 PoC | ❌ 未开始 |

### 4 个文件必读（按重要性）

1. [00-overview/01-applications.md](./00-overview/01-applications.md) — 4 应用详细分析
2. [00-overview/02-architecture.md](./00-overview/02-architecture.md) — sge/ 包架构 + 应用层边界
3. [00-overview/03-roadmap.md](./00-overview/03-roadmap.md) — Phase 3.1/3.2/3.3 时间线
4. [10-engineering/01-persistence.md](./10-engineering/01-persistence.md) — 持久化（Phase 3.1 第一个任务）

### 5 个研究维度（项目级）

| 维度 | 关联 | 状态 |
|------|------|------|
| **SGE**（本研究项目）| 核心 | 进行中 |
| **A→B**（学习状态迁移）| [30-atoB/](./30-atoB/) | 探索中 |
| **K12 学生认知结构** | [20-domain-k12/](./20-domain-k12/) | 探索中 |
| **学生数字孪生** | [90-applications/student-digital-twin.md](./90-applications/student-digital-twin.md) | 设计中 |
| **教学 AI 教练** | [90-applications/teaching-ai-coach.md](./90-applications/teaching-ai-coach.md) | 设计中 |

## 文档结构

```
research/phase3/
├── README.md                       # 本文件（SSOT 入口）
├── 00-overview/                    # 战略层（4 文件）
│   ├── 01-applications.md
│   ├── 02-architecture.md
│   ├── 03-roadmap.md
│   └── 04-risks.md
├── 10-engineering/                 # Phase 3.1 工程实现（6 文件）
│   ├── 01-persistence.md
│   ├── 02-session.md
│   ├── 03-context-injection.md
│   ├── 04-llm-cache.md
│   ├── 05-prompt-management.md
│   └── 06-testing.md
├── 20-domain-k12/                  # K12 认知结构（[未来]）
├── 30-atoB/                        # A→B 学习迁移（[未来]）
└── 90-applications/                # 具体应用 PoC（[未来]）
    ├── README.md
    ├── student-digital-twin.md
    ├── teaching-ai-coach.md
    ├── personal-ai.md
    └── multi-ai-collaboration.md
```

**编号约定**：
- `00-` 战略层（Phase 3 全局）
- `10-` 工程层（Phase 3.1 实现）
- `20-` 领域知识（K12 认知）
- `30-` 跨项目整合（A→B）
- `90-` 应用 PoC（具体场景）

## 关键决策（已经做了）

| 决策 | 选择 | 来源 |
|------|------|------|
| 包名 | `sge/`（pip install sge）| [00-overview/02-architecture.md](./00-overview/02-architecture.md) |
| 存储 | SQLite + JSON | [10-engineering/01-persistence.md](./10-engineering/01-persistence.md) |
| 借鉴 AiBeing | 引擎内部 9 机制（M2.1）+ 应用层 6 方向（Phase 3）| [discussions/2026-06-22-sge-phase3-aibeing-reflection.md](../../discussions/2026-06-22-sge-phase3-aibeing-reflection.md) |
| 不借鉴 AiBeing | SOUL.md persona、多语言、触觉/听觉 skill | 同上 |

## 下一步（立即）

| 优先级 | 任务 | 详见 |
|--------|------|------|
| **P0** | Phase 3.1 实施：persistence + session + context-injection | [10-engineering/](./10-engineering/) |
| **P0** | 完成 strategic significance doc 拆分到本目录 | 本文 §"迁移" |
| **P1** | 学生数字孪生 PoC 设计 | [90-applications/student-digital-twin.md](./90-applications/student-digital-twin.md) |
| **P2** | A→B 整合探索 | [30-atoB/](./30-atoB/) |
| **P2** | K12 认知结构研究 | [20-domain-k12/](./20-domain-k12/) |

## 迁移

从 `discussions/2026-06-21-...-strategic-significance.md` (v1.5) 和 `discussions/2026-06-22-...-aibeing-reflection.md` 拆分而来。原讨论文档归档后保留作为审计记录。

## 关联文档（项目级）

- [CLAUDE.md §应用方向](../../../CLAUDE.md)
- [ROADMAP.md §Phase 3](../../../ROADMAP.md)
- [sge/README.md §Phase 3 路线图](../../../sge/README.md)
- [discussions/2026-06-21-sge-strategic-significance.md](../../../discussions/2026-06-21-sge-strategic-significance.md) — 战略反思（原文档，已归档）
- [discussions/2026-06-22-sge-phase3-aibeing-reflection.md](../../../discussions/2026-06-22-sge-phase3-aibeing-reflection.md) — AiBeing 应用层反思（原文档，已归档）
- [research/sge-feasibility/SGE-M23-Implementation-Plan.md](../../sge-feasibility/SGE-M23-Implementation-Plan.md) — M2.3 计划（已合并到 03-roadmap.md）

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-22
**状态**：✅ Phase 3 规划骨架就绪，10 个核心文件填充中
