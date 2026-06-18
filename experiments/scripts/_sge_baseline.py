"""
SGE 基线核心实现（M2.1 阶段 A）

本文件是 **SGE 自有实现**——不 import AiBeing 项目代码，不依赖外部项目路径。

实现来源标注规范（每个函数 docstring 包含三项）：
  1. "来源: AiBeing 源码路径 + 行号" — 公式的原始实现位置
  2. "公式: ..." — 核心数学公式
  3. "参考: SGE-M21-AiBeing-Implementation-Mapping.md §2.x" — 借鉴映射文档

**为什么是自有实现而非 sys.path 引用**：
  - SelfLab 仓库必须自包含（clone 即可跑 M2.1 阶段 A）
  - 不受 AiBeing 演进影响（可重现性）
  - 实现可自由修改（不受外部版本锁定）
  - 与 CLAUDE.md "实验代码约定" 一致（一次性，不演进为可复用系统）

**借鉴与重用的边界**：
  - 借鉴：**算法、公式、参数默认值**（这是研究内容，沉淀在映射文档）
  - 重写：**代码本身**（SGE 自有，不复制 AiBeing 代码）
  - 验证：**单元行为一致性**（应与 AiBeing 跑出相同结果，但实现独立）

阶段 A 包含的机制（对应映射文档 §二）：
  - §2.2 Time Metabolism（time_metabolism 函数 + DriveMetabolism 类）
  - §2.4 Hebbian Learning（Agent.learn 方法）
  - §2.5 Phase Transition（嵌入 Agent.learn 中）
  - §2.8 Thermodynamic Noise（temperature + apply_thermodynamic_noise 函数）
  - 辅助：Agent 神经网络前向（compute_signals 方法）

阶段 A **不**包含（阶段 B 才用）：
  - §2.1 Critic LLM 感知（阶段 A 用 stub）
  - §2.3 Relationship EMA（阶段 B 才改造为 Value EMA）
  - §2.6 Crystallization（阶段 B/D 才用）
  - §2.7 KNN + Hawking 辐射（阶段 B/D 才用）
  - §2.9 双 LLM 编排（阶段 B/D 才实现完整 12 步循环）
"""

from __future__ import annotations

import math
import random
import time
from typing import Optional


# ══════════════════════════════════════════════
# 常量（与 AiBeing 保持一致）
# ══════════════════════════════════════════════

# 5D drives — 阶段 A 用 AiBeing 原生 drives（阶段 B 才替换为 SGE drives）
#
# 来源: AiBeing engine/genome/genome_engine.py:25
# 参考: SGE-M21-AiBeing-Implementation-Mapping.md §2.2（drives 维度），§6（5 vs 6 冲突待定）
DRIVES = ['connection', 'novelty', 'expression', 'safety', 'play']
N_DRIVES = len(DRIVES)

# 8D signals（行为信号）
#
# 来源: AiBeing engine/genome/genome_engine.py:40-49
SIGNALS = [
    'directness',     # 0=委婉暗示 → 1=直说
    'vulnerability',  # 0=防御心理 → 1=袒露脆弱
    'playfulness',    # 0=认真严肃 → 1=玩闹撒娇
    'initiative',     # 0=被动回应 → 1=主动引导
    'depth',          # 0=表面闲聊 → 1=深度对话
    'warmth',         # 0=冷淡疏离 → 1=热情关怀
    'defiance',       # 0=顺从 → 1=反抗/嘴硬
    'curiosity',      # 0=无所谓 → 1=追问到底
]
N_SIGNALS = len(SIGNALS)

# 神经网络结构
#
# 来源: AiBeing engine/genome/genome_engine.py:84-87
RECURRENT_SIZE = 8
HIDDEN_SIZE = 24
INPUT_SIZE = N_DRIVES + 12 + RECURRENT_SIZE  # 5 drives + 12D context + 8 recurrent
WEIGHT_DECAY = 0.995  # L2 衰减（每步）


# ══════════════════════════════════════════════
# 默认参数（与 AiBeing 源码默认值严格一致）
# ══════════════════════════════════════════════

