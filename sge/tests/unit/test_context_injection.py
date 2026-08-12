"""sge.context_injection pytest 单元测试。

从 sge/context_injection.py 的 _run_context_injection_unit_tests() 提取。
Phase 3.2 conversion 1/N — 模板：每个内联 [测试 N] 段落变 test_xxx()。
"""

from __future__ import annotations

from sge.context_injection import (
    TwinContextBuilder,
    AppContext,
    CRITIC_DEFAULT_8D,
    critic_extra_context_to_prompt,
    actor_extra_system_prompt_to_prompt,
)


# ── TwinContextBuilder.build_critic_context ──


def test_build_critic_context_default_8d_complete():
    builder = TwinContextBuilder(app_state={'student_name': 'Alice'})
    ctx = builder.build_critic_context(student_event={'type': 'success'})
    assert set(ctx.keys()) == set(CRITIC_DEFAULT_8D)
    assert ctx['user_emotion'] == 0.0
    for f in CRITIC_DEFAULT_8D:
        if f != 'user_emotion':
            assert ctx[f] == 0.5


def test_build_critic_context_extra_overrides_default():
    builder = TwinContextBuilder(app_state={'student_name': 'Alice'})
    extra = {
        'student_name': 'Alice',
        'student_grade': 7,
        'user_emotion': -0.8,
        'user_vulnerability': 0.9,
    }
    ctx = builder.build_critic_context(extra=extra)
    assert ctx['user_emotion'] == -0.8
    assert ctx['user_vulnerability'] == 0.9
    assert ctx['student_name'] == 'Alice'
    assert ctx['student_grade'] == 7
    # 未覆盖字段保持默认
    assert ctx['novelty_level'] == 0.5


def test_build_critic_context_no_app_state_works():
    """app_state=None 时 builder 仍可用。"""
    builder = TwinContextBuilder()
    ctx = builder.build_critic_context()
    assert set(ctx.keys()) == set(CRITIC_DEFAULT_8D)


# ── mastery_state duck typing ──


class _FakeMastery:
    def summary(self): return 'math: 90, english: 88'
    def most_recent_struggling(self): return 'math/geometry'
    def learning_velocity(self): return 0.85


class _BrokenMastery:
    def summary(self): raise RuntimeError("not yet implemented")


def test_build_critic_context_mastery_duck_typing():
    builder = TwinContextBuilder(app_state={'student_name': 'Bob', 'grade': 9})
    ctx = builder.build_critic_context(mastery_state=_FakeMastery())
    assert ctx['current_mastery_overview'] == 'math: 90, english: 88'
    assert ctx['recent_struggle'] == 'math/geometry'
    assert ctx['learning_pace'] == 0.85


def test_build_critic_context_mastery_exception_silent_fallback():
    """mastery.summary() 抛异常时，ctx 保持默认（不污染）。"""
    builder = TwinContextBuilder(app_state={'student_name': 'Bob', 'grade': 9})
    ctx = builder.build_critic_context(mastery_state=_BrokenMastery())
    assert 'current_mastery_overview' not in ctx
    assert ctx['user_emotion'] == 0.0


def test_build_critic_context_mastery_method_missing_silent():
    """mastery 无 summary() 时静默忽略（不是异常）。"""
    class EmptyMastery:
        pass
    builder = TwinContextBuilder()
    ctx = builder.build_critic_context(mastery_state=EmptyMastery())
    assert 'current_mastery_overview' not in ctx


# ── build_actor_prompt_context ──


def test_build_actor_prompt_context_three_sections():
    builder = TwinContextBuilder(app_state={
        'student_name': 'Alice', 'grade': 7,
        'current_mastery_overview': 'math: 65, english: 82',
        'recent_struggle': 'math/algebra',
    })
    actor_ctx = builder.build_actor_prompt_context(
        student_event={'type': 'failure', 'description': '测试没及格', 'intensity': 0.7},
    )
    assert '[学生信息]' in actor_ctx
    assert '姓名: Alice' in actor_ctx
    assert '年级: 7' in actor_ctx
    assert 'math: 65, english: 82' in actor_ctx
    assert 'math/algebra' in actor_ctx
    assert '[本次事件]' in actor_ctx
    assert '测试没及格' in actor_ctx
    assert '[回复要求]' in actor_ctx


