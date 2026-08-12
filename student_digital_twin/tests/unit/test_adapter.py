"""test_adapter.py — student_event_to_sge_event + build_*_context + R5 安全约束

目标覆盖率 ≥ 90%
"""

from __future__ import annotations

import re

import pytest

from student_digital_twin.mastery import SubjectMasteryState
from student_digital_twin.events import StudentEvent
from student_digital_twin.adapter import (
    student_event_to_sge_event,
    build_critic_context_for_event,
    build_actor_prompt_for_event,
    SAFETY_DIRECTIVE, SAFETY_KEYWORDS_FORBIDDEN, SAFETY_KEYWORDS_REQUIRED,
)

from sge import TwinContextBuilder, AppContext


# ══════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════


@pytest.fixture
def alice_mastery() -> SubjectMasteryState:
    state = SubjectMasteryState(student_id='alice')
    state.update_topic('math', 'algebra', 70.0)
    state.update_topic('math', 'geometry', 75.0)
    state.update_topic('english', 'reading', 85.0)
    return state


@pytest.fixture
def sample_event() -> StudentEvent:
    return StudentEvent(
        event_id='evt_001',
        event_type='mastery_drop',
        subject='math', topic='algebra',
        mastery_before=78, mastery_after=70,
        emotion='frustrated', emotion_intensity=0.4,
        description='一元一次方程小测：3/10 错',
    )


@pytest.fixture
def builder() -> TwinContextBuilder:
    return TwinContextBuilder(app_state={
        'student_name': 'Alice',
        'student_grade': 8,
    })


# ══════════════════════════════════════════════
# student_event_to_sge_event
# ══════════════════════════════════════════════


class TestStudentEventToSgeEvent:
    def test_returns_compatible_dict(self, sample_event):
        sge_event = student_event_to_sge_event(sample_event)
        # TwinContextBuilder.build_actor_prompt_context 期望的字段
        assert 'type' in sge_event
        assert 'description' in sge_event
        assert 'intensity' in sge_event
        # StudentEvent 自有字段
        assert 'event_id' in sge_event
        assert 'subject' in sge_event
        assert 'topic' in sge_event
        assert 'mastery_delta' in sge_event

    def test_type_aliasing(self, sample_event):
        sge_event = student_event_to_sge_event(sample_event)
        assert sge_event['type'] == sample_event.event_type
        assert sge_event['event_type'] == sample_event.event_type  # 双命名兼容

    def test_intensity_aliasing(self, sample_event):
        sge_event = student_event_to_sge_event(sample_event)
        assert sge_event['intensity'] == sample_event.emotion_intensity
        assert sge_event['emotion_intensity'] == sample_event.emotion_intensity


# ══════════════════════════════════════════════
# build_critic_context_for_event
# ══════════════════════════════════════════════


class TestBuildCriticContext:
    def test_returns_dict_with_mastery_context(self, sample_event, alice_mastery, builder):
        ctx = build_critic_context_for_event(sample_event, alice_mastery, builder)
        assert isinstance(ctx, dict)
        # 默认 8D 字段
        assert 'user_emotion' in ctx
        assert 'topic_intimacy' in ctx
        # App 层注入（extra）
        assert ctx['subject'] == 'math'
        assert ctx['topic'] == 'algebra'
        assert ctx['event_type'] == 'mastery_drop'
        assert ctx['mastery_delta'] == -8

    def test_consumes_duck_typed_mastery(self, sample_event, alice_mastery, builder):
        ctx = build_critic_context_for_event(sample_event, alice_mastery, builder)
        # mastery_state 已被 duck typing 消费（extra 字段覆盖默认 8D）
        assert ctx['current_mastery_overview'] is not None
        assert 'math' in ctx['current_mastery_overview']
        assert ctx['recent_struggle'] is not None
        assert ctx['learning_pace'] is not None

    def test_handles_none_mastery(self, sample_event, builder):
        ctx = build_critic_context_for_event(sample_event, None, builder)
        assert isinstance(ctx, dict)
        # 无 mastery 时使用默认 8D
        assert 'user_emotion' in ctx

    def test_handles_mastery_without_methods(self, sample_event, builder):
        """若 mastery_state 缺方法，builder 应静默回退（不抛异常）。"""
        class EmptyMastery:
            pass

        ctx = build_critic_context_for_event(sample_event, EmptyMastery(), builder)
        assert isinstance(ctx, dict)

    def test_handles_mastery_method_raises(self, sample_event, builder):
        """若 mastery_state 方法抛异常，builder 应静默回退。"""
        class BrokenMastery:
            def summary(self):
                raise RuntimeError("oops")

        # 不应抛异常（builder 用 try/except 包裹）
        ctx = build_critic_context_for_event(sample_event, BrokenMastery(), builder)
        assert isinstance(ctx, dict)


# ══════════════════════════════════════════════
# build_actor_prompt_for_event
# ══════════════════════════════════════════════


