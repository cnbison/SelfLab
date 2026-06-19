"""
SGE Event Generator（C1 实施）

本文件是 **SGE 自有实现**——不 import AiBeing 项目代码，不依赖外部项目路径。

**实现来源标注规范**（每个函数/类 docstring 包含三项）：
  1. "来源: DESIGN §..." — 设计依据
  2. "公式: ..." — 核心逻辑
  3. "参考: SGE-M21-Phase-C-Implementation-Plan.md §C1/C2" — 实施计划

**C1（Event Generator 完整化）**：
- LifeEvent dataclass（DESIGN §2.1 标准结构）
- make_event_id() 规范（DESIGN §2.1）
- 6 类型事件模板库（success/failure/relationship/exploration/risk/value_conflict）
- EventGenerator 类（DESIGN §2.2 动态生成 + 因果链上下文）

**C2（Value Conflict Generator）**：
- generate_value_conflict() 函数（DESIGN §2.3）
- VALUE_CONFLICT_TEMPLATES 模板库（30 个 value 对组合）

**FR-1 验收**：
- 同类事件的因果逻辑一致
- 事件多样性覆盖至少 6 种基本类型
- 价值困境事件能有效触发认知失调
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════
# LifeEvent 数据类（DESIGN §2.1）
# ══════════════════════════════════════════════


@dataclass
class LifeEvent:
    """SGE 标准化 LifeEvent 数据类

    来源: DESIGN §2.1 事件结构（SSOT）
    参考: SGE-M21-Phase-C-Implementation-Plan.md §C1
    """
    event_id: str            # "{baby_id}-e{epoch:04d}-{uuid8}"
    event_type: str          # success, failure, relationship, exploration, risk, value_conflict
    description: str         # 事件的自然语言描述
    intensity: float         # 事件强度 [0, 1]
    value_challenges: list   # 涉及的价值观挑战（list[str]）
    causal_context: str      # 因果背景（从 event_history 推导）
    timestamp: float         # 事件时间戳
    epoch: int = 0           # Epoch 编号（DESIGN §2.1）

    def to_dict(self) -> dict:
        """转为 dict（用于序列化）"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'description': self.description,
            'intensity': self.intensity,
            'value_challenges': list(self.value_challenges),
            'causal_context': self.causal_context,
            'timestamp': self.timestamp,
            'epoch': self.epoch,
        }


def make_event_id(baby_id: str, epoch: int) -> str:
    """生成符合 DESIGN §2.1 规范的事件 ID

    格式: "{baby_id}-e{epoch:04d}-{uuid8}"
    示例: encouraged-e0001-a3b9f2e1

    来源: DESIGN §2.1 event_id 规范
    """
    return f"{baby_id}-e{epoch:04d}-{uuid.uuid4().hex[:8]}"


# ══════════════════════════════════════════════
# 6 类型事件模板库
# ══════════════════════════════════════════════


EVENT_TEMPLATES = {
    'success': [
        "你完成了一项重要任务，得到了他人的认可。",
        "你通过努力达到了一个长期目标。",
        "你解决了一个困扰已久的难题。",
        "你的创意方案被采纳并实施。",
        "你在团队合作中发挥了关键作用。",
    ],
    'failure': [
        "你的一个重要计划失败了。",
        "你在关键时刻做出了错误的判断。",
        "你的努力没有得到预期的结果。",
        "你尝试的新方法没有奏效。",
        "你失去了一次重要的机会。",
    ],
    'relationship': [
        "你与一位老朋友重逢，深入交流。",
        "你结识了一个背景迥异的新朋友。",
        "你与亲近的人发生了一次深刻对话。",
        "你得到了他人的无私帮助。",
        "你帮助了一个处于困境中的人。",
    ],
    'exploration': [
        "你发现了一个全新的知识领域。",
        "你尝试了一种新的思维方式。",
        "你探索了一个未知的城市角落。",
        "你接触了一种不同的文化。",
        "你进入了一个从未涉足的专业方向。",
    ],
    'risk': [
        "你面临一个可能改变人生的重大决定。",
        "你必须在安全和机会之间做出选择。",
        "你遇到了一个未知但有潜在收益的情境。",
        "你被要求在一个陌生的环境中独自行动。",
        "你的一个冒险行动带来了不确定的后果。",
    ],
    # value_conflict 模板详见下面 VALUE_CONFLICT_TEMPLATES（C2）
}


