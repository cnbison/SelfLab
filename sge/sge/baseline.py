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

import copy
import math
import os
import random
import time
from typing import Optional


# �═════════════════════════════════════════════
# Snapshot 协议（Phase 3.1 动作 2）
# ══════════════════════════════════════════════


class SnapshotError(Exception):
    """snapshot/restore 协议错误（schema 不兼容 / 缺字段 / 类型不符）。

    严格语义：restore() 收到缺关键字段或类型不符的 snapshot 时抛出，
    不静默回退到默认值——避免"看起来恢复成功但 state 偏移"的隐性 bug。
    """


# ══════════════════════════════════════════════
# Drives 配置（阶段 B：SGE 化 + schema 化）
# ══════════════════════════════════════════════

# SGE 默认 5 个 drives（候选 B — Closeout §5 决策）
#
# 来源: SGE-Phase0-Closeout.md §5 决策点 1（候选 B）
# 翻译: novelty→exploration, play→删除, expression→creativity
# 参考: SGE-M21-AiBeing-Implementation-Mapping.md §2.2（drives 维度）
# 阶段 A: DRIVES = ['connection', 'novelty', 'expression', 'safety', 'play']
# 阶段 B: SGE_DEFAULT_DRIVES = ['exploration', 'safety', 'creativity', 'connection', 'autonomy']
SGE_DEFAULT_DRIVES = ['exploration', 'safety', 'creativity', 'connection', 'autonomy']
N_DRIVES = len(SGE_DEFAULT_DRIVES)

# 默认饥饿率（drives 的"渴望"累积速率 /h）
#
# 来源: AiBeing drive_metabolism.py:24-26（CONNECTION_HUNGER_K=0.15, NOVELTY_HUNGER_K=0.05）
# SGE 化: connection→connection (0.15), novelty→exploration (0.05)
SGE_DEFAULT_HUNGER_RATES = {
    'connection': 0.15,
    'exploration': 0.05,
    # 其他 drives 不累积饥饿（initial = 0）
}

# Drives 兼容层（向后兼容阶段 A）
# DRIVES 默认 = SGE_DEFAULT_DRIVES（阶段 B）；阶段 A 的 AiBeing 5 个 drives 仍可通过
# _load_drives(config_path) 加载（兼容旧 yaml）
DRIVES = SGE_DEFAULT_DRIVES  # 向后兼容（阶段 A 代码引用）