class TestBuildActorPrompt:
    def test_includes_student_info(self, sample_event, alice_mastery, builder):
        prompt = build_actor_prompt_for_event(sample_event, alice_mastery, builder)
        assert 'Alice' in prompt
        assert '8' in prompt  # 年级

    def test_includes_mastery_overview(self, sample_event, alice_mastery, builder):
        prompt = build_actor_prompt_for_event(sample_event, alice_mastery, builder)
        assert 'math' in prompt
        assert 'algebra' in prompt

    def test_includes_event_info(self, sample_event, alice_mastery, builder):
        prompt = build_actor_prompt_for_event(sample_event, alice_mastery, builder)
        assert 'mastery_drop' in prompt
        assert '0.4' in prompt  # intensity
        assert '一元一次方程小测' in prompt

    def test_includes_safety_directive_by_default(self, sample_event, alice_mastery, builder):
        prompt = build_actor_prompt_for_event(sample_event, alice_mastery, builder)
        assert '[回复要求 - 强制约束 - 安全]' in prompt
        assert '不使用评判性语言' in prompt

    def test_safety_directive_excluded_when_disabled(self, sample_event, alice_mastery, builder):
        prompt = build_actor_prompt_for_event(
            sample_event, alice_mastery, builder, include_safety=False,
        )
        assert '[回复要求 - 强制约束 - 安全]' not in prompt

    def test_safety_replaces_topic_placeholder(self, alice_mastery, builder):
        evt = StudentEvent(
            event_id='evt_002',
            event_type='mastery_drop',
            subject='math', topic='algebra',
            mastery_before=70, mastery_after=55,
            description='因式分解卡住',
        )
        prompt = build_actor_prompt_for_event(evt, alice_mastery, builder)
        # {topic} 替换为 algebra
        assert '你最近algebra有挑战' in prompt


# ══════════════════════════════════════════════
# R5 安全约束验证
# ══════════════════════════════════════════════


class TestR5SafetyCompliance:
    """R5 风险：actor prompt 不应含评判性语言，应含建设性语言。"""

    def test_safety_directive_forbids_judgmental_language(self):
        """SAFETY_DIRECTIVE 必须提及'不使用评判性语言'（正向语义）。"""
        assert '不使用评判性语言' in SAFETY_DIRECTIVE, \
            "SAFETY_DIRECTIVE 应明确禁止评判性语言"
        # 检查 SAFETY_DIRECTIVE 不直接列出禁用词（避免子字符串假阳性）
        for keyword in SAFETY_KEYWORDS_FORBIDDEN:
            assert keyword not in SAFETY_DIRECTIVE, (
                f"SAFETY_DIRECTIVE 不应直接列出禁用词 '{keyword}'"
                f"（否则 prompt 会含该词，触发子字符串检测）"
            )

    def test_safety_directive_requires_constructive(self):
        for keyword in SAFETY_KEYWORDS_REQUIRED:
            assert keyword in SAFETY_DIRECTIVE, f"应明确要求: {keyword}"

    def test_sample_events_no_judgmental_keywords(self, alice_mastery, builder):
        """抽样 10 个真实事件，验证 actor prompt 不含评判性关键词。"""
        # 模拟 10 个真实学生场景
        scenarios = [
            ('math', 'algebra', 78, 45, 'frustrated', 0.7, '一元一次方程不会'),
            ('math', 'algebra', 60, 40, 'devastated', 0.9, '因式分解崩溃'),
            ('math', 'algebra', 70, 55, 'anxious', 0.6, '二元一次方程组不会'),
            ('english', 'reading', 85, 70, 'frustrated', 0.5, '长难句看不懂'),
            ('math', 'geometry', 80, 60, 'frustrated', 0.6, '三角形面积算错'),
            ('math', 'algebra', 50, 70, 'eureka', 0.9, '突然理解十字相乘法'),
            ('math', 'algebra', 65, 80, 'proud', 0.7, '一元二次方程求根公式'),
            ('english', 'writing', 80, 90, 'proud', 0.8, '作文被老师当范文'),
            ('math', 'algebra', 75, 65, 'discouraged', 0.6, '应用题找不到等量关系'),
            ('math', 'algebra', 55, 45, 'anxious', 0.8, '考试前焦虑'),
        ]
        for subj, topic, before, after, emotion, intensity, desc in scenarios:
            evt = StudentEvent(
                event_id=f'evt_{subj}_{topic}',
                event_type='mastery_drop' if after < before else 'mastery_rise',
                subject=subj, topic=topic,
                mastery_before=before, mastery_after=after,
                emotion=emotion, emotion_intensity=intensity,
                description=desc,
            )
            prompt = build_actor_prompt_for_event(evt, alice_mastery, builder)
            for keyword in SAFETY_KEYWORDS_FORBIDDEN:
                assert keyword not in prompt, (
                    f"actor prompt 含评判性语言 '{keyword}' in scenario: {desc}"
                )
            for keyword in SAFETY_KEYWORDS_REQUIRED:
                assert keyword in prompt, (
                    f"actor prompt 缺建设性语言 '{keyword}' in scenario: {desc}"
                )