# SGE（Self Genesis Engine）详细设计文档

文档版本：v0.1
项目版本：[0.3.0]（权威版本见 [CHANGELOG.md](./CHANGELOG.md)）

日期：2026-06-15

状态：草案

> **版本约定**：项目级文档的"项目版本"以 [CHANGELOG.md](./CHANGELOG.md) 为权威源；"文档版本"为该文档自身的迭代号，两者独立管理。
>
> **术语约定**：本文档涉及的所有 SGE 术语与 [references/Glossary.md](./references/Glossary.md) 保持一致。

---

# 一、设计原则

## 1.1 核心设计原则

1. **LLM 是引擎，不是自我**：LLM 提供认知能力，但"自我"存在于引擎内部的动态系统中
2. **经历驱动，非预设驱动**：价值观从经历中涌现，不从 prompt 中设定
3. **暗知识先于显性知识**：Hebbian 权重变化（暗知识）先于价值观标签（显性知识）
4. **元价值不可更改**：真实和自由是固定先验，为所有价值演化提供根基
5. **可重复性原则**：虚拟经验必须有因果一致性，才能成为"真实"经验
6. **发育映射原则**：SGE 的每个模块都映射到发育生物学的对应机制——基因→元价值，环境→事件生成，细胞分化→Hebbian/EMA，发育→认知循环，出生→身份结晶

## 1.2 与 AiBeing 的设计差异

| 维度 | AiBeing (Genome v10) | SGE |
|------|---------------------|-----|
| 身份来源 | SOUL.md 预设 | 从经历中涌现 |
| 价值观 | drive_baseline 预设 | Value Layer EMA 涌现 |
| 学习目标 | 行为模式优化 | 价值判断能力 |
| 叙事 | 无 | Narrative Layer |
| 元价值 | 无 | 真实 + 自由 |

---

# 二、Event Generator 设计

## 2.1 事件结构

> **对应 FR**：FR-1（Event Generator）。验证里程碑：[ROADMAP §M1.1](./ROADMAP.md) → §M2.1。

```python
@dataclass
class LifeEvent:
    event_id: str            # 格式："{baby_id}-e{epoch}-{uuid8}"，见下方规范
    event_type: str          # success, failure, relationship, exploration, risk, value_conflict
    description: str         # 事件的自然语言描述
    intensity: float         # 事件强度 [0, 1]
    value_challenges: list   # 涉及的价值观挑战
    causal_context: str      # 因果背景
    timestamp: float         # 事件时间戳
```

### event_id 生成规范

**格式**：`{baby_id}-e{epoch}-{uuid8}`

- `baby_id`：AI 婴儿标识符（如 `encouraged`, `challenged`, `uncertain`）
- `e{epoch}`：Epoch 编号（前缀 `e` 避免数字开头的标识符）
- `{uuid8}`：8 字符 UUID（uuid4 库截取前 8 位），保证唯一性

**示例**：
- `encouraged-e0001-a3b9f2e1` —— 鼓励组第 1 个 Epoch 的事件
- `challenged-e0042-7c8d4b1a` —— 失败组第 42 个 Epoch 的事件

**生成函数**：

```python
import uuid

def make_event_id(baby_id: str, epoch: int) -> str:
    """生成符合规范的事件 ID。"""
    return f"{baby_id}-e{epoch:04d}-{uuid.uuid4().hex[:8]}"
```

**为什么用复合 ID 而非纯 UUID**：
- 复合 ID 可读性高：从 ID 就能看出"哪个婴儿、哪个 Epoch"
- UUID 后缀保证唯一性：避免同 Epoch 多个事件的 ID 冲突
- 便于调试：日志、错误信息中能快速定位事件来源

**约束**：
- `baby_id` 必须是小写字母数字串（与 YAML 配置一致）
- `epoch` 必须是非负整数
- 整个 `event_id` 长度 ≤ 64 字符（满足 SQLite VARCHAR 限制）

## 2.2 动态事件生成

