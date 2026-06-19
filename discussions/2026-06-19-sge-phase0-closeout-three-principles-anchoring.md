# 会话记录：SGE 三原则锚点 + Phase 0 收尾决策重打标

日期：2026-06-19

参与者：Bisen & Claude

---

## 讨论主题

M2.1 阶段 B 启动前的决策准备。原 [SGE-Phase0-Closeout.md](../research/sge-core/SGE-Phase0-Closeout.md) 列出了 6 个待决问题（drives 清单、Value scale、Phase Transition 阈值、Hawking gamma、Crystallize 阈值、LLM 选型），但 Bisen 在决策前希望先**重新锚定 SGE 项目的三个根本立场**，让所有候选方案在一个更清晰的判断框架下评估。

**讨论类型**：
- [x] 深度探讨（按 [CLAUDE.md §核心工作流](../../CLAUDE.md) 走完整闭环）
- [x] 关键设计决策（无论是否有洞察都存档）

## 背景与动机

**触发问题**：Bisen 在 [SGE-Phase0-Closeout.md](../research/sge-core/SGE-Phase0-Closeout.md) 决策点 1 的 4 个候选方案（A/B/C/D）中难以抉择。原文档的评估维度包括"哲学契合度"、"工程可实现性"、"实验可证伪性"、"借鉴一致性"，但 Bisen 觉得这套评估维度的**优先级顺序不对**——"借鉴一致性"权重过高，隐含着"尽量复用 AiBeing"的倾向，与 SGE 作为根项目的定位冲突。

**前置条件**：
- M2.1 阶段 A 已完成（2026-06-18，commit `1963854`）
- 阶段 B 启动前必须解决决策点 1（drives 清单）和决策点 2（Value scale）
- 其他 4 个决策点（3-6）属于工程参数/实验配置，可在阶段 B 实施中调整

**涉及文档**：
- [research/sge-core/SGE-Phase0-Closeout.md](../research/sge-core/SGE-Phase0-Closeout.md) — 决策文档主体
- [PRD.md §FR-4](../../PRD.md) — Value Layer 8 个价值维度（2 元价值 + 6 具体价值观）
- [ARCH.md](../../ARCH.md) — 整体架构
- [SGE-Key-Insights.md](../../SGE-Key-Insights.md) — 关键洞察集

## 核心观点（Bisen 提出的三原则）

### 原则 1：SGE 是研究项目，但也隐含产品底座目标

> "这是一个研究项目，同时也隐含着做出一个 Self Genesis Engine 产品的目标，以便于作为后续其他应用，诸如学生数字孪生、AI 教练、数字人等应用项目的认知架构的底座和基座。"

**含义**：SGE 的所有架构决策都应考虑"可复用性"——不是为单一应用优化，而是为**多场景、多领域**的认知架构底座设计。这意味着 drives/values 的设计应**通用、可配置、可扩展**。

### 原则 2：SGE 是根本，其他借鉴为 SGE 服务

> "SGE 项目是根本，其他的参考资料、借鉴，都是为 SGE 服务的，可以借鉴参考，但不能被带歪。"

**含义**：当 AiBeing 等外部参考的默认设计与 SGE 自身需要冲突时，**SGE 的需要优先**。"借鉴一致性"不是最高原则，"SGE 自我一致性"才是。

### 原则 3：逐步验证，逐步扩展

> "SGE 是逐步验证、逐步扩展的过程。"

**含义**：反对过早复杂化（3 层结构和过早简化（drives/values 合并）的极端方案；先做能区分假设的最简版本，然后基于实验结果扩展。

### Bisen 的关键表态

> "研究探索与具体应用两者是一体两面。"（对 Claude 提出的"用三条原则重新打标"分析框架的确认）

## 论证过程

### 一、三原则作为决策锚点

将三原则映射到决策评估：

| 原则 | 对决策评估的暗示 |
|------|---------------|
| **原则 1（产品底座）** | drives/values 设计要**通用、可配置、可扩展**——为多场景复用，不能为单一应用优化 |
| **原则 2（SGE 是根）** | 借鉴是为了让 SGE 更好；不要默认 AiBeing 的设计是对的，要敢于按 SGE 需要重构 |
| **原则 3（逐步验证）** | 反对过早复杂化（3 层）和过早简化（合并）；先做能区分假设的版本 |

**关键观察**：原决策文档的"借鉴一致性"维度权重过高（隐含着"尽量复用 AiBeing"），违反原则 2。新评估框架应该把"产品底座可复用性"和"SGE 自我一致性"放到最高优先级。

### 二、决策点 1（drives 清单）的重新评估

