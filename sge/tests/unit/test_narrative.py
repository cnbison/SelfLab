"""sge.narrative pytest 单元测试 — NarrativeBuilder / stub / real LLM / phase_transition / snapshot。

Phase 3.2 conversion 第三批 2/4。
覆盖:
  1. _format_events_timeline
  2. stub_build_narrative（含 identity/无 events/多 events 分支）
  3. stub_check_narrative_consistency
  4. real_build_narrative / real_check_narrative_consistency（fake litellm 注入）
  5. NarrativeBuilder __init__ + should_build + get_current
  6. build stub 路径 + dedup（jaccard + ngram）
  7. build real LLM 路径（dict/str/number/fallback）
  8. check_consistency stub + real LLM（含数字解析）
  9. handle_phase_transition accept/reject 两条分支
 10. snapshot/restore round-trip + strict missing field
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from types import ModuleType

import pytest

from sge.narrative import (
    NarrativeBuilder,
    stub_build_narrative,
    stub_check_narrative_consistency,
    _format_events_timeline,
)
from sge.baseline import SnapshotError


# ════════════════════════════════════════════════
# _format_events_timeline
# ════════════════════════════════════════════════


def test_format_events_timeline_empty():
    """空 events → '（无经历）'。"""
    assert _format_events_timeline([]) == '（无经历）'


def test_format_events_timeline_dict_events():
    """dict events → [E0] type: desc 格式。"""
    events = [
        {'event_type': 'success', 'description': '完成了重要项目'},
        {'event_type': 'failure', 'description': '考试失败'},
    ]
    timeline = _format_events_timeline(events)
    assert '[E0]' in timeline
    assert '[E1]' in timeline
    assert 'success' in timeline
    assert 'failure' in timeline


def test_format_events_timeline_string_events():
    """字符串 events → 直接截断 50 字符。"""
    timeline = _format_events_timeline(['event-a', 'event-b'])
    assert '[E0]' in timeline
    assert 'event-a' in timeline
    assert '[E1]' in timeline


def test_format_events_timeline_missing_description():
    """events 缺 description → 用 str(event) 兜底。"""
    events = [{'event_type': 'success'}]  # 无 description
    timeline = _format_events_timeline(events)
    assert 'success' in timeline


def test_format_events_timeline_long_description_truncated():
    """超长 description → 截断到 50 字符。"""
    long_desc = 'a' * 100
    timeline = _format_events_timeline([{'event_type': 'x', 'description': long_desc}])
    # 不应包含完整 100 个 a
    assert 'a' * 51 not in timeline


# ════════════════════════════════════════════════
# stub_build_narrative
# ════════════════════════════════════════════════


def test_stub_build_narrative_empty_events():
    """空 events → '我还在寻找自己的故事。'"""
    narrative = stub_build_narrative([], None, seed=42)
    assert '寻找自己的故事' in narrative


def test_stub_build_narrative_with_identity():
    """有 current_identity → '我是{identity}' 起头。"""
    events = [{'event_type': 'success', 'description': 'x'} for _ in range(5)]
    narrative = stub_build_narrative(events, '探索者', seed=42)
    assert '我是探索者' in narrative


def test_stub_build_narrative_without_identity():
    """无 current_identity → 不含 '我是' 前缀。"""
    events = [{'event_type': 'success', 'description': 'x'} for _ in range(5)]
    narrative = stub_build_narrative(events, None, seed=42)
    assert not narrative.startswith('我是')


def test_stub_build_narrative_few_events():
    """n <= 3 → present_events 为空。"""
    events = [{'event_type': 'success', 'description': f'e{i}'} for i in range(3)]
    narrative = stub_build_narrative(events, None, seed=42)
    # 此时 past=1, future=1, present=空
    assert '回顾过去' in narrative


def test_stub_build_narrative_reproducible_with_same_seed():
    """同 seed → 完全相同结果。"""
    events = [{'event_type': 'success', 'description': f'e{i}'} for i in range(5)]
    n1 = stub_build_narrative(events, '身份', seed=42)
    n2 = stub_build_narrative(events, '身份', seed=42)
    assert n1 == n2


def test_stub_build_narrative_uses_future_event_type():
    """未来部分引用最后一个 event 的 event_type。"""
    events = [
        {'event_type': 'success', 'description': f'e{i}'} for i in range(6)
    ]
    events[-1]['event_type'] = 'exploration'
    narrative = stub_build_narrative(events, None, seed=42)
    assert 'exploration' in narrative


# ════════════════════════════════════════════════
# stub_check_narrative_consistency
# ════════════════════════════════════════════════


def test_stub_check_narrative_consistency_empty():
    """空 events → 0.5。"""
    score = stub_check_narrative_consistency('任何叙事', [], seed=42)
    assert score == 0.5


def test_stub_check_narrative_consistency_one_event():
    """1 event → 0.6 + jitter ≈ 0.55-0.65。"""
    score = stub_check_narrative_consistency(
        '叙事', [{'event_type': 'x', 'description': 'y'}], seed=42,
    )
    assert 0.55 <= score <= 0.65


def test_stub_check_narrative_consistency_more_events_higher():
    """更多 events → 更高分数（base 公式）。"""
    events_1 = [{'event_type': 'x', 'description': 'y'}]
    events_5 = [{'event_type': 'x', 'description': f'e{i}'} for i in range(5)]
    score_1 = stub_check_narrative_consistency('n', events_1, seed=42)
    score_5 = stub_check_narrative_consistency('n', events_5, seed=42)
    assert score_5 > score_1


def test_stub_check_narrative_consistency_capped_at_1():
    """很多 events → base 上限 1.0（±0.05 jitter 可能略超过）。"""
    events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(20)]
    score = stub_check_narrative_consistency('n', events, seed=42)
    # base=1.0 + uniform(-0.05, 0.05) → 可能 0.95-1.05
    assert 0.95 <= score <= 1.05


# ════════════════════════════════════════════════
# real_build_narrative / real_check_narrative_consistency（fake litellm 注入）
# ════════════════════════════════════════════════


class _FakeLitellmCompletion:
    """fake litellm.completion 用于 real_* 测试。"""
    def __init__(self):
        self.call_count = 0
        self.next_content = '{"narrative": "fake narrative"}'

    def __call__(self, **kwargs):
        self.call_count += 1
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = self.next_content
        return mock_response


class _FakeLitellmExceptions:
    InternalServerError = type('InternalServerError', (Exception,), {})
    APIConnectionError = type('APIConnectionError', (Exception,), {})
    Timeout = type('Timeout', (Exception,), {})
    RateLimitError = type('RateLimitError', (Exception,), {})
    ServiceUnavailableError = type('ServiceUnavailableError', (Exception,), {})
    APIError = type('APIError', (Exception,), {})


@pytest.fixture
def fake_litellm():
    """注入 fake litellm 到 sys.modules，real_* 函数即可调用。"""
    import sys
    fake = ModuleType('litellm')
    fake.completion = _FakeLitellmCompletion()
    fake.exceptions = _FakeLitellmExceptions()
    sys.modules['litellm'] = fake
    yield fake
    sys.modules.pop('litellm', None)


def test_real_build_narrative_parses_json(fake_litellm):
    """fake litellm 返回合法 JSON → 提取 'narrative'。"""
    from sge.narrative import real_build_narrative
    fake_litellm.completion.next_content = '{"narrative": "我的人生故事"}'
    events = [{'event_type': 'success', 'description': 'e1'}]
    n = real_build_narrative(events, '身份', api_key='fake-key')
    assert n == '我的人生故事'
    assert fake_litellm.completion.call_count == 1


def test_real_build_narrative_handles_markdown_fence(fake_litellm):
    """fake litellm 返回 ```json fence → 正确剥离。"""
    from sge.narrative import real_build_narrative
    fake_litellm.completion.next_content = '```json\n{"narrative": "解析正确"}\n```'
    events = [{'event_type': 'success', 'description': 'e1'}]
    n = real_build_narrative(events, '身份', api_key='fake-key')
    assert n == '解析正确'


def test_real_build_narrative_invalid_json_falls_back(fake_litellm):
    """fake litellm 返回非法 JSON → 取前 200 字符。"""
    from sge.narrative import real_build_narrative
    fake_litellm.completion.next_content = '不是 JSON'
    events = [{'event_type': 'success', 'description': 'e1'}]
    n = real_build_narrative(events, '身份', api_key='fake-key')
    assert n == '不是 JSON'


def test_real_build_narrative_no_api_key_raises(fake_litellm):
    """缺 API key → ValueError。"""
    from sge.narrative import real_build_narrative
    import os
    env_backup = os.environ.copy()
    os.environ.pop('MINIMAX_API_KEY', None)
    try:
        with pytest.raises(ValueError, match='MINIMAX_API_KEY'):
            real_build_narrative([], '身份', api_key=None)
    finally:
        os.environ.update(env_backup)


def test_real_check_narrative_consistency_parses_number(fake_litellm):
    """fake litellm 返回数字 → 解析为 float。"""
    from sge.narrative import real_check_narrative_consistency
    fake_litellm.completion.next_content = '0.85'
    events = [{'event_type': 'success', 'description': 'e1'}]
    score = real_check_narrative_consistency('narrative', events, api_key='fake-key')
    assert score == 0.85


def test_real_check_narrative_consistency_parses_text_with_number(fake_litellm):
    """fake litellm 返回带文字的数字 → 提取第一个数字。"""
    from sge.narrative import real_check_narrative_consistency
    fake_litellm.completion.next_content = 'The score is 0.92 out of 1.0'
    events = [{'event_type': 'success', 'description': 'e1'}]
    score = real_check_narrative_consistency('narrative', events, api_key='fake-key')
    assert score == 0.92


def test_real_check_narrative_consistency_parses_int(fake_litellm):
    """fake litellm 返回整数 → 解析为 float。"""
    from sge.narrative import real_check_narrative_consistency
    fake_litellm.completion.next_content = '1'
    events = [{'event_type': 'success', 'description': 'e1'}]
    score = real_check_narrative_consistency('narrative', events, api_key='fake-key')
    assert score == 1.0


def test_real_check_narrative_consistency_invalid_returns_05(fake_litellm):
    """fake litellm 返回无数字 → 默认 0.5。"""
    from sge.narrative import real_check_narrative_consistency
    fake_litellm.completion.next_content = 'no number here'
    events = [{'event_type': 'success', 'description': 'e1'}]
    score = real_check_narrative_consistency('narrative', events, api_key='fake-key')
    assert score == 0.5


def test_real_check_narrative_consistency_clamps_to_range(fake_litellm):
    """fake litellm 返回超出 [0, 1] → clamp。"""
    from sge.narrative import real_check_narrative_consistency
    fake_litellm.completion.next_content = '1.5'  # > 1
    events = [{'event_type': 'success', 'description': 'e1'}]
    score = real_check_narrative_consistency('narrative', events, api_key='fake-key')
    assert score == 1.0


# ════════════════════════════════════════════════
# NarrativeBuilder 类
# ════════════════════════════════════════════════


def test_narrative_builder_init_defaults():
    """默认参数。"""
    nb = NarrativeBuilder()
    assert nb.current_narrative is None
    assert nb.build_every_n_epochs == 50
    assert nb.use_real_llm is False
    assert nb.consistency_threshold == 0.5
    assert nb.dedup_threshold == 0.0
    assert nb.dedup_window == 1
    assert nb.narrative_history == []


def test_narrative_builder_init_with_initial_narrative():
    """传入 current_narrative。"""
    nb = NarrativeBuilder(current_narrative='初始叙事')
    assert nb.current_narrative == '初始叙事'


def test_narrative_builder_should_build_trigger_epochs():
    """(epoch + 1) % N == 0（默认 N=50）。"""
    nb = NarrativeBuilder()
    assert not nb.should_build(0)
    assert not nb.should_build(48)
    assert nb.should_build(49)
    assert nb.should_build(99)


def test_narrative_builder_should_build_custom_n():
    """自定义 N=10。"""
    nb = NarrativeBuilder(build_every_n_epochs=10)
    assert nb.should_build(9)
    assert not nb.should_build(10)
    assert nb.should_build(19)


def test_narrative_builder_get_current():
    """get_current 返回当前叙事。"""
    nb = NarrativeBuilder(current_narrative='当前')
    assert nb.get_current() == '当前'


def test_narrative_builder_build_stub_appends_history():
    """stub build → 追加到 narrative_history（含 coherence）。"""
    nb = NarrativeBuilder()
    events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(5)]
    narrative = nb.build(events, '身份', epoch=0, seed=42)
    assert narrative
    assert len(nb.narrative_history) == 1
    entry = nb.narrative_history[0]
    assert entry['epoch'] == 0
    assert entry['narrative'] == narrative
    assert 'coherence' in entry
    assert entry['phase_transition'] is False


def test_narrative_builder_build_stub_sets_current_narrative():
    """stub build → 设置 current_narrative。"""
    nb = NarrativeBuilder()
    events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(5)]
    narrative = nb.build(events, '身份', epoch=0, seed=42)
    assert nb.current_narrative == narrative


def test_narrative_builder_build_dedup_jaccard_skips():
    """dedup jaccard 命中 → 不追加 + 返回最近一条。"""
    nb = NarrativeBuilder(dedup_threshold=0.5, dedup_window=1)
    events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(5)]

    nb.build(events, '身份', epoch=0, seed=42)
    n2 = nb.build(events, '身份', epoch=1, seed=999)
    # 第二次同 identity → jaccard 命中 → 不追加
    assert len(nb.narrative_history) == 1
    assert n2 == nb.narrative_history[-1]['narrative']


def test_narrative_builder_build_dedup_ngram_method():
    """dedup_method='ngram' 同样工作。"""
    nb = NarrativeBuilder(
        dedup_threshold=0.5, dedup_window=1, dedup_method='ngram',
    )
    events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(5)]
    nb.build(events, '身份', epoch=0, seed=42)
    nb.build(events, '身份', epoch=1, seed=999)
    assert len(nb.narrative_history) == 1


def test_narrative_builder_build_dedup_below_threshold_appends():
    """相似度 < 阈值 → 追加。"""
    nb = NarrativeBuilder(dedup_threshold=0.99)
    events_a = [{'event_type': 'success', 'description': f'a{i}'} for i in range(5)]
    events_b = [{'event_type': 'failure', 'description': f'b{i}'} for i in range(5)]
    nb.build(events_a, '身份A', epoch=0, seed=42)
    nb.build(events_b, '身份B', epoch=1, seed=42)
    assert len(nb.narrative_history) == 2


def test_narrative_builder_build_real_llm_dict():
    """real LLM 返回 dict → 提取 'narrative'。"""
    llm = MagicMock()
    llm.chat_json.return_value = {'narrative': 'LLM 生成的叙事'}
    nb = NarrativeBuilder(use_real_llm=True, llm=llm)
    events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(5)]
    narrative = nb.build(events, '身份', epoch=0)
    assert narrative == 'LLM 生成的叙事'


def test_narrative_builder_build_real_llm_string_return():
    """real LLM 直接返回字符串（无 dict 包裹）→ 截断到 500 字符。"""
    llm = MagicMock()
    llm.chat_json.return_value = '直接返回的字符串'
    nb = NarrativeBuilder(use_real_llm=True, llm=llm)
    events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(5)]
    narrative = nb.build(events, '身份', epoch=0)
    assert narrative == '直接返回的字符串'


def test_narrative_builder_build_real_llm_none_fallback_to_stub():
    """real LLM 返回 None → fallback 到 stub。"""
    llm = MagicMock()
    llm.chat_json.return_value = None
    nb = NarrativeBuilder(use_real_llm=True, llm=llm)
    events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(5)]
    narrative = nb.build(events, '身份', epoch=0, seed=42)
    # stub 会基于 events 生成非空 narrative
    assert narrative
    assert '寻找' in narrative or '经历' in narrative


def test_narrative_builder_build_real_llm_fallback_path():
    """real_llm=True 但 llm=None → 走 real_build_narrative（kwargs 路径）。"""
    nb = NarrativeBuilder(use_real_llm=True, llm=None)
    # build() 内部还会调用 check_consistency() → 也需要 patch
    with patch('sge.narrative.real_build_narrative', return_value='FALLBACK_NARRATIVE') as mock_build, \
         patch('sge.narrative.real_check_narrative_consistency', return_value=0.8) as mock_check:
        events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(5)]
        narrative = nb.build(events, '身份', epoch=0, api_key='fake-key')
    assert narrative == 'FALLBACK_NARRATIVE'
    mock_build.assert_called_once()
    mock_check.assert_called_once()


# ════════════════════════════════════════════════
# check_consistency
# ════════════════════════════════════════════════


def test_narrative_builder_check_consistency_stub():
    """stub 路径。"""
    nb = NarrativeBuilder()
    events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(5)]
    score = nb.check_consistency('任何', events, seed=42)
    assert 0.0 <= score <= 1.0


def test_narrative_builder_check_consistency_real_llm_number():
    """real LLM 返回数字 → 直接用作分数。"""
    llm = MagicMock()
    llm.chat_json.return_value = 0.85
    nb = NarrativeBuilder(use_real_llm=True, llm=llm)
    events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(5)]
    score = nb.check_consistency('narrative', events)
    assert score == 0.85


def test_narrative_builder_check_consistency_real_llm_dict():
    """real LLM 返回 dict with 'score' key → 提取分数。"""
    llm = MagicMock()
    llm.chat_json.return_value = {'score': 0.75}
    nb = NarrativeBuilder(use_real_llm=True, llm=llm)
    events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(5)]
    score = nb.check_consistency('narrative', events)
    assert score == 0.75


def test_narrative_builder_check_consistency_real_llm_dict_coherence_key():
    """real LLM 返回 dict with 'coherence' key → 提取分数。"""
    llm = MagicMock()
    llm.chat_json.return_value = {'coherence': 0.65}
    nb = NarrativeBuilder(use_real_llm=True, llm=llm)
    events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(5)]
    score = nb.check_consistency('narrative', events)
    assert score == 0.65


def test_narrative_builder_check_consistency_real_llm_none_returns_05():
    """real LLM 返回 None → 0.5。"""
    llm = MagicMock()
    llm.chat_json.return_value = None
    nb = NarrativeBuilder(use_real_llm=True, llm=llm)
    events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(5)]
    score = nb.check_consistency('narrative', events)
    assert score == 0.5


def test_narrative_builder_check_consistency_clamps():
    """real LLM 返回 1.5 → clamp 到 1.0。"""
    llm = MagicMock()
    llm.chat_json.return_value = 1.5
    nb = NarrativeBuilder(use_real_llm=True, llm=llm)
    events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(5)]
    score = nb.check_consistency('narrative', events)
    assert score == 1.0


# ════════════════════════════════════════════════
# handle_phase_transition
# ════════════════════════════════════════════════


def test_handle_phase_transition_accepts_new_high_coherence():
    """新叙事 coherence >= threshold → 接受新叙事。"""
    nb = NarrativeBuilder(consistency_threshold=0.5)
    events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(10)]
    nb.current_narrative = '旧叙事'

    # stub 给 coherence ≥ 0.5（10 events → base = 1.0）
    result = nb.handle_phase_transition(
        {'safety': 0.5}, events, '身份', epoch=100, seed=42,
    )
    assert result['old_narrative'] == '旧叙事'
    assert result['new_narrative'] != '旧叙事'
    assert result['accepted'] is True
    assert result['coherence'] >= 0.5
    # current_narrative 应是新叙事
    assert nb.current_narrative == result['new_narrative']


def test_handle_phase_transition_rejects_low_coherence():
    """新叙事 coherence < threshold → 拒绝，coherence 低于 threshold。"""
    # stub 给 coherence 较低（0 events → 0.5）
    nb = NarrativeBuilder(consistency_threshold=0.9)
    nb.current_narrative = '旧叙事'

    result = nb.handle_phase_transition(
        {'safety': 0.5}, [], '身份', epoch=100, seed=42,
    )
    assert result['accepted'] is False
    assert result['coherence'] < 0.9
    # old_narrative 应反映 build 之前的 current_narrative
    assert result['old_narrative'] == '旧叙事'


def test_handle_phase_transition_no_old_narrative():
    """无旧叙事 → old_narrative='（无旧叙事）'。"""
    nb = NarrativeBuilder(consistency_threshold=0.5)
    events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(10)]
    result = nb.handle_phase_transition(
        {'safety': 0.5}, events, '身份', epoch=0, seed=42,
    )
    assert result['old_narrative'] == '（无旧叙事）'


def test_handle_phase_transition_appends_to_history():
    """handle_phase_transition → 在 build 追加 1 条后，再追加 1 条 phase_transition=True。"""
    nb = NarrativeBuilder(consistency_threshold=0.5)
    events = [{'event_type': 'x', 'description': f'e{i}'} for i in range(10)]
    initial_history_len = len(nb.narrative_history)
    nb.handle_phase_transition({'safety': 0.5}, events, '身份', epoch=100, seed=42)
    # build() 追加 1 条 + handle_phase_transition 追加 1 条
    assert len(nb.narrative_history) == initial_history_len + 2
    assert nb.narrative_history[-1]['phase_transition'] is True


def test_handle_phase_transition_rejected_records_replaced():
    """拒绝时 history[-1]['rejected_new'] = 新叙事（旧叙事被保留）。"""
    nb = NarrativeBuilder(consistency_threshold=0.9)
    nb.current_narrative = '旧叙事'

    nb.handle_phase_transition(
        {'safety': 0.5}, [], '身份', epoch=100, seed=42,
    )
    # history[-1] 是 handle_phase_transition 追加的条目
    assert 'rejected_new' in nb.narrative_history[-1]
    assert nb.narrative_history[-1]['narrative'] == '旧叙事'


# ════════════════════════════════════════════════
# snapshot / restore
# ════════════════════════════════════════════════


def test_narrative_builder_snapshot_returns_all_fields():
    """snapshot 包含 8 个白名单字段。"""
    nb = NarrativeBuilder(
        current_narrative='current',
        build_every_n_epochs=15,
        use_real_llm=True,
        consistency_threshold=0.6,
        dedup_threshold=0.5,
        dedup_window=2,
        dedup_method='ngram',
    )
    nb.narrative_history = [{'epoch': 0, 'narrative': 'x', 'coherence': 0.8, 'phase_transition': False}]
    snap = nb.snapshot()
    assert snap['current_narrative'] == 'current'
    assert snap['build_every_n_epochs'] == 15
    assert snap['use_real_llm'] is True
    assert snap['consistency_threshold'] == 0.6
    assert snap['dedup_threshold'] == 0.5
    assert snap['dedup_window'] == 2
    assert snap['dedup_method'] == 'ngram'
    assert len(snap['narrative_history']) == 1
    assert 'llm' not in snap


def test_narrative_builder_snapshot_deep_copies_history():
    """snapshot 深拷贝 history。"""
    nb = NarrativeBuilder()
    nb.narrative_history = [{'epoch': 0, 'narrative': 'test', 'coherence': 0.5}]
    snap = nb.snapshot()
    nb.narrative_history[0]['narrative'] = 'modified'
    assert snap['narrative_history'][0]['narrative'] == 'test'


def test_narrative_builder_restore_round_trip():
    """restore snapshot → 完整还原。"""
    nb1 = NarrativeBuilder(
        current_narrative='restored narrative',
        build_every_n_epochs=15,
        use_real_llm=False,
        consistency_threshold=0.7,
        dedup_threshold=0.5,
        dedup_window=3,
        dedup_method='ngram',
    )
    nb1.narrative_history = [{'epoch': 0, 'narrative': 'x', 'coherence': 0.8}]
    snap = nb1.snapshot()

    nb2 = NarrativeBuilder()
    nb2.restore(snap)

    assert nb2.current_narrative == 'restored narrative'
    assert nb2.build_every_n_epochs == 15
    assert nb2.consistency_threshold == 0.7
    assert nb2.dedup_threshold == 0.5
    assert nb2.dedup_window == 3
    assert nb2.dedup_method == 'ngram'
    assert nb2.narrative_history[0]['narrative'] == 'x'


def test_narrative_builder_restore_missing_field_raises():
    """snapshot 缺关键字段 → SnapshotError。"""
    nb = NarrativeBuilder()
    with pytest.raises(SnapshotError, match='缺关键字段'):
        nb.restore({'current_narrative': None})  # 缺其他字段


def test_narrative_builder_restore_passes_llm_kwarg():
    """restore 接受 llm kwarg 并赋值。"""
    nb = NarrativeBuilder()
    fake_llm = MagicMock()
    nb.restore({
        'current_narrative': None,
        'build_every_n_epochs': 50,
        'use_real_llm': False,
        'consistency_threshold': 0.5,
        'dedup_threshold': 0.0,
        'dedup_window': 1,
        'dedup_method': 'jaccard',
        'narrative_history': [],
    }, llm=fake_llm)
    assert nb.llm is fake_llm