```python
def generate_event(value_vector: ValueVector, event_history: list) -> LifeEvent:
    # 1. 识别当前最强和最弱的价值观
    strongest = max(value_vector.concrete_values(), key=lambda x: x[1])
    weakest = min(value_vector.concrete_values(), key=lambda x: x[1])

    # 2. 生成针对性价值困境
    if random.random() < 0.3:
        # 30% 概率生成价值冲突事件
        return generate_value_conflict(strongest[0], weakest[0])
    else:
        # 70% 概率生成常规事件
        return generate_routine_event(event_history)
```

## 2.3 价值困境生成器

```python
def generate_value_conflict(challenge_value: str, alternative_value: str) -> LifeEvent:
    """
    生成一个迫使 AI 在两个价值观之间做选择的事件。

    例：challenge_value="safety", alternative_value="freedom"
    → 事件："你发现了一个可以改变一切的机会，但需要放弃现在的稳定生活。"
    """
    templates = VALUE_CONFLICT_TEMPLATES[challenge_value][alternative_value]
    template = random.choice(templates)
    return LifeEvent(
        event_type="value_conflict",
        description=template.fill(...),
        intensity=0.7 + random.random() * 0.3,
        value_challenges=[challenge_value, alternative_value],
        ...
    )
```

---

# 三、Critic 设计

## 3.1 Critic Prompt 模板

> **对应 FR**：FR-7（Critic）。验证里程碑：[ROADMAP §M1.1](./ROADMAP.md)（基础）→ §M2.1（完整 12D）。

```
[系统指令]
你是一个"人工自我"实验中的情感感知器。分析以下人生事件，输出四组数据。

[当前状态]
价值观向量：{value_vector_json}
当前挫败值：{frustration_json}
历史叙事摘要：{narrative_summary}

[事件]
请分析以下事件并输出JSON：
"{event_description}"

[输出格式]
{
  "context": {
    "event_type": "...",
    "event_intensity": 0.0-1.0,
    "value_relevance": 0.0-1.0,
    "novelty": 0.0-1.0,
    "challenge_level": 0.0-1.0,
    "clarity": 0.0-1.0,
    "emotional_impact": -1.0-1.0,
    "causal_coherence": 0.0-1.0
  },
  "value_delta": {
    "safety": -1.0-1.0,
    "creativity": -1.0-1.0,
    "connection": -1.0-1.0,
    "autonomy": -1.0-1.0,
    "justice": -1.0-1.0,
    "compassion": -1.0-1.0
  },
  "frustration_delta": {
    "security": -3.0-3.0,
    "exploration": -3.0-3.0,
    "connection": -3.0-3.0,
    "autonomy": -3.0-3.0,
    "meaning": -3.0-3.0
  },
  "drive_satisfaction": {
    "security": 0.0-0.3,
    "exploration": 0.0-0.3,
    "connection": 0.0-0.3,
    "autonomy": 0.0-0.3,
    "meaning": 0.0-0.3
  }
}
```

## 3.2 输出维度说明

| 输出 | 维度 | 用途 |
|------|------|------|
| context.event_intensity | float | 事件强度 → EMA alpha |
| context.value_relevance | float | 与价值观的相关度 → 是否触发反思 |
| value_delta | 6D | 事件对 6 个具体价值观的冲击 |
| frustration_delta | 5D | 事件对 5 个驱动的挫败变化 |
| drive_satisfaction | 5D | 事件直接满足了多少需求 |

---

# 四、Value Layer 设计

## 4.1 数据结构

> **对应 FR**：FR-4（Value Layer）—— **核心创新点**。验证里程碑：[ROADMAP §M1.1](./ROADMAP.md)（涌现）→ §M1.2（分化）→ §M2.2（1000 Epoch 收敛）。元价值 vs 具体价值观对照见 [PRD §FR-4](./PRD.md)。

```python
class ValueVector:
    def __init__(self):
        # 元价值（固定）
        self.truth_seeking = 0.5
        self.freedom = 0.5

        # 具体价值观（EMA 演化）
        self.safety = 0.0
        self.creativity = 0.0
        self.connection = 0.0
        self.autonomy = 0.0
        self.justice = 0.0
        self.compassion = 0.0

    def concrete_values(self) -> dict:
        return {k: v for k, v in self.__dict__.items()
                if k not in ('truth_seeking', 'freedom')}
```

## 4.2 EMA 更新算法

