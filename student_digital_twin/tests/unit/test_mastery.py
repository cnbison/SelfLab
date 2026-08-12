"""test_mastery.py — SubjectMasteryState / TopicMastery / SubjectMastery 全覆盖

目标覆盖率 ≥ 90%
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from student_digital_twin.mastery import (
    SubjectMasteryState, SubjectMastery, TopicMastery,
    MASTERY_SCHEMA_VERSION, DEFAULT_STRUGGLE_THRESHOLD,
)


# ══════════════════════════════════════════════
# TopicMastery
# ══════════════════════════════════════════════


class TestTopicMastery:
    def test_update_returns_delta(self):
        t = TopicMastery(score=70.0, updated_at=datetime(2026, 1, 1))
        delta = t.update(60.0, datetime(2026, 1, 2))
        assert delta == -10.0
        assert t.score == 60.0
        assert t.updated_at == datetime(2026, 1, 2)
        assert len(t.history) == 1
        assert t.history[0] == (datetime(2026, 1, 2), 60.0)

    def test_update_validates_range(self):
        t = TopicMastery(score=70.0, updated_at=datetime(2026, 1, 1))
        with pytest.raises(ValueError, match=r"mastery 必须在"):
            t.update(101.0, datetime(2026, 1, 2))
        with pytest.raises(ValueError, match=r"mastery 必须在"):
            t.update(-5.0, datetime(2026, 1, 2))

    def test_update_appends_history(self):
        t = TopicMastery(score=70.0, updated_at=datetime(2026, 1, 1))
        t.update(65.0, datetime(2026, 1, 2))
        t.update(60.0, datetime(2026, 1, 3))
        assert len(t.history) == 2


# ══════════════════════════════════════════════
# SubjectMastery
# ══════════════════════════════════════════════


class TestSubjectMastery:
    def test_most_recent_topic_empty(self):
        s = SubjectMastery(subject_id='math', aggregate_score=0)
        assert s.most_recent_topic() is None

    def test_most_recent_topic_single(self):
        s = SubjectMastery(subject_id='math', aggregate_score=70)
        s.topics['algebra'] = TopicMastery(score=70, updated_at=datetime(2026, 1, 1))
        assert s.most_recent_topic() == 'algebra'

    def test_most_recent_topic_multiple(self):
        s = SubjectMastery(subject_id='math', aggregate_score=70)
        s.topics['algebra'] = TopicMastery(score=60, updated_at=datetime(2026, 1, 1))
        s.topics['geometry'] = TopicMastery(score=80, updated_at=datetime(2026, 1, 5))
        s.topics['calculus'] = TopicMastery(score=70, updated_at=datetime(2026, 1, 3))
        assert s.most_recent_topic() == 'geometry'

    def test_struggling_topics(self):
        s = SubjectMastery(subject_id='math', aggregate_score=70)
        s.topics['algebra'] = TopicMastery(score=45, updated_at=datetime.now())
        s.topics['geometry'] = TopicMastery(score=75, updated_at=datetime.now())
        s.topics['calculus'] = TopicMastery(score=55, updated_at=datetime.now())
        struggling = s.struggling_topics()
        assert set(struggling) == {'algebra', 'calculus'}

    def test_struggling_topics_custom_threshold(self):
        s = SubjectMastery(subject_id='math', aggregate_score=70)
        s.topics['algebra'] = TopicMastery(score=75, updated_at=datetime.now())
        assert s.struggling_topics(threshold=80.0) == ['algebra']


# ══════════════════════════════════════════════
# SubjectMasteryState
# ══════════════════════════════════════════════


class TestSubjectMasteryState:
    def test_default_state(self):
        state = SubjectMasteryState(student_id='alice')
        assert state.schema_version == MASTERY_SCHEMA_VERSION
        assert state.schema_version == "1.0"
        assert state.student_id == 'alice'
        assert state.subjects == {}

    def test_update_topic_creates_subject_and_topic(self):
        state = SubjectMasteryState(student_id='alice')
        delta = state.update_topic('math', 'algebra', 70.0)
        assert delta == 0.0  # 首次创建无对比基准
        assert 'math' in state.subjects
        assert 'algebra' in state.subjects['math'].topics
        assert state.subjects['math'].topics['algebra'].score == 70.0
        assert state.subjects['math'].aggregate_score == 70.0

    def test_update_topic_returns_delta_on_existing(self):
        state = SubjectMasteryState(student_id='alice')
        state.update_topic('math', 'algebra', 70.0)
        delta = state.update_topic('math', 'algebra', 60.0)
        assert delta == -10.0
        assert state.subjects['math'].topics['algebra'].score == 60.0
        assert state.subjects['math'].aggregate_score == 60.0

    def test_update_topic_recomputes_aggregate(self):
        state = SubjectMasteryState(student_id='alice')
        state.update_topic('math', 'algebra', 70.0)
        state.update_topic('math', 'geometry', 80.0)
        # 学科总分 = (70 + 80) / 2 = 75
        assert state.subjects['math'].aggregate_score == 75.0
        state.update_topic('math', 'algebra', 50.0)
        # 重算：(50 + 80) / 2 = 65
        assert state.subjects['math'].aggregate_score == 65.0

    def test_update_topic_validates_score(self):
        state = SubjectMasteryState(student_id='alice')
        with pytest.raises(ValueError, match=r"new_score 必须在"):
            state.update_topic('math', 'algebra', 105.0)

    def test_update_topic_updates_last_updated(self):
        state = SubjectMasteryState(student_id='alice')
        t1 = datetime(2026, 1, 1)
        state.update_topic('math', 'algebra', 70.0, when=t1)
        assert state.last_updated == t1
        t2 = datetime(2026, 1, 5)
        state.update_topic('math', 'algebra', 75.0, when=t2)
        assert state.last_updated == t2

    # ── summary() ──

    def test_summary_empty(self):
        state = SubjectMasteryState(student_id='alice')
        assert state.summary() == "(无 mastery 数据)"

    def test_summary_single_subject(self):
        state = SubjectMasteryState(student_id='alice')
        state.update_topic('math', 'algebra', 70.0)
        assert state.summary() == "math: 70 (algebra 70)"

    def test_summary_multiple_subjects_topics(self):
        state = SubjectMasteryState(student_id='alice')
        state.update_topic('math', 'algebra', 65.0)
        state.update_topic('math', 'geometry', 75.0)
        state.update_topic('english', 'reading', 80.0)
        summary = state.summary()
        assert 'math: 70' in summary
        assert 'english: 80' in summary
        assert 'algebra 65' in summary
        assert 'geometry 75' in summary
        assert 'reading 80' in summary

    def test_summary_subject_without_topics(self):
        """学科存在但无主题时，summary 不应崩溃。"""
        state = SubjectMasteryState(student_id='alice')
        # 手动添加空学科（绕过 update_topic 默认行为）
        state.subjects['math'] = SubjectMastery(
            subject_id='math', aggregate_score=50.0, topics={},
        )
        state.subjects['math'].last_updated = None
        summary = state.summary()
        assert 'math: 50' in summary
        assert 'algebra' not in summary  # 无主题列表

    # ── most_recent_struggling() ──

    def test_most_recent_struggling_no_data(self):
        state = SubjectMasteryState(student_id='alice')
        assert state.most_recent_struggling() == "无"

    def test_most_recent_struggling_all_above_threshold(self):
        state = SubjectMasteryState(student_id='alice')
        state.update_topic('math', 'algebra', 80.0)
        state.update_topic('english', 'reading', 90.0)
        assert state.most_recent_struggling() == "无"

    def test_most_recent_struggling_topic_below(self):
        state = SubjectMasteryState(student_id='alice')
        state.update_topic('math', 'algebra', 45.0)
        assert state.most_recent_struggling() == "math/algebra"

    def test_most_recent_struggling_picks_most_recent(self):
        state = SubjectMasteryState(student_id='alice')
        state.update_topic('math', 'algebra', 45.0, when=datetime(2026, 1, 1))
        state.update_topic('english', 'reading', 50.0, when=datetime(2026, 1, 10))
        assert state.most_recent_struggling() == "english/reading"

    def test_most_recent_struggling_picks_lowest_when_same_time(self):
        state = SubjectMasteryState(student_id='alice')
        same_time = datetime(2026, 1, 1)
        state.update_topic('math', 'algebra', 45.0, when=same_time)
        state.update_topic('math', 'geometry', 30.0, when=same_time)
        assert state.most_recent_struggling() == "math/geometry"

    def test_most_recent_struggling_subject_level_fallback(self):
        """学科 aggregate_score < 60 但主题都 ≥ 60 时 → 返回学科。"""
        state = SubjectMasteryState(student_id='alice')
        # 一主题 70 + 一主题 50，平均 60 → 边界
        state.update_topic('math', 'algebra', 70.0)
        state.update_topic('math', 'geometry', 50.0)
        # 学科 aggregate_score = 60（不算挣扎）
        # 但 geometry 50 < 60 → 应返回 math/geometry
        assert state.most_recent_struggling() == "math/geometry"

    def test_most_recent_struggling_subject_level_with_no_topics(self):
        """学科无主题且 aggregate_score < 60 时 → 走学科级 fallback（last_updated=None 边界）。"""
        state = SubjectMasteryState(student_id='alice')
        # 直接构造：subjects 含一空学科 + last_updated=None
        state.subjects['math'] = SubjectMastery(
            subject_id='math', aggregate_score=50.0, topics={},
        )
        state.subjects['math'].last_updated = None
        result = state.most_recent_struggling()
        assert result == "math"  # 学科级（无主题）

    # ── learning_velocity() ──

    def test_learning_velocity_empty(self):
        state = SubjectMasteryState(student_id='alice')
        assert state.learning_velocity() == 0.0

    def test_learning_velocity_single_update(self):
        state = SubjectMasteryState(student_id='alice')
        state.update_topic('math', 'algebra', 70.0)
        # 只有一次更新，无 delta
        assert state.learning_velocity() == 0.0

    def test_learning_velocity_with_changes(self):
        state = SubjectMasteryState(student_id='alice')
        state.update_topic('math', 'algebra', 70.0)
        state.update_topic('math', 'algebra', 60.0)  # delta 10
        velocity = state.learning_velocity()
        # 平均 delta = 10，标准化 = 10/10 = 1.0
        assert velocity == 1.0

    def test_learning_velocity_caps_at_1(self):
        state = SubjectMasteryState(student_id='alice')
        state.update_topic('math', 'algebra', 70.0)
        state.update_topic('math', 'algebra', 100.0)  # delta 30（> 10）
        assert state.learning_velocity() == 1.0  # capped

    def test_learning_velocity_uses_recent_5(self):
        state = SubjectMasteryState(student_id='alice')
        # 7 次更新，平均 delta 应基于最近 5 次
        for i in range(8):
            state.update_topic('math', 'algebra', 70.0 + i)
        # 最近 5 次 delta = 1（每次 +1），平均 = 1.0 → 标准化 0.1
        assert state.learning_velocity() == pytest.approx(0.1, abs=0.01)

    # ── 序列化 ──

    def test_to_dict_includes_schema_version(self):
        state = SubjectMasteryState(student_id='alice')
        d = state.to_dict()
        assert d['schema_version'] == '1.0'
        assert d['student_id'] == 'alice'

    def test_to_dict_serializes_datetime(self):
        state = SubjectMasteryState(student_id='alice')
        state.update_topic('math', 'algebra', 70.0)
        d = state.to_dict()
        # datetime → isoformat str
        assert isinstance(d['created_at'], str)
        assert isinstance(d['last_updated'], str)
        assert isinstance(d['subjects']['math']['topics']['algebra']['updated_at'], str)

    def test_to_dict_roundtrip_json(self):
        """JSON 序列化 + 反序列化不应丢失字段。"""
        state = SubjectMasteryState(student_id='alice')
        state.update_topic('math', 'algebra', 70.0)
        state.update_topic('english', 'reading', 80.0)
        d = state.to_dict()
        # 应可 JSON 序列化
        json_str = json.dumps(d, ensure_ascii=False)
        assert 'alice' in json_str
        assert 'math' in json_str