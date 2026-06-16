# SGE 记忆层设计

> **本文件是 SGE 记忆层的正式设计文档**，由 [discussions/2026-06-15-memory-layer-design.md](../../discussions/2026-06-15-memory-layer-design.md) 升格而来。
>
> 关键术语参见 [references/Glossary.md](../../references/Glossary.md)；与 PRD/ARCH/DESIGN 的对应关系见文末"相关文档"。

---

## 一、设计原则

### 1.1 核心立场

SGE 的记忆不是"聊天历史"，而是"**人格状态**"——这是 SGE 与所有对话型 AI 系统的本质区别。

| 维度 | 对话型记忆（SGE 之外） | SGE 人格状态 |
|------|---------------------|-------------|
| 内容 | 聊天消息、用户输入 | 价值观、身份、叙事、行为模式 |
| 访问模式 | 按时间序、按用户 | 按状态、按相似度 |
| 检索方式 | 关键词匹配 | KNN 语义检索 |
| 状态变化 | 用户消息驱动 | 经历 + 反思驱动 |
| 持久化目标 | 短期会话 | 长期人格延续 |

### 1.2 双视角原则

SGE 记忆层设计采用**认知科学视角**与**工程视角**并行的双视角——两套分层互补，不矛盾。

- **认知科学视角**（回答"什么样的记忆"）：源自 Atkinson-Shiffrin 记忆模型
- **工程视角**（回答"记忆存哪里、怎么检索"）：基于 AiBeing 本地架构

详细对应关系见 [PRD §4.1 FR-2 认知科学 vs 工程映射表](../../PRD.md)。

### 1.3 自建原则

**不引入外部记忆框架**（MemGPT/Mem0/Zep 等），基于 AiBeing 本地架构自建记忆层。

详细理由见 §四"方案对比"。

---

## 二、记忆内容分类

### 2.1 按内容分类

| 记忆类型 | 内容 | 认知科学归属 | 访问模式 | 存储位置 |
|---------|------|------------|---------|---------|
| 引擎状态 | drive_state, W1/W2, frustration | 短时记忆 / 内部状态 | 每轮读写 | `state/engine/agent_state.json` |
| 价值观向量 | 6 个具体价值观 + 2 个元价值 | 语义记忆 | 每轮读写 | `state/self/value_vector.json` |
| 结晶事件 | 带 context 向量的关键事件 | 情节记忆 | KNN 检索 | `memory/crystallized_events.json` |
| 身份标签 | "我是谁"的描述 | 自我概念 | 定期写，频繁读 | `state/self/identity.json` |
| 叙事文本 | 人生故事 | 自传体记忆 | 定期写，频繁读 | `state/self/narrative.json` |
| 行为模式 | Hebbian 权重（暗知识） | 程序性记忆 | 每轮读写 | `state/engine/agent_state.json`（W1/W2） |
| 短期上下文 | 当前事件输入 | 工作记忆 | 单轮临时 | 进程内存 |

### 2.2 按状态分类（Engine vs Self）

按 [ARCH §5.1 Engine/Self 区分](../../ARCH.md) 原则：

| 类别 | 包含 | 与 Self 的关系 |
|------|------|--------------|
| **Self 状态** | value_vector, identity, narrative | 直接构成"自我" |
| **Engine 状态** | agent_state, relationship_ema, frustration, metadata | 支撑 Self 的物理载体 |

**为什么分类**：
- Self 状态可独立备份（人格延续性验证）
- Engine 状态可独立复现（确定性测试）
- 符合"LLM 是引擎，Self 独立"（[SGE-Key-Insights 洞察 2](../../SGE-Key-Insights.md)）

---

## 三、推荐架构

### 3.1 三层架构

```
Layer 1：引擎状态层（SQLite / JSON）
  drive_state, W1/W2, frustration, value_vector, identity, narrative

Layer 2：事件记忆层（SQLite + 向量检索）
  crystallized_events 表 + ChromaDB 语义检索 + KNN Hawking 辐射

Layer 3：日志层（JSONL）
  epoch_log, value_trajectory, reward_history
```

