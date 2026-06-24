# 2026-06-24 · ECOS 独立项目决策

## 主题

Bisen 进一步深化对 ECOS 项目的判断：从"作为 SelfLab 子项目"升级为"**作为与 SelfLab 并列的独立项目**"。完整迁移 5 份核心研究文档 + 5 份选择性参考文档到新项目 `/Users/loubicheng/project/ecos/`，SelfLab 端删除 4 份 ECOS 专属文档。

## 日期

2026-06-24

## 决策

**ECOS（Educational Cognitive Operating System）应作为与 SelfLab 并列的独立项目**，路径为 `/Users/loubicheng/project/ecos/`。

| 决策项 | 选择 |
|--------|------|
| 项目名 | ECOS |
| 项目路径 | /Users/loubicheng/project/ecos |
| 与 SelfLab 关系 | 兄弟项目（不是子项目）|
| SelfLab 端处理 | 删除 4 份 ECOS 专属文档 + 标注已迁移 |
| Git 初始化 | 初始化为新仓库（不自动 push）|

## 决策过程

### 阶段 1：v1.0（基于 3 轮对话）— 接受 SGE Phase 3 应用层定位

v1.0 深度研究文档判断 ECOS 适合作为 SGE Phase 3 的"应用层 PoC"（`phase3/90-applications/student-digital-twin.md` + `teaching-ai-coach.md`）。

### 阶段 2：v2.0（基于 5 轮对话）— 不适合 SGE 应用

v2.0 深度研究文档经 Explore agent 交叉验证，发现 SGE Phase 3 与 ECOS 存在 **4 大根本冲突**：

1. **方向错位**：SGE 把"学生数字孪生"定义为"AI 模拟学生身份"，ECOS 需要"理解真实学生"
2. **维度错位 + 方法论降级**：SGE 把 9D 强行映射到 value/drive，丢失 IRT/BKT 等科学估计方法
3. **Bloom 目标空间结构性缺席**：SGE Phase 3 目录零提及
4. **单 Agent 架构无法表达双 Agent 互校**

v2.0 提出 ECOS 应作为 **SelfLab 独立子项目**（`research/ecos/` + `ecos/` Python 包），与 SGE 并列。

### 阶段 3：进一步判断（2026-06-24）— 独立项目

Bisen 在 v2.0 基础上**进一步判断**：

> "ECOS 更适合作为单独一个项目，与 SelfLab 并列"

理由：

1. **避免散乱**：SelfLab 已有 SGE（主项目）+ Phase 3（应用化）+ A→B（调研子项目），再加 ECOS 子项目会让目录结构复杂
2. **独立发展**：SGE 关注"AI 自我涌现"，ECOS 关注"教育认知操作系统"——研究目标、目标用户、技术栈、用户群体都不同
3. **降低认知负担**：Bisen 在研究 ECOS 时被 SGE 内容分散注意力；独立项目让研究者在两个项目间清晰切换
4. **合作灵活**：未来 ECOS 与教育机构合作时，独立项目身份更合适（不需要引入 SGE 的所有上下文）

这是从"项目内部子项目"升级为"项目间独立项目"的架构调整。

## 核心架构（ECOS）

```
┌──────────────────────────────────────────────────────────┐
│              Bloom Goal Space（目标坐标系）                 │
│  Remember → Understand → Apply → Analyze → Evaluate → Create │
└──────────────────────────────────────────────────────────┘
                            ↕
┌──────────────────────────────────────────────────────────┐
│       Learning Coach Agent (LCA) — Policy Optimizer       │
└──────────────────────────────────────────────────────────┘
                            ↕
┌──────────────────────────────────────────────────────────┐
│     Cognitive Twin Agent (CTA) — State Estimator          │
│     状态：K/P/S/C/X + BloomProfile + LearningDNA + Trajectory │
└──────────────────────────────────────────────────────────┘
                            ↕
                         Student
```

## 产出

### ECOS 独立项目（新建，commit f5eeea0）

- 路径：`/Users/loubicheng/project/ecos/`
- 44 个文件，10610 行
- 5 份核心研究文档（从 SelfLab 迁移）+ 5 份选择性参考文档 + 14 份研究维度占位 + 7 份项目根级文件 + 9 份 Python 包骨架
- Git 初始化完成（不 push，等用户决定）