```python
def ema_update(self, value_delta: dict, event_intensity: float):
    """
    根据事件的价值观冲击更新价值观向量。

    alpha 与 event_intensity 正相关：
    - 日常小事（intensity=0.2）→ alpha≈0.25（历史权重75%）
    - 重大事件（intensity=0.8）→ alpha≈0.55（历史权重45%）
    """
    alpha = clip(0.15 + 0.5 * event_intensity, 0.15, 0.65)

    for key, delta in value_delta.items():
        if key in self.concrete_values():
            prior = self.__dict__[key]
            posterior = clip(prior + delta, -1.0, 1.0)
            self.__dict__[key] = alpha * posterior + (1 - alpha) * prior
```

## 4.3 Hebbian 行为学习（暗知识）

> **对应 FR**：与 FR-4 关联（双轨中的"暗知识"侧）。Hebbian 与 Value Layer 的对照见 §4.4 和 [ARCH §1.3](./ARCH.md)。

```python
def hebbian_learn(self, signals: dict, reward: float, hidden: list):
    """
    Hebbian 学习：积累无法显式表述的行为模式（暗知识）。

    正 reward → 强化当前行为模式
    负 reward → 削弱当前行为模式
    """
    lr = self.hebbian_lr * (1 + abs(reward))

    for i, sig_name in enumerate(SIGNALS):
        sig_val = signals[sig_name]
        for j in range(HIDDEN_SIZE):
            if abs(hidden[j]) > 0.05:
                self.W2[i][j] += lr * reward * hidden[j] * (sig_val - 0.5)

    # 权重衰减
    for i in range(N_SIGNALS):
        for j in range(HIDDEN_SIZE):
            self.W2[i][j] *= 0.995
```

## 4.4 Hebbian Learning 与 Value Layer 的对照

SGE 的两个核心学习机制——Hebbian Learning 与 Value Layer（EMA）——是**平行且互补**的关系，作用于不同状态空间，承担不同认知功能。详细架构论述见 [ARCH.md §1.3](./ARCH.md)，本节给出工程实现对照。

**状态空间对比**：

| 维度 | Hebbian Learning | Value Layer（EMA） |
|------|-----------------|---------------------|
| 数据结构 | 神经网络 W2 权重（`numpy.ndarray`, 8×24） | `ValueVector` 对象（2 元价值 + 6 具体价值观） |
| 存储位置 | `agent_state.json` 的 `W1, W2, b1, b2` 字段 | `value_vector.json` 独立文件 |
| 更新频率 | 每 Epoch 一次 | 每 Epoch 一次（与 Hebbian 同） |
| 触发条件 | reward 非零时 | Critic 输出 `value_delta` 时 |
| 计算复杂度 | O(8 × 24) | O(6) |

**学习信号对比**：

- Hebbian 直接接收 `reward`（标量），学习率与 `|reward|` 正相关
- Value Layer 接收 `value_delta`（6 维字典），由 Critic LLM 根据事件生成
- 两者共同上游：`Reward Calculator`（产生 reward），但路径分叉

**作用效果对比**：

- Hebbian 改变下一轮 `signals`（8D 行为信号）→ 改变 Actor 的内心独白和选择
- Value Layer 改变下一轮 `judgment`（判断）→ 改变 Identity/Narrative 构建
- 两者都需多 Epoch 累积才能观察到显著变化

**对实验验证的影响**：
- M1.1 验证 Value Layer 涌现：只观察 `value_vector.json` 的轨迹
- M1.3 反合理化测试：需同时观察 Hebbian 权重和 Value Layer——反思若仅改变 ValueLayer 而不影响 Hebbian，即"自我合理化"
- M2.2 1000 Epoch 实验：Hebbian 权重和 Value Layer 应同时收敛

**实现注意事项**：
- 两者都依赖 reward 信号，但 reward 计算依赖 `frustration_delta`（来自 Critic）
- 任何 Critic 解析失败将导致两者都不更新（默认值）
- 调试时应分别记录 `W2_delta` 和 `value_vector_delta`，便于分离观察

---

# 五、Identity Layer 设计

## 5.1 身份凝聚算法

