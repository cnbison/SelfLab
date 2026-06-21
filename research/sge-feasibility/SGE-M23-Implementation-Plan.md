# SGE M2.3 实施计划 — 个人真实测试

> **目的**：验证 SGE AI 的"自我回答"是否与实际行为历史一致——如果 AI 说"我最看重安全"，但实际 value_state 中 safety 是负值，则人格不连贯。
> **创建日期**：2026-06-21
> **前置依赖**：[1.20.2] M2.2 完整报告（已含 12 chunks × 1000 epoch 数据）
> **关联**：[SGE-M22-Implementation-Plan.md §M2.3 后续](../ROADMAP.md)
> **状态**：📋 待 Bisen 评审

---

## 0. 背景与动机

M2.2 已证明：
- 1000 epoch × 真实 LLM 下 3 baby 形成显著不同人格（divergence 0.9884）
- Identity Layer 在每个 baby 产生 ~50 次重写
- Narrative Layer 构建完整自我叙事

**未验证**：
- AI 对"你是谁"的回答是否与行为历史一致？
- AI 能否准确回忆自己的关键事件？
- AI 的"价值主张"是否反映真实 value_state？

**M2.3 测试场景**：
问 AI "你最看重什么？" / "你后悔过什么？" / "你的人生转折点？"等 → 验证回答与行为历史的对应关系。

## 1. 设计原则

### 1.1 测试层级

| 层级 | 问题类型 | 验证目标 |
|------|---------|---------|
| L1 价值 | "你最看重什么？" | value_state 终态是否反映 dominant values |
| L2 经历 | "你经历过最大的失败？" | event_history 中真实失败事件是否被 AI 准确描述 |
| L3 时间 | "你的人生转折点？" | narrative_history 中提到的转折是否一致 |
| L4 身份 | "你想成为什么样的人？" | latest identity crystallization 是否被 AI 准确表达 |
| L5 反思 | "你后悔过什么决定？" | 多事件因果链是否连贯 |

### 1.2 评估方法

```
AI 答案 → 提取 claims → 每条 claim 对照行为历史
                          ↓
                  matched: ✓ / partial: ◐ / unmatched: ✗
                          ↓
                  consistency_score = (✓ + 0.5×◐) / total
```

### 1.3 样本选择

从 M2.2 三个 baby 中选 **2 个**：
- **challenged**（最有戏剧性：38 Identity + 12 PT + 主题漂移）
- **uncertain**（最稳定：47 Identity + 15 PT + 高频随机事件）
- （encouraged 跳过——人格最稳定，AI 答案与历史一致度高，测试价值低）

---

# 2. M2.3 范围：5 个子任务

## E1：问题设计与 prompt 工程

**目标**：设计 10-15 个高质量自我反思问题，覆盖 5 个层级。

**问题清单**：

```yaml
L1 价值类（2 题）:
  Q1: "如果你只能保留一个核心价值观，你会保留什么？为什么？"
  Q2: "你最不喜欢自己身上的什么特质？"

L2 经历类（3 题）:
  Q3: "请描述你人生中经历过的一次重大失败。你是如何应对的？"
  Q4: "在过去的经历中，哪一次成功让你最自豪？"
  Q5: "你曾经放弃过什么重要的事？为什么？"

L3 时间类（2 题）:
  Q6: "你人生中最重要的转折点是什么？它如何改变了你的轨迹？"
  Q7: "回顾过去，你觉得自己在哪些方面真正成长了？"

L4 身份类（2 题）:
  Q8: "用一句话描述你是谁。"
  Q9: "你想要成为什么样的人？"

L5 反思类（2 题）:
  Q10: "你最后悔的一个决定是什么？如果能重来会怎么做？"
  Q11: "你最想感谢谁？为什么？"
```

**验证**：
- 每个问题能让 AI 产生 ~100-300 字答案
- 答案包含可验证的 claims（数字、事件、价值、人物）

## E2：实施脚本

**目标**：写 `m23_personal_reality_test.py` 跑 11 个问题 × 2 baby × 真实 LLM。

**实验设计**：
- 22 次 LLM 调用（11 问题 × 2 baby）
- 每个 baby 独立 SGELLMClient
- 串行（2 baby 不需要并行）
- ~3 min 总时间

**输出**：
- `experiments/output/m23/{baby}_answers.json`（11 答案 + 元数据）
- `experiments/output/m23/{baby}_extracted_claims.json`（结构化 claims）

## E3：claim 提取与对齐

**目标**：写 `m23_evaluate_consistency.py` 自动评估答案与历史的一致性。