**问题**：SGE drives 应该用 AiBeing 原生 5 个（候选 A）？SGE 化 5 个（候选 B）？与 values 合并（候选 C）？分层 3 层结构（候选 D）？

**重新评估**：

- **候选 A 违反原则 2**：隐含"AiBeing 已经做对"——AiBeing 的 5 个 drives 是为**角色扮演场景**（Luna）设计的，`play` 和 `expression` 在 SGE 的"涌现"主题下意义不明
- **候选 C 违反原则 3**：过早简化。drives 与 values 是两个独立维度（产生行为动力 vs 指导应然选择），合并会丢失"本能需求张力"的工程机制
- **候选 D 违反原则 3**：过早复杂化。3 层结构（drives + values + meta-values）的实验调参成本过高，违背"先做最简能验证假设的版本"
- **候选 B 最契合**：SGE 化的 5 个 drives（`exploration, safety, creativity, connection, autonomy`），语义对齐 SGE 主题，保留独立 drives 维度，符合所有三条原则

**推荐**：候选 B

### 三、决策点 1 的更深层问题：维度可配置性

候选 A/B/C/D 都是**固定清单**——这与原则 1（产品底座）隐含冲突。作为产品底座，drives 维度应该是**可配置的 schema**，而非 hard-coded 列表：
- 学生数字孪生可能需要 `curiosity, mastery`
- AI 教练可能需要 `empathy, challenge`
- 数字人可能需要 `expression, recognition`

**建议**：阶段 B 用候选 B 的固定清单（满足"逐步验证"），但**在代码层让 drives 维度 schema 化**——为后续多场景复用留接口。

### 四、决策点 2（Value scale）的重新评估

**推荐 A（[-1, 1]）**：三条原则都支持：
- 原则 1（产品底座）：[-1, 1] 更接近人类价值观的真实分布
- 原则 2（SGE 是根）：开放的价值空间让"涌现"更自然
- 原则 3（逐步验证）：开放空间更利于发现"价值分化"现象（这正是 SGE 想要研究的）

[0, 1] 的人为约束会过早限制价值空间——而当前 Bisen 并没有充分理由要这个约束。

### 五、决策点 3-5（参数类）的重新评估

| 决策点 | 推荐 | 理由 |
|--------|------|------|
| 决策点 3（Phase Transition 阈值）| B（扫描 [1.0, 3.0]） | SGE 的挫败源是 values，机制与 AiBeing 不同，固定值风险大；扫描能给出实验支撑的默认值 |
| 决策点 4（Hawking gamma）| B（0.01/h，3 天半衰期） | 1000 epoch 实验窗口就是几天，0.001/h 几乎无衰减；先用 0.01/h 跑，看效果再调 |
| 决策点 5（Crystallize 阈值）| B（维度归一化 0.25/sqrt(N)） | 体现"产品基座"思维：阈值不随维度变，让架构可扩展。这是**反 AiBeing 默认值的**——但更可持续 |

**共同原则**：作为产品底座，**默认值要可解释、参数要可调**——而不是"用某个 magic number"。

### 六、决策点 6（LLM 选型）的重新评估

这条决策的**性质**和其他 5 条不同——它是**实验性决策**（影响实验质量），不是**架构决策**（影响 SGE 本身）。

- 阶段 B 的目标是**验证 SGE 机制**（drives/values 演化），不是验证 LLM 能力
- M1.x 已用 MiniMax-M3 跑通，阶段 B 沿用能减少混淆变量
- 等 SGE 机制验证通过后，M2.2 / M2.3 阶段再升级 LLM（或用双模型）

**推荐 A**（MiniMax-M3），M2.2/M2.3 阶段再升级。

### 七、决策文档漏问的两个元问题

读完决策文档，识别出两个**没问但应该问**的问题——它们由三条原则暗示：

#### 元问题 1：Value 维度是不是应该"领域适配"？

PRD §FR-4 定义的 6 values 是**给通用 SGE 用的**。但作为产品底座：
- 学生数字孪生可能需要 `mastery, growth` 而非 `justice`
- AI 教练需要 `empathy, challenge`
- 数字人需要 `authenticity, expressiveness`

当前文档没问："6 values 是固定清单，还是不同应用加载不同 value profile？"

**建议**：阶段 B 用固定 6 values 验证机制；架构上**为 value profile 留接口**。

#### 元问题 2：Meta-values（truth-seeking, freedom）真的"绝对不可修改"吗？

PRD §FR-4 把 2 个 meta-values 标为"❌ 不可修改（固定先验）"。但作为产品底座：
- AI 教练场景下，`freedom` 的绝对性 vs 保护用户免伤害的张力
- 数字人模拟历史人物时，`truth-seeking` vs 角色一致性的张力

