# SGE M2.1 — AiBeing 实施映射

整理者：Bisen & Claude

日期：2026-06-18

> **本文件性质**：**M2.1 实施前的工程映射文档**。把 `SGE-Technology-Stack-Overview.md` §一 列出的 8 个可复用机制 + 1 个架构，逐项落到源码位置、关键公式、SGE 改造点和验证方式。
>
> **本文件不复制代码**——所有源码都在 `~/project/AiBeing/`（Bisen 本地管理），SelfLab 仓库内只保留"指针 + 改造契约"。这与 CLAUDE.md "实验代码约定" 一致。
>
> **SSOT 关系**：
> - [SGE-Technology-Stack-Overview.md §一](./SGE-Technology-Stack-Overview.md#一来自-aibeinggenome-v10-的-8-个可复用机制) — 调研层（已存在）
> - [SGE-Learning-from-AiBeing.md](./SGE-Learning-from-AiBeing.md) — 借鉴分析（已存在）
> - **本文件** — 实施层（新建）：源码位置 + 公式 + 改造契约 + 验证方式

---

# 一、总览：借鉴-改造矩阵

下表是 M2.1 实施时的"借鉴-改造"边界。**复用程度**列的语义：

- **直接复用**：照搬公式/算法，只改调用入口和数据结构
- **低改造**：复用核心公式，但需要改输入维度或参数语义
- **中改造**：复用核心思想（如 KNN、EMA、Hebbian），但 SGE 场景需要重新设计数据结构
- **新增**：AiBeing 没有，SGE 需要从零构建

| # | 机制 | AiBeing 源码 | 复用程度 | SGE 对应模块 | 实施阶段 |
|---|------|-------------|---------|-------------|---------|
| 1 | Critic 感知 | `engine/genome/critic.py` | 低改造 | Event → 结构化向量 | M2.1 |
| 2 | Time Metabolism | `engine/genome/drive_metabolism.py` | 直接复用 | Memory/Reflection 时间层 | M2.1 |
| 3 | Relationship EMA | `agent/evermemos_mixin.py` | 低改造 | Value Layer（价值观演化） | M2.1 |
| 4 | Hebbian Learning | `engine/genome/genome_engine.py` (Agent.learn) | 直接复用（核心） | Value Layer（行为偏好） | M2.1 |
| 5 | Phase Transition | `engine/genome/genome_engine.py` (Agent.learn) | 低改造（改阈值/维度） | Reflection/Narrative 相变 | M2.1 |
| 6 | Crystallization | `engine/genome/style_memory.py` | 低改造（改评分） | Memory 筛选门 | M2.1 |
| 7 | KNN + Hawking 辐射 | `engine/genome/style_memory.py` | 直接复用 | Memory 检索 | M2.1 |
| 8 | Thermodynamic Noise | `engine/genome/drive_metabolism.py` | 直接复用 | Value/Actor 行为噪声 | M2.1 |
| 9 | 双 LLM 架构 | `agent/chat_agent.py`（架构） | 直接复用 | Critic + Actor 编排 | M2.1 |
| — | Value EMA Tracker | — | **新增** | Value Layer（多维价值观） | M2.1 |
| — | Value Conflict Generator | — | **新增** | Event Generator | M2.1 |
| — | Identity Crystallizer | — | **新增** | Identity Layer | M2.2 |
| — | Narrative Builder | — | **新增** | Narrative Layer | M2.1（MVP）/M2.2（完整） |
| — | Narrative Consistency Checker | — | **新增** | Reflection Layer | M2.2+ |

**关键含义**：

- M2.1 结束时，**9 个借鉴机制**全部应该有可运行的实验代码（一次性，验证后归档）
- 4 个**新增组件**中，Value EMA Tracker 和 Value Conflict Generator 是 M2.1 范围；Identity Crystallizer 推到 M2.2；Narrative Builder MVP 放 M2.1，完整版放 M2.2

---

# 二、逐机制映射

> 每节格式：**源码位置 → 关键公式/算法 → SGE 改造契约 → 验证方式**。
>
> "改造契约"定义 SGE 版本与 AiBeing 版本的差异边界——M2.1 实施时严格按照契约编写。

## 2.1 Critic 感知 → SGE Event 感知层

**AiBeing 源码**：`engine/genome/critic.py:76-190`（`critic_sense()` 函数）

**当前实现的输入/输出**：

```
输入：用户消息文本 + 当前 frustration 状态 + 用户画像 + 历史叙事 + persona 提示
输出：
  - context (8D): user_emotion, topic_intimacy, conversation_depth, user_engagement,
                  conflict_level, novelty_level, user_vulnerability, time_of_day
  - frustration_delta (5D): connection, novelty, expression, safety, play
  - relationship_delta (3D): relationship_delta, trust_delta, emotional_valence
  - drive_satisfaction (5D): 0~0.3 范围
合计：21 维结构化向量
```

**关键工程细节**：

- temperature=0.2（稳定结构化输出）
- LLM 输出后用正则清理 `<think>...</think>`（Qwen3 兼容）
- JSON 解析三层容错：直接 `json.loads` → 大括号配对提取 → 重试（带"请只输出 JSON"指令）
- 失败 fallback：返回 0.5 中性 context + 0.0 delta（不阻塞认知循环）

**SGE 改造契约**：

| 维度 | AiBeing | SGE |
|------|---------|-----|
| **输入文本** | 用户消息 | 模拟人生事件（Event Generator 产出） |
| **感知对象** | 用户 → 角色 | 事件 → AI 婴儿的内心状态 |
| **context (8D)** | 复用 prompt 结构，键名可改 | "事件情境向量"：event_severity, intimacy, depth, surprise, conflict, novelty, vulnerability, time_of_day |
| **frustration_delta (5D)** | 5 个 AiBeing drives | **改维度** → 5 个 SGE drives（探索/安全/创造/联结/自主）。**待 Phase 0 终稿确认** |
| **relationship_delta (3D)** | 适用（人际关系） | **不适用**——SGE 的 AI 婴儿不与"用户"建立关系，relationship 维度应替换为 **value_conflict_vector**（哪些价值观在事件中冲突） |
| **drive_satisfaction (5D)** | 复用键名 | 复用——SGE 同样有 drives 满足问题 |
| **prompt 中 user_profile/episode** | EverMemOS 注入 | **不直接复用**——SGE 的"历史叙事"由 Narrative Layer 注入 |
| **temperature** | 0.2 | 保持 0.2 |

**关键代码指针**：

- Prompt 结构：`_FALLBACK_CRITIC` 字符串（critic.py:22-62）——**结构可复用，键名需改**
- JSON 容错：`critic.py:144-158`（大括号配对提取）——**直接复用**
- 重试逻辑：`critic.py:196-235`——**直接复用**

**验证方式**：

- 单元测试：构造 10 个不同事件，验证 Critic 输出 21 维结构化向量
- 一致性测试：相同事件输入 10 次，输出方差 < 阈值（temperature=0.2 应有高一致性）
- 容错测试：故意让 LLM 输出不合法 JSON，验证三层容错都能恢复

---

## 2.2 Time Metabolism → SGE 时间动力学

**AiBeing 源码**：`engine/genome/drive_metabolism.py:57-87`（`time_metabolism()` 方法）

**核心公式**：

```python
# 冷却：挫败感指数衰减
delta_hours = (now - last_tick) / 3600
decay_factor = exp(-decay_lambda * delta_hours)
for d in DRIVES:
    frustration[d] *= decay_factor

# 饥饿：联结/新鲜感线性累积
frustration['connection'] += connection_hunger_k * delta_hours
frustration['novelty'] += novelty_hunger_k * delta_hours

# Clamp 到 [0, 5]
```

**默认参数**（`drive_metabolism.py:24-28`）：

| 参数 | 默认值 | 含义 | SGE 是否调整 |
|------|--------|------|------------|
| `frustration_decay_lambda` | 0.08/h | 挫败感半衰期 ~8.7h | 保留（事件对价值观的"自然淡化"是普适机制） |
| `connection_hunger_k` | 0.15/h | 联结渴望累积 | **改名/重组**为 SGE 维度的渴望累积 |
| `novelty_hunger_k` | 0.05/h | 新鲜感渴望累积 | 同上 |
| `temp_coeff` | 0.12 | 温度斜率 | 保留 |
| `temp_floor` | 0.03 | 温度下限 | 保留 |

**SGE 改造契约**：

- **直接复用核心公式**——冷却 + 饥饿机制是普适的
- **改维度名**：`connection/novelty` → SGE 维度的对应 drives（探索/联结/...）
- **改 scale**：AiBeing 范围 [0, 5]，SGE 价值观用 [-1, 1] 范围（与 EMA 输出一致）
- **新增维度**：价值观（values）也需要时间冷却——创伤事件的影响应该随时间淡化

**关键代码指针**：

- `time_metabolism()` 方法（drive_metabolism.py:57-87）——**直接复用算法**
- `apply_llm_delta()` 方法（drive_metabolism.py:89-107）——**直接复用结构**
- 参数可覆盖（`engine_params`）——**直接复用机制**

**验证方式**：

- 单调性测试：注入 delta=+1.0 后调用 1 次 time_metabolism，验证 frustration 减少
- 边界测试：长时间（>100h）不调用，验证不出现负值或数值爆炸
- 多 seed 测试：3 个不同 engine_params 集合，验证参数生效

---

## 2.3 Relationship EMA → SGE Value Layer 演化

**AiBeing 源码**：`agent/evermemos_mixin.py:52-106`（`_apply_relationship_ema()` 方法）

**核心公式**：

```python
# 1. Posterior = clip(prior + LLM_delta)
posterior[k] = clip(prior[k] + delta_map[k], lo, hi)

# 2. Depth-modulated alpha
alpha = clip(0.15 + 0.5 * conversation_depth, 0.15, 0.65)

# 3. EMA smooth
ema[k] = alpha * posterior[k] + (1 - alpha) * prev_ema[k]
```

**SGE 改造契约**（**这是 SGE Value Layer 的核心机制**）：

| 元素 | AiBeing | SGE |
|------|---------|-----|
| **state 变量** | 4D 关系向量（depth, trust, valence, foresight） | **N 维价值观向量**（如诚实、自由、仁慈、勇气等） |
| **prior** | EverMemOS 注入的历史关系 | **SGE 初始价值观**（从元价值 + 种子事件生成） |
| **delta** | Critic 判断的关系变化量 | **Critic 判断的"事件对该价值观的冲击量"**（替换 relationship_delta） |
| **depth** | conversation_depth（对话深度） | **event_intensity**（事件强度）——越重大事件越快更新 |
| **alpha 公式** | `0.15 + 0.5 * depth` | **保留** `0.15 + 0.5 * intensity` |
| **alpha 范围** | [0.15, 0.65] | **保留** |
| **scale** | [0, 1] 或 [-1, 1] | **统一 [-1, 1]**（价值观有正负极性） |

**关键设计**：

- **alpha 与事件强度正相关**——日常小事几乎不改变价值观，重大事件大幅更新（与 SGE-Key-Insights 洞察对齐）
- **prior + delta + EMA** 三步法是普适的——SGE 改造主要是把"关系"换成"价值观"

**关键代码指针**：

- `_apply_relationship_ema()` 方法（evermemos_mixin.py:52-106）——**结构直接复用，参数名改**
- 公式：`posterior = clip(prior + delta)` + `alpha = clip(0.15 + 0.5*x, 0.15, 0.65)` + `ema = α·posterior + (1-α)·prev`

**验证方式**：

- **收敛性测试**：用相同的 event sequence 跑 100 epoch，验证 values 收敛
- **alpha 边界测试**：event_intensity=0 → alpha=0.15（信任 prior）；intensity=1 → alpha=0.65（信任 LLM）
- **价值差异度**：用不同 seed 跑 3 个 AI 婴儿，验证最终价值观显著不同（参考 M2.2 三胞胎实验）

---

## 2.4 Hebbian Learning → SGE Value Layer 行为偏好

**AiBeing 源码**：`engine/genome/genome_engine.py:289-354`（`Agent.learn()` 方法）

**核心公式**：

```python
# W2 更新（输出层）
lr = hebbian_lr * (1 + abs(reward))
for i, sig_name in enumerate(SIGNALS):
    sig_val = signals[sig_name]
    for j in range(HIDDEN_SIZE):
        if abs(hidden[j]) > 0.05:
            W2[i][j] += lr * reward * hidden[j] * (sig_val - 0.5)

# W1 更新（隐藏层）
if abs(reward) > 0.05:
    for i in range(HIDDEN_SIZE):
        if abs(hidden[i]) > 0.15:
            for j in range(INPUT_SIZE):
                W1[i][j] += lr * 0.3 * reward * full_input[j] * hidden[i]
```

**SGE 改造契约**：

| 元素 | AiBeing | SGE |
|------|---------|-----|
| **输入** | 25 维（5 drives + 12 context + 8 recurrent） | **改维度**——SGE 的输入是 Event 感知向量（21 维）+ Value state（N 维）+ recurrent |
| **网络结构** | 24 hidden + 8 signals | **可保留 hidden size**；改 output 维度（signals → SGE 的"行为模式标签"） |
| **reward** | 单标量（来自 frustration delta） | **改**为"事件对该 AI 婴儿的价值回报"——可以是 Critic LLM 给出，也可以是基于"选择是否成功"的事后评估 |
| **学习率** | hebbian_lr=0.02（可覆盖） | **保留范围**——0.02 是合理起点 |
| **W2 更新** | `W2 += lr * reward * hidden * (sig - 0.5)` | **直接复用** |
| **W1 更新** | `W1 += lr*0.3 * reward * input * hidden` | **直接复用**（0.3 是子学习率） |
| **weight decay** | 0.995（L2）+ clamp [-1.5, 1.5]/[-2.0, 2.0] | **直接复用**——防止权重爆炸 |

**关键设计**：

- SGE 的 Hebbian 学习**不直接用 signals**，而是把"行为模式"抽象为**价值观相关动作**（如"选择诚实"→ 与"诚实"价值相关 W 增强）
- 公式本身可复用，关键是**reward 信号的设计**——这决定 AI 婴儿"学什么"

**关键代码指针**：

- `Agent.learn()` 方法（genome_engine.py:289-354）——**直接复用核心**
- `Agent.compute_signals()` 方法（genome_engine.py:233-277）——**可复用为 value-to-action 的映射器**（改 output 维度即可）

**验证方式**：

- **学习曲线**：用相同 reward 序列，验证 W2 矩阵的 Frobenius 范数单调变化
- **权重稳定**：100 epoch 后验证无权重爆炸（< clamp 范围）
- **行为分化**：3 个 AI 婴儿经过不同 reward 历史后，行为模式显著不同

---

## 2.5 Phase Transition → SGE 叙事/价值观相变

**AiBeing 源码**：`engine/genome/genome_engine.py:320-335`（`Agent.learn()` 中的 phase transition 段）

**核心逻辑**：

```python
# 挫败感累积
if reward < -0.1:
    self._frustration += abs(reward)
else:
    self._frustration = max(0, self._frustration - reward * 0.5)

# 超过阈值 → 触发相变
if self._frustration > self.phase_threshold:  # 默认 2.0
    for i in range(N_SIGNALS):
        sig_val = signals[SIGNALS[i]]
        kick = -0.3 * (sig_val - 0.5) + random.gauss(0, 0.15)
        self.b2[i] += kick
    for i in range(HIDDEN_SIZE):
        self.b1[i] += random.gauss(0, 0.1)
    self._frustration = 0.0
    self._last_phase_transition = True
```

**SGE 改造契约**：

| 元素 | AiBeing | SGE |
|------|---------|-----|
| **触发器** | 挫败感 > 阈值（2.0） | **可保留**——SGE 中"连续负面事件导致挫败累积"是叙事断裂的前提 |
| **kick 公式** | `b2 += -0.3*(sig-0.5) + gauss(0, 0.15)` | **直接复用**（行为信号翻转） |
| **b1 噪声** | `b1 += gauss(0, 0.1)` | **直接复用** |
| **重置 frustration** | `_frustration = 0.0` | **直接复用** |
| **threshold** | 2.0 | **可调**——SGE 可能需要更高阈值（让 AI 婴儿"扛更多事"才相变） |
| **语义映射** | 行为模式剧烈扰动 | **叙事断裂 + 价值观重构**（对应 SGE-Key-Insights 洞察 14） |

**关键设计**：

- SGE 的相变是"价值观的非连续重构"——AiBeing 的相变是"行为模式剧烈扰动"
- 公式可复用，**trigger 条件可能要拓展**（如加入"叙事一致性评分 < 阈值"作为另一触发器）

**关键代码指针**：

- `Agent.learn()` 中的 phase transition 段（genome_engine.py:320-335）——**直接复用**
- 参数：`phase_threshold` 默认 2.0（`genome_engine.py:204`）

**验证方式**：

- **触发频率统计**：1000 epoch 中 phase transition 触发次数
- **前后对比**：相变前后的 behavior signal 分布差异（应有明显跳变）
- **叙事断裂检测**：相变后调用 Narrative Consistency Checker，验证能检测到断裂

---

## 2.6 Crystallization → SGE Memory 筛选门

**AiBeing 源码**：`engine/genome/style_memory.py:274-337`（`ContinuousStyleMemory.crystallize()` 方法）

**核心逻辑**：

```python
# 1. 距离最近记忆 < 0.25 → 合并增厚（mass += 1.0）
# 2. 否则创建新记忆（mass = 2.0）
# 3. 距离阈值 0.25 是硬编码
```

**SGE 改造契约**：

| 元素 | AiBeing | SGE |
|------|---------|-----|
| **距离度量** | 8D context 空间的 L2 距离 | **改维度**——SGE 用 Event 感知向量（21D）的子集（如 8D 关键维度） |
| **距离阈值** | 0.25（硬编码） | **可调**——M2.1 实验中扫描 [0.15, 0.35] 找最优 |
| **新记忆 mass** | 2.0 | **保留** |
| **合并增厚** | mass += 1.0 | **保留**——重复事件强化记忆的机制 |
| **评分维度** | 无显式评分（distance 决定） | **可加显式评分**——SGE 关心"事件对价值观的冲击"（impact × novelty × clarity） |

**关键设计**：

- SGE 的"什么值得记住"比 AiBeing 更复杂——不仅考虑 context 相似度，还要考虑**对价值观的冲击程度**
- 建议在 SGE 版本中加入**预筛选门**：先评估 event_impact（LLM 给分 0-1），高于阈值才进入 KNN 合并/新建

**关键代码指针**：

- `ContinuousStyleMemory.crystallize()` 方法（style_memory.py:274-337）——**结构直接复用**
- 距离阈值：style_memory.py:292（硬编码 0.25）——SGE 改为可配置

**验证方式**：

- **召回率测试**：注入 100 个相似事件 + 100 个不同事件，验证合并/新建比例合理
- **mass 分布**：1000 epoch 后 memory mass 分布不应过度集中（避免单个记忆"吃光"所有）
- **生成质量**：用结晶记忆作为 few-shot，验证 Actor 输出质量提升

---

## 2.7 KNN + Hawking 辐射 → SGE Memory 检索

**AiBeing 源码**：`engine/genome/style_memory.py:209-255`（`ContinuousStyleMemory.retrieve()` 方法）

**核心公式**：

```python
# 有效距离 = 物理距离 / √mass_eff
# 物理距离 = 8D context 空间的 L2 距离
# mass_eff = 1.0 + (mass_raw - 1.0) * exp(-gamma * delta_hours)
# gamma = 0.001/h（半衰期 ~29 天）
```

**SGE 改造契约**：

| 元素 | AiBeing | SGE |
|------|---------|-----|
| **距离度量** | 8D context L2 | **改维度**——SGE 用 Event 感知向量子集（具体维度在 M2.1 实验中确定） |
| **Hawking gamma** | 0.001/h（~29 天半衰期） | **保留**——长时间尺度的记忆淡化机制 |
| **mass 起点** | 1.0（基因）或 2.0（个人） | **保留** |
| **检索 top_k** | 默认 3 | **可调**——SGE 可能需要 top_k=5 作为 few-shot |
| **语言过滤** | `lang_preference` 参数 | **不适用**——SGE 不用 persona 语言，改为"事件类型过滤" |

**关键设计**：

- Hawking 辐射是**普适机制**——SGE 直接复用
- 距离公式 `effective_distance = physical / √mass_eff` 是核心创新——印象深的记忆更容易被检索到

**关键代码指针**：

- `ContinuousStyleMemory.retrieve()` 方法（style_memory.py:209-255）——**直接复用**
- `HAWKING_GAMMA` 常量（style_memory.py:29）——**直接复用**
- `_hawking_mass()` 函数（style_memory.py:56-65）——**直接复用**

**验证方式**：

- **检索准确性**：构造 10 个 query，验证 top-3 检索结果与人工标注的一致率 > 70%
- **质量衰减**：把记忆 last_used_at 设为 30 天前，验证检索排名下降
- **语言过滤**（如适用）：验证跨语言检索的降权生效

---

## 2.8 Thermodynamic Noise → SGE 行为噪声

**AiBeing 源码**：`engine/genome/drive_metabolism.py:113-136`（`DriveMetabolism.temperature()` 和 `apply_thermodynamic_noise()`）

**核心公式**：

```python
# 温度（tanh 饱和曲线）
max_temp = temp_coeff * 2.5
temperature = max_temp * tanh(total * temp_coeff / max_temp) + temp_floor

# 噪声注入
noisy[key] = clip(base_signals[key] + gauss(0, temperature), 0, 1)
```

**默认参数**：

- `temp_coeff = 0.12`
- `temp_floor = 0.03`
- tanh 饱和（避免高温时信号完全随机化）

**SGE 改造契约**：

- **直接复用整个模块**——温度公式 + 高斯噪声注入是普适的
- 改 `total()` 的输入——SGE 的"挫败感"来自 Value Layer 的负向冲击总和
- 改 `apply_thermodynamic_noise()` 的应用对象——SGE 应用在 Actor 输出上（行为信号 + 价值观表达）

**关键代码指针**：

- `DriveMetabolism.temperature()` 方法（drive_metabolism.py:113-123）——**直接复用**
- `apply_thermodynamic_noise()` 方法（drive_metabolism.py:125-136）——**直接复用**

**验证方式**：

- **温度单调性**：注入不同 frustration，验证 temperature 单调上升
- **饱和保护**：frustration=5.0 时验证 tanh 不会让信号完全随机
- **行为可变性**：相同状态下 100 次采样，验证信号分布的方差与温度正相关

---

## 2.9 双 LLM 架构 → SGE Critic + Actor 编排

**AiBeing 源码**：`agent/chat_agent.py:_chat_inner()`（编排主循环）

**架构**：

```
单轮对话 = 12 步循环
  Step 0:    加载 EverMemOS（用户画像 + 历史叙事）
  Step 1:    Time Metabolism（时间驱动更新）
  Step 2:    Critic（LLM 感知，temperature=0.2）
  Step 2.5:  Relationship EMA（关系状态更新）
  Step 3:    Drive metabolism + LLM delta → reward
  Step 4:    Crystallization gate（决定是否存记忆）
  Step 5:    Compute signals（神经网络前向）
  Step 6:    Thermodynamic noise（行为噪声）
  Step 7:    KNN retrieval（few-shot 准备）
  Step 8:    Build single-pass prompt
  Step 9:    Actor LLM 生成回复（temperature=0.9）
  Step 10:   Hebbian learning（神经网络更新）
  Step 11:   异步存储到 EverMemOS
  Step 12:   触觉/听觉 skill 处理
```

**SGE 改造契约**：

| AiBeing Step | SGE 对应 | 改造点 |
|-------------|---------|--------|
| 0 (EverMemOS 加载) | **替换**——SGE 的"历史"由 Memory Layer + Narrative Layer 提供 | 无外部 DB 依赖 |
| 1 (Time Metabolism) | **复用** §2.2 | 直接复用 |
| 2 (Critic) | **复用结构** §2.1 | 改输入/输出维度 |
| 2.5 (Relationship EMA) | **改造** §2.3 | 关系 → 价值观 |
| 3 (Reward) | **改造** | 挫败感变化 → 价值观冲击 |
| 4 (Crystallization) | **复用结构** §2.6 | 改距离度量 |
| 5 (Signals) | **复用** §2.4 | 改 output 维度 |
| 6 (Noise) | **复用** §2.8 | 直接复用 |
| 7 (KNN) | **复用** §2.7 | 改距离维度 |
| 8 (Prompt 构建) | **新增**——SGE 的 prompt 应包含 Value state + Narrative 当前段 | 新建 `_build_prompt()` |
| 9 (Actor) | **复用结构** | temperature=0.9，输出内心独白 + 行为 |
| 10 (Hebbian) | **复用** §2.4 | 直接复用核心 |
| 11 (异步存储) | **新增/复用**——SGE 用 SQLite 即可 | 简化为本地存储 |
| 12 (Skill) | **不适用**——SGE 无多模态 skill | 跳过 |

**关键设计**：

- 双 LLM 分离（感知 + 表达）的核心思想直接复用
- Step 8 的 prompt 构建是 SGE 的**新增点**——AiBeing 没考虑"叙事片段"作为 prompt 输入
- Step 11 的异步存储 SGE 简化为同步（实验阶段无并发需求）

**关键代码指针**：

- `_chat_inner()` 方法（chat_agent.py:237-...）——**架构复用，单步实现替换**
- Actor 模板：`actor_single` 模板（`engine/prompts/`）——**结构参考，prompt 改写**

**验证方式**：

- **端到端跑通**：构造 1 个事件，验证 12 步循环全部执行
- **时序检查**：验证 Step 顺序正确（如 EMA 在 Critic 之后）
- **双 LLM 分离**：验证 Critic 用 temperature=0.2，Actor 用 temperature=0.9

---

# 三、关键参数速查表

把 M2.1 实施时需要"直接复用默认值"的参数集中在这里，避免在多个章节里翻找：

| 参数 | 默认值 | 来源 | SGE 用途 |
|------|--------|------|---------|
| `frustration_decay_lambda` | 0.08/h | drive_metabolism.py:24 | 价值观冷却速率 |
| `connection_hunger_k` | 0.15/h | drive_metabolism.py:25 | 联结维度饥饿累积 |
| `novelty_hunger_k` | 0.05/h | drive_metabolism.py:26 | 新鲜维度饥饿累积 |
| `temp_coeff` | 0.12 | drive_metabolism.py:27 | 温度斜率 |
| `temp_floor` | 0.03 | drive_metabolism.py:28 | 温度下限 |
| `decay_rate`（每轮） | 0.1 | drive_metabolism.py:46 | Critic delta 应用后衰减 |
| `hebbian_lr` | 0.02 | genome_engine.py:203 | Hebbian 学习率 |
| `phase_threshold` | 2.0 | genome_engine.py:204 | 相变触发阈值 |
| `WEIGHT_DECAY` | 0.995 | genome_engine.py:87 | L2 衰减 |
| `HIDDEN_SIZE` | 24 | genome_engine.py:86 | 隐藏层维度 |
| `RECURRENT_SIZE` | 8 | genome_engine.py:84 | 循环状态维度 |
| `crystallize_distance_threshold` | 0.25 | style_memory.py:292 | 记忆合并距离阈值 |
| `HAWKING_GAMMA` | 0.001/h | style_memory.py:29 | 记忆衰减率 |
| `alpha_min` | 0.15 | evermemos_mixin.py:86 | EMA 学习率下限 |
| `alpha_max` | 0.65 | evermemos_mixin.py:86 | EMA 学习率上限 |
| `alpha_base` | 0.15 | evermemos_mixin.py:86 | EMA 基础学习率 |
| `alpha_depth_coeff` | 0.5 | evermemos_mixin.py:86 | EMA 强度斜率 |
| `critic_temperature` | 0.2 | critic.py:132 | Critic 稳定性 |
| `actor_temperature` | 0.9 | （参考设置） | Actor 创造性 |

---

# 四、与现有 SelfLab 文档的关联

| 文档 | 关联方式 |
|------|---------|
| [PRD.md §FR-1~10](../../PRD.md) | M2.1 实现的功能范围 |
| [ARCH.md §1.3, §3](../../ARCH.md) | 6 层架构中可借鉴/新增的层 |
| [DESIGN.md §4](../../DESIGN.md) | 自研组件清单的工程细节 |
| [ROADMAP.md §M2.1](../../ROADMAP.md) | M2.1 内容/技术方案/成本 |
| [DEVELOP.md §二](../../DEVELOP.md) | 技术栈（SSOT） |
| [SGE-Technology-Stack-Overview.md §一](./SGE-Technology-Stack-Overview.md) | 调研层（8 个机制的简介） |
| [SGE-Learning-from-AiBeing.md](./SGE-Learning-from-AiBeing.md) | 借鉴分析（哲学 + 工程） |
| [SGE-M11-Experiment-Design.md](./SGE-M11-Experiment-Design.md) | 上一阶段实验（已有数据可参考） |
| [references/AiBeing-Core-Engine-Reference.md](../../references/AiBeing-Core-Engine-Reference.md) | AiBeing 12 步详解（已存在摘录） |

**关键交叉引用**：

- 实施时如对"借鉴/改造"边界有疑问，先查本文件 §2.x 改造契约
- 如对机制**为什么**要借鉴（哲学依据），查 `SGE-Learning-from-AiBeing.md` §三
- 如对机制**怎么用**（公式细节），查 `references/AiBeing-Core-Engine-Reference.md` 对应 step 文档
- 实际**读源码**：~/project/AiBeing/（Bisen 本地）

---

# 五、M2.1 实施步骤建议

按"借鉴-改造"边界，M2.1 的实施应该**先复用、后改造**，避免一上来就改维度：

## 阶段 A：复制 + 直接复用（1-2 周）

1. **A1**：在 `experiments/scripts/m21_setup.py` 中设置项目骨架（不依赖 sge/ 包）
2. **A2**：复制 `drive_metabolism.py` 中的 `time_metabolism()` 和 `temperature()` 到 `experiments/sge_core/time.py`（**直接复用**，不修改）
3. **A3**：复制 `genome_engine.py` 中的 `Agent.learn()`（仅 Hebbian 部分）到 `experiments/sge_core/hebbian.py`
4. **A4**：复制 `style_memory.py` 中的 `retrieve()` + `HAWKING_GAMMA` 到 `experiments/sge_core/memory.py`
5. **A5**：用 AiBeing 的 5D drives（connection, novelty, ...）跑通基础循环，**先验证复用机制的正确性**

## 阶段 B：低改造（2-3 周）

6. **B1**：改造 Critic prompt（`critic.py:22-62`）→ SGE 事件感知 prompt（键名替换）
7. **B2**：改造 Relationship EMA（`evermemos_mixin.py:52-106`）→ Value EMA（relationship → value）
8. **B3**：改造 Phase Transition trigger（加入"叙事一致性低"作为辅助触发器）
9. **B4**：在 SGE 的 Value scale [-1, 1] 下重新校准所有 clamp 范围

## 阶段 C：新增组件（1-2 周）

10. **C1**：实现 `Value EMA Tracker`（多维价值观的 EMA 状态管理）
11. **C2**：实现 `Value Conflict Generator`（基于当前 Value state 生成针对性事件）
12. **C3**：实现 `Event Generator`（不基于 Critic 的"外部事件源"——为 AI 婴儿提供人生事件）
13. **C4**：Narrative Builder MVP（把 Event 序列串联为简短叙事——M2.1 MVP 版）

## 阶段 D：集成 + 验证（1-2 周）

14. **D1**：组装完整 12 步循环（参考 §2.9）
15. **D2**：跑 100 epoch 冒烟测试（参考 M1.1 冒烟测试流程）
16. **D3**：跑 1000 epoch 三胞胎实验（M2.2 的预备）

**总时长估算**：6-9 周

---

# 六、风险与开放问题

## 6.1 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| AiBeing 改造后性能差异大 | M2.1 实验数据可能与 AiBeing 不可比 | 阶段 A 先跑通基线，建立可比基线 |
| Value scale [-1, 1] 与 AiBeing [0, 5] 不兼容 | 直接复用时 clamp 范围需调整 | 阶段 B4 集中处理所有 clamp |
| SGE drives 数量与 AiBeing 5 个不同 | Critic prompt、EMA 维度都需改 | **Phase 0 终稿必须先确定 SGE drives 清单** |
| Phase Transition 在 SGE 中可能不触发或过于频繁 | 叙事断裂 / 价值观重构的可观察性差 | 阶段 B3 加入辅助 trigger；M2.1 跑完后看统计 |

## 6.2 开放问题（需要 Phase 0 终稿或 M2.1 实验回答）

1. **SGE 的 drives 清单**到底是哪几个？（[洞察 24](SGE-Key-Insights.md) 提到"探索/安全/创造/联结/自主"，但这是初稿）
2. **Value scale** 用 [-1, 1] 还是 [0, 1]？前者允许"反价值"，后者不允许
3. **Phase Transition 阈值** 在 SGE 中应该是多少？AiBeing 的 2.0 是否合适？
4. **Hawking gamma** 在 SGE 中应该是多少？AiBeing 的 0.001/h（29 天半衰期）对"AI 婴儿的 1000 epoch 实验"是否过长？
5. **crystallize 距离阈值** 0.25 在 SGE 的 21D 空间是否合适？（维度变化后阈值需重新校准）

这些问题的答案会影响 M2.1 实施时的具体参数选择——**不要在 Phase 0 终稿之前贸然调参**。

---

# 七、一句话总结

> **M2.1 = "9 个借鉴机制 + 4 个新增组件"的工程组装**。借鉴机制按"直接复用 / 低改造 / 中改造"三档管理边界，新增组件聚焦 Value Layer 和 Event Generator。M2.1 产出 1000 epoch 可跑的完整 12 步循环，**为 M2.2 三胞胎实验提供工程基线**。