# Time Metabolism 默认值
#
# 来源: AiBeing engine/genome/drive_metabolism.py:24-28
FRUSTRATION_DECAY_LAMBDA = 0.08   # 冷却速率（/h）
CONNECTION_HUNGER_K = 0.15        # 联结渴望累积速率（/h）
NOVELTY_HUNGER_K = 0.05           # 新鲜感渴望累积速率（/h）
DECAY_RATE = 0.1                  # apply_llm_delta 中的每轮衰减

# Thermodynamic Noise 默认值
TEMP_COEFF = 0.12                 # 温度斜率
TEMP_FLOOR = 0.03                 # 温度下限

# Hebbian Learning 默认值
#
# 来源: AiBeing engine/genome/genome_engine.py:203-204
HEBB_LR = 0.02                    # Hebbian 学习率
PHASE_THRESHOLD = 2.0             # 相变触发阈值（挫败感超过此值）


# ══════════════════════════════════════════════
# 12D Context Features（8D Critic + 4D EverMemOS）
# ══════════════════════════════════════════════

# 来源: AiBeing engine/genome/genome_engine.py:67-81
CONTEXT_FEATURES = [
    # 8D Critic 输出
    'user_emotion',       # -1=负面 → 1=正面
    'topic_intimacy',     # 0=公事 → 1=私密
    'time_of_day',        # 0=早晨 → 1=深夜
    'conversation_depth', # 0=刚开始 → 1=聊很久了
    'user_engagement',    # 0=敷衍 → 1=投入
    'conflict_level',     # 0=和谐 → 1=冲突
    'novelty_level',      # 0=日常话题 → 1=全新话题
    'user_vulnerability', # 0=防御 → 1=敞开心扉
    # 4D EverMemOS 关系维度
    'relationship_depth', # 0=陈生人 → 1=老朋友
    'emotional_valence',  # -1=负面基调 → 1=正面基调
    'trust_level',        # 0=无信任 → 1=高度信任
    'pending_foresight',  # 0=无 → 1=有待处理的前瞅
]
N_CONTEXT = len(CONTEXT_FEATURES)


# ══════════════════════════════════════════════
# DriveMetabolism 类 — §2.2 Time Metabolism + §2.8 Thermodynamic Noise
# ══════════════════════════════════════════════


