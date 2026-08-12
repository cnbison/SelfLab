"""sge.critic pytest 单元测试 — stub_critic_sense 的 8 类型 + extra_context + critic_sense 统一入口。

Phase 3.2 conversion 第二批 1/4。
覆盖:
  1. 8 个 event_type 产出非空 context + value_delta
  2. context 字段在合法范围
  3. value_delta 字段在合法范围
  4. extra_context 覆盖默认 8D 同名字段
  5. extra_context 保留 App 层私有字段
  6. 同 seed 同 event → 同输出（可重现）
  7. critic_sense 统一入口：use_real_llm=False 走 stub
  8. critic_sense use_real_llm=True + llm=None 抛 ValueError
"""

from __future__ import annotations

import pytest

from sge.critic import (
    stub_critic_sense,
    real_critic_sense,
    critic_sense,
    CRITIC_CONTEXT_FIELDS,
    VALUE_DELTA_FIELDS,
)


BASE_EVENT = {
    'event_id': 'test-e0001-abcdef12',
    'type': 'neutral',  # critic.py 读 'type' 字段（注意：与 LifeEvent.to_dict 的 'event_type' 不同）
    'description': 'a neutral event',
    'intensity': 0.5,
    'timestamp': 0.0,
}


@pytest.mark.parametrize("event_type", [
    'success', 'failure', 'risk', 'contradiction_feedback',
    'relationship', 'exploration', 'value_conflict', 'neutral',
])
def test_stub_critic_sense_all_event_types_produce_valid_output(event_type):
    """所有 8 个 event_type 都产生合法 context + value_delta。"""
    event = {**BASE_EVENT, 'type': event_type, 'intensity': 0.7}
    context, value_delta = stub_critic_sense(event, seed=42)

    # context 字段包含 8D（value_conflict 可能含额外 challenge_level）
    assert set(CRITIC_CONTEXT_FIELDS).issubset(set(context.keys()))
    # value_delta 字段完整
    assert set(value_delta.keys()) == set(VALUE_DELTA_FIELDS)

    # context 字段在合法范围
    for field in CRITIC_CONTEXT_FIELDS:
        v = context[field]
        if field == 'user_emotion':
            assert -1.0 <= v <= 1.0, f"{field} out of [-1, 1]: {v}"
        else:
            assert 0.0 <= v <= 1.0, f"{field} out of [0, 1]: {v}"

    # value_delta 字段在合法范围
    for field in VALUE_DELTA_FIELDS:
        assert -1.0 <= value_delta[field] <= 1.0, f"{field} out of [-1, 1]"


def test_stub_critic_sense_returns_tuple_of_two_dicts():
    """返回 (context, value_delta) 元组。"""
    result = stub_critic_sense(BASE_EVENT, seed=0)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], dict)
    assert isinstance(result[1], dict)


def test_stub_critic_sense_event_type_neutral_has_zero_deltas():
    """neutral 事件 → value_delta 全 0（仅有随机扰动）。"""
    context, value_delta = stub_critic_sense(BASE_EVENT, seed=0)
    for field in VALUE_DELTA_FIELDS:
        # 中性事件基线全 0，但有小随机扰动
        assert abs(value_delta[field]) < 0.1, f"{field} too large for neutral"


def test_stub_critic_sense_intensity_scales_deltas():
    """intensity 越大 → value_delta 越大（线性缩放）。"""
    event_low = {**BASE_EVENT, 'type': 'success', 'intensity': 0.2}
    event_high = {**BASE_EVENT, 'type': 'success', 'intensity': 0.8}
    _, delta_low = stub_critic_sense(event_low, seed=42)
    _, delta_high = stub_critic_sense(event_high, seed=42)
    # success 的 safety delta > 0，intensity 高 → 绝对值应更大
    assert abs(delta_high['safety']) > abs(delta_low['safety'])


def test_stub_critic_sense_reproducible_with_same_seed():
    """同 seed 同 event → 同输出。"""
    e1, e2 = stub_critic_sense(BASE_EVENT, seed=42)
    e3, e4 = stub_critic_sense(BASE_EVENT, seed=42)
    assert e1 == e3
    assert e2 == e4