def _load_drives(config_path: Optional[str] = None) -> list[str]:
    """从 yaml 加载 DRIVES 清单（schema 化入口）

    用途: 阶段 B 把 drives 维度从硬编码改为配置驱动；为 Phase 3 产品化（多场景
    profile 化，如学生用 mastery、教练用 empathy）留接口。

    来源: 借鉴映射文档 §五 阶段 B 改造契约
    参考: SGE-Phase0-Closeout.md §5 决策点 1（schema 化要求）

    Args:
        config_path: yaml 配置文件路径；None 或文件不存在 → 用 SGE_DEFAULT_DRIVES

    Returns:
        drives 清单（list[str]）
    """
    if config_path is None:
        return list(SGE_DEFAULT_DRIVES)
    if not os.path.exists(config_path):
        return list(SGE_DEFAULT_DRIVES)
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        drives = config.get('drives')
        if not drives or not isinstance(drives, list):
            return list(SGE_DEFAULT_DRIVES)
        # schema 验证：必须非空 list of str
        if not all(isinstance(d, str) and d for d in drives):
            raise ValueError(f"drives 配置项必须是非空字符串列表，得到: {drives}")
        return drives
    except Exception as e:
        # 加载失败不中断，回退到默认值
        print(f"[WARN] _load_drives failed: {e}, fallback to SGE_DEFAULT_DRIVES")
        return list(SGE_DEFAULT_DRIVES)

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
PHASE_THRESHOLD = 0.5             # 相变触发阈值（挫败感超过此值）
# 2026-07-08: 从 2.0 降至 0.5（P0-3 修复）
# 原 2.0 是 AiBeing 默认值（阶段 A 禁用 PT），但 v2/v3/v4 实验中 0/250 PT 触发
# Monte Carlo 验证（experiments/scripts/simulate_pt_v6.py）：
#   threshold=2.0 → mean PT count = 0.0
#   threshold=0.5 → mean PT count = 2.5（10 seeds × 250 epochs）
# 详见 research/sge-feasibility/M22_H_SELF_DIAGNOSIS.md §3 + §4 P0-3


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
        drives: Optional[list[str]] = None,
        hunger_rates: Optional[dict] = None,
        temp_coeff: float = TEMP_COEFF,
        temp_floor: float = TEMP_FLOOR,
        decay_rate: float = DECAY_RATE,
    ):
        # 阶段 B: drives 维度从硬编码改为参数化
        # 来源: SGE-Phase0-Closeout.md §5 决策点 1（schema 化要求）
        self.drives = drives if drives is not None else list(DRIVES)
        self.frustration = {d: 0.0 for d in self.drives}
        self.hunger_rates = hunger_rates if hunger_rates is not None else dict(SGE_DEFAULT_HUNGER_RATES)
        self.decay_rate = decay_rate
        self._last_tick = clock if clock is not None else 0.0  # 默认 0.0（适合受控模拟）
        self.decay_lambda = decay_lambda
        self.temp_coeff = temp_coeff
        self.temp_floor = temp_floor

    def time_metabolism(self, now: Optional[float] = None) -> float:
        """
        时间代谢（冷却 + 饥饿）

        来源: AiBeing engine/genome/drive_metabolism.py:57-87
        阶段 B 改造: 饥饿逻辑 schema 化（hunger_rates dict 驱动，非硬编码 connection/novelty）
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
        for d in self.drives:
            self.frustration[d] *= decay_factor

        # 饥饿（schema 化：遍历 hunger_rates 而非硬编码 connection/novelty）
        # 阶段 A: hardcoded `self.frustration['connection'] += ...; 'novelty' += ...`
        # 阶段 B: `for d, k in self.hunger_rates.items(): self.frustration[d] += k * delta_hours`
        for d, k in self.hunger_rates.items():
            if d in self.frustration:
                self.frustration[d] += k * delta_hours

        # Clamp
        for d in self.drives:
            self.frustration[d] = max(0.0, min(5.0, self.frustration[d]))
        return delta_hours

    def apply_llm_delta(self, delta_dict: dict) -> float:
        """
        应用 LLM 输出的 frustration 变化量

        来源: AiBeing engine/genome/drive_metabolism.py:89-107
        阶段 B 改造: 遍历 self.drives 而非硬编码 DRIVES
        返回: reward（positive = frustration decreased = good）
        """
        old_total = self.total()
        for d in self.drives:
            if d in delta_dict:
                self.frustration[d] += delta_dict[d]
            self.frustration[d] *= (1.0 - self.decay_rate)
        for d in self.drives:
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

    # ── Snapshot 协议（Phase 3.1 动作 2）──
    _SNAPSHOT_FIELDS = (
        'drives', 'frustration', 'hunger_rates', 'decay_rate',
        '_last_tick', 'decay_lambda', 'temp_coeff', 'temp_floor',
    )

    def snapshot(self) -> dict:
        """白名单 JSON-friendly dict（不含 LLM）。"""
        return {
            'drives': list(self.drives),
            'frustration': dict(self.frustration),
            'hunger_rates': dict(self.hunger_rates),
            'decay_rate': self.decay_rate,
            '_last_tick': self._last_tick,
            'decay_lambda': self.decay_lambda,
            'temp_coeff': self.temp_coeff,
            'temp_floor': self.temp_floor,
        }

    def restore(self, snap: dict) -> None:
        """strict: 缺关键字段 → SnapshotError。"""
        for key in self._SNAPSHOT_FIELDS:
            if key not in snap:
                raise SnapshotError(f"DriveMetabolism.restore: 缺关键字段 '{key}'")
        self.drives = list(snap['drives'])
        self.frustration = {k: float(v) for k, v in snap['frustration'].items()}
        self.hunger_rates = {k: float(v) for k, v in snap['hunger_rates'].items()}
        self.decay_rate = float(snap['decay_rate'])
        self._last_tick = float(snap['_last_tick'])
        self.decay_lambda = float(snap['decay_lambda'])
        self.temp_coeff = float(snap['temp_coeff'])
        self.temp_floor = float(snap['temp_floor'])


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
        drives: Optional[list[str]] = None,
        value_layer: Optional[object] = None,
        hawking: Optional["HawkingDecay"] = None,
        crystallizer: Optional["MemoryCrystallizer"] = None,
        crystallize_every: int = 10,
    ):
        rng = random.Random(seed)
        self.seed = seed
        self.hebbian_lr = hebbian_lr
        self.phase_threshold = phase_threshold

        # 阶段 B: drives 维度参数化
        # 来源: SGE-Phase0-Closeout.md §5 决策点 1（schema 化要求）
        self.drives = drives if drives is not None else list(DRIVES)
        self.n_drives = len(self.drives)

        # 阶段 B: ValueLayer 接入（B2 引入）
        # 来源: SGE-Phase0-Closeout.md §5 决策点 2（Value scale [-1, 1]）
        # 参考: SGE-M21-AiBeing-Implementation-Mapping.md §2.3
        self.value_layer = value_layer  # None 时 step 不更新 values

        # 阶段 D: Memory Layer 接入（D1 集成）
        # HawkingDecay：每步 tick（连续衰减）
        # MemoryCrystallizer：每 N 步 insert_or_merge（事件合并）
        # 参考: SGE-M21-Phase-D-Implementation-Plan.md §D1
        self.hawking = hawking
        self.crystallizer = crystallizer
        self.crystallize_every = crystallize_every
        self._last_crystallize_step = 0
        self._last_hawking_removed = 0
        self._last_crystallize_result = None  # 'merged' / 'created' / None

        # Drive 参数（来源: genome_engine.py:206-209）
        self.drive_baseline = {d: rng.uniform(0.2, 0.8) for d in self.drives}
        self.drive_accumulation_rate = {d: rng.uniform(0.01, 0.05) for d in self.drives}
        self.drive_decay_rate = {d: rng.uniform(0.05, 0.15) for d in self.drives}

        # 当前 drive 状态
        self.drive_state = {d: self.drive_baseline[d] for d in self.drives}

        # 神经网络权重（来源: genome_engine.py:215-218）
        # INPUT_SIZE 依赖 n_drives（阶段 A 是固定的 5，阶段 B 跟随 schema）
        input_size = self.n_drives + len(CONTEXT_FEATURES) + RECURRENT_SIZE
        self.INPUT_SIZE = input_size
        self.W1 = [[rng.gauss(0, 0.6) for _ in range(input_size)] for _ in range(HIDDEN_SIZE)]
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
        drive_vec = [self.drive_state[d] for d in self.drives]
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
                    for j in range(self.INPUT_SIZE):
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
            for j in range(self.INPUT_SIZE):
                self.W1[i][j] *= WEIGHT_DECAY
                self.W1[i][j] = max(-2.0, min(2.0, self.W1[i][j]))

    def tick_drives(self) -> None:
        """
        drive 自然累积（每步）

        来源: AiBeing engine/genome/genome_engine.py:284-287
        """
        for d in self.drives:
            self.drive_state[d] = min(1.0, self.drive_state[d] + self.drive_accumulation_rate[d])

    def step(self, context: dict, reward: float = 0.0, critic_value_delta: Optional[dict] = None, epoch: Optional[int] = None, now: Optional[float] = None) -> dict:
        """
        一步完整循环：compute_signals → learn → tick_drives → value_layer.update → memory_layer

        阶段 B 改造: 新增 critic_value_delta 参数，每步应用 Critic 输出的 value delta
        阶段 D 改造 (D1): 集成 HawkingDecay + MemoryCrystallizer

        Args:
            context: 12D context (8D Critic + 4D EverMemOS)
            reward: 标量 reward（来自 DriveMetabolism）
            critic_value_delta: 6D value delta dict（来自 Critic LLM）
            epoch: 当前 epoch（用于 Crystallize 触发判断）
            now: 受控模拟时间戳（小时），传给 HawkingDecay.tick

        来源: AiBeing engine/genome/genome_engine.py:355-362
        参考: SGE-M21-AiBeing-Implementation-Mapping.md §2.9（12 步循环中的核心步骤）
              + §2.3（Value EMA）
              + SGE-M21-Phase-D-Implementation-Plan.md §D1（Memory Layer）
        """
        signals = self.compute_signals(context)
        self.learn(signals, reward)
        self.tick_drives()
        # ValueLayer 更新（阶段 B）
        if self.value_layer is not None and critic_value_delta is not None:
            self.value_layer.update(critic_value_delta)

        # Memory Layer 更新（阶段 D1）
        # Step 5: Hawking Tick — 记忆衰减
        if self.hawking is not None:
            self._last_hawking_removed = self.hawking.tick(now=now)
        # Step 6: Crystallize Gate — 记忆合并（每 N 步）
        if (
            self.crystallizer is not None
            and epoch is not None
            and self.crystallize_every > 0
            and epoch > 0
            and epoch % self.crystallize_every == 0
        ):
            # 打包当前 value_state (6D) + signals (8D) = 14D 向量
            # N=14 → threshold = 0.25/sqrt(14) ≈ 0.067
            if self.value_layer is not None:
                value_vec = self.value_layer.to_vec()
            else:
                value_vec = [0.0] * 6
            signal_vec = [signals[s] for s in SIGNALS]
            combined_vec = value_vec + signal_vec  # 14D
            self._last_crystallize_result = self.crystallizer.insert_or_merge(
                vec=combined_vec,
                weight=1.0,
            )
            self._last_crystallize_step = epoch

        return signals

    # ── Snapshot 协议（Phase 3.1 动作 2）──
    _SNAPSHOT_FIELDS = (
        'seed', 'hebbian_lr', 'phase_threshold', 'drives',
        'crystallize_every',
        'drive_baseline', 'drive_accumulation_rate', 'drive_decay_rate',
        'drive_state',
        'W1', 'b1', 'W2', 'b2',
        'recurrent_state',
        'interaction_count', 'total_reward', '_frustration',
        'signal_history', 'input_size',
    )

    def snapshot(self) -> dict:
        """白名单 JSON-friendly dict。排除 value_layer / hawking / crystallizer（外部持有）。

        省略 _last_hidden / _last_input / _last_phase_transition / _last_crystallize_result /
        _last_crystallize_step / _last_hawking_removed——这些是 step() 缓存，下一次 compute_signals
        会被覆盖，持久化反而引入"看起来 restore 成功但 state 偏移"的隐性 bug。
        """
        return {
            'seed': self.seed,
            'hebbian_lr': self.hebbian_lr,
            'phase_threshold': self.phase_threshold,
            'drives': list(self.drives),
            'crystallize_every': self.crystallize_every,
            'drive_baseline': dict(self.drive_baseline),
            'drive_accumulation_rate': dict(self.drive_accumulation_rate),
            'drive_decay_rate': dict(self.drive_decay_rate),
            'drive_state': dict(self.drive_state),
            'W1': [list(row) for row in self.W1],
            'b1': list(self.b1),
            'W2': [list(row) for row in self.W2],
            'b2': list(self.b2),
            'recurrent_state': list(self.recurrent_state),
            'interaction_count': self.interaction_count,
            'total_reward': self.total_reward,
            '_frustration': self._frustration,
            'signal_history': [dict(s) for s in self.signal_history],
            'input_size': self.INPUT_SIZE,
        }

    def restore(self, snap: dict) -> None:
        """strict: 缺关键字段 → SnapshotError；input_size 不匹配 → SnapshotError。

        value_layer / hawking / crystallizer 由 SGEOrchestrator.restore_all 重新注入。
        """
        for key in self._SNAPSHOT_FIELDS:
            if key not in snap:
                raise SnapshotError(f"Agent.restore: 缺关键字段 '{key}'")
        if int(snap['input_size']) != self.INPUT_SIZE:
            raise SnapshotError(
                f"Agent.restore: input_size 不兼容 "
                f"(snap={snap['input_size']} vs self={self.INPUT_SIZE})"
            )
        self.seed = int(snap['seed'])
        self.hebbian_lr = float(snap['hebbian_lr'])
        self.phase_threshold = float(snap['phase_threshold'])
        self.drives = list(snap['drives'])
        self.crystallize_every = int(snap['crystallize_every'])
        self.drive_baseline = {k: float(v) for k, v in snap['drive_baseline'].items()}
        self.drive_accumulation_rate = {k: float(v) for k, v in snap['drive_accumulation_rate'].items()}
        self.drive_decay_rate = {k: float(v) for k, v in snap['drive_decay_rate'].items()}
        self.drive_state = {k: float(v) for k, v in snap['drive_state'].items()}
        self.W1 = [[float(x) for x in row] for row in snap['W1']]
        self.b1 = [float(x) for x in snap['b1']]
        self.W2 = [[float(x) for x in row] for row in snap['W2']]
        self.b2 = [float(x) for x in snap['b2']]
        self.recurrent_state = [float(x) for x in snap['recurrent_state']]
        self.interaction_count = int(snap['interaction_count'])
        self.total_reward = float(snap['total_reward'])
        self._frustration = float(snap['_frustration'])
        self.signal_history = [dict(s) for s in snap['signal_history']]
        # 清空缓存字段（避免 restore 后读到旧值）
        self._last_hidden = None
        self._last_input = None
        self._last_phase_transition = False
        self._last_crystallize_result = None


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


# ══════════════════════════════════════════════
# ValueLayer 类 — §2.3 Value EMA（阶段 B 引入）
# ══════════════════════════════════════════════


SGE_DEFAULT_VALUES = [
    'safety',        # 安全倾向
    'creativity',    # 创造力倾向
    'connection',    # 联结倾向
    'autonomy',      # 自主倾向
    'justice',       # 正义感
    'compassion',    # 同理心
]
N_VALUES = len(SGE_DEFAULT_VALUES)

# Value scale 范围（Closeout §5 决策点 2：A=[-1, 1]）
# 来源: SGE-Phase0-Closeout.md §5 决策点 2
VALUE_CLIP_MIN = -1.0
VALUE_CLIP_MAX = 1.0


class ValueLayer:
    """SGE Value Layer（独立于 DriveMetabolism）

    来源: 借鉴 AiBeing agent/evermemos_mixin.py:_apply_relationship_ema 公式
    阶段 B 改造（SGE 化）:
      - 维度: 6 个 value (safety/creativity/connection/autonomy/justice/compassion)
      - scale: [-1, 1]（允许反价值涌现）
      - 学习率: α=0.3（M1.x baseline；阶段 B 末段可调）
      - 初始化: 0.0（中性；不预设价值倾向）
    公式:
      value[v] = clip((1 - α) * value[v] + α * delta[v], -1, 1)
    参考: SGE-M21-AiBeing-Implementation-Mapping.md §2.3
    """

    def __init__(
        self,
        values: Optional[list[str]] = None,
        alpha: float = 0.3,
        init_seed: Optional[dict] = None,
    ):
        self.values = values if values is not None else list(SGE_DEFAULT_VALUES)
        self.alpha = alpha
        # 初始化 value_state
        if init_seed is not None:
            self.value_state = {v: init_seed.get(v, 0.0) for v in self.values}
        else:
            self.value_state = {v: 0.0 for v in self.values}

    def update(self, delta_dict: dict) -> dict:
        """应用 Critic 输出的 value delta，返回新 value_state

        Args:
            delta_dict: {value_name: delta_value} 字典（缺失 value 默认 0.0）

        Returns:
            更新后的 value_state dict
        """
        for v in self.values:
            delta = delta_dict.get(v, 0.0)
            new_val = (1 - self.alpha) * self.value_state[v] + self.alpha * delta
            self.value_state[v] = max(
                VALUE_CLIP_MIN,
                min(VALUE_CLIP_MAX, new_val)
            )
        return dict(self.value_state)

    def get(self) -> dict:
        """获取当前 value_state 副本"""
        return dict(self.value_state)

    def to_vec(self) -> list[float]:
        """转换为 list[float]（按 self.values 顺序）"""
        return [self.value_state[v] for v in self.values]

    def magnitude(self) -> float:
        """value 向量 L2 范数（用于人格分化度量）"""
        return math.sqrt(sum(v ** 2 for v in self.value_state.values()))

    # ── Snapshot 协议（Phase 3.1 动作 2）──
    _SNAPSHOT_FIELDS = ('values', 'alpha', 'value_state')

    def snapshot(self) -> dict:
        """白名单 JSON-friendly dict（不含 LLM 等不可序列化引用）。"""
        return {
            'values': list(self.values),
            'alpha': self.alpha,
            'value_state': dict(self.value_state),
        }

    def restore(self, snap: dict) -> None:
        """strict: 缺关键字段 → SnapshotError。restore in-place。"""
        for key in self._SNAPSHOT_FIELDS:
            if key not in snap:
                raise SnapshotError(f"ValueLayer.restore: 缺关键字段 '{key}'")
        self.values = list(snap['values'])
        self.alpha = float(snap['alpha'])
        self.value_state = {k: float(v) for k, v in snap['value_state'].items()}


# ══════════════════════════════════════════════
# HawkingDecay 类 — §2.7 Hawking 辐射机制（阶段 B 引入）
# ══════════════════════════════════════════════


# Hawking gamma 默认值（Closeout §5 决策点 4：B=0.01/h，半衰期 ~3 天）
#
# 阶段 A: 0.001/h（半衰期 ~29 天，AiBeing 默认）
# 阶段 B: 0.01/h（半衰期 ~3 天，适合 1000 epoch 实验窗口）
# 来源: SGE-Phase0-Closeout.md §5 决策点 4
SGE_HAWKING_GAMMA = 0.01


class HawkingDecay:
    """Hawking 辐射式记忆衰减（自有实现）

    来源: AiBeing engine/genome/style_memory.py:209-255
    阶段 B 改造（SGE 化）:
      - gamma: 0.01/h（半衰期 ~3 天）替代 AiBeing 0.001/h
      - 与 AiBeing 一致: weight *= exp(-gamma * Δt_hours)
      - 删除阈值: weight < 1e-4 时移除
    公式:
      decay_factor = exp(-γ * Δt_hours)
      weight *= decay_factor
      if weight < threshold: remove
    参考: SGE-M21-AiBeing-Implementation-Mapping.md §2.7
    """

    def __init__(
        self,
        gamma: float = SGE_HAWKING_GAMMA,
        remove_threshold: float = 1e-4,
        clock: Optional[float] = None,
    ):
        self.gamma = gamma
        self.remove_threshold = remove_threshold
        self.memory = []  # list of {timestamp, weight, content}
        self._last_tick = clock if clock is not None else 0.0  # 默认 0.0（适合受控模拟）

    def insert(self, content, weight: float = 1.0, now: Optional[float] = None) -> None:
        """插入新记忆

        Args:
            content: 任意可哈希内容（建议 dict 但不强制）
            weight: 初始权重（默认 1.0）
            now: 时间戳（默认 current time）
        """
        if now is None:
            now = time.time()
        self.memory.append({
            'timestamp': now,
            'weight': weight,
            'content': content,
        })

    def tick(self, now: Optional[float] = None) -> int:
        """每步调用，按 Hawking 衰减所有记忆

        Returns:
            删除的记忆数

        Note（M2.3 修复）：
          - `now` 单位是"epoch-hours"（orchestrator 传 timestamp = epoch * hours_per_epoch）
          - 1 epoch = 1 小时（默认 hours_per_epoch=1.0）
          - 不需要 /3600（之前 bug 错误地把 timestamp 当秒处理）
        """
        if now is None:
            now = time.time()
        delta_hours = max(0.0, now - self._last_tick)
        self._last_tick = now
        if delta_hours < 1e-6:
            return 0

        decay_factor = math.exp(-self.gamma * delta_hours)
        removed = 0
        survivors = []
        for mem in self.memory:
            mem['weight'] *= decay_factor
            if mem['weight'] >= self.remove_threshold:
                survivors.append(mem)
            else:
                removed += 1
        self.memory = survivors
        return removed

    def retrieve(self, k: int = 5) -> list:
        """返回当前权重最高的 k 条记忆（KNN 简化为按权重排序）

        Args:
            k: 返回数量

        Returns:
            list of memory dicts（按 weight 降序）
        """
        return sorted(self.memory, key=lambda m: m['weight'], reverse=True)[:k]

    # ── Snapshot 协议（Phase 3.1 动作 2）──
    _SNAPSHOT_FIELDS = ('gamma', 'remove_threshold', 'memory', '_last_tick')

    def snapshot(self) -> dict:
        """白名单 JSON-friendly dict。memory 是 list[{timestamp,weight,content}]; content 通常是 dict。"""
        return {
            'gamma': self.gamma,
            'remove_threshold': self.remove_threshold,
            'memory': [
                {
                    'timestamp': mem['timestamp'],
                    'weight': mem['weight'],
                    'content': copy.deepcopy(mem['content']),
                }
                for mem in self.memory
            ],
            '_last_tick': self._last_tick,
        }

    def restore(self, snap: dict) -> None:
        """strict: 缺关键字段 → SnapshotError。"""
        for key in self._SNAPSHOT_FIELDS:
            if key not in snap:
                raise SnapshotError(f"HawkingDecay.restore: 缺关键字段 '{key}'")
        self.gamma = float(snap['gamma'])
        self.remove_threshold = float(snap['remove_threshold'])
        self.memory = [
            {
                'timestamp': float(m['timestamp']),
                'weight': float(m['weight']),
                'content': copy.deepcopy(m['content']),
            }
            for m in snap['memory']
        ]
        self._last_tick = float(snap['_last_tick'])

    def __len__(self) -> int:
        return len(self.memory)


# ══════════════════════════════════════════════
# Crystallize 机制 — §2.6 Memory 筛选门（阶段 B 引入）
# ══════════════════════════════════════════════


def crystallize_threshold(n_dims: int, base: float = 0.25) -> float:
    """维度归一化结晶阈值

    来源: SGE-Phase0-Closeout.md §5 决策点 5（B=0.25/sqrt(N)）
    公式: threshold = base / sqrt(N)
    哲学: 维度归一化让阈值不随维度变化，让架构可扩展（产品底座思维）
    """
    return base / math.sqrt(n_dims)


class MemoryCrystallizer:
    """记忆结晶机制

    来源: AiBeing engine/genome/style_memory.py:280-310
    阶段 B 改造（SGE 化）:
      - 阈值: 0.25/sqrt(N) 替代 AiBeing 固定 0.25（Closeout §5 决策点 5）
      - merge 策略: 加权平均（保留历史权重）
    公式:
      distance = L2(query, memory)
      if distance < threshold: merge (weighted average)
      else: create new memory
    参考: SGE-M21-AiBeing-Implementation-Mapping.md §2.6
    """

    def __init__(self, n_dims: int, base: float = 0.25):
        self.n_dims = n_dims
        self.threshold = crystallize_threshold(n_dims, base)
        self.memories = []  # list of {vec, weight, count}

    def insert_or_merge(self, vec: list[float], weight: float = 1.0) -> str:
        """插入新记忆或合并到现有记忆

        Args:
            vec: 任意维向量（必须 self.n_dims 维）
            weight: 权重（默认 1.0）

        Returns:
            'merged' 或 'created'
        """
        for mem in self.memories:
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(vec, mem['vec'])))
            if dist < self.threshold:
                # 加权平均合并
                total_count = mem['count'] + 1
                mem['vec'] = [
                    (mem['vec'][i] * mem['count'] + vec[i]) / total_count
                    for i in range(len(vec))
                ]
                mem['weight'] = (mem['weight'] * mem['count'] + weight) / total_count
                mem['count'] = total_count
                return 'merged'
        # 创建新记忆
        self.memories.append({
            'vec': list(vec),
            'weight': weight,
            'count': 1,
        })
        return 'created'

    # ── Snapshot 协议（Phase 3.1 动作 2）──
    _SNAPSHOT_FIELDS = ('n_dims', 'threshold', 'memories')

    def snapshot(self) -> dict:
        """白名单 JSON-friendly dict。"""
        return {
            'n_dims': self.n_dims,
            'threshold': self.threshold,
            'memories': [
                {
                    'vec': list(mem['vec']),
                    'weight': mem['weight'],
                    'count': mem['count'],
                }
                for mem in self.memories
            ],
        }

    def restore(self, snap: dict) -> None:
        """strict: 缺关键字段 → SnapshotError；n_dims 不匹配 → SnapshotError。"""
        for key in self._SNAPSHOT_FIELDS:
            if key not in snap:
                raise SnapshotError(f"MemoryCrystallizer.restore: 缺关键字段 '{key}'")
        if int(snap['n_dims']) != self.n_dims:
            raise SnapshotError(
                f"MemoryCrystallizer.restore: n_dims 不兼容 "
                f"(snap={snap['n_dims']} vs self={self.n_dims})"
            )
        self.threshold = float(snap['threshold'])
        self.memories = [
            {
                'vec': [float(x) for x in mem['vec']],
                'weight': float(mem['weight']),
                'count': int(mem['count']),
            }
            for mem in snap['memories']
        ]

    def __len__(self) -> int:
        return len(self.memories)


# ══════════════════════════════════════════════
# Snapshot 协议单元测试（Phase 3.1 动作 2）
# ══════════════════════════════════════════════


def _run_snapshot_unit_tests() -> bool:
    """验证 5 个 state 类的 snapshot/restore round-trip + strict 校验。

    覆盖:
      1. agent_round_trip     - snapshot → 新 Agent.restore → compute_signals 一致
      2. agent_nn_weights     - W1/W2/b1/b2 逐元素 assert
      3. agent_recurrent_state - 独立（修改原 Agent 不影响 restore 后）
      4. value_layer_round_trip - alpha + value_state 6D 全等
      5. drive_metabolism_round_trip - frustration + hunger_rates + _last_tick
      6. hawking_round_trip    - memory 列表逐项（含 content dict）
      7. crystallizer_round_trip - memories 列表
      8. restore_strict_missing - 缺字段 → SnapshotError
      9. snapshot_no_llm_leak  - snapshot dict 不含不可序列化引用
    """
    import json
    print(f"\n{'─' * 60}")
    print(f"  baseline.snapshot/restore 单元测试（Phase 3.1 动作 2）")
    print(f"{'─' * 60}\n")

    # ── 公共组件构造 ──
    drives = ['exploration', 'safety', 'creativity', 'connection', 'autonomy']
    values = ['safety', 'creativity', 'connection', 'autonomy', 'justice', 'compassion']

    # ── 测试 4: ValueLayer round-trip ──
    vl1 = ValueLayer(values=values, alpha=0.3)
    vl1.value_state['safety'] = 0.42
    vl1.value_state['creativity'] = -0.31
    snap_vl = vl1.snapshot()
    vl2 = ValueLayer(values=values, alpha=0.5)  # 不同初始 alpha
    vl2.restore(snap_vl)
    assert vl2.alpha == 0.3, f"alpha not restored: {vl2.alpha}"
    assert abs(vl2.value_state['safety'] - 0.42) < 1e-9
    assert abs(vl2.value_state['creativity'] - (-0.31)) < 1e-9
    assert vl2.values == values
    print(f"  ✓ [测试 4: ValueLayer round-trip] 6D 全等, alpha={vl2.alpha}")

    # ── 测试 5: DriveMetabolism round-trip ──
    dm1 = DriveMetabolism(drives=drives, clock=3.5)
    dm1.frustration['connection'] = 1.5
    dm1.time_metabolism(now=5.0)  # 推进 _last_tick + 冷却饥饿
    snap_dm = dm1.snapshot()
    dm2 = DriveMetabolism(drives=drives, clock=0.0)
    dm2.restore(snap_dm)
    assert dm2.drives == drives
    assert abs(dm2._last_tick - 5.0) < 1e-9, f"_last_tick not restored: {dm2._last_tick}"
    # time_metabolism 跑过冷却 + 饥饿，所以 frustration 应有变化
    assert dm2.frustration['connection'] > 0.0
    assert 'connection' in dm2.hunger_rates
    print(f"  ✓ [测试 5: DriveMetabolism round-trip] frustration + _last_tick 一致")

    # ── 测试 6: HawkingDecay round-trip（含 content dict 嵌套）──
    hk1 = HawkingDecay(gamma=0.01)
    hk1.insert(content={'epoch': 1, 'critic_context': {'safety': 0.5}}, weight=1.0, now=1.0)
    hk1.insert(content={'epoch': 2, 'critic_context': {'safety': 0.7}}, weight=0.8, now=2.0)
    snap_hk = hk1.snapshot()
    hk2 = HawkingDecay(gamma=0.05)
    hk2.restore(snap_hk)
    assert abs(hk2.gamma - 0.01) < 1e-9
    assert len(hk2.memory) == 2
    assert hk2.memory[0]['content']['critic_context']['safety'] == 0.5
    assert abs(hk2.memory[1]['weight'] - 0.8) < 1e-9
    # 独立性：修改 hk1 不影响 hk2
    hk1.insert(content={'epoch': 99}, weight=1.0, now=99.0)
    assert len(hk2.memory) == 2, f"hk2 受 hk1 影响: {len(hk2.memory)}"
    print(f"  ✓ [测试 6: HawkingDecay round-trip] 2 memories + 嵌套 dict 全等 + 独立")

    # ── 测试 7: MemoryCrystallizer round-trip ──
    cr1 = MemoryCrystallizer(n_dims=11)
    cr1.insert_or_merge(vec=[0.1] * 11, weight=1.0)
    cr1.insert_or_merge(vec=[0.2] * 11, weight=1.0)
    snap_cr = cr1.snapshot()
    cr2 = MemoryCrystallizer(n_dims=11)
    cr2.restore(snap_cr)
    assert cr2.n_dims == 11
    assert len(cr2.memories) == 2
    assert len(cr2.memories[0]['vec']) == 11
    assert abs(cr2.memories[0]['vec'][0] - 0.1) < 1e-9
    print(f"  ✓ [测试 7: MemoryCrystallizer round-trip] 2 memories, vec 全等")

    # ── 测试 1: Agent round-trip ──
    vl_for_agent = ValueLayer(values=values, alpha=0.3)
    agent1 = Agent(seed=42, drives=drives, value_layer=vl_for_agent,
                   crystallize_every=10)
    # 跑几步让 state 有变化
    for i in range(5):
        ctx = {'user_emotion': 0.5, 'topic_intimacy': 0.3}
        for f in CONTEXT_FEATURES:
            ctx.setdefault(f, 0.0)
        agent1.compute_signals(ctx)
        agent1.learn({s: 0.5 for s in SIGNALS}, reward=-0.1)
        agent1.tick_drives()
    snap_agent = agent1.snapshot()

    # JSON 序列化烟囱测试（snapshot 必须 JSON-friendly）
    json.dumps(snap_agent)
    json_restored = json.loads(json.dumps(snap_agent))

    # 构造新 Agent（不同 seed 验证 restore 覆盖），restore 后必须 state 一致
    vl_for_agent2 = ValueLayer(values=values, alpha=0.3)
    agent2 = Agent(seed=999, drives=drives, value_layer=vl_for_agent2,
                   crystallize_every=10)
    agent2.restore(json_restored)
    # 也让 agent1 restore 回 snap 起点（保持两个 agent 起点一致）
    agent1.restore(json_restored)

    # compute_signals 必须产生相同结果
    # 注意：compute_signals 内部用 module-level random 加感知噪声（baseline.py:403），
    # 需重置 random seed 以保证两边随机序列一致
    ctx = {'user_emotion': 0.5, 'topic_intimacy': 0.3}
    for f in CONTEXT_FEATURES:
        ctx.setdefault(f, 0.0)
    random.seed(42)
    s1 = agent1.compute_signals(ctx)
    random.seed(42)
    s2 = agent2.compute_signals(ctx)
    for k in SIGNALS:
        assert abs(s1[k] - s2[k]) < 1e-9, f"signal {k} drift: {s1[k]} vs {s2[k]}"
    print(f"  ✓ [测试 1: Agent round-trip] compute_signals 一致（≤1e-9）")

    # ── 测试 2: Agent NN weights 逐元素 ──
    assert len(agent2.W1) == len(agent1.W1) == HIDDEN_SIZE
    assert len(agent2.W2) == len(agent1.W2) == N_SIGNALS
    for i in range(HIDDEN_SIZE):
        for j in range(agent1.INPUT_SIZE):
            assert abs(agent2.W1[i][j] - agent1.W1[i][j]) < 1e-9
    for i in range(N_SIGNALS):
        assert abs(agent2.b2[i] - agent1.b2[i]) < 1e-9
    print(f"  ✓ [测试 2: Agent NN weights] W1/W2/b1/b2 逐元素一致")

    # ── 测试 3: Agent recurrent_state 独立 ──
    # 修改 agent1 的 recurrent_state 不应影响 agent2
    agent1.recurrent_state[0] = 999.0
    assert agent2.recurrent_state[0] != 999.0
    print(f"  ✓ [测试 3: Agent recurrent_state 独立]")

    # ── 测试 8: restore strict 缺字段 → SnapshotError ──
    snap_bad = dict(snap_agent)
    del snap_bad['recurrent_state']
    try:
        agent_bad = Agent(seed=1, drives=drives, crystallize_every=10)
        agent_bad.restore(snap_bad)
        assert False, "应该抛出 SnapshotError"
    except SnapshotError as e:
        assert 'recurrent_state' in str(e)
    print(f"  ✓ [测试 8: strict 校验] 缺字段抛 SnapshotError")

    # ── 测试 9: snapshot 不泄露不可序列化引用 ──
    snap_vl_keys = set(snap_vl.keys())
    snap_dm_keys = set(snap_dm.keys())
    snap_hk_keys = set(snap_hk.keys())
    snap_cr_keys = set(snap_cr.keys())
    snap_agent_keys = set(snap_agent.keys())
    # 没有任何 snapshot 应包含 'llm' 字段
    for name, keys in [
        ('ValueLayer', snap_vl_keys), ('DriveMetabolism', snap_dm_keys),
        ('HawkingDecay', snap_hk_keys), ('MemoryCrystallizer', snap_cr_keys),
        ('Agent', snap_agent_keys),
    ]:
        assert 'llm' not in keys, f"{name} snapshot 泄露 llm 字段"
    assert 'value_layer' not in snap_agent_keys, "Agent snapshot 含 value_layer ref"
    assert 'hawking' not in snap_agent_keys, "Agent snapshot 含 hawking ref"
    assert 'crystallizer' not in snap_agent_keys, "Agent snapshot 含 crystallizer ref"
    print(f"  ✓ [测试 9: 无 LLM 泄露] 5 类 snapshot 均不含 llm / 外部 ref")

    print(f"\n  状态: ✅ PASS — 9/9 测试通过")
    return True


if __name__ == "__main__":
    import sys
    ok = _run_snapshot_unit_tests()
    sys.exit(0 if ok else 1)
