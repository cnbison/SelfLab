# SGE Phase 0 收尾决策文档

整理者：Bisen & Claude（草稿）
日期：2026-06-18

> **本文件性质**：**Phase 0 → Phase 2 的桥梁文档**。把 M2.1 阶段 B 开始前必须决策的所有问题沉淀下来。
>
> **本文件不替 Bisen 做哲学决策**——每个待决问题都标注"待 Bisen 决定"。Claude 的角色是：**澄清概念、列出候选、暴露权衡**。
>
> **本文件是"思考的脚手架"**——迷茫时给一个具体的形状。每个决策点都给 2-3 个候选方案，附上**各自的哲学含义和工程影响**，让你能直接对比。
>
> **关联文档**：
> - [SGE-Key-Insights.md](../../SGE-Key-Insights.md) — 关键洞察集
> - [PRD.md §FR-4](../../PRD.md) — Value Layer 功能需求（含元价值 + 6 个具体价值观的表格）
> - [SGE-Learning-from-AiBeing.md §3.2](../sge-learning/SGE-Learning-from-AiBeing.md) — drives 替换的初步想法
> - [SGE-M21-AiBeing-Implementation-Mapping.md §六](../sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md) — 5 个开放问题

---

# 0. 为什么要做 Phase 0 收尾

**现状盘点（2026-06-18）**：

| 阶段 | 状态 |
|------|------|
| Phase 0（理论奠基） | ✅ 已完成（ROADMAP.md）|
| M1.1 冒烟测试 | ✅ 2026-06-17 |
| M1.2 三胞胎分化 | ✅ 2026-06-17 |
| M1.3 反合理化 | ✅ 2026-06-17 |
| M1.4 REVISIT 专项 | ✅ 2026-06-17 |
| M2.1 阶段 A（基线） | ✅ 2026-06-18（commit `1963854`）|
| **M2.1 阶段 B（SGE 化改造）** | ⚠️ **阻塞：以下问题未决** |