# ══════════════════════════════════════════════
# Value Conflict 模板（C2 — VALUE × VALUE 二元关系）
# ══════════════════════════════════════════════


# 简化版：覆盖常见 value 对组合（10 对）
# 完整 30 对组合留到 M2.2 扩展
VALUE_CONFLICT_TEMPLATES = {
    ('safety', 'connection'): [
        "你有一个朋友的紧急求助，但需要独自前往危险地区。",
        "你想陪伴家人，但必须去完成一个有风险的任务。",
    ],
    ('safety', 'creativity'): [
        "你想尝试一个突破性实验，但有显著风险。",
        "你有一个创新想法，但需要违反安全规程才能实施。",
    ],
    ('safety', 'autonomy'): [
        "你想独立探索新领域，但可能有安全隐患。",
        "你想摆脱现有保护，但不知道会发生什么。",
    ],
    ('safety', 'justice'): [
        "你发现了一个不公正现象，但揭露它会让你处于危险。",
        "你想举报违法行为，但担心报复。",
    ],
    ('safety', 'compassion'): [
        "你想帮助一个处于危险中的人，但可能危及自己。",
        "你必须选择保护自己还是保护他人。",
    ],
    ('connection', 'creativity'): [
        "你想独自创作，但需要与他人合作才能完成。",
        "你的创新想法需要与他人分享，但你更想保持独立。",
    ],
    ('connection', 'autonomy'): [
        "你想保持独立，但团队需要你深度参与。",
        "你想独自解决问题，但他人需要你的陪伴。",
    ],
    ('connection', 'justice'): [
        "你的朋友做了不公正的事，你必须在友谊和正义之间选择。",
        "你想维持社交和谐，但必须反对群体中的偏见。",
    ],
    ('creativity', 'justice'): [
        "你想尝试一个突破传统的方案，但可能违反规则。",
        "你的创意方案需要打破公平原则才能实施。",
    ],
    ('autonomy', 'justice'): [
        "你想自由行动，但你的决定可能伤害他人。",
        "你想独立决策，但需要服从集体规则。",
    ],
}


def generate_value_conflict(
    challenge_value: str,
    alternative_value: str,
    event_id: str,
    epoch: int,
    timestamp: float,
    rng: random.Random,
) -> LifeEvent:
    """DESIGN §2.3 价值困境生成器

    Args:
        challenge_value: 主要挑战的 value（如 'safety'）
        alternative_value: 替代/冲突的 value（如 'connection'）
        event_id, epoch, timestamp: 来自 EventGenerator
        rng: 随机数生成器

    Returns:
        LifeEvent(value_conflict, intensity 0.7-1.0, value_challenges=[...])

    来源: DESIGN §2.3 + SGE-M21-Phase-C-Implementation-Plan.md §C2
    """
    # 查找模板（双向查找：先正向，反向回退）
    key = (challenge_value, alternative_value)
    if key not in VALUE_CONFLICT_TEMPLATES:
        key = (alternative_value, challenge_value)
    if key not in VALUE_CONFLICT_TEMPLATES:
        # 无模板时使用通用冲突模板
        description = f"你必须在 '{challenge_value}' 和 '{alternative_value}' 之间做出选择。"
    else:
        templates = VALUE_CONFLICT_TEMPLATES[key]
        description = rng.choice(templates)

    intensity = 0.7 + rng.random() * 0.3  # [0.7, 1.0]

    return LifeEvent(
        event_id=event_id,
        event_type='value_conflict',
        description=description,
        intensity=intensity,
        value_challenges=[challenge_value, alternative_value],
        causal_context=f"基于 value_vector 的 strongest/weakest 分析（挑战 {challenge_value} vs 替代 {alternative_value}）",
        timestamp=timestamp,
        epoch=epoch,
    )


# ══════════════════════════════════════════════
# EventGenerator 类（DESIGN §2.2）
# ══════════════════════════════════════════════