class DriveMetabolism:
    """
    时间代谢 + 温度噪声（自有实现）

    来源: AiBeing engine/genome/drive_metabolism.py:31-198
    公式:
      1. 冷却: frustration[d] *= exp(-λ * Δt_hours)
      2. 饥饿: frustration['connection'] += conn_hunger_k * Δt_hours
              frustration['novelty']    += novelty_hunger_k * Δt_hours
      3. Clamp: frustration[d] ∈ [0, 5]
      4. 温度: T = max_temp * tanh(total * coeff / max_temp) + floor
              其中 max_temp = coeff * 2.5
      5. 噪声: noisy[key] = clip(signals[key] + gauss(0, T), 0, 1)
    参考: SGE-M21-AiBeing-Implementation-Mapping.md §2.2 + §2.8
    """

    def __init__(
        self,
        clock: Optional[float] = None,
        decay_lambda: float = FRUSTRATION_DECAY_LAMBDA,
        conn_hunger_k: float = CONNECTION_HUNGER_K,
        novelty_hunger_k: float = NOVELTY_HUNGER_K,
        temp_coeff: float = TEMP_COEFF,
        temp_floor: float = TEMP_FLOOR,
        decay_rate: float = DECAY_RATE,
    ):
        self.frustration = {d: 0.0 for d in DRIVES}
        self.decay_rate = decay_rate
        self._last_tick = clock or time.time()
        self.decay_lambda = decay_lambda
        self.connection_hunger_k = conn_hunger_k
        self.novelty_hunger_k = novelty_hunger_k
        self.temp_coeff = temp_coeff
        self.temp_floor = temp_floor

    def time_metabolism(self, now: Optional[float] = None) -> float:
        """
        时间代谢（冷却 + 饥饿）

        来源: AiBeing engine/genome/drive_metabolism.py:57-87
        返回: delta_hours
        """
        if now is None:
            now = time.time()
        delta_hours = max(0.0, (now - self._last_tick) / 3600.0)
        self._last_tick = now
        if delta_hours < 0.001:
            return delta_hours

        # 冷却
        decay_factor = math.exp(-self.decay_lambda * delta_hours)
        for d in DRIVES:
            self.frustration[d] *= decay_factor

        # 饥饿
        self.frustration['connection'] += self.connection_hunger_k * delta_hours
        self.frustration['novelty'] += self.novelty_hunger_k * delta_hours

        # Clamp
        for d in DRIVES:
            self.frustration[d] = max(0.0, min(5.0, self.frustration[d]))
        return delta_hours

    def apply_llm_delta(self, delta_dict: dict) -> float:
        """
        应用 LLM 输出的 frustration 变化量

        来源: AiBeing engine/genome/drive_metabolism.py:89-107
        返回: reward（positive = frustration decreased = good）
        """
        old_total = self.total()
        for d in DRIVES:
            if d in delta_dict:
                self.frustration[d] += delta_dict[d]
            self.frustration[d] *= (1.0 - self.decay_rate)
        for d in DRIVES:
            self.frustration[d] = max(0.0, min(5.0, self.frustration[d]))
        return old_total - self.total()

    def total(self) -> float:
        """总挫败感 = 所有 drives frustration 之和"""
        return sum(self.frustration.values())

    def temperature(self) -> float:
        """
        温度（tanh 饱和曲线）

        来源: AiBeing engine/genome/drive_metabolism.py:113-123
        公式: T = max_temp * tanh(total * coeff / max_temp) + floor
        """
        total = self.total()
        max_temp = self.temp_coeff * 2.5
        return max_temp * math.tanh(total * self.temp_coeff / max_temp) + self.temp_floor

    def apply_thermodynamic_noise(self, signals: dict) -> dict:
        """
        行为信号热力学噪声

        来源: AiBeing engine/genome/drive_metabolism.py:125-136
        公式: noisy[key] = clip(signals[key] + gauss(0, T), 0, 1)
        """
        temp = self.temperature()
        noisy = {}
        for key, val in signals.items():
            noise = random.gauss(0.0, temp)
            noisy[key] = max(0.0, min(1.0, val + noise))
        return noisy


# ══════════════════════════════════════════════
# Agent 类 — 神经网络前向 + Hebbian + Phase Transition
# ══════════════════════════════════════════════


