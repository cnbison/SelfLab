# SGE Phase 0 收尾决策文档

整理者：Bisen & Claude
日期：2026-06-18（初稿）→ 2026-06-19（加入三原则锚点 + 两个元问题）

> **本文件性质**：**Phase 0 → Phase 2 的桥梁文档**。把 M2.1 阶段 B 开始前必须决策的所有问题沉淀下来。
>
> **本文件不替 Bisen 做哲学决策**——每个待决问题都标注"待 Bisen 决定"。Claude 的角色是：**澄清概念、列出候选、暴露权衡**。
>
> **本文件是"思考的脚手架"**——迷茫时给一个具体的形状。每个决策点都给 2-3 个候选方案，附上**各自的哲学含义和工程影响**，让你能直接对比。
>
> **2026-06-19 重大更新**：Bisen 在决策准备阶段提出 SGE 三个根本立场锚点（详见 §0.5），用三原则重新评估了原 6 个决策点，并补充了 2 个原文档漏问的元问题（详见 §3）。原 §1-§5 文档结构保留，新增章节按需插入。
>
> **关联文档**：
> - [SGE-Key-Insights.md §洞察 30](../../SGE-Key-Insights.md) — 三原则锚点（2026-06-19）
> - [discussions/2026-06-19-sge-phase0-closeout-three-principles-anchoring.md](../../discussions/2026-06-19-sge-phase0-closeout-three-principles-anchoring.md) — 本次讨论完整记录
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

# 0.5 决策锚点：SGE 三原则（2026-06-19 新增）

> **本节是 2026-06-19 Bisen 提出的项目级锚点**——所有 §2-§3 的决策评估都应优先用这三原则。
>
> 完整讨论见 [discussions/2026-06-19-sge-phase0-closeout-three-principles-anchoring.md](../../discussions/2026-06-19-sge-phase0-closeout-three-principles-anchoring.md)；详细论证见 [SGE-Key-Insights.md §洞察 30](../../SGE-Key-Insights.md)。

## 三原则的精确表述

| 原则 | Bisen 原文 | 核心含义 |
|------|----------|---------|
| **原则 1：研究+产品一体两面** | "这是一个研究项目，同时也隐含着做出一个 Self Genesis Engine 产品的目标，以便于作为后续其他应用，诸如学生数字孪生、AI 教练、数字人等应用项目的认知架构的底座和基座。" | SGE 同时是研究纲领和**产品底座**——为多场景复用设计，不为单一应用优化 |
| **原则 2：SGE 是根** | "SGE 项目是根本，其他的参考资料、借鉴，都是为 SGE 服务的，可以借鉴参考，但不能被带歪。" | 当外部参考（AiBeing、金观涛哲学等）与 SGE 自身需要冲突时，**SGE 自我一致性优先** |
| **原则 3：逐步验证、逐步扩展** | "SGE 是逐步验证、逐步扩展的过程。" | 反对过早复杂化（3 层结构）和过早简化（drives/values 合并）；先做能区分假设的最简版本，然后基于实验结果扩展 |

**Bisen 关键表态**："研究探索与具体应用两者是一体两面。"

## 三原则作为决策评估维度

将三原则映射到决策评估（**替代原文档中权重过高的"借鉴一致性"**）：

| 原则 | 对决策评估的暗示 |
|------|---------------|
| 原则 1（产品底座） | drives/values 设计要**通用、可配置、可扩展** |
| 原则 2（SGE 是根） | 借鉴是为了让 SGE 更好；不要默认外部参考的设计是对的 |
| 原则 3（逐步验证） | 反对过早复杂化（3 层）和过早简化（合并） |

## 三原则对 6 决策点的重打标结论

| 决策点 | 三原则倾向 | 关键理由 |
|-------|----------|---------|
| 1. drives 清单 | **候选 B** | A 违反原则 2（照搬 AiBeing）；C/D 违反原则 3（过早简化/复杂化）；B 最契合 |
| 2. Value scale | **A（[-1, 1]）** | 开放价值空间对齐 SGE 涌现主题，符合所有三条原则 |
| 3. Phase Transition 阈值 | **B（扫描 [1.0, 3.0]）** | SGE 挫败源与 AiBeing 不同，固定值风险大 |
| 4. Hawking gamma | **B（0.01/h，3 天半衰期）** | 1000 epoch 实验窗口就是几天，0.001/h 几乎无衰减 |
| 5. Crystallize 阈值 | **B（维度归一化 0.25/sqrt(N)）** | 体现"产品基座"思维：阈值不随维度变，让架构可扩展 |
| 6. LLM 选型 | **A（MiniMax-M3）** | 阶段 B 目标是验证 SGE 机制，不是验证 LLM 能力；减少混淆变量 |

> **重要修正**：原 §2 决策点 1 的"借鉴一致性"评估维度与原则 2 冲突。**新评估应以"产品底座可复用性"和"SGE 自我一致性"为最高优先级**。

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

> **2026-06-19 更新**：用 §0.5 三原则重新评估。原"借鉴一致性"维度与原则 2 冲突，已替换为"产品底座可复用性"和"SGE 自我一致性"。

