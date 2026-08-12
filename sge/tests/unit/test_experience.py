"""sge.experience pytest 单元测试 — Experience / stub_encode_experience / real_encode_experience。

Phase 3.2 conversion 第二批 3/4。
覆盖:
  1. Experience dataclass + to_dict
  2. make_experience_id 格式
  3. stub_encode_experience 7 类型全部产出合法 Experience
  4. emotion / goal_relevance / uncertainty 在 [0, 1]
  5. experience_id 格式正确
  6. 可重现（同 seed 同结果）
  7. _clip01 边界（0/1 clamp）
  8. real_encode_experience 无 llm 抛 ValueError
  9. real_encode_experience LLM 返回 None → 回退 stub
  10. encode_experience 统一入口
"""

from __future__ import annotations

import pytest

from sge.experience import (
    Experience,
    make_experience_id,
    stub_encode_experience,
    real_encode_experience,
    encode_experience,
    _clip01,
    _TYPE_TO_MEANING,
)


BASE_EVENT = {
    'event_id': 'test-e0001-abcd1234',
    'event_type': 'neutral',
    'description': 'a neutral event',
    'intensity': 0.5,
    'causal_context': 'prior context',
    'timestamp': 100.0,
}


# ════════════════════════════════════════════════
# Experience dataclass
# ════════════════════════════════════════════════


def test_experience_dataclass_construction():
    """Experience dataclass 构造。"""
    exp = Experience(
        experience_id='e1-exp',
        event={'event_id': 'e1'},
        context='ctx',
        emotion={'valence': 0.7, 'arousal': 0.5},
        goal_relevance=0.6,
        meaning='m',
        uncertainty=0.3,
        timestamp=1.0,
    )
    assert exp.experience_id == 'e1-exp'
    assert exp.meaning == 'm'


def test_experience_to_dict_round_trip():
    """to_dict 返回 dict 含全部字段。"""
    exp = Experience(
        experience_id='e1-exp',
        event={'event_id': 'e1'},
        context='ctx',
        emotion={'valence': 0.7, 'arousal': 0.5},
        goal_relevance=0.6,
        meaning='m',
        uncertainty=0.3,
        timestamp=1.0,
        action_taken='at',
        outcome='o',
        reflection='r',
    )
    d = exp.to_dict()
    assert d['experience_id'] == 'e1-exp'
    assert d['meaning'] == 'm'
    assert d['action_taken'] == 'at'
    assert d['outcome'] == 'o'
    assert d['reflection'] == 'r'


def test_experience_default_post_event_fields_empty():
    """action_taken / outcome / reflection MVP 默认空串。"""
    exp = Experience(
        experience_id='e1-exp',
        event={}, context='', emotion={},
        goal_relevance=0.5, meaning='', uncertainty=0.5, timestamp=0.0,
    )
    assert exp.action_taken == ''
    assert exp.outcome == ''
    assert exp.reflection == ''


def test_make_experience_id_format():
    """make_experience_id 格式：'{event_id}-exp'。"""
    assert make_experience_id('e1') == 'e1-exp'
    assert make_experience_id('test-e0001-abcd1234') == 'test-e0001-abcd1234-exp'


# ════════════════════════════════════════════════
# _clip01 工具函数
# ════════════════════════════════════════════════


def test_clip01_clamps_above_1():
    """_clip01 把 > 1 截到 1。"""
    assert _clip01(2.5) == 1.0


def test_clip01_clamps_below_0():
    """_clip01 把 < 0 截到 0。"""
    assert _clip01(-0.5) == 0.0


def test_clip01_passes_through_valid():
    """_clip01 保留 [0, 1] 范围内的值。"""
    assert _clip01(0.5) == 0.5
    assert _clip01(0.0) == 0.0
    assert _clip01(1.0) == 1.0


# ════════════════════════════════════════════════
# stub_encode_experience
# ════════════════════════════════════════════════


@pytest.mark.parametrize("event_type", [
    'success', 'failure', 'risk', 'relationship',
    'exploration', 'value_conflict', 'neutral',
])
def test_stub_encode_experience_all_event_types(event_type):
    """7 个事件类型全部产出非空 meaning + 合法 emotion/goal_relevance/uncertainty。"""
    event = {**BASE_EVENT, 'event_type': event_type, 'intensity': 0.7}
    exp = stub_encode_experience(event, seed=42)

    assert exp.meaning, f"empty meaning for {event_type}"
    assert 0.0 <= exp.emotion['valence'] <= 1.0
    assert 0.0 <= exp.emotion['arousal'] <= 1.0
    assert 0.0 <= exp.goal_relevance <= 1.0
    assert 0.0 <= exp.uncertainty <= 1.0
    assert exp.experience_id == 'test-e0001-abcd1234-exp'