**建议**：阶段 B 把 meta-values 当固定先验（满足"先验证机制"），但**留一个元配置层**允许产品级 override。

### 八、决策路径建议

```
1. 现在决定：决策点 1（候选 B + drives 维度 schema 化）、决策点 2（A：[-1, 1]）
2. 阶段 B 实施中决定：决策点 3-5（用推荐默认值 + 扫描）
3. 阶段 B 后期决定：决策点 6（M2.2/M2.3 再升级）
4. 留到 Phase 3（产品化）反思：元问题 1、2
```

## 核心结论

1. **三原则作为决策锚点**：研究+产品一体两面 / SGE 是根 / 逐步验证扩展——这三条原则应作为所有 SGE 决策的最高优先级评估维度。

2. **决策点 1 推荐候选 B**（SGE 化的 5 drives：`exploration, safety, creativity, connection, autonomy`），但代码层 drives 维度必须 schema 化、可配置。

3. **决策点 2 推荐 A**（[-1, 1]）—— 开放价值空间对齐 SGE 涌现主题。

4. **决策点 3-5 推荐扫描 + 推荐默认值**组合——体现"产品基座"思维：默认值要可解释、参数要可调。

5. **决策点 6 推荐 A**（MiniMax-M3）—— 阶段 B 是验证 SGE 机制，不是验证 LLM 能力。

6. **补充两个元问题**到决策文档：
   - 元问题 1：value 维度应该支持领域适配（value profile）
   - 元问题 2：meta-values 应该留产品级 override 接口

7. **决策路径**：1,2 现在决定 → 3,4,5 阶段 B 实施中决定 → 6 阶段 B 后期决定 → 元问题 1,2 留到 Phase 3。

## 产出文件

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| discussions/2026-06-19-sge-phase0-closeout-three-principles-anchoring.md | 新增 | 本文件 |
| SGE-Key-Insights.md | 新增 | 洞察 30：SGE 三原则锚点（研究+产品一体两面 / SGE 是根 / 逐步验证扩展） |
| research/sge-core/SGE-Phase0-Closeout.md | 修正 | 加入三原则决策框架；补充两个元问题（价值维度领域适配、meta-values override 接口）；更新决策点 1 的候选 B 推荐理由 |
| CHANGELOG.md | 更新 | 记录本次闭环产出 |

## 开放问题

| 问题 | 优先级 | 后续处理建议 |
|------|--------|------------|
| 决策点 1（drives 清单）— Bisen 实际选择 | 高 | 在 SGE-Phase0-Closeout.md §5 决策模板中填写 |
| 决策点 2（Value scale）— Bisen 实际选择 | 高 | 同上 |
| 元问题 1：value profile 的具体 schema 设计 | 中 | Phase 3（产品化）时启动 |
| 元问题 2：meta-values override 的边界条件 | 中 | Phase 3（产品化）时启动 |
| 决策点 3-5：阶段 B 实施中的实际扫描结果 | 高 | 阶段 B 实验报告 |

## 是否产生关键洞察

**是**

本次讨论明确提出了 SGE 项目的**三个根本立场锚点**——这是 project-level 洞察，影响所有未来决策。建议作为 **洞察 30** 添加到 SGE-Key-Insights.md，标题建议为"**SGE 三原则锚点：研究+产品一体两面 / SGE 是根 / 逐步验证扩展**"。

判断依据：
- [x] 明确了项目的哲学立场（SGE 是根项目，借鉴一致性不是最高原则）
- [x] 明确了技术方向（产品底座思维：通用、可配置、可扩展）
- [x] 建立了新的理论框架（三原则作为决策评估的最高优先级维度）

## 参考资料

- [SGE-Phase0-Closeout.md](../research/sge-core/SGE-Phase0-Closeout.md) — 决策文档主体
- [PRD.md §FR-4](../../PRD.md) — Value Layer 8 个价值维度
- [SGE-Key-Insights.md §洞察 29](../../SGE-Key-Insights.md) — REVISIT 0% 是 prompt bias（M1.4 验证）
- [SGE-Key-Insights.md §洞察 26](../../SGE-Key-Insights.md) — 6 维价值系统的非对称响应与 compassion 韧性
- [SGE-Key-Insights.md §洞察 15](../../SGE-Key-Insights.md) — 价值观向量非正交
- [CLAUDE.md §核心工作流](../../CLAUDE.md) — 探讨→洞察→修正闭环流程
- [SGE-Learning-from-AiBeing.md §3.2](../sge-learning/SGE-Learning-from-AiBeing.md) — drives 替换的初步想法
- [SGE-M21-AiBeing-Implementation-Mapping.md](../sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md) — 5 个待决问题

---

**记录者**：Bisen & Claude
**最后更新**：2026-06-19
