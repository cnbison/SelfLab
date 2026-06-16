# 会话记录：SGE 记忆层设计探讨

日期：2026-06-15

参与者：Bisen & Claude

---

## 讨论主题

SGE 的记忆层应该用哪种方案？对比了四种方案：
1. AiBeing 方式（本地 Style Memory + EverMemOS）
2. MemGPT / Letta
3. Mem0
4. Zep

## 核心结论

**不是四选一，而是混合方案。** SGE 的记忆不是"聊天历史"，而是"人格状态"，没有单一框架能覆盖所有需求。

### SGE 记忆层的实际需求

| 记忆类型 | 内容 | 访问模式 |
|---------|------|---------|
| 引擎状态 | drive_state, W1/W2, frustration | 每轮读写 |
| 价值观向量 | 6 个具体价值观 + 2 个元价值 | 每轮读写 |
| 结晶事件 | 带 context 向量的关键事件 | KNN 语义检索 |
| 身份标签 | "我是谁"的描述 | 定期写，频繁读 |
| 叙事文本 | 人生故事 | 定期写，频繁读 |
| 行为模式 | Hebbian 权重（暗知识） | 每轮读写 |

### 推荐架构

```
Layer 1：引擎状态层（SQLite / JSON）
  drive_state, W1/W2, frustration, value_vector, identity, narrative

Layer 2：事件记忆层（SQLite + 向量检索）
  crystallized_events 表 + ChromaDB 语义检索 + KNN Hawking 辐射

Layer 3：日志层（JSONL）
  epoch_log, value_trajectory, reward_history
```

### 为什么不直接用 MemGPT / Mem0 / Zep

- MemGPT：设计目标是"聊天助手的记忆"，不是"人格状态的持久化"
- Mem0：太轻量，只有向量存取，没有结构化状态管理
- Zep：知识图谱对 SGE 过度工程化，事件是模拟生成的不是真实对话

### 最终方案

以 AiBeing 的本地架构为基底，用 SQLite 替代 JSON 文件，用 ChromaDB 替代暴力 KNN，去掉 EverMemOS。不引入外部框架。

## 产出文件

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| discussions/2026-06-15-memory-layer-design.md | 新增 | 本次讨论记录 |
| PRD.md §4.1 FR-2 | 修正 | 增加"认知科学三层 vs 工程三层"映射表，引用本讨论 |
| ARCH.md §5.1 | 修正 | 状态文件按 Engine/Self 分类，与本讨论的"Layer 1 引擎状态"对应 |

## 是否产生关键洞察

> **2026-06-15 修正**：本次讨论原自评"否"。按 [CLAUDE.md §核心工作流第二步](./../CLAUDE.md) 的判断标准"是否提出了新的核心概念或框架"，本讨论提出的"**认知科学三层 vs 工程三层**"双视角映射是新的概念框架。

**是。** 本次讨论产生以下新概念/框架：

1. **记忆双视角**：认知科学视角（工作/情节/语义记忆）vs 工程视角（引擎状态/事件记忆/日志层）—— 两套分层互补，不矛盾
2. **混合方案判断标准**：SGE 的记忆不是"聊天历史"而是"人格状态"，所以不能用现成的对话记忆框架
3. **"不引入外部框架"决策**：明确 SGE 自建记忆层（基于 AiBeing 本地架构），不引入 MemGPT/Mem0/Zep 等外部依赖

**对应修正**（参见 PRD.md §4.1 FR-2、ARCH.md §5.1）：
- 记忆双视角已成为 SGE 记忆层设计的核心原则
- "不引入外部框架"决策已落实为 ARCH §5.1 的状态文件结构

**建议**：作为 [SGE-Key-Insights](./../SGE-Key-Insights.md) 候选洞察 20，标题"记忆的双视角：认知分层与工程分层的对应"——但因本次讨论结论已在 PRD/ARCH 中具体落地，洞察价值相对低，可暂不添加。