def test_stub_encode_experience_unknown_type_falls_back_to_neutral():
    """未知 event_type → neutral 模板。"""
    event = {**BASE_EVENT, 'event_type': 'unknown_xyz'}
    exp = stub_encode_experience(event, seed=0)
    assert exp.meaning == _TYPE_TO_MEANING['neutral']


def test_stub_encode_experience_value_conflict_higher_uncertainty():
    """value_conflict 类事件 uncertainty 基础值更高（0.5 vs 0.25）。"""
    event_conflict = {**BASE_EVENT, 'event_type': 'value_conflict'}
    event_neutral = {**BASE_EVENT, 'event_type': 'neutral'}
    # 同 seed 不一定能完美比较，但 value_conflict 应明显更高
    exp_conflict = stub_encode_experience(event_conflict, seed=42)
    exp_neutral = stub_encode_experience(event_neutral, seed=42)
    assert exp_conflict.uncertainty > exp_neutral.uncertainty


def test_stub_encode_experience_arousal_scales_with_intensity():
    """arousal 受 intensity 影响（intensity 越高 arousal 越高）。"""
    event_low = {**BASE_EVENT, 'event_type': 'risk', 'intensity': 0.1}
    event_high = {**BASE_EVENT, 'event_type': 'risk', 'intensity': 0.9}
    exp_low = stub_encode_experience(event_low, seed=42)
    exp_high = stub_encode_experience(event_high, seed=42)
    assert exp_high.emotion['arousal'] > exp_low.emotion['arousal']


def test_stub_encode_experience_reproducible_with_same_seed():
    """同 seed 同 event → 完全相同的 Experience。"""
    e1 = stub_encode_experience(BASE_EVENT, seed=7)
    e2 = stub_encode_experience(BASE_EVENT, seed=7)
    assert e1.to_dict() == e2.to_dict()


def test_stub_encode_experience_different_seeds_may_differ():
    """不同 seed 通常产生不同 emotion/goal_relevance/uncertainty。"""
    e1 = stub_encode_experience(BASE_EVENT, seed=1)
    e2 = stub_encode_experience(BASE_EVENT, seed=999)
    # 至少 emotion 不同（随机扰动）
    assert e1.emotion != e2.emotion


def test_stub_encode_experience_context_from_causal():
    """context 优先取 causal_context，否则取 description。"""
    event = {**BASE_EVENT, 'causal_context': 'CAUSAL_PRIORITY'}
    exp = stub_encode_experience(event, seed=0)
    assert exp.context == 'CAUSAL_PRIORITY'

    event_no_causal = {k: v for k, v in BASE_EVENT.items() if k != 'causal_context'}
    event_no_causal['description'] = 'DESC_ONLY'
    exp2 = stub_encode_experience(event_no_causal, seed=0)
    assert exp2.context == 'DESC_ONLY'


def test_stub_encode_experience_event_missing_event_id_uses_unknown():
    """event 缺 event_id → 'unknown'。"""
    event = {k: v for k, v in BASE_EVENT.items() if k != 'event_id'}
    event['event_type'] = 'success'
    exp = stub_encode_experience(event, seed=0)
    assert exp.experience_id == 'unknown-exp'


def test_stub_encode_experience_event_missing_timestamp_defaults_to_0():
    """event 缺 timestamp → 0.0。"""
    event = {k: v for k, v in BASE_EVENT.items() if k != 'timestamp'}
    exp = stub_encode_experience(event, seed=0)
    assert exp.timestamp == 0.0


# ════════════════════════════════════════════════
# real_encode_experience
# ════════════════════════════════════════════════


def test_real_encode_experience_requires_llm():
    """real_encode_experience 无 llm 时抛 ValueError。"""
    with pytest.raises(ValueError, match='requires llm'):
        real_encode_experience(BASE_EVENT, llm=None)


def test_real_encode_experience_fallback_on_llm_none():
    """LLM 返回 None → 回退到 stub。"""
    from unittest.mock import MagicMock
    llm = MagicMock()
    llm.chat_json.return_value = None
    exp = real_encode_experience(BASE_EVENT, llm=llm)
    assert isinstance(exp, Experience)
    assert exp.meaning  # stub meaning 非空