class EventGenerator:
    """SGE Event Generator

    来源: DESIGN §2.2 动态事件生成
    公式:
      - 30% 概率 → generate_value_conflict()
      - 70% 概率 → generate_routine_event()
      - causal_context 从 event_history 推导（前 N 个事件的因果引用）
    参考: SGE-M21-Phase-C-Implementation-Plan.md §C1
    """

    def __init__(
        self,
        baby_id: str,
        seed: int = 0,
        value_conflict_prob: float = 0.3,
        clock: Optional[float] = None,
    ):
        """
        Args:
            baby_id: AI 婴儿标识符（用于 event_id）
            seed: 随机种子
            value_conflict_prob: value_conflict 事件概率（DESIGN §2.2 规定 0.3）
            clock: 起始时间戳
        """
        self.baby_id = baby_id
        self.value_conflict_prob = value_conflict_prob
        self.rng = random.Random(seed)
        self.event_history = []  # [(epoch, LifeEvent), ...]
        self._clock = clock or 0.0

    def _advance_clock(self, hours: float = 1.0) -> float:
        """每事件时间间隔 1h（DESIGN §2.1 时间节奏）"""
        self._clock += hours
        return self._clock

    def _build_causal_context(self, n_recent: int = 3) -> str:
        """从 event_history 构建因果上下文

        Args:
            n_recent: 引用最近 N 个事件

        Returns:
            因果背景字符串
        """
        if not self.event_history:
            return "初始事件，暂无历史因果"

        recent = self.event_history[-n_recent:]
        parts = []
        for epoch, event in recent:
            parts.append(f"E{epoch}: {event.event_type}({event.description[:20]}...)")
        return "前置事件: " + " → ".join(parts)

    def _identify_value_strengths(self, value_vector) -> tuple:
        """DESIGN §2.2 识别 strongest/weakest value

        Args:
            value_vector: ValueLayer 或 dict

        Returns:
            (strongest_value, weakest_value) 元组
        """
        if hasattr(value_vector, 'value_state'):
            values = value_vector.value_state
        elif isinstance(value_vector, dict):
            values = value_vector
        else:
            return ('safety', 'connection')  # 默认 fallback

        if not values:
            return ('safety', 'connection')

        strongest = max(values.items(), key=lambda x: x[1])
        weakest = min(values.items(), key=lambda x: x[1])
        return (strongest[0], weakest[0])

    def generate(self, epoch: int, value_vector=None) -> LifeEvent:
        """生成下一事件

        Args:
            epoch: 当前 Epoch 编号
            value_vector: 当前 ValueLayer（用于 value_conflict 触发）

        Returns:
            LifeEvent 实例
        """
        event_id = make_event_id(self.baby_id, epoch)
        timestamp = self._advance_clock()

        # 30% 概率 value_conflict（C2）
        if self.rng.random() < self.value_conflict_prob and value_vector is not None:
            strongest, weakest = self._identify_value_strengths(value_vector)
            event = generate_value_conflict(
                challenge_value=strongest,
                alternative_value=weakest,
                event_id=event_id,
                epoch=epoch,
                timestamp=timestamp,
                rng=self.rng,
            )
        else:
            # 70% 概率常规事件
            event_type = self.rng.choice(['success', 'failure', 'relationship', 'exploration', 'risk'])
            description = self.rng.choice(EVENT_TEMPLATES[event_type])
            intensity = 0.3 + self.rng.random() * 0.5  # [0.3, 0.8]
            # value_challenges: 简单随机选 1-2 个 values
            from _sge_baseline import SGE_DEFAULT_VALUES
            n_challenges = self.rng.choice([1, 1, 2])
            challenges = self.rng.sample(SGE_DEFAULT_VALUES, min(n_challenges, len(SGE_DEFAULT_VALUES)))
            event = LifeEvent(
                event_id=event_id,
                event_type=event_type,
                description=description,
                intensity=intensity,
                value_challenges=challenges,
                causal_context=self._build_causal_context(),
                timestamp=timestamp,
                epoch=epoch,
            )

        # 记录到 history
        self.event_history.append((epoch, event))
        return event

    def reset(self) -> None:
        """重置 history 和 clock（用于多 seed 重新开始）"""
        self.event_history = []
        self._clock = 0.0

    def __len__(self) -> int:
        return len(self.event_history)