### 3.2 工程实现细节

#### Layer 1：引擎状态层

**存储方式**：JSON 文件（开发期）→ SQLite（生产期）

**文件结构**：
```
state/
├── self/                      # === Self 状态 ===
│   ├── value_vector.json     # 价值观向量
│   ├── identity.json         # 身份标签
│   └── narrative.json        # 人生叙事
│
├── engine/                    # === Engine 状态 ===
│   ├── agent_state.json      # drive_state, W1/W2, b1/b2, recurrent
│   ├── relationship_ema.json # 关系 EMA
│   ├── frustration.json      # 当前 frustration
│   └── metadata.json         # age, interaction_count, total_reward, epoch
│
└── checkpoints/               # 周期性快照
    └── checkpoint-{epoch}.tar
```

详见 [ARCH §5.1 状态持久化](../../ARCH.md)。

#### Layer 2：事件记忆层

**存储方式**：SQLite + ChromaDB

**表结构**：
```sql
CREATE TABLE crystallized_events (
    event_id TEXT PRIMARY KEY,    -- 格式：{baby_id}-e{epoch}-{uuid8}
    event_type TEXT,              -- success/failure/...
    context_vector BLOB,          -- 12D context 向量
    description TEXT,
    intensity REAL,
    timestamp REAL,
    reward REAL,
    embedding BLOB                -- ChromaDB 同步存储
);

CREATE INDEX idx_timestamp ON crystallized_events(timestamp);
CREATE INDEX idx_intensity ON crystallized_events(intensity DESC);
```

**检索机制**：
- KNN 风格检索（基于 context 向量的余弦相似度）
- Hawking 辐射：质量（重要度）高的记忆更难消失
- 默认 Top-K = 3

**为什么用 ChromaDB**：
- 轻量级，单机部署
- 与 SQLite 互补（SQLite 存结构化，ChromaDB 存向量）
- 比暴力 KNN 快 10-100 倍

#### Layer 3：日志层

**存储方式**：JSONL（每行一个 JSON 对象）

**日志文件**：
```
logs/
├── epoch_log.jsonl           # 每个 Epoch 的完整输入/输出
├── value_trajectory.jsonl    # 价值观向量时间序列
├── identity_history.jsonl    # 身份标签演化历史
└── reward_history.jsonl      # reward 时间序列
```

**优势**：JSONL 易于追加写入、易于 grep、易于流式处理。

### 3.3 数据流图

```
Event Generator
    │
    ▼
Critic (LLM) ──────────────────────┐
    │                               │
    ├─→ context (12D) ───────────┬─→ KNN 检索
    │                            │
    ├─→ value_delta (6D) ───────┼─→ Value Layer EMA
    │                            │
    ├─→ frustration_delta (5D) ──┼─→ Reward Calculator
    │                            │
    └─→ relationship_delta (3D) ─┘
                                        │
                                        ▼
                            ┌─────────────────────┐
                            │ 写入 crystallized   │
                            │ events（如果结晶）   │
                            └─────────────────────┘
                                        │
                                        ▼
                                    ChromaDB
```

---

## 四、方案对比

### 4.1 候选方案

| 方案 | 架构特点 | 优势 | 劣势 |
|------|---------|------|------|
| **AiBeing 本地** | Style Memory + KNN + 本地 JSON | 与 SGE 架构契合；无外部依赖；可定制 | 需自建 KNN 索引 |
| **MemGPT / Letta** | 受 OS 虚拟内存启发，分层 working/archival/recall | 成熟；公司化运营 | 设计目标是"聊天助手"，不是"人格状态" |
| **Mem0** | 轻量级个性化记忆 API | 简单易用 | 只有向量存取，无结构化状态管理 |
| **Zep** | 时序知识图谱 + 向量混合检索 | 强在结构化事实记忆 | 对 SGE 过度工程化；事件是模拟生成的，不是真实对话 |