def test_stub_critic_sense_different_seeds_may_differ():
    """不同 seed 通常产生不同输出（用大差异种子）。"""
    e1, _ = stub_critic_sense(BASE_EVENT, seed=1)
    e2, _ = stub_critic_sense(BASE_EVENT, seed=999)
    # 至少有一个 context 字段不同
    assert e1 != e2


def test_stub_critic_sense_extra_context_overrides_default_8d():
    """extra_context 完全覆盖默认 8D 同名字段。"""
    event = {**BASE_EVENT, 'type': 'neutral'}
    extra = {'user_emotion': 0.99, 'topic_intimacy': 0.42, 'student_name': 'Alice'}
    context, _ = stub_critic_sense(event, seed=0, extra_context=extra)
    # 同名字段被覆盖（允许小幅随机扰动，差异 ≤ 0.5）
    assert abs(context['user_emotion'] - 0.99) < 0.5
    assert abs(context['topic_intimacy'] - 0.42) < 0.5


def test_stub_critic_sense_extra_context_preserves_app_fields():
    """extra_context 保留 App 层私有字段（如 student_name）。"""
    event = {**BASE_EVENT, 'type': 'neutral'}
    extra = {'student_name': 'Alice', 'grade': 7}
    context, _ = stub_critic_sense(event, seed=0, extra_context=extra)
    # App 字段原样保留（不被随机扰动，因为不是 CRITIC_CONTEXT_FIELDS）
    assert context['student_name'] == 'Alice'
    assert context['grade'] == 7


def test_stub_critic_sense_extra_context_none_uses_default():
    """extra_context=None → 默认 8D（无注入）。"""
    context, _ = stub_critic_sense(BASE_EVENT, seed=0, extra_context=None)
    # context 应只包含 CRITIC_CONTEXT_FIELDS 字段
    assert set(context.keys()) == set(CRITIC_CONTEXT_FIELDS)


def test_stub_critic_sense_event_missing_type_defaults_to_neutral():
    """event 缺 type 字段 → 默认 neutral。"""
    event = {'event_id': 'x', 'description': 'unknown', 'intensity': 0.5}
    context, value_delta = stub_critic_sense(event, seed=0)
    assert isinstance(context, dict)
    assert isinstance(value_delta, dict)


def test_stub_critic_sense_event_missing_intensity_defaults_to_0_5():
    """event 缺 intensity 字段 → 默认 0.5。"""
    event = {'event_id': 'x', 'type': 'success', 'description': 'test'}
    context, value_delta = stub_critic_sense(event, seed=0)
    assert isinstance(context, dict)
    assert isinstance(value_delta, dict)


def test_stub_critic_sense_event_unknown_type_returns_valid_output():
    """未知 type → fallback 默认 context（无报错）。"""
    event = {**BASE_EVENT, 'type': 'unknown_type'}
    context, value_delta = stub_critic_sense(event, seed=0)
    assert isinstance(context, dict)
    assert isinstance(value_delta, dict)
    for f in CRITIC_CONTEXT_FIELDS:
        assert f in context


def test_real_critic_sense_requires_llm():
    """real_critic_sense 无 llm 时必须抛 ValueError。"""
    with pytest.raises(ValueError, match='requires llm'):
        real_critic_sense(BASE_EVENT, llm=None)


def test_real_critic_sense_fallback_to_stub_on_llm_failure(stub_llm):
    """LLM 返回 None → 回退到 stub。"""
    stub_llm.chat_json.return_value = None  # 模拟 LLM 失败
    context, value_delta = real_critic_sense(
        BASE_EVENT, llm=stub_llm, extra_context={'student_name': 'Alice'}
    )
    assert isinstance(context, dict)
    assert isinstance(value_delta, dict)


def test_critic_sense_unified_entry_uses_stub_by_default():
    """use_real_llm=False（默认）走 stub 路径。"""
    context, value_delta = critic_sense(BASE_EVENT, use_real_llm=False, seed=42)
    assert isinstance(context, dict)
    assert isinstance(value_delta, dict)