### SelfLab 端清理（commit 待）

- 删除 4 份 ECOS 专属文档：
  - `research/cognitive-architecture/Cognitive-Digital-Twin.md`
  - `research/cognitive-architecture/Cognitive-Digital-Twin02.md`
  - `research/cognitive-architecture/Cognitive-Digital-Twin03.md`
  - `research/cognitive-architecture/Cognitive-Digital-Twin-Deep-Research.md`
- CHANGELOG.md 1.24.0 条目追加
- SGE-Key-Insights.md 正式洞察 31/32 新增
- discussions/2026-06-24-ecos-independent-project-decision.md（本文件）

## 文件迁移清单

### 完全复制（5 份核心研究文档）

| SelfLab 源 | ECOS 目标 |
|----------|---------|
| `research/cognitive-architecture/Cognitive-State-A-to-B-Research.md` | `research/gpt-dialogues/01-cognitive-state-a-to-b-research.md` |
| `research/cognitive-architecture/Cognitive-Digital-Twin.md` | `research/gpt-dialogues/02-cognitive-digital-twin-rounds-1-3.md` |
| `research/cognitive-architecture/Cognitive-Digital-Twin02.md` | `research/gpt-dialogues/03-cognitive-digital-twin-rounds-4-5.md` |
| `research/cognitive-architecture/Cognitive-Digital-Twin03.md` | `research/gpt-dialogues/04-cognitive-digital-twin-v01-report.md` |
| `research/cognitive-architecture/Cognitive-Digital-Twin-Deep-Research.md` | `research/deep-research/Cognitive-Digital-Twin-Deep-Research.md` |

### 选择性复制（5 份共享基础参考）

| SelfLab 源 | ECOS 目标 |
|----------|---------|
| `research/cognitive-architecture/Shared-Cognitive-Science-Toolbox.md` | `research/30-shared-cognitive-tools/shared-cognitive-science-toolbox.md` |
| `research/sge-learning/SGE-Learning-from-AiBeing.md` | `research/40-aibeing-borrowing/01-concept-borrowing.md` |
| `discussions/2026-06-22-sge-phase3-aibeing-reflection.md` | `research/40-aibeing-borrowing/02-application-layer-borrowing.md` |
| `research/cognitive-architecture/Cognitive-Architectures-Overview.md` | `references/cognitive-architectures-overview.md` |
| `references/AiBeing-Core-Engine-Reference.md` | `references/aibeing-core-engine-reference.md` |

### SelfLab 保留（5 份非 ECOS 专属）

- `research/cognitive-architecture/Cognitive-Architectures-Overview.md` — 认知架构综述（共享基础）
- `research/cognitive-architecture/Cognitive-State-A-to-B-Distilled.md` — A→B 精要版
- `research/cognitive-architecture/Cognitive-State-A-to-B-Research.md` — 7 页综合站点（保留作为 A→B 调研历史）
- `research/cognitive-architecture/SGE-Cognitive-Tools-Application.md` — SGE 工具应用
- `research/cognitive-architecture/Shared-Cognitive-Science-Toolbox.md` — 共享工具箱

## 项目结构对比

### 旧结构（v2.0 之前）

```
SelfLab/
├── CLAUDE.md
├── README.md
├── ROADMAP.md
├── SGE-Key-Insights.md
├── research/
│   ├── sge-core/
│   ├── sge-feasibility/
│   ├── sge-learning/
│   ├── cognitive-architecture/  (含 A→B 调研 + ECOS 文档)
│   └── phase3/                  (SGE Phase 3 规划)
├── sge/                          (Python 包)
├── experiments/
├── references/
├── discussions/
└── prototypes/
```

### 新结构（v2.0 + 独立项目决策后）