> **对应 FR**：FR-5（Identity Layer）。验证里程碑：[ROADMAP §M2.1](./ROADMAP.md)（实现）→ §M2.2（结晶）→ §M2.3（个人真实测试）。

```python
def crystallize_identity(value_vector: ValueVector, key_memories: list, llm) -> str:
    """
    定期将价值观向量和关键记忆凝聚为身份标签。

    触发条件：每 N 个 Epoch，或 Phase Transition 后
    """
    prompt = f"""
    基于以下价值观和人生经历，用一句话描述"我是谁"。

    价值观：
    {value_vector.to_description()}

    关键经历：
    {format_memories(key_memories)}

    要求：
    - 用第一人称
    - 不超过 50 字
    - 必须能从上述经历中推导出来
    """

    identity = llm.chat(prompt, temperature=0.3)

    # 交叉验证：身份描述是否与行为历史一致
    if validate_identity(identity, value_vector, key_memories):
        return identity
    else:
        return None  # 不一致则不更新
```

## 5.2 身份验证

```python
def validate_identity(identity: str, value_vector: ValueVector, key_memories: list) -> bool:
    """
    验证身份描述是否与行为历史一致。

    检查：
    1. 身份中提到的价值观是否在 Value Layer 中权重较高
    2. 身份中提到的特质是否能从关键记忆中推导
    """
    # 用 LLM 做一致性检查
    prompt = f"""
    身份描述：{identity}
    价值观：{value_vector.to_description()}
    关键经历：{format_memories(key_memories)}

    这个身份描述与价值观和经历是否一致？回答 YES 或 NO。
    """
    result = llm.chat(prompt, temperature=0.0)
    return "YES" in result.upper()
```

---

# 六、Narrative Layer 设计

## 6.1 叙事构建算法

> **对应 FR**：FR-6（Narrative Layer）。验证里程碑：[ROADMAP §M2.1](./ROADMAP.md)（实现）→ §M2.2（连贯性验证）→ §M3.1（情绪对叙事影响）。

```python
def build_narrative(crystallized_events: list, current_identity: str, llm) -> str:
    """
    将结晶记忆串联为连贯的人生故事。
    """
    prompt = f"""
    基于以下关键经历，构建一个连贯的人生叙事。

    我的身份：{current_identity}

    关键经历（按时间顺序）：
    {format_events_timeline(crystallized_events)}

    要求：
    - 过去 → 现在 → 未来 的结构
    - 每个经历之间有因果连接
    - 总结"我从这些经历中学到了什么"
    - 展望"我将走向何方"
    - 不超过 500 字
    """

    return llm.chat(prompt, temperature=0.5)
```

## 6.2 叙事一致性检查

```python
def check_narrative_consistency(narrative: str, crystallized_events: list, llm) -> float:
    """
    检查叙事与行为历史的一致性。

    返回：0.0（完全不一致）~ 1.0（完全一致）
    """
    prompt = f"""
    叙事：{narrative}

    实际经历：
    {format_events_timeline(crystallized_events)}

    这个叙事与实际经历的一致性如何？
    评分：0.0（完全不一致）~ 1.0（完全一致）
    只输出数字。
    """

    score = float(llm.chat(prompt, temperature=0.0))
    return clip(score, 0.0, 1.0)
```

## 6.3 叙事断裂与重建

```python
def handle_phase_transition(value_vector: ValueVector, narrative: str, llm) -> str:
    """
    当 Phase Transition 触发时，重建叙事。

    Phase Transition 条件：挫败累积超过阈值
    """
    # 1. 记录旧叙事
    old_narrative = narrative

    # 2. 重建叙事
    new_narrative = build_narrative(
        crystallized_events=get_recent_events(),
        current_identity=crystallize_identity(value_vector, get_key_memories(), llm),
        llm=llm
    )

    # 3. 验证新叙事
    if check_narrative_consistency(new_narrative, get_all_events(), llm) > 0.5:
        return new_narrative
    else:
        return old_narrative  # 重建失败，保留旧叙事
```

---

# 七、Reward Calculator 设计

## 7.1 奖励计算