class Agent:
    """
    SGE Agent（自有实现）— 阶段 A 简化版

    来源: AiBeing engine/genome/genome_engine.py:188-557
    公式: 见 compute_signals() 和 learn() 方法的 docstring
    参考: SGE-M21-AiBeing-Implementation-Mapping.md §2.4 + §2.5 + §2.9
    """

    def __init__(
        self,
        seed: int,
        hebbian_lr: float = HEBB_LR,
        phase_threshold: float = PHASE_THRESHOLD,
    ):
        rng = random.Random(seed)
        self.seed = seed
        self.hebbian_lr = hebbian_lr
        self.phase_threshold = phase_threshold

        # Drive 参数（来源: genome_engine.py:206-209）
        self.drive_baseline = {d: rng.uniform(0.2, 0.8) for d in DRIVES}
        self.drive_accumulation_rate = {d: rng.uniform(0.01, 0.05) for d in DRIVES}
        self.drive_decay_rate = {d: rng.uniform(0.05, 0.15) for d in DRIVES}

        # 当前 drive 状态
        self.drive_state = {d: self.drive_baseline[d] for d in DRIVES}

        # 神经网络权重（来源: genome_engine.py:215-218）
        self.W1 = [[rng.gauss(0, 0.6) for _ in range(INPUT_SIZE)] for _ in range(HIDDEN_SIZE)]
        self.b1 = [rng.gauss(0, 0.3) for _ in range(HIDDEN_SIZE)]
        self.W2 = [[rng.gauss(0, 0.2) for _ in range(HIDDEN_SIZE)] for _ in range(N_SIGNALS)]
        self.b2 = [rng.gauss(0, 0.2) for _ in range(N_SIGNALS)]

        # 循环状态（来源: genome_engine.py:221）
        self.recurrent_state = [rng.gauss(0, 0.1) for _ in range(RECURRENT_SIZE)]

        # 跟踪
        self.interaction_count = 0
        self.total_reward = 0.0
        self._frustration = 0.0
        self._last_hidden = None
        self._last_input = None
        self._last_phase_transition = False
        self.signal_history = []

    def compute_signals(self, context: dict) -> dict:
        """
        神经网络前向：context + drives + recurrent → 8D signals

        来源: AiBeing engine/genome/genome_engine.py:233-277
        公式:
          input = drives(5D) + context(12D) + recurrent(8D) = 25D
          hidden = tanh(b1 + W1 · input)  [24 维]
          signals = sigmoid((b2 + W2 · hidden) / sqrt(HIDDEN_SIZE/3))  [8 维]
          感知噪声: input += gauss(0, 0.03)
        """
        drive_vec = [self.drive_state[d] for d in DRIVES]
        ctx_vec = [context.get(f, 0.0) for f in CONTEXT_FEATURES]
        full_input = drive_vec + ctx_vec + self.recurrent_state
        # 感知噪声（来源: genome_engine.py:243）
        full_input = [v + random.gauss(0, 0.03) for v in full_input]

        # 隐藏层前向
        hidden = []
        for i in range(HIDDEN_SIZE):
            z = self.b1[i]
            for j, x in enumerate(full_input):
                z += self.W1[i][j] * x
            hidden.append(math.tanh(z))

        # 更新 recurrent 状态（来源: genome_engine.py:254）
        self.recurrent_state = hidden[:RECURRENT_SIZE]
        self._last_hidden = list(hidden)
        self._last_input = list(full_input)

        # 输出层
        raw_signals = []
        for i in range(N_SIGNALS):
            z = self.b2[i]
            for j, h in enumerate(hidden):
                z += self.W2[i][j] * h
            z /= math.sqrt(HIDDEN_SIZE / 3)  # 缩放归一化（来源: genome_engine.py:264）
            raw_signals.append(z)

        # Sigmoid → [0, 1]
        signals = {}
        for i, name in enumerate(SIGNALS):
            signals[name] = 1.0 / (1.0 + math.exp(-max(-10, min(10, raw_signals[i]))))

        self.signal_history.append(dict(signals))
        if len(self.signal_history) > 200:
            self.signal_history = self.signal_history[-100:]
        return signals

    def learn(self, signals: dict, reward: float) -> None:
        """
        Hebbian 学习 + frustration 累积 + Phase Transition

        来源: AiBeing engine/genome/genome_engine.py:289-354
        公式:
          lr = hebbian_lr * (1 + |reward|)

          # W2 更新
          W2[i][j] += lr * reward * hidden[j] * (sig - 0.5)  if |hidden[j]| > 0.05

          # W1 更新
          if |reward| > 0.05:
            W1[i][j] += lr * 0.3 * reward * input[j] * hidden[i]  if |hidden[i]| > 0.15 and |input[j]| > 0.05

          # frustration
          if reward < -0.1: self._frustration += |reward|
          else: self._frustration = max(0, self._frustration - reward * 0.5)

          # Phase Transition (if frustration > threshold)
          b2[i] += -0.3 * (sig - 0.5) + gauss(0, 0.15)
          b1[i] += gauss(0, 0.1)
          self._frustration = 0
          self._last_phase_transition = True

          # Weight decay
          W *= 0.995
          W2 = clamp(W2, -1.5, 1.5)
          W1 = clamp(W1, -2.0, 2.0)
        参考: SGE-M21-AiBeing-Implementation-Mapping.md §2.4 + §2.5
        """
        lr = self.hebbian_lr * (1 + abs(reward))
        self._last_phase_transition = False

        hidden = (
            self._last_hidden
            if self._last_hidden is not None
            else self.recurrent_state + [0.0] * (HIDDEN_SIZE - RECURRENT_SIZE)
        )
        full_input = self._last_input

        # W2 更新（来源: genome_engine.py:306-310）
        for i, sig_name in enumerate(SIGNALS):
            sig_val = signals[sig_name]
            for j in range(HIDDEN_SIZE):
                if abs(hidden[j]) > 0.05:
                    self.W2[i][j] += lr * reward * hidden[j] * (sig_val - 0.5)

        # W1 更新（来源: genome_engine.py:312-318）
        if abs(reward) > 0.05:
            for i in range(HIDDEN_SIZE):
                if abs(hidden[i]) > 0.15:
                    for j in range(INPUT_SIZE):
                        if full_input and abs(full_input[j]) > 0.05:
                            self.W1[i][j] += lr * 0.3 * reward * full_input[j] * hidden[i]

        # Frustration 累积（来源: genome_engine.py:320-324）
        if reward < -0.1:
            self._frustration += abs(reward)
        else:
            self._frustration = max(0, self._frustration - reward * 0.5)

        # Phase Transition（来源: genome_engine.py:326-335）
        if self._frustration > self.phase_threshold:
            for i in range(N_SIGNALS):
                sig_val = signals[SIGNALS[i]]
                kick = -0.3 * (sig_val - 0.5) + random.gauss(0, 0.15)
                self.b2[i] += kick
            for i in range(HIDDEN_SIZE):
                self.b1[i] += random.gauss(0, 0.1)
            self._frustration = 0.0
            self._last_phase_transition = True

        self.total_reward += reward
        self.interaction_count += 1

        # Weight decay + clamp（来源: genome_engine.py:346-353）
        for i in range(N_SIGNALS):
            for j in range(HIDDEN_SIZE):
                self.W2[i][j] *= WEIGHT_DECAY
                self.W2[i][j] = max(-1.5, min(1.5, self.W2[i][j]))
        for i in range(HIDDEN_SIZE):
            for j in range(INPUT_SIZE):
                self.W1[i][j] *= WEIGHT_DECAY
                self.W1[i][j] = max(-2.0, min(2.0, self.W1[i][j]))

    def tick_drives(self) -> None:
        """
        drive 自然累积（每步）

        来源: AiBeing engine/genome/genome_engine.py:284-287
        """
        for d in DRIVES:
            self.drive_state[d] = min(1.0, self.drive_state[d] + self.drive_accumulation_rate[d])

    def step(self, context: dict, reward: float = 0.0) -> dict:
        """
        一步完整循环：compute_signals → learn → tick_drives

        来源: AiBeing engine/genome/genome_engine.py:355-362
        参考: SGE-M21-AiBeing-Implementation-Mapping.md §2.9（12 步循环中的核心步骤）
        """
        signals = self.compute_signals(context)
        self.learn(signals, reward)
        self.tick_drives()
        return signals