```
SelfLab/                                    ECOS/
├── CLAUDE.md                               ├── README.md
├── README.md                               ├── CLAUDE.md
├── ROADMAP.md                              ├── CHANGELOG.md
├── SGE-Key-Insights.md (32 条洞察)         ├── LICENSE
├── research/                               ├── pyproject.toml
│   ├── sge-core/                           ├── ecos/  (Python 包骨架)
│   ├── sge-feasibility/                    ├── research/
│   ├── sge-learning/                       │   ├── deep-research/
│   ├── cognitive-architecture/             │   │   └── Cognitive-Digital-Twin-Deep-Research.md
│   │   ├── Cognitive-Architectures-...     │   ├── gpt-dialogues/
│   │   ├── Cognitive-State-A-to-B-...      │   │   ├── 01-cognitive-state-a-to-b-research.md
│   │   ├── Shared-Cognitive-Science-...    │   │   ├── 02-cognitive-digital-twin-rounds-1-3.md
│   │   ├── SGE-Cognitive-Tools-...         │   │   ├── 03-cognitive-digital-twin-rounds-4-5.md
│   │   └── (移除 4 份 ECOS 专属文档)        │   │   └── 04-cognitive-digital-twin-v01-report.md
│   └── phase3/                             │   ├── 00-overview/  (4 战略层占位)
├── sge/  (Python 包)                       │   ├── 10-engineering/  (5 工程层占位)
├── experiments/                            │   ├── 20-pedagogy/  (4 教学法占位)
├── references/                             │   ├── 30-shared-cognitive-tools/
├── discussions/                            │   ├── 40-aibeing-borrowing/
└── prototypes/                             │   ├── 90-mvp/
                                            ├── references/
                                            ├── experiments/
                                            ├── discussions/
                                            └── prototypes/
```

两项目**共享 7 个认知科学工具**(在各自 `research/30-shared-cognitive-tools/` 保留副本),各自独立演进。

## 关键洞察

### 洞察 31（新增）

> ECOS 应作为与 SelfLab 并列的独立项目,而不是 SelfLab 的子项目

**理由**：避免散乱 + 独立发展 + 降低认知负担 + 合作灵活

### 洞察 32（新增）

> SGE 的"价值/驱动"机制不适合建模"对学生的理解"

**理由**：SGE value/drive 是 AI 视角，ECOS 9D + BloomProfile 是观察者视角，方向性不同

## 与 SelfLab 主线的关系

| 维度 | SelfLab (SGE) | ECOS |
|------|---------------|------|
| 核心问题 | AI 自我涌现 | AI 理解并帮助学生成长 |
| 核心架构 | 单一 Agent 12 步 | 双 Agent 互校（CTA + LCA）|
| 状态空间 | AI 自身 value/drive | 学生 9D + BloomProfile |
| 共享基础 | 7 个认知科学工具 | 同上（共享）|
| 不共享 | 自我/身份涌现 | value/drive（方向错位）|

**未来可能的连接**：
- SGE 可作为 ECOS LCA 的"教师侧人格引擎"（提供内在人格）
- ECOS Python 包可通过 pip 依赖 `sge` 子集
- 研究文档互相引用

## 下一步

### ECOS 项目
- 填充战略层 4 份文档（`research/00-overview/`）
- 填充工程层 5 份文档（`research/10-engineering/`）
- 填充教学法层 4 份文档（`research/20-pedagogy/`）
- 设计 MVP（`research/90-mvp/`）
- 实施 Python 包（`ecos/`）

### SelfLab 项目
- 等待 ECOS 项目 GitHub 仓库创建（如果用户决定推送）
- 关注 SGE Phase 3 后续实施（不包含 ECOS 应用）
- 关注 SGE 引擎在 Personal AI / 协作 agent / 历史人物等应用方向

## 关联文档

- ECOS 端：[discussions/2026-06-24-ecos-project-establishment.md](https://github.com/cnbison/ecos/blob/main/discussions/2026-06-24-ecos-project-establishment.md)
- v2.0 深度研究（已迁移到 ECOS）：[research/deep-research/Cognitive-Digital-Twin-Deep-Research.md](https://github.com/cnbison/ecos/blob/main/research/deep-research/Cognitive-Digital-Twin-Deep-Research.md)
- SGE-Key-Insights 31/32：[SGE-Key-Insights.md §31-32](../SGE-Key-Insights.md)

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-24
**版本**：v1.0