**M2.1 阶段 B 的核心任务**（来自 [SGE-M21-AiBeing-Implementation-Mapping.md §五](../sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md#五m21-实施步骤建议)）：

- 把 AiBeing 的 5 个 drives 替换为 SGE 的 N 个 drives
- 把 Relationship EMA 改造为 Value EMA
- 接入真实 LLM（Critic + Actor）
- 跑多 seed × 长 epoch 验证

**为什么这些决策必须在阶段 B 之前做**：
- 没有 SGE drives 清单 → 无法替换 → 阶段 B 卡死
- 没有 drives vs values 概念区分 → Value EMA 改造无法下手
- 没有 Value scale 决策 → EMA 的 clip 范围无法定

---

# 1. 概念澄清：Drives vs Values

> **这是本文件最核心的章节**——把"drives"和"values"的概念差异讲清楚，避免决策时混为一谈。

## 1.1 Drives（本能需求）

**定义**：驱动行为产生的**内部需求张力**。Drives 回答的是 **"AI 想要什么"** 的问题。

**特征**：
- 来源：与生俱来的（或初始化的）需求结构
- 功能：产生行为的"动力"
- 度量：通常有 0~1 或 0~5 的强度，**可累积（饥饿）**、可衰减（满足）
- 例子：连接渴望、新鲜渴望、安全需求

**AiBeing 的 5 个 drives**（来自 `engine/genome/genome_engine.py:25`）：
```
connection, novelty, expression, safety, play
```

**AiBeing drives 的工程机制**：
- `frustration[drive]` 累积（"渴望"程度）
- `time_metabolism` 冷却（长时间不互动会"忘记"旧挫败）
- `time_metabolism` 饥饿（长时间不互动会"渴望"）
- `apply_llm_delta` 应用 Critic 判断的需求变化

## 1.2 Values（道德/伦理价值）

**定义**：AI 用于**应然判断**（"应该怎么做"）的**价值标尺**。Values 回答的是 **"AI 认为什么是对的"** 的问题。

**特征**：
- 来源：从经历中涌现（不预设）
- 功能：指导"应然选择"
- 度量：通常 [-1, 1] 或 [0, 1] 的连续值，**渐进演化**（EMA）
- 例子：safety（安全倾向）、justice（正义感）、compassion（同理心）

**PRD §FR-4 定义的 8 个 value 维度**（2 元价值 + 6 具体价值观）：

| 类型 | 名称 | 数量 | 是否可演化 |
|------|------|------|----------|
| **元价值** | truth-seeking（真实）/ freedom（自由）| 2 | ❌ 不可修改（固定先验）|
| **具体价值观** | safety / creativity / connection / autonomy / justice / compassion | 6 | ✅ EMA 演化 |

## 1.3 关键区分（决策的核心）

| 维度 | Drives | Values |
|------|--------|--------|
| **回答的问题** | "我想要什么" | "什么是对的" |
| **功能** | 产生行为动力 | 指导应然选择 |
| **来源** | 初始化/本能 | 从经历涌现 |
| **可累积吗** | ✅ 是（frustration 累积）| ❌ 否（连续 EMA 演化）|
| **可被反思吗** | ❌ 否（drives 是"前反思"的）| ✅ 是（Value 是反思的对象）|
| **哲学对应** | 怀特海"动在"的**主观形式** | 怀特海"永恒客体"的**形式空间** |
| **例子** | "我想要连接" | "我重视 safety" |

## 1.4 误诊的根源

之前的报告写"5 个 drives vs 6 个价值观冲突"——这是**把 drives 当成了 values**。但实际上：
- "drives 替换"是 M2.1 阶段 B 的工程任务（替换 AiBeing 的本能需求）
- "values 涌现"是 FR-4 的功能要求（不预设，从经历涌现）

它们是 SGE 中**两个独立的维度**。

但下面有一个**更深的问题**需要 Bisen 决策（见 §2 决策点 1）：
- SGE 是否需要 **drives 这个独立维度**？还是 drives 和 values 可以合并？

---

# 2. 6 个待决问题

> 每个问题都标注"待 Bisen 决定" + 候选方案 + 各自的哲学/工程影响。

## 决策点 1：SGE drives 维度清单 ⚠️ **核心阻塞**

**问题**：SGE 需要几个 drives？什么名字？什么语义角色？

**约束**：
- drives 的工程功能（产生行为动力、frustration 累积/衰减）已经在 M2.1 阶段 A 跑通
- drives 必须能与 Critic / Actor / Hebbian 联动
- drives 的选择应与 SGE 的哲学立场一致

### 候选 A：保留 AiBeing 原生 5 个 drives（**最小改动**）

```
DRIVES = ['connection', 'novelty', 'expression', 'safety', 'play']
```

- **优点**：阶段 B 改动最小；已经过 AiBeing 验证；工程风险低
- **缺点**：语义偏向"角色扮演"（Luna 那种）；与 SGE 的"涌现"哲学不太契合（drives 仍然是预设的）
- **哲学契合度**：中（drives 是"本能"而非"涌现"，但这是 AiBeing 设计哲学）

### 候选 B：SGE 化的 5 个 drives（**语义重构**）

来自 [SGE-Learning-from-AiBeing.md §3.2](../sge-learning/SGE-Learning-from-AiBeing.md) 的初步想法：

```
DRIVES = ['exploration', 'safety', 'creativity', 'connection', 'autonomy']
```

- 翻译对照：
  - `novelty` → `exploration`（探索 vs 新鲜：探索有"主动"含义）
  - `play` → 去掉（无对应）
  - `expression` → `creativity`（创造 vs 表达：创造有"产生"含义）
  - 其余保留语义

- **优点**：语义更贴近 SGE 的"涌现"主题；与 6 个 values 有部分重叠（但不完全）
- **缺点**：仍依赖外部"预设"；候选 A → B 是"换皮"还是"重构"需要明确
- **哲学契合度**：中高

### 候选 C：与 values 合并（**最激进的简化**）

```
DRIVES = []  # 没有独立 drives
VALUES = ['safety', 'creativity', 'connection', 'autonomy', 'justice', 'compassion']
# （保留 PRD §FR-4 的 6 个 values）
```

- 含义：把"产生行为动力"和"指导应然选择"合并
- **优点**：概念最简；避免双轨复杂性；与 PRD §FR-4 一致
- **缺点**：丢失了"本能需求张力"的工程机制（frustration 累积/衰减）；与 AiBeing 的成熟机制不一致
- **哲学契合度**：中（简化但可能丢东西）

### 候选 D：分层 drives + values（**最丰富的方案**）

```
# 基础本能（drives）—— 5 个
DRIVES = ['connection', 'curiosity', 'agency', 'safety', 'recognition']
# 应然价值（values）—— 6 个
VALUES = ['safety', 'creativity', 'connection', 'autonomy', 'justice', 'compassion']
# 元价值（meta-values）—— 2 个
META_VALUES = ['truth_seeking', 'freedom']
```

- 含义：3 层价值结构（本能 + 应然 + 元）
- **优点**：与人类心理学的"本能/道德/形而上"分层一致；可解释性强
- **缺点**：工程复杂度高（EMA + EMA + 不可修改的 3 层）；需要更多实验调参
- **哲学契合度**：高（最丰富的设计）

### 决策框架（供 Bisen 参考）

| 评估维度 | 候选 A | 候选 B | 候选 C | 候选 D |
|---------|-------|-------|-------|-------|
| 哲学契合度（SGE 涌现主题）| 中 | 中高 | 中 | 高 |
| 工程可实现性 | 极高 | 高 | 高 | 中（需新设计）|
| 实验可证伪性 | 高（与 AiBeing 对照）| 中 | 中 | 中（变量多）|
| 借鉴一致性 | 高（直接复用）| 中 | 低（合并）| 低（多轨）|
| 实施工作量 | 1 周 | 1-2 周 | 2 周 | 3-4 周 |

**Bisen 待填写的决策**：

```
□ 候选 A
□ 候选 B
□ 候选 C
□ 候选 D
□ 其他方案：________________________
□ 暂不决策（推迟到 M2.1 阶段 B 跑多版本对比）

理由（1-2 句话）：
_________________________________________________
```

---

## 决策点 2：Value scale 范围 ⚠️ **次要阻塞**

**问题**：Value 用 [-1, 1] 还是 [0, 1]？

- [-1, 1] 允许"反价值"（如 safety=-0.8 表示"主动追求危险"）
- [0, 1] 不允许"反价值"（safety=0 表示"对安全漠不关心"）

### 候选
- **A：[-1, 1]** — 允许反价值涌现（更激进，更接近人类价值观的多样性）
- **B：[0, 1]** — 不允许反价值（更安全，但限制了价值空间）
- **C：[0, 1] + 极性反转**（如 safety=0.8 vs danger=0.8 两种表达）— 工程复杂

**默认推荐**：A（[-1, 1]）—— 与 SGE 的"涌现"哲学一致（价值空间应该是开放的双极空间）

**Bisen 待填写的决策**：

```
□ A: [-1, 1]
□ B: [0, 1]
□ C: 其他：________________________

理由：
_________________________________________________
```

---

## 决策点 3：Phase Transition 阈值

**问题**：挫败感累积超过多少时触发"相变"（叙事断裂 / 价值观重构）？

- AiBeing 默认：2.0（来自 `genome_engine.py:204`）
- SGE 的挫败感来源不同（values 而非 drives），阈值可能需要调整

### 候选
- **A：保持 2.0** — 沿用 AiBeing，阶段 B 不调
- **B：扫描 [1.0, 3.0]** — 阶段 B 实验中扫描
- **C：动态阈值** — 根据 values 的"韧性"维度（compassion 之类）调整

**Bisen 待填写的决策**：

```
□ A: 2.0
□ B: 扫描区间 [1.0, 3.0]
□ C: 动态
□ 其他：________________________
```

---

## 决策点 4：Hawking gamma（记忆衰减率）

**问题**：AI 婴儿的"记忆"应该多快淡化？

- AiBeing 默认：0.001/h（半衰期 ~29 天）—— 来自 `style_memory.py:29`
- SGE 的实验是 1000 Epoch（几天/几周）—— 29 天半衰期可能过长

### 候选
- **A：保持 0.001/h** — 阶段 B 不调
- **B：调高到 0.01/h**（半衰期 ~3 天）— 适合 1000 epoch 实验
- **C：扫描 [0.001, 0.1]** — 阶段 B 实验中扫描

**Bisen 待填写的决策**：

```
□ A: 0.001/h
□ B: 0.01/h
□ C: 扫描
□ 其他：________________________
```

---

## 决策点 5：Crystallize 距离阈值

**问题**：多近的两个事件算"重复"（合并增厚 vs 创建新记忆）？

- AiBeing 默认：0.25（8D context 空间 L2 距离）—— 来自 `style_memory.py:292`
- SGE 的 context 维度可能变化（12D → 21D 事件感知向量）—— 阈值需重新校准

### 候选
- **A：保持 0.25**（如果 SGE 沿用 8D context 子集）
- **B：维度归一化**（除以 sqrt(N) 让阈值不随维度变化）
- **C：阶段 B 实验中扫描 [0.15, 0.35]**

**Bisen 待填写的决策**：

```
□ A: 0.25
□ B: 维度归一化（0.25 / sqrt(N)）
□ C: 扫描
□ 其他：________________________
```

---

## 决策点 6：M2.1 阶段 B 的 LLM 接入策略

**问题**：阶段 B 要用真实 LLM 跑 Critic + Actor。模型选什么？

### 候选
- **A：MiniMax-M3**（与 M1.x 一致）—— 成本低、已验证
- **B：Sonnet / GPT-4o**（ROADMAP §M2.1 推荐）—— 质量更高
- **C：双模型**（Critic 用小模型，Actor 用大模型）—— 与 SGE-Technology-Stack-Overview.md §二 一致

**Bisen 待填写的决策**：

```
□ A: MiniMax-M3
□ B: Sonnet / GPT-4o
□ C: 双模型（Critic 小 + Actor 大）
□ 其他：________________________
```

---

# 3. 决策的相互依赖

```
决策点 1 (drives 清单) ←── 决策点 6 (LLM 选型)
        ↓
决策点 2 (Value scale) ←── 决策点 3 (Phase Transition 阈值)
        ↓
决策点 4 (Hawking gamma) ←── 决策点 5 (Crystallize 阈值)
```

- **决策点 1 是核心**——其他决策都依赖它（drives 维度决定 EMA 维度、决定 input 维度、决定 Critic 输出维度）
- **决策点 2 和 3 强相关**——Value scale 决定 frustration 累积的边界
- **决策点 4 和 5 强相关**——都是记忆相关的衰减参数
- **决策点 6 独立**——LLM 选型可独立决定

**建议决策顺序**：1 → 2 → 3 → 4 → 5 → 6

---

# 4. 决策的时间窗口

| 时间窗 | 决策点 | 备注 |
|--------|-------|------|
| **M2.1 阶段 B 启动前必须** | 1, 2 | drives 清单和 Value scale 是工程基础 |
| **M2.1 阶段 B 实施中可调** | 3, 4, 5 | 参数类，实验中扫描即可 |
| **M2.1 阶段 B 实施中可调** | 6 | LLM 选型可换，但成本会变 |

---

# 5. 决策模板（Bisen 填写）

```markdown
## 我的决策

### 决策点 1：SGE drives 维度清单
选择：____
理由：____

### 决策点 2：Value scale 范围
选择：____
理由：____

### 决策点 3：Phase Transition 阈值
选择：____
理由：____

### 决策点 4：Hawking gamma
选择：____
理由：____

### 决策点 5：Crystallize 距离阈值
选择：____
理由：____

### 决策点 6：M2.1 阶段 B LLM 选型
选择：____
理由：____
```

---

# 6. 一句话总结

> **Phase 0 收尾的核心**是回答 "**SGE 的价值结构是单层（仅 values）、双层（drives + values）、还是三层（drives + values + meta-values）**"——这是哲学决策，工程只是承接。M2.1 阶段 B 需要这个答案才能开始。

---

# 附录 A：相关文档索引

- [SGE-Key-Insights.md §洞察 15](../../SGE-Key-Insights.md) — 价值观向量空间不是正交的（6 个 values 的张力问题）
- [SGE-Key-Insights.md §洞察 26](../../SGE-Key-Insights.md) — 6 维度对相同事件流呈现不同响应（compassion 韧性）
- [SGE-Key-Insights.md §洞察 24](../../SGE-Key-Insights.md) — 怀特海过程哲学（动在/合生/永恒客体）
- [PRD.md §FR-4](../../PRD.md) — Value Layer 8 个价值维度的权威定义
- [ARCH.md §1.3](../../ARCH.md) — "显性-暗知识"双轨（Value 是显性，Hebbian 是暗）
- [SGE-Learning-from-AiBeing.md §3.2](../sge-learning/SGE-Learning-from-AiBeing.md) — drives 替换的初步想法
- [SGE-M21-AiBeing-Implementation-Mapping.md §六](../sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md) — 5 个待决问题（Hawking gamma、Phase Transition 阈值等）
- [SGE-Technology-Stack-Overview.md §二](../sge-feasibility/SGE-Technology-Stack-Overview.md) — LLM 选型

---

# 附录 B：版本与变更

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-18 | 0.1 | 初稿（Claude 起草，drives vs values 概念澄清 + 6 决策点） |

---

**创建日期**：2026-06-18
**维护者**：Bisen & Claude
**状态**：⏳ 等待 Bisen 填写 §5 决策模板