def test_real_encode_experience_uses_llm_values():
    """LLM 返回有效 JSON → 使用 LLM 的 meaning/emotion 等。"""
    from unittest.mock import MagicMock
    llm = MagicMock()
    llm.chat_json.return_value = {
        'context': 'LLM_GENERATED_CTX',
        'emotion': {'valence': 0.9, 'arousal': 0.8},
        'goal_relevance': 0.7,
        'meaning': 'LLM_GENERATED_MEANING',
        'uncertainty': 0.4,
    }
    exp = real_encode_experience(BASE_EVENT, llm=llm)
    assert exp.meaning == 'LLM_GENERATED_MEANING'
    assert exp.context == 'LLM_GENERATED_CTX'
    assert exp.emotion['valence'] == 0.9


def test_real_encode_experience_clamps_values():
    """LLM 返回超出 [0, 1] 的值 → _clip01 截断。"""
    from unittest.mock import MagicMock
    llm = MagicMock()
    llm.chat_json.return_value = {
        'context': 'ctx',
        'emotion': {'valence': 5.0, 'arousal': -1.0},
        'goal_relevance': 2.0,
        'meaning': 'm',
        'uncertainty': -0.5,
    }
    exp = real_encode_experience(BASE_EVENT, llm=llm)
    assert exp.emotion['valence'] == 1.0
    assert exp.emotion['arousal'] == 0.0
    assert exp.goal_relevance == 1.0
    assert exp.uncertainty == 0.0


def test_real_encode_experience_empty_meaning_fallback():
    """LLM 返回 meaning 空字符串 → 回退到 stub 模板。"""
    from unittest.mock import MagicMock
    llm = MagicMock()
    llm.chat_json.return_value = {
        'context': 'ctx',
        'emotion': {'valence': 0.5, 'arousal': 0.5},
        'goal_relevance': 0.5,
        'meaning': '',
        'uncertainty': 0.3,
    }
    exp = real_encode_experience(BASE_EVENT, llm=llm)
    assert exp.meaning == _TYPE_TO_MEANING['neutral']


def test_real_encode_experience_context_fallback_to_causal():
    """LLM 返回 context 空 → 回退到 event.causal_context。"""
    from unittest.mock import MagicMock
    llm = MagicMock()
    llm.chat_json.return_value = {
        'context': '',
        'emotion': {'valence': 0.5, 'arousal': 0.5},
        'goal_relevance': 0.5,
        'meaning': 'm',
        'uncertainty': 0.3,
    }
    exp = real_encode_experience(BASE_EVENT, llm=llm)
    assert exp.context == 'prior context'


# ════════════════════════════════════════════════
# encode_experience 统一入口
# ════════════════════════════════════════════════


def test_encode_experience_uses_stub_by_default():
    """use_real_llm=False（默认）走 stub。"""
    exp = encode_experience(BASE_EVENT, use_real_llm=False, seed=42)
    assert isinstance(exp, Experience)
    assert exp.meaning


def test_encode_experience_real_llm_requires_llm_parameter():
    """use_real_llm=True + llm=None → ValueError。"""
    with pytest.raises(ValueError, match='use_real_llm=True requires llm'):
        encode_experience(BASE_EVENT, use_real_llm=True, llm=None)


def test_encode_experience_unified_entry_with_real_llm():
    """统一入口 + use_real_llm=True + stub_llm fixture → 走 real 路径。"""
    from unittest.mock import MagicMock
    llm = MagicMock()
    llm.chat_json.return_value = {
        'context': 'CTX',
        'emotion': {'valence': 0.7, 'arousal': 0.5},
        'goal_relevance': 0.6,
        'meaning': 'LLM_MEANING',
        'uncertainty': 0.3,
    }
    exp = encode_experience(BASE_EVENT, use_real_llm=True, llm=llm)
    assert exp.meaning == 'LLM_MEANING'


def test_encode_experience_value_state_and_goal_passed_to_stub():
    """value_state/goal 参数透传到 stub（不抛错即可）。"""
    value_state = {'safety': 0.5, 'creativity': 0.3}
    exp = encode_experience(
        BASE_EVENT, value_state=value_state, goal='learn',
        use_real_llm=False, seed=42,
    )
    assert isinstance(exp, Experience)


# ════════════════════════════════════════════════
# _TYPE_TO_MEANING 完整性
# ════════════════════════════════════════════════


def test_type_to_meaning_covers_required_types():
    """_TYPE_TO_MEANING 包含 7 种核心类型。"""
    required = {'success', 'failure', 'risk', 'relationship',
                'exploration', 'value_conflict', 'neutral'}
    assert required.issubset(set(_TYPE_TO_MEANING.keys()))


def test_type_to_meaning_all_meanings_non_empty():
    """所有 meaning 模板非空。"""
    for etype, meaning in _TYPE_TO_MEANING.items():
        assert meaning, f"empty meaning for {etype}"
        assert isinstance(meaning, str)