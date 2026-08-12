"""sge.identity pytest 单元测试 — IdentityLayer / stub / real LLM / dedup / snapshot。

Phase 3.2 conversion 第三批 1/4。
覆盖:
  1. _value_vector_to_description + _memories_to_description
  2. stub_crystallize_identity 4 个 value polarity 模板分支
  3. stub_validate_identity 含/不含 value name
  4. real_crystallize_identity / real_validate_identity LLM mock 路径
  5. _jaccard_similarity / _char_ngram_vector / _tfidf_cosine / _ngram_similarity
  6. IdentityLayer __init__ + should_crystallize + get_current
  7. crystallize stub 路径 + dedup（jaccard + ngram）
  8. crystallize real LLM 路径（含 LLM 返回 None fallback）
  9. crystallize 验证失败 → None
 10. stability_score 0/1/N 个 identity
 11. snapshot/restore round-trip + strict missing field
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sge.identity import (
    IdentityLayer,
    stub_crystallize_identity,
    stub_validate_identity,
    _value_vector_to_description,
    _memories_to_description,
    _jaccard_similarity,
    _char_ngram_vector,
    _tfidf_cosine,
    _ngram_similarity,
)
from sge.baseline import ValueLayer, SnapshotError


# ════════════════════════════════════════════════
# _value_vector_to_description
# ════════════════════════════════════════════════


def test_value_vector_to_description_with_value_layer():
    """ValueLayer 实例 → 排序后 top 3 描述。"""
    vl = ValueLayer(values=['safety', 'creativity', 'justice'])
    vl.value_state = {'safety': 0.8, 'creativity': 0.5, 'justice': -0.7}
    desc = _value_vector_to_description(vl)
    # safety=+0.80 absolute max, creativity=+0.50, justice=-0.70 absolute second
    assert 'safety=+0.80' in desc
    assert 'justice=-0.70' in desc


def test_value_vector_to_description_with_dict():
    """dict 输入 → 同样输出。"""
    desc = _value_vector_to_description({'safety': 0.5, 'creativity': 0.8})
    assert 'creativity=+0.80' in desc
    assert 'safety=+0.50' in desc


def test_value_vector_to_description_unknown_input():
    """未知类型 → '无价值向量数据'。"""
    desc = _value_vector_to_description([1, 2, 3])  # list 不是 dict 也不是 ValueLayer
    assert '无价值向量数据' in desc


def test_value_vector_to_description_empty_dict():
    """空 dict → 空字符串（sorted 后无元素）。"""
    desc = _value_vector_to_description({})
    assert desc == ''


# ════════════════════════════════════════════════
# _memories_to_description
# ════════════════════════════════════════════════


def test_memories_to_description_empty():
    """空 memories → '暂无关键经历'。"""
    assert _memories_to_description([]) == '暂无关键经历'


def test_memories_to_description_dict_format():
    """dict memories → [event_type] description 格式。"""
    memories = [
        {'event_type': 'success', 'description': '完成了项目'},
        {'event_type': 'failure', 'description': '考试没及格'},
    ]
    desc = _memories_to_description(memories)
    assert '[success]' in desc
    assert '[failure]' in desc
    assert '完成了项目' in desc
    assert '考试没及格' in desc


def test_memories_to_description_string_format():
    """字符串 memories → 直接截断 30 字符。"""
    desc = _memories_to_description(['a' * 50, 'short'])
    # 前 30 字符 + 后 30 字符
    assert 'a' * 30 in desc
    assert 'short' in desc


def test_memories_to_description_max_n():
    """max_n 控制取最后 N 条。"""
    memories = [{'event_type': f'e{i}', 'description': f'd{i}'} for i in range(10)]
    desc = _memories_to_description(memories, max_n=3)
    # 只应包含最后 3 条
    assert 'd7' in desc
    assert 'd8' in desc
    assert 'd9' in desc
    assert 'd0' not in desc


# ════════════════════════════════════════════════
# stub_crystallize_identity
# ════════════════════════════════════════════════


def test_stub_crystallize_identity_both_positive():
    """top1 + top2 都为正 → '重视' 模板。"""
    values = {'safety': 0.8, 'creativity': 0.5, 'justice': 0.0}
    identity = stub_crystallize_identity(values, [], seed=42)
    assert '重视' in identity
    assert 'safety' in identity
    assert 'creativity' in identity


def test_stub_crystallize_identity_positive_then_negative():
    """top1 正, top2 负 → '追求...谨慎' 模板。"""
    values = {'safety': 0.8, 'justice': -0.7, 'creativity': 0.0}
    identity = stub_crystallize_identity(values, [], seed=42)
    assert '追求' in identity
    assert '谨慎' in identity


def test_stub_crystallize_identity_negative_then_positive():
    """top1 负, top2 正 → '矛盾...相信' 模板。"""
    values = {'safety': -0.8, 'creativity': 0.7, 'justice': 0.0}
    identity = stub_crystallize_identity(values, [], seed=42)
    assert '矛盾' in identity
    assert '相信' in identity


def test_stub_crystallize_identity_both_negative():
    """top1 + top2 都负 → '保持距离' 模板。"""
    values = {'safety': -0.8, 'justice': -0.7, 'creativity': 0.0}
    identity = stub_crystallize_identity(values, [], seed=42)
    assert '保持距离' in identity


def test_stub_crystallize_identity_accepts_value_layer():
    """接受 ValueLayer 实例（用 .value_state 属性）。"""
    vl = ValueLayer(values=['safety', 'creativity'])
    vl.value_state = {'safety': 0.8, 'creativity': 0.5}
    identity = stub_crystallize_identity(vl, [], seed=42)
    assert 'safety' in identity


# ════════════════════════════════════════════════
# stub_validate_identity
# ════════════════════════════════════════════════


def test_stub_validate_identity_contains_value_name_returns_true():
    """identity 含 value name → True。"""
    values = {'safety': 0.5, 'creativity': 0.3}
    assert stub_validate_identity("我重视 safety", values, []) is True


def test_stub_validate_identity_no_value_name_returns_false():
    """identity 不含任何 value name → False。"""
    values = {'safety': 0.5, 'creativity': 0.3}
    assert stub_validate_identity("我是一个程序员", values, []) is False


def test_stub_validate_identity_empty_identity_returns_false():
    """空 identity → False（无 value name 匹配）。"""
    values = {'safety': 0.5}
    assert stub_validate_identity("", values, []) is False


def test_stub_validate_identity_accepts_value_layer():
    """接受 ValueLayer 实例。"""
    vl = ValueLayer(values=['safety'])
    vl.value_state = {'safety': 0.5}
    assert stub_validate_identity("我重视 safety", vl, []) is True


# ════════════════════════════════════════════════
# real_crystallize_identity / real_validate_identity（LLM mock）
# ════════════════════════════════════════════════


def _has_litellm():
    """检查 litellm 是否可用（real_* 测试依赖）。"""
    try:
        import litellm  # noqa: F401
        return True
    except ImportError:
        return False


requires_litellm = pytest.mark.skipif(
    not _has_litellm(), reason="litellm 未安装，跳过 real_* LLM 集成测试",
)


@requires_litellm
@patch('litellm.completion')
def test_real_crystallize_identity_parses_json(mock_completion):
    """LLM 返回合法 JSON → 提取 'identity' 字段。"""
    from sge.identity import real_crystallize_identity

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"identity": "我是一个探索者"}'
    mock_completion.return_value = mock_response

    identity = real_crystallize_identity(
        {'safety': 0.5}, [], api_key='fake-key',
    )
    assert identity == '我是一个探索者'


@requires_litellm
@patch('litellm.completion')
def test_real_crystallize_identity_handles_markdown_fence(mock_completion):
    """LLM 返回 ```json ... ``` → 正确剥离。"""
    from sge.identity import real_crystallize_identity

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '```json\n{"identity": "解析正确"}\n```'
    mock_completion.return_value = mock_response

    identity = real_crystallize_identity(
        {'safety': 0.5}, [], api_key='fake-key',
    )
    assert identity == '解析正确'


@requires_litellm
@patch('litellm.completion')
def test_real_crystallize_identity_invalid_json_falls_back_to_content(mock_completion):
    """LLM 返回非法 JSON → 取前 50 字符。"""
    from sge.identity import real_crystallize_identity

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '这不是 JSON 格式'
    mock_completion.return_value = mock_response

    identity = real_crystallize_identity(
        {'safety': 0.5}, [], api_key='fake-key',
    )
    assert identity == '这不是 JSON 格式'  # 14 字符 < 50 截断


@requires_litellm
@patch('litellm.completion')
def test_real_validate_identity_yes_returns_true(mock_completion):
    """LLM 返回 'YES' → True。"""
    from sge.identity import real_validate_identity

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = 'YES, consistent'
    mock_completion.return_value = mock_response

    valid = real_validate_identity(
        'identity', {'safety': 0.5}, [], api_key='fake-key',
    )
    assert valid is True


@requires_litellm
@patch('litellm.completion')
def test_real_validate_identity_no_returns_false(mock_completion):
    """LLM 返回 'NO' → False。"""
    from sge.identity import real_validate_identity

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = 'NO, inconsistent'
    mock_completion.return_value = mock_response

    valid = real_validate_identity(
        'identity', {'safety': 0.5}, [], api_key='fake-key',
    )
    assert valid is False


@requires_litellm
def test_real_crystallize_identity_no_api_key_raises():
    """缺 API key → ValueError。"""
    from sge.identity import real_crystallize_identity
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError, match='MINIMAX_API_KEY'):
            real_crystallize_identity(
                {'safety': 0.5}, [], api_key=None,
            )


# ════════════════════════════════════════════════
# 不依赖 litellm 真实安装：通过 sys.modules 注入 fake litellm 测 real_* 函数
# ════════════════════════════════════════════════


class _FakeLitellmCompletion:
    """fake litellm.completion 模块级对象。"""
    def __init__(self):
        self.call_count = 0
        self.last_kwargs = None
        self.next_response_content = '{"identity": "fake identity"}'

    def __call__(self, **kwargs):
        self.call_count += 1
        self.last_kwargs = kwargs
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = self.next_response_content
        return mock_response


class _FakeLitellmExceptions:
    """fake litellm.exceptions 模块。"""
    InternalServerError = type('InternalServerError', (Exception,), {})
    APIConnectionError = type('APIConnectionError', (Exception,), {})
    Timeout = type('Timeout', (Exception,), {})
    RateLimitError = type('RateLimitError', (Exception,), {})
    ServiceUnavailableError = type('ServiceUnavailableError', (Exception,), {})
    APIError = type('APIError', (Exception,), {})


def _install_fake_litellm():
    """注入 fake litellm 到 sys.modules，让 real_* 可调用。"""
    import sys
    from types import ModuleType

    fake_litellm = ModuleType('litellm')
    fake_litellm.completion = _FakeLitellmCompletion()
    fake_litellm.exceptions = _FakeLitellmExceptions()
    sys.modules['litellm'] = fake_litellm
    return fake_litellm


def test_real_crystallize_identity_with_fake_litellm():
    """通过注入 fake litellm 测 real_crystallize_identity 主路径。"""
    fake = _install_fake_litellm()
    from sge.identity import real_crystallize_identity

    fake.completion.next_response_content = '{"identity": "fake 身份"}'
    identity = real_crystallize_identity(
        {'safety': 0.5}, [], api_key='fake-key',
    )
    assert identity == 'fake 身份'
    assert fake.completion.call_count == 1
    assert fake.completion.last_kwargs['api_key'] == 'fake-key'


def test_real_crystallize_identity_markdown_fence_with_fake_litellm():
    """fake litellm 返回 ```json fence → 正确剥离。"""
    fake = _install_fake_litellm()
    from sge.identity import real_crystallize_identity

    fake.completion.next_response_content = '```json\n{"identity": "fenced"}\n```'
    identity = real_crystallize_identity(
        {'safety': 0.5}, [], api_key='fake-key',
    )
    assert identity == 'fenced'


def test_real_crystallize_identity_no_fence_json_keyword_with_fake_litellm():
    """LLM 返回 ```json（无闭合 fence）→ 走 fallback。"""
    fake = _install_fake_litellm()
    from sge.identity import real_crystallize_identity

    fake.completion.next_response_content = '```json\n{"identity": "no closing"}'
    # 不闭合 fence → fallback 取前 50 字符
    identity = real_crystallize_identity(
        {'safety': 0.5}, [], api_key='fake-key',
    )
    # 不闭合 fence 时 raw = "{"identity": "no closing"}" 长度 30
    assert 'identity' in identity or identity.startswith('```')


def test_real_validate_identity_with_fake_litellm():
    """fake litellm → real_validate_identity。"""
    fake = _install_fake_litellm()
    from sge.identity import real_validate_identity

    fake.completion.next_response_content = 'YES'
    valid = real_validate_identity(
        'identity', {'safety': 0.5}, [], api_key='fake-key',
    )
    assert valid is True


def test_real_validate_identity_lowercase_yes_with_fake_litellm():
    """fake litellm 返回 'yes'（小写）→ True（uppercase 比较）。"""
    fake = _install_fake_litellm()
    from sge.identity import real_validate_identity

    fake.completion.next_response_content = 'yes, consistent'
    valid = real_validate_identity(
        'identity', {'safety': 0.5}, [], api_key='fake-key',
    )
    assert valid is True


def test_real_validate_identity_no_keyword_with_fake_litellm():
    """fake litellm 返回 'NO' → False。"""
    fake = _install_fake_litellm()
    from sge.identity import real_validate_identity

    fake.completion.next_response_content = 'NO, inconsistent'
    valid = real_validate_identity(
        'identity', {'safety': 0.5}, [], api_key='fake-key',
    )
    assert valid is False


# ════════════════════════════════════════════════
# _jaccard_similarity / _char_ngram_vector / _tfidf_cosine / _ngram_similarity
# ════════════════════════════════════════════════


def test_jaccard_similarity_identical_strings():
    """相同字符串 → 1.0。"""
    assert _jaccard_similarity('探索者', '探索者') == 1.0


def test_jaccard_similarity_disjoint_strings():
    """字符集完全不交 → 0.0。"""
    assert _jaccard_similarity('abc', 'xyz') == 0.0


def test_jaccard_similarity_partial_overlap():
    """部分字符重合 → 中间值。"""
    sim = _jaccard_similarity('abc', 'bcd')
    # 字符集 {a,b,c} ∩ {b,c,d} = {b,c}, ∪ = {a,b,c,d}
    # Jaccard = 2/4 = 0.5
    assert abs(sim - 0.5) < 1e-9


def test_jaccard_similarity_empty_strings():
    """空字符串 → 0.0。"""
    assert _jaccard_similarity('', 'abc') == 0.0
    assert _jaccard_similarity('abc', '') == 0.0
    assert _jaccard_similarity('', '') == 0.0


def test_char_ngram_vector_unigram_only():
    """ns=(1,) → 只有 unigram 计数。"""
    vec = _char_ngram_vector('abc', ns=(1,))
    assert dict(vec) == {'a': 1, 'b': 1, 'c': 1}


def test_char_ngram_vector_bigram():
    """ns=(2,) → 只有 bigram 计数。"""
    vec = _char_ngram_vector('abcd', ns=(2,))
    assert dict(vec) == {'ab': 1, 'bc': 1, 'cd': 1}


def test_char_ngram_vector_mixed():
    """ns=(1, 2) → unigram + bigram。"""
    vec = _char_ngram_vector('abc', ns=(1, 2))
    d = dict(vec)
    assert d['a'] == 1
    assert d['ab'] == 1
    assert d['bc'] == 1


def test_char_ngram_vector_short_string():
    """字符串长度 < n → 跳过该 n。"""
    vec = _char_ngram_vector('a', ns=(1, 2))
    assert dict(vec) == {'a': 1}


def test_tfidf_cosine_identical():
    """相同 vector → 1.0。"""
    vec = _char_ngram_vector('hello')
    assert abs(_tfidf_cosine(vec, vec) - 1.0) < 1e-9


def test_tfidf_cosine_disjoint():
    """无交集 → 0.0。"""
    a = _char_ngram_vector('abc', ns=(1,))
    b = _char_ngram_vector('xyz', ns=(1,))
    assert _tfidf_cosine(a, b) == 0.0


def test_tfidf_cosine_empty_vector():
    """空 vector → 0.0。"""
    assert _tfidf_cosine({}, _char_ngram_vector('a')) == 0.0
    assert _tfidf_cosine(_char_ngram_vector('a'), {}) == 0.0
    assert _tfidf_cosine({}, {}) == 0.0


def test_ngram_similarity_similar_identities():
    """相似身份描述 → 高分。"""
    sim = _ngram_similarity('我是探索者', '我是创造探索者')
    assert sim > 0.5  # 共享 unigram + 部分 bigram


def test_ngram_similarity_unrelated_identities():
    """无关身份 → 低分。"""
    sim = _ngram_similarity('我是医生', '我来自火星')
    assert sim < 0.3


# ════════════════════════════════════════════════
# IdentityLayer 类
# ════════════════════════════════════════════════


def test_identity_layer_init_defaults():
    """默认参数 → 正确初始化。"""
    layer = IdentityLayer()
    assert layer.identity_history == []
    assert layer.crystallize_every_n_epochs == 20
    assert layer.use_real_llm is False
    assert layer.dedup_threshold == 0.0
    assert layer.dedup_window == 1
    assert layer.dedup_method == 'jaccard'


def test_identity_layer_init_with_history():
    """传入 history → 正确设置。"""
    history = [{'epoch': 0, 'identity': '我是探索者', 'value_snapshot': {}}]
    layer = IdentityLayer(identity_history=history)
    assert layer.identity_history == history


def test_identity_layer_should_crystallize_trigger_epochs():
    """(epoch + 1) % N == 0 触发（默认 N=20）。"""
    layer = IdentityLayer()
    assert not layer.should_crystallize(0)
    assert not layer.should_crystallize(18)
    assert layer.should_crystallize(19)   # epoch=19 → 跑完 20 个
    assert not layer.should_crystallize(20)
    assert layer.should_crystallize(39)


def test_identity_layer_should_crystallize_custom_n():
    """自定义 N=5。"""
    layer = IdentityLayer(crystallize_every_n_epochs=5)
    assert layer.should_crystallize(4)   # epoch=4 → 跑完 5 个
    assert layer.should_crystallize(9)   # epoch=9 → 跑完 10 个
    assert not layer.should_crystallize(5)


def test_identity_layer_crystallize_stub_appends_history():
    """stub crystallize → 追加到 identity_history。"""
    layer = IdentityLayer()
    values = {'safety': 0.8, 'creativity': 0.5}
    identity = layer.crystallize(values, [], epoch=0, seed=42)
    assert identity is not None
    assert len(layer.identity_history) == 1
    assert layer.identity_history[0]['epoch'] == 0
    assert layer.identity_history[0]['identity'] == identity
    assert 'safety' in layer.identity_history[0]['value_snapshot']


def test_identity_layer_crystallize_returns_identity():
    """返回的 identity 与 history 一致。"""
    layer = IdentityLayer()
    values = {'safety': 0.8, 'creativity': 0.5}
    identity = layer.crystallize(values, [], epoch=0, seed=42)
    assert layer.get_current() == identity


def test_identity_layer_get_current_empty_history():
    """空 history → None。"""
    layer = IdentityLayer()
    assert layer.get_current() is None


def test_identity_layer_crystallize_dedup_jaccard_skips_append():
    """dedup jaccard 命中阈值 → 不追加，返回最近一条。"""
    layer = IdentityLayer(dedup_threshold=0.5, dedup_window=1)
    values = {'safety': 0.8, 'creativity': 0.5}

    layer.crystallize(values, [], epoch=0, seed=42)  # baseline
    # 第二次相同 values + 不同 seed → identity 内容相同（stub 是 deterministic）
    identity2 = layer.crystallize(values, [], epoch=1, seed=999)
    # 应该被 dedup 命中 → 不追加
    assert len(layer.identity_history) == 1
    # 返回的还是第一次的 identity（保证兼容）
    assert identity2 == layer.identity_history[-1]['identity']


def test_identity_layer_crystallize_dedup_ngram_method():
    """dedup_method='ngram' 同样工作。"""
    layer = IdentityLayer(dedup_threshold=0.5, dedup_window=1, dedup_method='ngram')
    values = {'safety': 0.8, 'creativity': 0.5}
    layer.crystallize(values, [], epoch=0, seed=42)
    layer.crystallize(values, [], epoch=1, seed=999)
    assert len(layer.identity_history) == 1


def test_identity_layer_crystallize_dedup_below_threshold_appends():
    """相似度 < 阈值 → 追加。"""
    layer = IdentityLayer(dedup_threshold=0.99)  # 极高阈值
    values1 = {'safety': 0.8, 'creativity': 0.5}
    values2 = {'justice': -0.8, 'compassion': 0.7}
    layer.crystallize(values1, [], epoch=0, seed=42)
    layer.crystallize(values2, [], epoch=1, seed=42)
    assert len(layer.identity_history) == 2


def test_identity_layer_crystallize_force_validate_rejects_invalid():
    """force_validate=True 且 stub_validate 返回 False → None。"""
    layer = IdentityLayer()
    values = {'safety': 0.5, 'creativity': 0.3}  # 至少 2 个 value
    with patch('sge.identity.stub_validate_identity', return_value=False):
        identity = layer.crystallize(values, [], epoch=0, seed=42, force_validate=True)
    assert identity is None
    assert len(layer.identity_history) == 0


def test_identity_layer_crystallize_force_validate_accepts_valid():
    """force_validate=True 且 validate 返回 True → 追加。"""
    layer = IdentityLayer()
    values = {'safety': 0.5, 'creativity': 0.3}
    with patch('sge.identity.stub_validate_identity', return_value=True):
        identity = layer.crystallize(values, [], epoch=0, seed=42, force_validate=True)
    assert identity is not None
    assert len(layer.identity_history) == 1


def test_identity_layer_crystallize_real_llm_success():
    """real LLM 路径 → chat_json 返回 dict → 使用 'identity' 字段。"""
    llm = MagicMock()
    llm.chat_json.return_value = {'identity': 'LLM 生成的探索者'}
    llm.chat.return_value = 'YES'  # validate 通过
    layer = IdentityLayer(use_real_llm=True, llm=llm)
    values = {'safety': 0.5, 'creativity': 0.3}
    identity = layer.crystallize(values, [], epoch=0, seed=42)
    assert identity == 'LLM 生成的探索者'
    assert llm.chat_json.called


def test_identity_layer_crystallize_real_llm_string_return():
    """real LLM 直接返回字符串（无 dict 包裹）→ 使用该字符串。"""
    llm = MagicMock()
    llm.chat_json.return_value = 'LLM 直接返回的字符串'
    llm.chat.return_value = 'YES'
    layer = IdentityLayer(use_real_llm=True, llm=llm)
    identity = layer.crystallize({'safety': 0.5, 'creativity': 0.3}, [], epoch=0)
    assert identity == 'LLM 直接返回的字符串'


def test_identity_layer_crystallize_real_llm_none_returns_none():
    """real LLM 返回 None → crystallize 返回 None。"""
    llm = MagicMock()
    llm.chat_json.return_value = None
    layer = IdentityLayer(use_real_llm=True, llm=llm)
    identity = layer.crystallize({'safety': 0.5, 'creativity': 0.3}, [], epoch=0)
    assert identity is None
    assert len(layer.identity_history) == 0


def test_identity_layer_crystallize_real_llm_with_dedup_returns_previous():
    """real LLM + dedup 命中 → 返回最近一条 identity（不追加）。"""
    llm = MagicMock()
    llm.chat_json.return_value = {'identity': '我是探索者'}
    llm.chat.return_value = 'YES'
    layer = IdentityLayer(
        use_real_llm=True, llm=llm,
        dedup_threshold=0.5, dedup_method='jaccard',
    )
    values = {'safety': 0.5, 'creativity': 0.3}
    id1 = layer.crystallize(values, [], epoch=0)
    assert id1 == '我是探索者'
    # 第二次相同 identity → dedup 命中 → 返回 id1
    id2 = layer.crystallize(values, [], epoch=1)
    assert id2 == '我是探索者'
    assert len(layer.identity_history) == 1


def test_identity_layer_crystallize_real_llm_validate_fail():
    """real LLM + validate 返回 NO → crystallize 返回 None。"""
    llm = MagicMock()
    llm.chat_json.return_value = {'identity': '探索者'}
    llm.chat.return_value = 'NO, inconsistent'
    layer = IdentityLayer(use_real_llm=True, llm=llm)
    identity = layer.crystallize({'safety': 0.5, 'creativity': 0.3}, [], epoch=0)
    assert identity is None
    assert len(layer.identity_history) == 0


def test_identity_layer_crystallize_real_llm_validate_yes():
    """real LLM + validate 返回 YES → 追加。"""
    llm = MagicMock()
    llm.chat_json.return_value = {'identity': '探索者'}
    llm.chat.return_value = 'YES'
    layer = IdentityLayer(use_real_llm=True, llm=llm)
    identity = layer.crystallize({'safety': 0.5, 'creativity': 0.3}, [], epoch=0)
    assert identity == '探索者'
    assert len(layer.identity_history) == 1


def test_identity_layer_crystallize_real_llm_fallback_path():
    """real_llm=True 但 llm=None → 走 real_crystallize_identity（kwargs 路径）。"""
    layer = IdentityLayer(use_real_llm=True, llm=None)
    # 同时 patch 真实函数避免 litellm 报错
    with patch('sge.identity.real_crystallize_identity', return_value='FALLBACK_IDENTITY') as mock_crystallize, \
         patch('sge.identity.real_validate_identity', return_value=True) as mock_validate:
        identity = layer.crystallize(
            {'safety': 0.5, 'creativity': 0.3}, [], epoch=0,
            api_key='fake-key',
        )
    assert identity == 'FALLBACK_IDENTITY'
    mock_crystallize.assert_called_once()
    mock_validate.assert_called_once()


# ════════════════════════════════════════════════
# stability_score
# ════════════════════════════════════════════════


def test_stability_score_empty_history():
    """空 history → 1.0（默认稳定）。"""
    layer = IdentityLayer()
    assert layer.stability_score() == 1.0


def test_stability_score_single_identity():
    """只有 1 条 identity → 1.0。"""
    layer = IdentityLayer(identity_history=[{'identity': 'x', 'value_snapshot': {}}])
    assert layer.stability_score() == 1.0


def test_stability_score_identical_identities_high():
    """全部相同 identity → 高分（接近 1.0）。"""
    layer = IdentityLayer(identity_history=[
        {'identity': 'same', 'value_snapshot': {}},
        {'identity': 'same', 'value_snapshot': {}},
        {'identity': 'same', 'value_snapshot': {}},
    ])
    assert layer.stability_score() > 0.9


def test_stability_score_diverse_identities_lower():
    """多种 identity → 较低分。"""
    layer = IdentityLayer(identity_history=[
        {'identity': f'identity-{i}', 'value_snapshot': {}} for i in range(5)
    ])
    score = layer.stability_score()
    assert 0.0 < score < 0.9


# ════════════════════════════════════════════════
# snapshot / restore
# ════════════════════════════════════════════════


def test_identity_layer_snapshot_returns_all_fields():
    """snapshot 包含 6 个白名单字段。"""
    layer = IdentityLayer(
        identity_history=[{'epoch': 0, 'identity': 'test', 'value_snapshot': {}}],
        crystallize_every_n_epochs=15,
        use_real_llm=True,
        dedup_threshold=0.5,
        dedup_window=2,
        dedup_method='ngram',
    )
    snap = layer.snapshot()
    assert snap['crystallize_every_n_epochs'] == 15
    assert snap['use_real_llm'] is True
    assert snap['dedup_threshold'] == 0.5
    assert snap['dedup_window'] == 2
    assert snap['dedup_method'] == 'ngram'
    assert len(snap['identity_history']) == 1
    # llm 句柄不持久化
    assert 'llm' not in snap


def test_identity_layer_snapshot_deep_copies_history():
    """snapshot 深拷贝 history（避免与原对象共享引用）。"""
    layer = IdentityLayer(identity_history=[
        {'epoch': 0, 'identity': 'test', 'value_snapshot': {'safety': 0.5}},
    ])
    snap = layer.snapshot()
    # 修改原 history 不影响 snapshot
    layer.identity_history[0]['identity'] = 'modified'
    assert snap['identity_history'][0]['identity'] == 'test'
    # 修改 snapshot 不影响原
    snap['identity_history'][0]['value_snapshot']['safety'] = 0.9
    assert layer.identity_history[0]['value_snapshot']['safety'] == 0.5


def test_identity_layer_restore_round_trip():
    """restore snapshot → 完整还原 state。"""
    layer1 = IdentityLayer(
        identity_history=[{'epoch': 0, 'identity': 'a', 'value_snapshot': {'s': 0.5}}],
        crystallize_every_n_epochs=15,
        use_real_llm=False,
        dedup_threshold=0.5,
        dedup_window=2,
        dedup_method='ngram',
    )
    snap = layer1.snapshot()

    layer2 = IdentityLayer()
    layer2.restore(snap)

    assert layer2.crystallize_every_n_epochs == 15
    assert layer2.dedup_threshold == 0.5
    assert layer2.dedup_window == 2
    assert layer2.dedup_method == 'ngram'
    assert layer2.identity_history[0]['identity'] == 'a'


def test_identity_layer_restore_missing_field_raises():
    """snapshot 缺关键字段 → SnapshotError。"""
    layer = IdentityLayer()
    with pytest.raises(SnapshotError, match='缺关键字段'):
        layer.restore({'identity_history': []})  # 缺其他字段


def test_identity_layer_restore_passes_llm_kwarg():
    """restore 接受 llm kwarg 并赋值。"""
    layer = IdentityLayer()
    fake_llm = MagicMock()
    layer.restore({
        'identity_history': [],
        'crystallize_every_n_epochs': 20,
        'use_real_llm': False,
        'dedup_threshold': 0.0,
        'dedup_window': 1,
        'dedup_method': 'jaccard',
    }, llm=fake_llm)
    assert layer.llm is fake_llm