| 评估维度 | 候选 A | 候选 B | 候选 C | 候选 D |
|---------|-------|-------|-------|-------|
| **产品底座可复用性**（原则 1）| 中（角色化清单）| 中高（语义通用）| 中（语义抽象）| 中（多层但固定）|
| **SGE 自我一致性**（原则 2）| 低（照搬 AiBeing）| 高（按 SGE 主题重构）| 高（敢于质疑）| 中（自创结构）|
| **逐步验证可行性**（原则 3）| 高 | 高 | 中（合并后难拆分）| 低（3 层调参成本高）|
| 哲学契合度（SGE 涌现主题）| 中 | 中高 | 中 | 高 |
| 工程可实现性 | 极高 | 高 | 高 | 中（需新设计）|
| 实验可证伪性 | 高（与 AiBeing 对照）| 中 | 中 | 中（变量多）|
| 借鉴一致性（**次要**）| 高 | 中 | 低 | 低 |
| 实施工作量 | 1 周 | 1-2 周 | 2 周 | 3-4 周 |

### 决策建议（基于三原则）

- **首选候选 B**（SGE 化的 5 drives：`exploration, safety, creativity, connection, autonomy`）
- **代码层要求**：drives 维度必须 **schema 化、可配置**（即使阶段 B 用固定清单验证，架构层也要为后续多场景 profile 化留接口）
- **不推荐候选 A**：违反原则 2（"借鉴一致性"不是最高原则）
- **不推荐候选 C/D**：违反原则 3（过早简化/复杂化）

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

# 2.5 两个被遗漏的元问题（2026-06-19 新增）

> **本节是 §0.5 三原则揭示的两个原文档漏问的问题**——它们影响 SGE 作为"产品底座"的长期可演化性。
>
> 完整讨论见 [discussions/2026-06-19-sge-phase0-closeout-three-principles-anchoring.md](../../discussions/2026-06-19-sge-phase0-closeout-three-principles-anchoring.md)。
>
> **当前建议**：阶段 B 不直接决策（满足"逐步验证"），但在**架构层留接口**；具体设计留到 Phase 3（产品化阶段）。

## 元问题 1：Value 维度是不是应该"领域适配"？

**问题**：PRD §FR-4 定义的 6 values（safety / creativity / connection / autonomy / justice / compassion）是给通用 SGE 用的。但作为产品底座：
- 学生数字孪生可能需要 `mastery, growth` 而非 `justice`
- AI 教练需要 `empathy, challenge`
- 数字人需要 `authenticity, expressiveness`

**当前文档没问**：6 values 是**固定清单**，还是**不同应用加载不同 value profile**？

### 候选
- **A：固定清单**（6 values 通用所有应用）
  - 优点：研究阶段简单，PRD 已定义
  - 缺点：违反原则 1（产品底座可复用性）；不同应用可能需要不同 value 空间
- **B：Value profile 化**（应用层加载不同 value 维度）
  - 优点：产品底座可扩展；学生用 `mastery`，教练用 `empathy`，数字人用 `authenticity`
  - 缺点：工程复杂度高；需要定义 profile 加载机制
- **C：核心 + 扩展**（核心 6 values 必有 + 应用可扩展）
  - 优点：兼顾通用性和可扩展性
  - 缺点：需要明确"核心"和"扩展"的边界

**建议**：阶段 B 用候选 A（满足"逐步验证"）；架构层**为 value profile 留接口**；具体设计留到 Phase 3。

## 元问题 2：Meta-values 是不是"绝对不可修改"？

**问题**：PRD §FR-4 把 2 个 meta-values（`truth-seeking`, `freedom`）标为"❌ 不可修改（固定先验）"。但作为产品底座：
- AI 教练场景下，`freedom` 的绝对性 vs 保护用户免伤害的张力
- 数字人模拟历史人物时，`truth-seeking` vs 角色一致性的张力

**当前文档没问**：meta-values 是**绝对哲学立场**（不可修改），还是**可产品级 override**？

### 候选
- **A：绝对不可修改**（PRD 当前定义）
  - 优点：哲学立场清晰；保护 SGE 的核心价值
  - 缺点：限制产品灵活性；可能让 SGE 无法部署到"需要保护用户"的场景
- **B：可产品级 override**（产品层可覆盖）
  - 优点：产品底座灵活；可适配不同应用场景
  - 缺点：哲学立场被稀释；需明确 override 的边界条件
- **C：核心架构不可修改 + 产品层软调整**（如 freedom 在 AI 教练场景下"软约束"）
  - 优点：兼顾哲学立场和产品灵活性
  - 缺点：需设计"软约束"机制（哲学 + 工程难度高）

**建议**：阶段 B 用候选 A（满足"先验证机制"）；架构层**为元配置层留接口**；具体边界条件留到 Phase 3 哲学讨论。

## 两个元问题的共同原则

- **哲学立场不能锁死工程灵活性**（违反原则 1）
- **不能为多场景兼容性牺牲哲学清晰度**（违反原则 2）
- **当前不决策，架构留接口**（符合原则 3）

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

# 6. 一句话总结（2026-06-19 更新）

> **Phase 0 收尾的核心**是用 **§0.5 三原则**（研究+产品一体两面 / SGE 是根 / 逐步验证扩展）作为决策锚点，回答 "**SGE 的价值结构是单层（仅 values）、双层（drives + values）、还是三层（drives + values + meta-values）**"——这是哲学决策，工程只是承接。同时要**为 Phase 3 产品化预留维度可配置性和元配置层接口**（元问题 1、2）。M2.1 阶段 B 需要这个答案才能开始。

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
| 2026-06-19 | 0.2 | 加入 §0.5 三原则决策锚点（Bisen 提出），重打标 6 决策点；新增 §2.5 两个元问题（value 维度领域适配 + meta-values override） |

---

**创建日期**：2026-06-18
**最后更新**：2026-06-19
**维护者**：Bisen & Claude
**状态**：⏳ 等待 Bisen 填写 §5 决策模板
