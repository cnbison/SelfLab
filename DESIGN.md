# SGE（Self Genesis Engine）详细设计文档

版本：v0.1

日期：2026-06-15

状态：草案

---

# 一、设计原则

## 1.1 核心设计原则

1. **LLM 是引擎，不是自我**：LLM 提供认知能力，但"自我"存在于引擎内部的动态系统中
2. **经历驱动，非预设驱动**：价值观从经历中涌现，不从 prompt 中设定
3. **暗知识先于显性知识**：Hebbian 权重变化（暗知识）先于价值观标签（显性知识）
4. **元价值不可更改**：真实和自由是固定先验，为所有价值演化提供根基
5. **可重复性原则**：虚拟经验必须有因果一致性，才能成为"真实"经验

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

```python
@dataclass
class LifeEvent:
    event_id: str
    event_type: str          # success, failure, relationship, exploration, risk, value_conflict
    description: str         # 事件的自然语言描述
    intensity: float         # 事件强度 [0, 1]
    value_challenges: list   # 涉及的价值观挑战
    causal_context: str      # 因果背景
    timestamp: float         # 事件时间戳
```

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

---

# 五、Identity Layer 设计

## 5.1 身份凝聚算法

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