### 4.2 为什么选择 AiBeing 本地

- **架构契合**：SGE 直接复用 AiBeing 的 8 个机制（[SGE-Technology-Stack-Overview.md §一](./SGE-Technology-Stack-Overview.md)）
- **无外部依赖**：避免 MemGPT/Mem0/Zep 的 API 限制
- **可定制**：SGE 的"价值困境事件"是模拟生成的，不是真实对话——通用记忆框架不适用
- **可复现性**：本地存储更易保证实验可复现

### 4.3 MemGPT/Mem0/Zep 不适用的原因

| 方案 | 不适用原因 |
|------|----------|
| MemGPT | 设计目标是"聊天助手的记忆"，但 SGE 需要的是"人格状态的持久化"——本质不同 |
| Mem0 | 太轻量级，只有向量存取，缺少 SGE 需要的结构化状态管理（如 ValueVector 元数据、身份标签的演化追踪） |
| Zep | 知识图谱对 SGE 过度工程化；SGE 的事件是模拟生成的，知识图谱没有意义 |

---

## 五、关键决策汇总

| 决策 | 内容 | 理由 | 来源 |
|------|------|------|------|
| **自建而非引入外部框架** | 基于 AiBeing 本地架构 | SGE 记忆是"人格状态"不是"聊天历史" | [discussions/2026-06-15-memory-layer-design.md](../../discussions/2026-06-15-memory-layer-design.md) |
| **SQLite + ChromaDB 混合** | SQLite 存结构化，ChromaDB 存向量 | 各取所长；避免单一数据库的局限 | 同上 |
| **去 EverMemOS** | 不使用 AiBeing 的 EverMemOS | SGE 的事件量可控（1000 Epoch），本地文件足够 | 同上 |
| **JSONL 日志** | 每行一个 JSON 对象 | 易于追加写入、流式处理、grep | 通用最佳实践 |
| **Engine/Self 状态分类** | `state/self/` vs `state/engine/` | 便于独立备份、复现；符合"LLM ≠ Self"哲学 | [ARCH §5.1](../../ARCH.md) |

---

## 六、与项目级文档的对应

| 主题 | 本文件 | 相关文档 |
|------|--------|---------|
| 记忆层功能需求 | §三、§四 | [PRD §4.1 FR-2](../../PRD.md) |
| 状态文件分类 | §二.2 | [ARCH §5.1](../../ARCH.md) |
| 记忆实验运行 | §三.3 数据流图 | [research/sge-feasibility/SGE-Experiment-Protocol.md §二](./SGE-Experiment-Protocol.md) |
| 记忆相关术语 | 全文 | [references/Glossary.md §四 SGE 架构术语](../../references/Glossary.md) |
| 记忆设计讨论 | §四 方案对比 | [discussions/2026-06-15-memory-layer-design.md](../../discussions/2026-06-15-memory-layer-design.md) |

---

## 七、相关文档

- **产品需求**：[PRD.md](../../PRD.md) — FR-2 Memory Layer
- **架构**：[ARCH.md](../../ARCH.md) — §1.2 4 层架构，§5.1 状态持久化
- **详细设计**：[DESIGN.md](../../DESIGN.md) — §2 Event Generator
- **技术栈全景**：[SGE-Technology-Stack-Overview.md](./SGE-Technology-Stack-Overview.md)
- **术语表**：[references/Glossary.md](../../references/Glossary.md)
- **讨论记录**：[discussions/2026-06-15-memory-layer-design.md](../../discussions/2026-06-15-memory-layer-design.md)
- **实验手册**：[SGE-Experiment-Protocol.md](./SGE-Experiment-Protocol.md)

---

**创建日期**：2026-06-15
**升格来源**：discussions/2026-06-15-memory-layer-design.md
**维护者**：Bisen & Claude