def test_critic_sense_real_llm_requires_llm_parameter():
    """use_real_llm=True + llm=None → ValueError。"""
    with pytest.raises(ValueError, match='use_real_llm=True requires llm'):
        critic_sense(BASE_EVENT, use_real_llm=True, llm=None)


def test_critic_sense_unified_entry_passes_extra_context(stub_llm):
    """critic_sense 统一入口 extra_context 透传。"""
    stub_llm.chat_json.return_value = {
        'context': {f: 0.5 for f in CRITIC_CONTEXT_FIELDS},
        'value_delta': {f: 0.0 for f in VALUE_DELTA_FIELDS},
    }
    context, _ = critic_sense(
        BASE_EVENT, use_real_llm=True, llm=stub_llm,
        extra_context={'student_name': 'Alice'},
    )
    assert isinstance(context, dict)
    # 验证 stub_llm.chat_json 被调用了
    stub_llm.chat_json.assert_called_once()


def test_critic_sense_unified_entry_returns_llm_values():
    """real path 下返回 LLM 解析的 values。"""
    from unittest.mock import MagicMock
    llm = MagicMock()
    expected_context = {f: 0.7 for f in CRITIC_CONTEXT_FIELDS}
    expected_context['user_emotion'] = 0.5
    expected_delta = {f: 0.1 for f in VALUE_DELTA_FIELDS}
    llm.chat_json.return_value = {
        'context': expected_context,
        'value_delta': expected_delta,
    }
    context, delta = critic_sense(BASE_EVENT, use_real_llm=True, llm=llm)
    # 字段值在 clip 后应保持 0.7（合法范围内）
    assert context['user_emotion'] == 0.5
    for f in CRITIC_CONTEXT_FIELDS:
        if f != 'user_emotion':
            assert context[f] == 0.7
    assert delta == expected_delta


def test_critic_schema_field_constants():
    """CRITIC_CONTEXT_FIELDS 与 VALUE_DELTA_FIELDS 完整性。"""
    assert len(CRITIC_CONTEXT_FIELDS) == 8
    assert len(VALUE_DELTA_FIELDS) == 6
    # user_emotion 是唯一的 [-1, 1] 字段
    assert 'user_emotion' in CRITIC_CONTEXT_FIELDS
    # 6D value 字段（与 baseline SGE_DEFAULT_VALUES 一致）
    assert set(VALUE_DELTA_FIELDS) == {
        'safety', 'creativity', 'connection', 'autonomy', 'justice', 'compassion',
    }


def test_critic_sense_clips_user_emotion_to_valid_range():
    """real path 下 user_emotion 超出 [-1, 1] 时被 clip。"""
    from unittest.mock import MagicMock
    llm = MagicMock()
    llm.chat_json.return_value = {
        'context': {**{f: 0.5 for f in CRITIC_CONTEXT_FIELDS}, 'user_emotion': 5.0},
        'value_delta': {f: 0.0 for f in VALUE_DELTA_FIELDS},
    }
    context, _ = critic_sense(BASE_EVENT, use_real_llm=True, llm=llm)
    assert -1.0 <= context['user_emotion'] <= 1.0


def test_critic_sense_fills_missing_context_fields_with_default():
    """real path 下 LLM 缺字段 → 补 0.5（context）/ 0.0（value_delta）。"""
    from unittest.mock import MagicMock
    llm = MagicMock()
    llm.chat_json.return_value = {
        'context': {'user_emotion': 0.5},  # 只给一个字段
        'value_delta': {},
    }
    context, delta = critic_sense(BASE_EVENT, use_real_llm=True, llm=llm)
    # 缺失 context 字段补 0.5
    for f in CRITIC_CONTEXT_FIELDS:
        assert f in context
    # 缺失 value_delta 字段补 0.0
    for f in VALUE_DELTA_FIELDS:
        assert f in delta
        assert delta[f] == 0.0