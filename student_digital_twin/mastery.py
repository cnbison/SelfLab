"""SubjectMasteryState — 学生学科掌握状态（学科×主题二维混合）

设计 SSOT：[research/phase3/90-applications/student-digital-twin.md §2.2](../research/phase3/90-applications/student-digital-twin.md)

3 个 duck typing 方法（与 sge/sge/context_injection.py §build_critic_context 严格对齐）：
  - summary()                → 'current_mastery_overview'
  - most_recent_struggling() → 'recent_struggle'
  - learning_velocity()      → 'learning_pace'
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


# ══════════════════════════════════════════════
# 常量
# ══════════════════════════════════════════════

MASTERY_SCHEMA_VERSION = "1.0"
DEFAULT_STRUGGLE_THRESHOLD = 60.0  # mastery < 60 视为挣扎


# ══════════════════════════════════════════════
# TopicMastery：单个主题的 mastery
# ══════════════════════════════════════════════


@dataclass
class TopicMastery:
    """单个主题的 mastery 状态（含历史时间序列）。"""

    score: float                              # 当前 mastery (0-100)
    updated_at: datetime
    history: list[tuple[datetime, float]] = field(default_factory=list)

    def update(self, new_score: float, when: datetime) -> float:
        """更新 mastery，返回 delta（新-旧）。"""
        if not 0.0 <= new_score <= 100.0:
            raise ValueError(
                f"mastery 必须在 [0, 100]，得到: {new_score}"
            )
        old_score = self.score
        self.score = new_score
        self.updated_at = when
        self.history.append((when, new_score))
        return new_score - old_score


# ══════════════════════════════════════════════
# SubjectMastery：单个学科（含主题层级）
# ══════════════════════════════════════════════


@dataclass
class SubjectMastery:
    """单个学科的 mastery 状态（含主题层级）。"""

    subject_id: str
    aggregate_score: float                    # 学科总分（主题平均）
    topics: dict[str, TopicMastery] = field(default_factory=dict)
    last_updated: Optional[datetime] = None

    def most_recent_topic(self) -> Optional[str]:
        """最近更新的主题（无主题返回 None）。"""
        if not self.topics:
            return None
        return max(self.topics.keys(), key=lambda t: self.topics[t].updated_at)

    def struggling_topics(self, threshold: float = DEFAULT_STRUGGLE_THRESHOLD) -> list[str]:
        """挣扎主题列表（mastery < threshold）。"""
        return [t for t, m in self.topics.items() if m.score < threshold]


# ══════════════════════════════════════════════
# SubjectMasteryState：学生整体 mastery 状态
# ══════════════════════════════════════════════


@dataclass
class SubjectMasteryState:
    """学生整体 mastery 状态（学科×主题二维）。

    设计要点：
      - schema_version 字段：未来变更的迁移锚点（PoC 阶段不写 migration）
      - 3 个 duck typing 方法固定签名（与 TwinContextBuilder 严格对齐）
      - 序列化：dataclasses.asdict + 自定义 datetime encoder
    """

    schema_version: str = MASTERY_SCHEMA_VERSION
    student_id: str = ""
    subjects: dict[str, SubjectMastery] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    # ── duck typing 方法（TwinContextBuilder §build_critic_context 调用） ──

    def summary(self) -> str:
        """生成 mastery 总览字符串（注入 critic context）。

        例：'math: 58 (algebra 45, geometry 71) | english: 82 (reading 78, writing 86)'
        """
        if not self.subjects:
            return "(无 mastery 数据)"
        parts = []
        for subj_id, subj in self.subjects.items():
            if subj.topics:
                topics_str = ", ".join(
                    f"{t} {m.score:.0f}"
                    for t, m in sorted(subj.topics.items())
                )
                parts.append(f"{subj_id}: {subj.aggregate_score:.0f} ({topics_str})")
            else:
                parts.append(f"{subj_id}: {subj.aggregate_score:.0f}")
        return " | ".join(parts)

    def most_recent_struggling(self) -> str:
        """返回最近挣扎的主题（注入 critic context）。

        优先级：(1) 分数 < DEFAULT_STRUGGLE_THRESHOLD；(2) 最近更新；(3) 分数最低。
        返回格式：'math/algebra' 或 'math' 或 '无'。
        """
        candidates = []
        for subj_id, subj in self.subjects.items():
            for topic_id, m in subj.topics.items():
                if m.score < DEFAULT_STRUGGLE_THRESHOLD:
                    candidates.append((m.updated_at, m.score, f"{subj_id}/{topic_id}"))
        if not candidates:
            # 检查学科级挣扎（无主题的学科）
            for subj_id, subj in self.subjects.items():
                if subj.aggregate_score < DEFAULT_STRUGGLE_THRESHOLD:
                    candidates.append((subj.last_updated or self.last_updated,
                                       subj.aggregate_score, subj_id))
            if not candidates:
                return "无"
        # 排序：(1) 最近更新（降序），(2) 分数最低（升序）
        candidates.sort(key=lambda x: (-x[0].timestamp(), x[1]))
        return candidates[0][2]

    def learning_velocity(self) -> float:
        """返回学习速率（注入 critic context 的 learning_pace）。

        定义：所有主题最近 5 次更新的平均 |delta| / 标准化。
        返回 0-1 标准化值（1.0 = 高速变化，0.0 = 无变化）。

        标准化：|delta| 平均 10 分 = 高速 (1.0)；平均 1 分 = 0.1。
        """
        if not self.subjects:
            return 0.0
        deltas = []
        for subj in self.subjects.values():
            for topic in subj.topics.values():
                # 取最近 5 次更新（含当前）
                recent = topic.history[-5:]
                if len(recent) >= 2:
                    for i in range(1, len(recent)):
                        delta = abs(recent[i][1] - recent[i-1][1])
                        deltas.append(delta)
        if not deltas:
            return 0.0
        avg = sum(deltas) / len(deltas)
        return min(1.0, avg / 10.0)

    # ── 更新 API ──

    def update_topic(
        self,
        subject: str,
        topic: str,
        new_score: float,
        when: Optional[datetime] = None,
    ) -> float:
        """更新主题 mastery，返回 delta（首次创建主题返回 0.0）。

        自动重算学科 aggregate_score（=主题平均分）。
        """
        when = when or datetime.now()
        if not 0.0 <= new_score <= 100.0:
            raise ValueError(
                f"new_score 必须在 [0, 100]，得到: {new_score}"
            )

        if subject not in self.subjects:
            self.subjects[subject] = SubjectMastery(
                subject_id=subject,
                aggregate_score=new_score,
                topics={},
                last_updated=when,
            )

        subj = self.subjects[subject]
        if topic not in subj.topics:
            # 新主题：首次设置，delta = 0.0（无对比基准）
            subj.topics[topic] = TopicMastery(score=new_score, updated_at=when)
            subj.topics[topic].history.append((when, new_score))
            delta = 0.0
        else:
            # 已存在：调用 TopicMastery.update 返回 delta
            delta = subj.topics[topic].update(new_score, when)

        # 重算学科总分（主题平均分）
        subj.aggregate_score = sum(t.score for t in subj.topics.values()) / len(subj.topics)
        subj.last_updated = when
        self.last_updated = when
        return delta

    # ── 序列化 ──

    def to_dict(self) -> dict:
        """序列化为 dict（datetime → isoformat str）。"""
        return _asdict_with_datetime(self)


# ══════════════════════════════════════════════
# 序列化辅助
# ══════════════════════════════════════════════


def _asdict_with_datetime(obj):
    """递归 asdict + datetime → isoformat str。

    dataclasses.asdict 不处理 datetime；SubjectMasteryState 含 datetime 字段
    (created_at / last_updated) 和嵌套 TopicMastery.history（含 datetime 元组）。
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _asdict_with_datetime(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        converted = [_asdict_with_datetime(v) for v in obj]
        return tuple(converted) if isinstance(obj, tuple) else converted
    if hasattr(obj, '__dict__') and not isinstance(obj, type):
        # dataclass 实例：递归字段
        d = {}
        for k, v in obj.__dict__.items():
            d[k] = _asdict_with_datetime(v)
        return d
    return obj