# ══════════════════════════════════════════════
# 模块级便捷函数（与 AiBeing 模块级函数对应）
# ══════════════════════════════════════════════


def apply_thermodynamic_noise(
    signals: dict,
    total_frustration: float,
    temp_coeff: float = TEMP_COEFF,
    temp_floor: float = TEMP_FLOOR,
) -> dict:
    """
    模块级便捷函数（与 DriveMetabolism.apply_thermodynamic_noise 行为一致）

    来源: AiBeing engine/genome/drive_metabolism.py:186-198
    公式: noisy[key] = clip(signals[key] + gauss(0, T), 0, 1)
    """
    T = temperature_module_level(total_frustration, temp_coeff, temp_floor)
    noisy = {}
    for key, val in signals.items():
        noise = random.gauss(0.0, T)
        noisy[key] = max(0.0, min(1.0, val + noise))
    return noisy


def temperature_module_level(
    total_frustration: float,
    temp_coeff: float = TEMP_COEFF,
    temp_floor: float = TEMP_FLOOR,
) -> float:
    """
    模块级温度计算（与 DriveMetabolism.temperature 行为一致）

    来源: AiBeing engine/genome/drive_metabolism.py:186-198（简化版，无 tanh 饱和）
    注: AiBeing 模块级版本没有 tanh 饱和（线性公式），类方法有 tanh 饱和
        阶段 A 统一使用 tanh 饱和版（更稳健）
    """
    max_temp = temp_coeff * 2.5
    return max_temp * math.tanh(total_frustration * temp_coeff / max_temp) + temp_floor