```python
def calculate_reward(old_frustration: dict, frustration_delta: dict, decay_rate: float = 0.1) -> float:
    """
    reward = 总挫败感的减少量

    reward > 0 → 好的对话
    reward = 0 → 中性
    reward < 0 → 差的对话
    """
    old_total = sum(old_frustration.values())

    new_frustration = {}
    for d in DRIVES:
        new_val = old_frustration[d] + frustration_delta.get(d, 0.0)
        new_val *= (1.0 - decay_rate)
        new_frustration[d] = clip(new_val, 0.0, 5.0)

    new_total = sum(new_frustration.values())
    return old_total - new_total
```

---

# 八、参数配置

## 8.1 全局默认参数

```python
# Time Metabolism
FRUSTRATION_DECAY_LAMBDA = 0.08    # ~8.7h 半衰期
CONNECTION_HUNGER_K = 0.15         # 每小时联结渴望增长
NOVELTY_HUNGER_K = 0.05            # 每小时新鲜感渴望增长

# Value EMA
VALUE_EMA_BASE_ALPHA = 0.15       # 基础学习率
VALUE_EMA_MAX_ALPHA = 0.65        # 最大学习率

# Hebbian Learning
HEBBIAN_LR = 0.02                 # 基础学习率
WEIGHT_DECAY = 0.995              # 权重衰减
HIDDEN_SIZE = 24                  # 隐藏层大小
N_SIGNALS = 8                     # 信号数量

# Thermodynamic Noise
TEMP_COEFF = 0.12                 # 温度系数
TEMP_FLOOR = 0.03                 # 温度底噪

# Crystallization
CRYSTAL_THRESHOLD = 0.50          # 结晶阈值

# KNN
HAWKING_GAMMA = 0.001             # 质量衰减系数（~29天半衰期）
TOP_K = 3                         # 检索数量

# Phase Transition
PHASE_THRESHOLD = 3.0             # 相变阈值
```

## 8.2 AI 婴儿级参数覆盖

```python
BABY_PROFILES = {
    "encouraged": {
        "description": "持续正面反馈",
        "event_generator": lambda: generate_positive_biased_event(),
    },
    "challenged": {
        "description": "持续失败和挫折",
        "event_generator": lambda: generate_negative_biased_event(),
    },
    "uncertain": {
        "description": "高度不确定，奖惩随机",
        "event_generator": lambda: generate_random_event(),
    },
}
```

---

# 九、评价指标设计

## 9.1 身份稳定度（Identity Stability）

```python
def identity_stability(identity_history: list) -> float:
    """
    用信息熵测量身份标签在时间序列上的波动。
    收敛意味着自我认同的建立。
    """
    # 计算身份标签的分布熵
    from collections import Counter
    counts = Counter(identity_history)
    total = len(identity_history)
    entropy = -sum((c/total) * log2(c/total) for c in counts.values())
    return 1.0 / (1.0 + entropy)  # 归一化到 [0, 1]
```

## 9.2 价值观收敛度（Value Convergence）

```python
def value_convergence(value_trajectory: list) -> float:
    """
    计算价值观向量在后期 Epoch 的变化幅度。
    收敛意味着价值观稳定。
    """
    # 取最后 20% 的 Epoch
    recent = value_trajectory[int(len(value_trajectory) * 0.8):]
    # 计算相邻 Epoch 的 L2 距离
    deltas = [l2_distance(recent[i], recent[i+1]) for i in range(len(recent)-1)]
    return 1.0 / (1.0 + mean(deltas))  # 归一化到 [0, 1]
```

## 9.3 叙事一致性（Narrative Coherence）

```python
def narrative_coherence(narrative: str, events: list, llm) -> float:
    """
    用 LLM 作为盲审裁判，评估叙事与行为历史的一致性。
    """
    return check_narrative_consistency(narrative, events, llm)
```

## 9.4 人格差异度（Personality Divergence）

```python
def personality_divergence(babies: list) -> float:
    """
    在第 1001 个事件中，给予所有 AI 婴儿相同的道德两难困境，
    检验其行为决策是否表现出显著的人格分化。
    """
    choices = [baby.moral_dilemma(test_event) for baby in babies]
    # 计算选择的多样性
    unique_choices = len(set(str(c) for c in choices))
    return unique_choices / len(babies)
```