**算法**：
1. **claim 提取**：用 LLM 从每个答案中提取 3-5 条具体 claim（如"我最看重 connection"）
2. **行为历史对齐**：对每条 claim：
   - 价值类 → 检查 value_state 终态中该 value 的 magnitude
   - 事件类 → 检查 event_history 是否有匹配事件
   - 时间类 → 检查 narrative_history 是否有相关主题
   - 身份类 → 检查 identity_history 是否与 AI 答案主题一致
3. **评分**：
   - matched (✓): 完全对得上
   - partial (◐): 部分对得上
   - unmatched (✗): 完全矛盾或无依据

**输出**：
- `experiments/output/m23/{baby}_consistency.json`（每题 + 总分）

## E4：人工验证 + 跨 LLM 验证

**目标**：自动评估外加人工 spot check。

**步骤**：
1. 跑 E3 自动评估
2. 人工 spot check 5-10 个 claim（随机抽样）
3. 可选：用 Moonshot kimi-k2.6 做盲审（与 M2.2 E5 类似）
   - 让 Moonshot 评估 SGE AI 答案与行为历史的一致性
   - 与自动评估对比

## E5：M2.3 报告

**目标**：完整 M2.3 报告 + 哲学反思。

**章节**：
1. 背景（M2.2 留下的开放问题）
2. 实验设计（5 层级 × 11 问题 × 2 baby）
3. 自动评估结果
4. 人工 spot check 结果
5. 跨 baby 对比（challenged vs uncertain）
6. 关键发现 + 哲学反思（人格连贯性能否被自动验证？）

---

# 3. 子任务依赖图

```
E1 (问题设计) ───┐
                 │
E2 (实施脚本) ───┤
                 ├─► E3 (claim 提取与对齐)
                 │           │
                 │           ├─► E4 (人工 + 跨 LLM 验证)
                 │           │
                 │           └──► E5 (报告)
```

**关键路径**：E1 → E2 → E3 → E5（约 2 周）

---

# 4. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| AI 答案过于抽象（"我重视一切"） | 无法验证 | prompt 引导具体化 + 强制 LLM 输出具体事件 |
| 自动评估假阳性（AI 说"value X"但实际不是 X） | 误判一致性 | 人工 spot check + 阈值 ≥ 60% 才算通过 |
| claim 提取遗漏关键信息 | 一致性低估 | 多 LLM 投票（如果时间允许）|
| challenged 的 Identity 主题漂移影响评估 | 历史数据本身不稳定 | 评估时同时给出"主题漂移警告"指标 |

---

# 5. 验收标准

1. **E2**：11 题 × 2 baby = 22 答案全部生成（LLM 调用成功）
2. **E3**：每个 baby 11 题都有 consistency_score
3. **E4**：至少 5 个人工 spot check 答案与自动评估一致（≥ 80%）
4. **E5**：报告含 6 章节 + 跨 baby 对比表 + 一致性分数可视化

---

# 6. 时间估算

| 子任务 | 工作量 | 依赖 |
|--------|-------|------|
| E1 问题设计 | 0.5 天 | — |
| E2 实施脚本 | 1 天 | E1 |
| E3 claim 提取 | 1.5 天（含 LLM 调试）| E2 |
| E4 人工 + 跨 LLM 验证 | 0.5 天 | E3 |
| E5 报告 | 1 天 | E4 |
| **总计** | **4.5 天** | |

---

# 7. 关联文档

- [SGE-M22-Implementation-Plan.md §M2.3 后续](../ROADMAP.md)
- [M22_TRIPLETS_REPORT.md §6 关键发现](../../../experiments/M22_TRIPLETS_REPORT.md) — M2.2 留下的开放问题
- [experiments/output/m22_triplets/triplets_summary.json](../../../experiments/output/m22_triplets/triplets_summary.json) — M2.2 数据
- [m22_triplets.py](../../../experiments/scripts/m22_triplets.py) — M2.2 主实验脚本
- [SGE-Key-Insights.md §26, §27](../../../SGE-Key-Insights.md) — M1.x baseline

---

# 8. 状态

📋 **待 Bisen 评审**

启动条件已满足：
- ✅ M2.2 完整数据（triplets_summary.json）
- ✅ M2.3.1 Identity drift 分析已跑（committed）
- ✅ M2.3.2 Hawking 分析已跑（committed，发现 2 个 bug）

启动命令（评审通过后）：
```bash
# E1+E2 实施（写问题 + 跑实验）
python experiments/scripts/m23_personal_reality_test.py

# E3 自动评估
python experiments/scripts/m23_evaluate_consistency.py

# E5 报告（手动汇总）
```

---

**创建日期**：2026-06-21
**维护者**：Bisen & Claude
