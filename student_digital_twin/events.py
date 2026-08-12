"""StudentEvent — 学生事件（App 层构造 → SGE 编排）

设计 SSOT：[research/phase3/90-applications/student-digital-twin.md §2.1](../research/phase3/90-applications/student-digital-twin.md)

事件类型枚举（EventType 8 类）：
  mastery_drop / mastery_rise / struggle_breakthrough /
  emotional_event / social_event / fatigue_event /
  praise_event / criticism_event
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Literal, Optional


# ══════════════════════════════════════════════
# 事件类型枚举
# ══════════════════════════════════════════════

EventType = Literal[
    'mastery_drop',           # 某主题分数下降（小测失利）
    'mastery_rise',           # 某主题分数上升
    'struggle_breakthrough',  # 长期挣扎后突然理解
    'emotional_event',        # 情感事件（和父母吵架/老师表扬）
    'social_event',           # 社交事件（和朋友冲突/结交新朋友）
    'fatigue_event',          # 疲劳/睡眠不足
    'praise_event',           # 被表扬
    'criticism_event',        # 被批评
]

ALL_EVENT_TYPES: tuple[str, ...] = (
    'mastery_drop',
    'mastery_rise',
    'struggle_breakthrough',
    'emotional_event',
    'social_event',
    'fatigue_event',
    'praise_event',
    'criticism_event',
)


# ══════════════════════════════════════════════
# StudentEvent
# ══════════════════════════════════════════════


@dataclass
class StudentEvent:
    """学生在某一时刻发生的一个事件（App 层构造 → SGE 编排）。

    用法：
        evt = StudentEvent(
            event_id='evt_001',
            event_type='mastery_drop',
            subject='math', topic='algebra',
            mastery_before=78, mastery_after=70,
            emotion='frustrated', emotion_intensity=0.4,
            description='一元一次方程小测：3/10 错',
        )
    """

    event_id: str
    event_type: str                           # 实际约束靠 ALL_EVENT_TYPES（PoC 不强制 enum）
    subject: Optional[str] = None             # 学科（如 math/english），emotional_event 可 None
    topic: Optional[str] = None               # 主题（如 algebra/reading）
    mastery_before: float = 0.0               # 事件前 mastery
    mastery_after: float = 0.0                # 事件后 mastery
    mastery_delta: float = 0.0                # 变化量（=after - before，可负）
    emotion: str = 'neutral'                  # 主导情绪
    emotion_intensity: float = 0.0            # 强度 0-1
    description: str = ''                     # 人读描述
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)  # 扩展字段

    def __post_init__(self):
        # 验证 event_type
        if self.event_type not in ALL_EVENT_TYPES:
            raise ValueError(
                f"event_type 必须是 {ALL_EVENT_TYPES} 之一，得到: {self.event_type!r}"
            )
        # 验证 mastery 范围
        for name, val in [('mastery_before', self.mastery_before),
                          ('mastery_after', self.mastery_after)]:
            if not 0.0 <= val <= 100.0:
                raise ValueError(f"{name} 必须在 [0, 100]，得到: {val}")
        # 验证 emotion_intensity 范围
        if not 0.0 <= self.emotion_intensity <= 1.0:
            raise ValueError(
                f"emotion_intensity 必须在 [0, 1]，得到: {self.emotion_intensity}"
            )
        # 自动计算 delta（如调用方未提供）
        if self.mastery_delta == 0.0 and (self.mastery_after != self.mastery_before):
            self.mastery_delta = self.mastery_after - self.mastery_before

    def to_dict(self) -> dict:
        """序列化为 dict（datetime → isoformat str）。"""
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d

    def to_human_readable(self) -> str:
        """构造注入 Actor prompt 的人读描述（02-architecture §5 [本次事件]）。"""
        subj_topic = f"{self.subject or '?'}/{self.topic or '?'}"
        return (
            f"[{self.event_type}] {subj_topic} | "
            f"mastery {self.mastery_before:.0f}→{self.mastery_after:.0f} "
            f"(Δ{self.mastery_delta:+.0f}) | "
            f"情绪 {self.emotion} (强度 {self.emotion_intensity:.1f}) | "
            f"{self.description}"
        )

    @classmethod
    def from_dict(cls, d: dict) -> 'StudentEvent':
        """从 dict 反序列化（支持 datetime ISO 字符串）。"""
        d = dict(d)  # 拷贝避免修改原 dict
        if isinstance(d.get('timestamp'), str):
            d['timestamp'] = datetime.fromisoformat(d['timestamp'])
        # 过滤未知字段
        known_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in d.items() if k in known_fields}
        return cls(**filtered)