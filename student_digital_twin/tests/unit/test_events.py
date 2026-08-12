"""test_events.py — StudentEvent + from_dict + to_human_readable + 验证

目标覆盖率 ≥ 95%
"""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from student_digital_twin.events import (
    StudentEvent, ALL_EVENT_TYPES,
)


# ══════════════════════════════════════════════
# StudentEvent 验证
# ══════════════════════════════════════════════


class TestStudentEventValidation:
    def test_valid_event(self):
        evt = StudentEvent(
            event_id='evt_001',
            event_type='mastery_drop',
            subject='math', topic='algebra',
            mastery_before=78, mastery_after=70,
            emotion='frustrated', emotion_intensity=0.4,
            description='一元一次方程小测：3/10 错',
        )
        assert evt.event_id == 'evt_001'
        assert evt.mastery_delta == -8  # 自动计算

    def test_invalid_event_type(self):
        with pytest.raises(ValueError, match=r"event_type 必须是"):
            StudentEvent(
                event_id='evt_001',
                event_type='invalid_type',
            )

    def test_invalid_mastery_range(self):
        with pytest.raises(ValueError, match=r"mastery_before 必须在"):
            StudentEvent(
                event_id='evt_001',
                event_type='mastery_drop',
                mastery_before=105.0,
            )
        with pytest.raises(ValueError, match=r"mastery_after 必须在"):
            StudentEvent(
                event_id='evt_001',
                event_type='mastery_drop',
                mastery_after=-5.0,
            )

    def test_invalid_emotion_intensity(self):
        with pytest.raises(ValueError, match=r"emotion_intensity 必须在"):
            StudentEvent(
                event_id='evt_001',
                event_type='emotional_event',
                emotion_intensity=1.5,
            )
        with pytest.raises(ValueError, match=r"emotion_intensity 必须在"):
            StudentEvent(
                event_id='evt_001',
                event_type='emotional_event',
                emotion_intensity=-0.1,
            )

    def test_explicit_delta_preserved(self):
        """若调用方显式提供 delta 且与计算不符，应保留显式值（不会自动覆盖非零 delta）。"""
        evt = StudentEvent(
            event_id='evt_001',
            event_type='mastery_drop',
            mastery_before=70, mastery_after=60,
            mastery_delta=999.0,  # 显式但矛盾
        )
        # 矛盾 delta 不会被自动覆盖（PoC 阶段不强制）
        assert evt.mastery_delta == 999.0


# ══════════════════════════════════════════════
# to_dict / from_dict / to_human_readable
# ══════════════════════════════════════════════


class TestStudentEventSerialization:
    def test_to_dict_includes_all_fields(self):
        evt = StudentEvent(
            event_id='evt_001',
            event_type='mastery_drop',
            subject='math', topic='algebra',
            mastery_before=78, mastery_after=70,
            emotion='frustrated', emotion_intensity=0.4,
            description='一元一次方程小测',
        )
        d = evt.to_dict()
        assert d['event_id'] == 'evt_001'
        assert d['event_type'] == 'mastery_drop'
        assert d['subject'] == 'math'
        assert d['topic'] == 'algebra'
        assert isinstance(d['timestamp'], str)

    def test_to_dict_serializable_to_json(self):
        evt = StudentEvent(
            event_id='evt_001',
            event_type='mastery_drop',
            subject='math', topic='algebra',
            mastery_before=78, mastery_after=70,
        )
        d = evt.to_dict()
        json_str = json.dumps(d, ensure_ascii=False)
        assert 'evt_001' in json_str

    def test_from_dict_roundtrip(self):
        original = StudentEvent(
            event_id='evt_001',
            event_type='mastery_drop',
            subject='math', topic='algebra',
            mastery_before=78, mastery_after=70,
            emotion='frustrated', emotion_intensity=0.4,
            description='一元一次方程小测',
            metadata={'teacher': 'Mr. Smith'},
        )
        d = original.to_dict()
        restored = StudentEvent.from_dict(d)
        assert restored.event_id == original.event_id
        assert restored.event_type == original.event_type
        assert restored.subject == original.subject
        assert restored.topic == original.topic
        assert restored.mastery_before == original.mastery_before
        assert restored.mastery_after == original.mastery_after
        assert restored.emotion == original.emotion
        assert restored.emotion_intensity == original.emotion_intensity
        assert restored.description == original.description
        assert restored.metadata == original.metadata
        assert restored.timestamp == original.timestamp

    def test_from_dict_filters_unknown_fields(self):
        d = {
            'event_id': 'evt_001',
            'event_type': 'mastery_drop',
            'unknown_field': 'should_be_filtered',
        }
        evt = StudentEvent.from_dict(d)
        assert evt.event_id == 'evt_001'
        assert evt.event_type == 'mastery_drop'

    def test_to_human_readable(self):
        evt = StudentEvent(
            event_id='evt_001',
            event_type='mastery_drop',
            subject='math', topic='algebra',
            mastery_before=78, mastery_after=70,
            emotion='frustrated', emotion_intensity=0.4,
            description='一元一次方程小测：3/10 错',
        )
        s = evt.to_human_readable()
        assert '[mastery_drop]' in s
        assert 'math/algebra' in s
        assert '78→70' in s
        assert 'Δ-8' in s
        assert 'frustrated' in s
        assert '0.4' in s
        assert '一元一次方程小测' in s

    def test_to_human_readable_none_subject_topic(self):
        evt = StudentEvent(
            event_id='evt_001',
            event_type='emotional_event',
            subject=None, topic=None,
            description='和妈妈吵架',
        )
        s = evt.to_human_readable()
        assert '?/?' in s  # 占位符


# ══════════════════════════════════════════════
# ALL_EVENT_TYPES
# ══════════════════════════════════════════════


class TestEventTypes:
    def test_all_event_types_count(self):
        assert len(ALL_EVENT_TYPES) == 8

    def test_all_event_types_contains_expected(self):
        expected = {
            'mastery_drop', 'mastery_rise', 'struggle_breakthrough',
            'emotional_event', 'social_event', 'fatigue_event',
            'praise_event', 'criticism_event',
        }
        assert set(ALL_EVENT_TYPES) == expected