def test_build_actor_prompt_context_no_event_shows_placeholder():
    builder = TwinContextBuilder(app_state={'student_name': 'Alice'})
    actor_ctx = builder.build_actor_prompt_context()
    assert '（无事件）' in actor_ctx


def test_build_actor_prompt_context_mastery_overrides_app_state():
    """mastery_state 覆盖 app_state['current_mastery_overview']。"""
    builder = TwinContextBuilder(app_state={'current_mastery_overview': 'stale'})
    actor_ctx = builder.build_actor_prompt_context(mastery_state=_FakeMastery())
    assert 'math: 90, english: 88' in actor_ctx
    assert 'stale' not in actor_ctx


# ── AppContext dataclass ──


def test_app_context_to_dict_skips_none_and_flattens_extra():
    ctx = AppContext(
        student_name='Alice', student_grade=7,
        current_mastery_overview='math: 65',
        extra={'learning_pace': 0.6, 'recent_struggle': 'math/algebra'},
    )
    d = ctx.to_dict()
    assert d['student_name'] == 'Alice'
    assert d['student_grade'] == 7
    assert d.get('learning_pace') == 0.6
    assert d.get('recent_struggle') == 'math/algebra'
    assert 'extra' not in d
    assert 'learning_goals' not in d  # 未填字段跳过
    assert 'user_name' not in d


def test_app_context_to_dict_all_optional():
    """全字段默认时 to_dict 返回空 dict。"""
    ctx = AppContext()
    assert ctx.to_dict() == {}


def test_app_context_supports_personal_ai_fields():
    """Personal AI 场景字段（user_name / relationship_history）。"""
    ctx = AppContext(user_name='Alice', relationship_history='3-year friendship')
    d = ctx.to_dict()
    assert d['user_name'] == 'Alice'
    assert d['relationship_history'] == '3-year friendship'


def test_app_context_supports_historical_figure_fields():
    """历史人物场景字段（person_name / era / historical_context）。"""
    ctx = AppContext(
        person_name='苏格拉底', era='古希腊',
        historical_context='公元前 399 年被处死',
    )
    d = ctx.to_dict()
    assert d['person_name'] == '苏格拉底'
    assert d['era'] == '古希腊'
    assert d['historical_context'] == '公元前 399 年被处死'


# ── 序列化辅助 ──


def test_critic_extra_context_to_prompt_serialization():
    s = critic_extra_context_to_prompt({'student_name': 'Alice', 'grade': 7})
    assert '[App Context]' in s
    assert '"student_name": "Alice"' in s


def test_critic_extra_context_to_prompt_none_returns_empty():
    assert critic_extra_context_to_prompt(None) == ''


def test_critic_extra_context_to_prompt_empty_dict_returns_empty():
    assert critic_extra_context_to_prompt({}) == ''


def test_actor_extra_system_prompt_to_prompt_passthrough():
    assert actor_extra_system_prompt_to_prompt('hello') == 'hello'
    assert actor_extra_system_prompt_to_prompt('') == ''
    assert actor_extra_system_prompt_to_prompt(None) == ''


# ── critic_sense extra_context plumbing ──


def test_critic_sense_extra_context_overrides_default_8d_stub():
    """critic_sense stub 路径：extra 覆盖默认 8D + App 私有字段透传。"""
    from sge import critic_sense

    extra = {
        'user_emotion': -0.7,
        'user_vulnerability': 0.9,
        'student_name': 'Alice',
        'student_grade': 7,
    }
    ctx, _ = critic_sense(
        event={'type': 'failure', 'intensity': 0.8},
        seed=42,
        extra_context=extra,
    )
    # stub 给 8D 数值加 ±0.2 范围内扰动，App 字符串/整数原样
    assert abs(ctx['user_emotion'] - (-0.7)) < 0.2
    assert abs(ctx['user_vulnerability'] - 0.9) < 0.2
    assert ctx['student_name'] == 'Alice'
    assert ctx['student_grade'] == 7
    assert abs(ctx['novelty_level'] - 0.5) < 0.2


def test_critic_sense_extra_context_none_keeps_default():
    """extra_context=None 时 critic_sense 行为与原版一致。"""
    from sge import critic_sense

    ctx, _ = critic_sense(
        event={'type': 'failure', 'intensity': 0.5},
        seed=42,
        extra_context=None,
    )
    assert 'student_name' not in ctx
    assert set(ctx.keys()) == set(CRITIC_DEFAULT_8D)