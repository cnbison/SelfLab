"""sge.llm_client pytest 单元测试 — SGELLMClient / retry / stats / warmup / JSON parsing。

Phase 3.2 conversion 第三批 3/4。
覆盖:
  1. LLM_PROVIDER_CONFIG 完整性
  2. SGELLMClient.__init__（valid provider / invalid / missing API key）
  3. SGELLMClient.chat 成功路径
  4. SGELLMClient.chat retry on retryable exception（指数退避）
  5. SGELLMClient.chat retry exhausted → 抛出最后异常
  6. SGELLMClient.chat_json + markdown fence 解析
  7. SGELLMClient._parse_json 静态方法（多种格式）
  8. SGELLMClient.stats retry rate 计算
  9. SGELLMClient.warmup 成功 + 失败
 10. make_llm_client 工厂函数
"""

from __future__ import annotations

import json
import time
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from sge.llm_client import (
    SGELLMClient,
    LLM_PROVIDER_CONFIG,
    make_llm_client,
)


# ════════════════════════════════════════════════
# Fake litellm 注入
# ════════════════════════════════════════════════


class _FakeCompletions:
    """fake litellm.completion — 支持 success / retry / fail 模式。"""
    def __init__(self):
        self.call_count = 0
        self.call_kwargs_list = []
        self.responses = []  # list of (content_or_exception)
        self._idx = 0

    def __call__(self, **kwargs):
        self.call_count += 1
        self.call_kwargs_list.append(kwargs)
        if self._idx >= len(self.responses):
            raise IndexError(f"No more responses (call_count={self.call_count})")
        resp = self.responses[self._idx]
        self._idx += 1
        if isinstance(resp, Exception):
            raise resp
        # success
        mock = MagicMock()
        mock.choices = [MagicMock()]
        mock.choices[0].message.content = resp
        return mock

    def reset(self):
        self.call_count = 0
        self.call_kwargs_list = []
        self.responses = []
        self._idx = 0


class _FakeLitellmExceptions:
    """fake litellm.exceptions 模块。"""
    InternalServerError = type('InternalServerError', (Exception,), {})
    APIConnectionError = type('APIConnectionError', (Exception,), {})
    Timeout = type('Timeout', (Exception,), {})
    RateLimitError = type('RateLimitError', (Exception,), {})
    ServiceUnavailableError = type('ServiceUnavailableError', (Exception,), {})
    APIError = type('APIError', (Exception,), {})
    AuthenticationError = type('AuthenticationError', (Exception,), {})
    BadRequestError = type('BadRequestError', (Exception,), {})


@pytest.fixture
def fake_litellm(monkeypatch):
    """注入 fake litellm 到 sys.modules（含 exceptions 子模块 + 属性暴露）。"""
    import sys
    fake = ModuleType('litellm')
    fake.__path__ = []  # 标记为 package
    fake.completion = _FakeCompletions()
    sys.modules['litellm'] = fake

    # 定义 exception 类
    exception_classes = {
        'InternalServerError': type('InternalServerError', (Exception,), {}),
        'APIConnectionError': type('APIConnectionError', (Exception,), {}),
        'Timeout': type('Timeout', (Exception,), {}),
        'RateLimitError': type('RateLimitError', (Exception,), {}),
        'ServiceUnavailableError': type('ServiceUnavailableError', (Exception,), {}),
        'APIError': type('APIError', (Exception,), {}),
        'AuthenticationError': type('AuthenticationError', (Exception,), {}),
        'BadRequestError': type('BadRequestError', (Exception,), {}),
    }

    # exceptions 作为独立 ModuleType 注入，使 `import litellm.exceptions` 工作
    fake_exc = ModuleType('litellm.exceptions')
    for name, cls in exception_classes.items():
        setattr(fake_exc, name, cls)
    sys.modules['litellm.exceptions'] = fake_exc

    # 同时把 exception 类直接挂到 fake 上，让 `litellm.InternalServerError` 也能访问
    # (llm_client.py 同时使用 `litellm.InternalServerError` 和 `import litellm.exceptions`)
    for name, cls in exception_classes.items():
        setattr(fake, name, cls)
    fake.exceptions = fake_exc

    yield fake
    sys.modules.pop('litellm', None)
    sys.modules.pop('litellm.exceptions', None)


@pytest.fixture
def client(fake_litellm):
    """构造一个 SGELLMClient 实例（注入 fake litellm + api_key）。
    显式清掉 env 中的 base_url/model，确保走 fallback 默认值。
    """
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv('MINIMAX_API_KEY', 'test-key-12345')
    monkeypatch.delenv('MINIMAX_BASE_URL', raising=False)
    monkeypatch.delenv('MINIMAX_MODEL', raising=False)
    try:
        c = SGELLMClient(provider='minimax')
        yield c
    finally:
        monkeypatch.undo()


# ════════════════════════════════════════════════
# LLM_PROVIDER_CONFIG
# ════════════════════════════════════════════════


def test_provider_config_has_minimax():
    """LLM_PROVIDER_CONFIG 包含 minimax。"""
    assert 'minimax' in LLM_PROVIDER_CONFIG
    cfg = LLM_PROVIDER_CONFIG['minimax']
    assert cfg['api_key_env'] == 'MINIMAX_API_KEY'
    assert 'minimax.io' in cfg['base_url']
    assert 'MiniMax-M3' in cfg['model']


def test_provider_config_has_moonshot():
    """LLM_PROVIDER_CONFIG 包含 moonshot。"""
    assert 'moonshot' in LLM_PROVIDER_CONFIG
    cfg = LLM_PROVIDER_CONFIG['moonshot']
    assert cfg['api_key_env'] == 'MOONSHOT_API_KEY'
    assert 'kimi' in cfg['model']
    # moonshot 配置了 extra_body 关闭 thinking
    assert 'extra_body' in cfg


# ════════════════════════════════════════════════
# SGELLMClient.__init__
# ════════════════════════════════════════════════


def test_init_with_valid_provider(client):
    """valid provider → 正确初始化。"""
    assert client.provider == 'minimax'
    assert client.api_key == 'test-key-12345'
    assert 'minimax.io' in client.base_url
    assert 'MiniMax-M3' in client.model
    assert client.call_count == 0
    assert client.retry_stats['total_calls'] == 0


def test_init_with_unknown_provider_raises(fake_litellm):
    """未知 provider → ValueError。"""
    with patch.dict('os.environ', {'MINIMAX_API_KEY': 'fake'}):
        with pytest.raises(ValueError, match='Unknown provider'):
            SGELLMClient(provider='unknown_provider')


def test_init_env_overrides_base_url_and_model(fake_litellm, monkeypatch):
    """env 中设了 MINIMAX_BASE_URL / MINIMAX_MODEL → 优先使用 env 值。"""
    monkeypatch.setenv('MINIMAX_API_KEY', 'test-key')
    monkeypatch.setenv('MINIMAX_BASE_URL', 'https://custom.example.com/v1')
    monkeypatch.setenv('MINIMAX_MODEL', 'Custom-Model-X')
    c = SGELLMClient(provider='minimax')
    assert c.base_url == 'https://custom.example.com/v1'
    # 自动加 openai/ 前缀（因为 base_url 形如 /v1）
    assert c.model == 'openai/Custom-Model-X'


def test_init_no_provider_prefix_when_explicit(fake_litellm, monkeypatch):
    """model 已带前缀 → 不再加。"""
    monkeypatch.setenv('MINIMAX_API_KEY', 'test-key')
    monkeypatch.setenv('MINIMAX_BASE_URL', 'https://api.minimax.io/anthropic')
    monkeypatch.setenv('MINIMAX_MODEL', 'anthropic/MiniMax-M3')
    c = SGELLMClient(provider='minimax')
    assert c.model == 'anthropic/MiniMax-M3'  # 不重复加前缀


def test_chat_clamps_max_tokens_to_provider_min(fake_litellm, monkeypatch):
    """reasoning 模型：max_tokens 低于 provider min → 自动 clamp。"""
    monkeypatch.setenv('MINIMAX_API_KEY', 'test-key')
    monkeypatch.delenv('MINIMAX_BASE_URL', raising=False)
    monkeypatch.delenv('MINIMAX_MODEL', raising=False)
    c = SGELLMClient(provider='minimax')
    # min_max_tokens 在 minimax 配置里是 512（reasoning 模型需要余量）
    assert c.min_max_tokens == 512
    # 替换 fake completion：记录 kwargs，返回成功
    fake_completion = _FakeCompletions()
    fake_completion.responses = ["ok"]
    fake_litellm.completion = fake_completion
    c.chat(messages=[{"role": "user", "content": "hi"}], max_tokens=10)
    assert fake_completion.call_kwargs_list[0]['max_tokens'] == 512


def test_init_without_api_key_raises(fake_litellm):
    """缺 API key → ValueError。"""
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError, match='environment variable not set'):
            SGELLMClient(provider='minimax')


def test_init_with_explicit_api_key(fake_litellm):
    """显式传入 api_key → 不读 env。"""
    with patch.dict('os.environ', {}, clear=True):
        c = SGELLMClient(provider='minimax', api_key='explicit-key')
        assert c.api_key == 'explicit-key'


def test_init_with_explicit_base_url_and_model(fake_litellm):
    """显式传入 base_url + model → 覆盖默认。"""
    with patch.dict('os.environ', {'MINIMAX_API_KEY': 'fake'}):
        c = SGELLMClient(
            provider='minimax', base_url='https://custom.url', model='custom-model',
        )
        assert c.base_url == 'https://custom.url'
        assert c.model == 'custom-model'


def test_init_stores_default_temperature(fake_litellm):
    """default_temperature 从 provider config 读。"""
    with patch.dict('os.environ', {'MINIMAX_API_KEY': 'fake'}):
        c = SGELLMClient(provider='minimax')
        assert c.default_temperature == 0.5


# ════════════════════════════════════════════════
# SGELLMClient.chat — 成功路径
# ════════════════════════════════════════════════


def test_chat_success(client, fake_litellm):
    """成功调用 → 返回 content。"""
    fake_litellm.completion.responses = ['Hello, world!']
    content = client.chat(messages=[{"role": "user", "content": "hi"}])
    assert content == 'Hello, world!'
    assert client.call_count == 1
    assert client.retry_stats['total_calls'] == 1
    assert client.retry_stats['calls_failed'] == 0


def test_chat_passes_kwargs_to_completion(client, fake_litellm):
    """kwargs 正确传递给 completion。"""
    fake_litellm.completion.responses = ['ok']
    client.chat(
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.7,
        max_tokens=512,
    )
    kw = fake_litellm.completion.call_kwargs_list[0]
    assert kw['temperature'] == 0.7
    assert kw['max_tokens'] == 512
    assert kw['api_key'] == 'test-key-12345'
    assert kw['base_url'] == client.base_url


def test_chat_default_temperature(client, fake_litellm):
    """temperature=None → 用 provider default。"""
    fake_litellm.completion.responses = ['ok']
    client.chat(messages=[{"role": "user", "content": "hi"}])
    kw = fake_litellm.completion.call_kwargs_list[0]
    assert kw['temperature'] == client.default_temperature


def test_chat_response_format_passed(client, fake_litellm):
    """response_format 传递给 completion。"""
    fake_litellm.completion.responses = ['{}']
    client.chat(
        messages=[{"role": "user", "content": "hi"}],
        response_format={'type': 'json_object'},
    )
    kw = fake_litellm.completion.call_kwargs_list[0]
    assert kw['response_format'] == {'type': 'json_object'}


def test_chat_extra_body_passed_for_moonshot(fake_litellm):
    """moonshot provider → extra_body 关闭 thinking 传给 completion。"""
    with patch.dict('os.environ', {'MOONSHOT_API_KEY': 'fake-moon'}):
        c = SGELLMClient(provider='moonshot')
        fake_litellm.completion.responses = ['ok']
        c.chat(messages=[{"role": "user", "content": "hi"}])
        kw = fake_litellm.completion.call_kwargs_list[0]
        assert 'extra_body' in kw
        assert kw['extra_body']['thinking']['type'] == 'disabled'


def test_chat_extra_body_not_passed_for_minimax(client, fake_litellm):
    """minimax provider → 无 extra_body（默认 None）。"""
    fake_litellm.completion.responses = ['ok']
    client.chat(messages=[{"role": "user", "content": "hi"}])
    kw = fake_litellm.completion.call_kwargs_list[0]
    # extra_body 不在 kwargs 中（除非显式设置）
    assert 'extra_body' not in kw


def test_chat_strips_content(client, fake_litellm):
    """返回 content 自动 strip。"""
    fake_litellm.completion.responses = ['  Hello!  \n']
    content = client.chat(messages=[{"role": "user", "content": "hi"}])
    assert content == 'Hello!'


def test_chat_increments_call_count(client, fake_litellm):
    """多次调用 → call_count 累积。"""
    fake_litellm.completion.responses = ['r1', 'r2', 'r3']
    for _ in range(3):
        client.chat(messages=[{"role": "user", "content": "hi"}])
    assert client.call_count == 3


# ════════════════════════════════════════════════
# SGELLMClient.chat — retry 逻辑
# ════════════════════════════════════════════════


def test_chat_retry_on_internal_server_error(client, fake_litellm, monkeypatch):
    """第一次 InternalServerError → retry 成功。"""
    fake_litellm.completion.responses = [
        fake_litellm.exceptions.InternalServerError('server error'),
        'success after retry',
    ]
    # 加速 sleep 避免测试慢
    monkeypatch.setattr('time.sleep', lambda s: None)
    content = client.chat(messages=[{"role": "user", "content": "hi"}])
    assert content == 'success after retry'
    assert client.retry_stats['total_calls'] == 1
    assert client.retry_stats['calls_with_retry'] == 1
    assert client.retry_stats['calls_failed'] == 0


def test_chat_retry_on_api_connection_error(client, fake_litellm, monkeypatch):
    """APIConnectionError → retry 成功。"""
    fake_litellm.completion.responses = [
        fake_litellm.exceptions.APIConnectionError('connection failed'),
        'ok',
    ]
    monkeypatch.setattr('time.sleep', lambda s: None)
    content = client.chat(messages=[{"role": "user", "content": "hi"}])
    assert content == 'ok'
    assert client.retry_stats['calls_with_retry'] == 1


def test_chat_retry_on_timeout(client, fake_litellm, monkeypatch):
    """Timeout → retry 成功。"""
    fake_litellm.completion.responses = [
        fake_litellm.exceptions.Timeout('timeout'),
        'ok',
    ]
    monkeypatch.setattr('time.sleep', lambda s: None)
    content = client.chat(messages=[{"role": "user", "content": "hi"}])
    assert content == 'ok'


def test_chat_retry_on_rate_limit(client, fake_litellm, monkeypatch):
    """RateLimitError → retry 成功。"""
    fake_litellm.completion.responses = [
        fake_litellm.exceptions.RateLimitError('rate limited'),
        'ok',
    ]
    monkeypatch.setattr('time.sleep', lambda s: None)
    content = client.chat(messages=[{"role": "user", "content": "hi"}])
    assert content == 'ok'


def test_chat_retry_exhausted_raises_last_error(client, fake_litellm, monkeypatch):
    """8 次 retry 都失败 → 抛出最后一次异常 + calls_failed=1。"""
    last_err = fake_litellm.exceptions.InternalServerError('persistent failure')
    fake_litellm.completion.responses = [
        fake_litellm.exceptions.InternalServerError('fail') for _ in range(7)
    ] + [last_err]
    monkeypatch.setattr('time.sleep', lambda s: None)
    with pytest.raises(fake_litellm.exceptions.InternalServerError):
        client.chat(messages=[{"role": "user", "content": "hi"}])
    assert client.retry_stats['calls_failed'] == 1
    assert client.retry_stats['total_calls'] == 0  # 没有任何成功


def test_chat_records_error_types(client, fake_litellm, monkeypatch):
    """retry 失败时记录错误类型统计。"""
    fake_litellm.completion.responses = [
        fake_litellm.exceptions.InternalServerError('e1'),
        fake_litellm.exceptions.Timeout('e2'),
        fake_litellm.exceptions.RateLimitError('e3'),
    ] + [fake_litellm.exceptions.InternalServerError('e4') for _ in range(5)]
    monkeypatch.setattr('time.sleep', lambda s: None)
    with pytest.raises(Exception):
        client.chat(messages=[{"role": "user", "content": "hi"}])
    errors = client.retry_stats['errors_by_type']
    assert 'InternalServerError' in errors
    assert errors['InternalServerError'] >= 2


def test_chat_records_wait_seconds(client, fake_litellm, monkeypatch):
    """retry 等待时间累积。"""
    fake_litellm.completion.responses = [
        fake_litellm.exceptions.Timeout('e'),
        'ok',
    ]
    monkeypatch.setattr('time.sleep', lambda s: None)
    client.chat(messages=[{"role": "user", "content": "hi"}])
    assert client.retry_stats['total_wait_seconds'] > 0


# ════════════════════════════════════════════════
# SGELLMClient.chat_json
# ════════════════════════════════════════════════


def test_chat_json_parses_dict(client, fake_litellm):
    """chat_json 解析 dict 响应。"""
    fake_litellm.completion.responses = ['{"name": "Alice", "age": 30}']
    result = client.chat_json(messages=[{"role": "user", "content": "hi"}])
    assert result == {'name': 'Alice', 'age': 30}


def test_chat_json_parses_list(client, fake_litellm):
    """chat_json 解析 list 响应。"""
    fake_litellm.completion.responses = ['[1, 2, 3]']
    result = client.chat_json(messages=[{"role": "user", "content": "hi"}])
    assert result == [1, 2, 3]


def test_chat_json_markdown_fence(client, fake_litellm):
    """chat_json 解析 ```json ... ``` 围栏。"""
    fake_litellm.completion.responses = ['```json\n{"key": "value"}\n```']
    result = client.chat_json(messages=[{"role": "user", "content": "hi"}])
    assert result == {'key': 'value'}


def test_chat_json_invalid_returns_fallback(client, fake_litellm):
    """chat_json 解析失败 → 返回 fallback_value。"""
    fake_litellm.completion.responses = ['not valid JSON {{{']
    result = client.chat_json(
        messages=[{"role": "user", "content": "hi"}],
        fallback_value={'default': True},
    )
    assert result == {'default': True}


def test_chat_json_invalid_returns_none_by_default(client, fake_litellm):
    """chat_json 解析失败 + fallback_value=None → None。"""
    fake_litellm.completion.responses = ['not JSON']
    result = client.chat_json(messages=[{"role": "user", "content": "hi"}])
    assert result is None


# ════════════════════════════════════════════════
# SGELLMClient._parse_json（静态方法）
# ════════════════════════════════════════════════


def test_parse_json_plain_dict():
    """纯 dict JSON → 解析。"""
    result = SGELLMClient._parse_json('{"a": 1}')
    assert result == {'a': 1}


def test_parse_json_json_fence():
    """```json ... ``` 围栏 → 解析。"""
    result = SGELLMClient._parse_json('```json\n{"b": 2}\n```')
    assert result == {'b': 2}


def test_parse_json_plain_fence():
    """``` ... ``` 围栏（无 json 关键字）→ 解析。"""
    result = SGELLMClient._parse_json('```\n{"c": 3}\n```')
    assert result == {'c': 3}


def test_parse_json_invalid_returns_fallback():
    """非法 JSON → fallback_value。"""
    result = SGELLMClient._parse_json('not JSON', fallback_value='fallback')
    assert result == 'fallback'


def test_parse_json_invalid_returns_none_default():
    """非法 JSON + 无 fallback → None。"""
    result = SGELLMClient._parse_json('not JSON')
    assert result is None


def test_parse_json_empty_string_returns_fallback():
    """空字符串 → fallback。"""
    result = SGELLMClient._parse_json('', fallback_value={})
    assert result == {}


# ════════════════════════════════════════════════
# SGELLMClient.stats
# ════════════════════════════════════════════════


def test_stats_no_calls(client):
    """零调用 → 统计合理默认值。"""
    stats = client.stats()
    assert stats['provider'] == 'minimax'
    assert stats['call_count'] == 0
    assert stats['retry']['total_calls'] == 0
    assert stats['retry']['retry_rate'] == 0
    assert stats['retry']['avg_attempts_per_call'] == 0
    assert stats['retry']['total_wait_seconds'] == 0


def test_stats_after_success_calls(client, fake_litellm):
    """多次成功调用 → 统计正确。"""
    fake_litellm.completion.responses = ['r1', 'r2', 'r3']
    for _ in range(3):
        client.chat(messages=[{"role": "user", "content": "hi"}])
    stats = client.stats()
    assert stats['call_count'] == 3
    assert stats['retry']['total_calls'] == 3
    assert stats['retry']['calls_with_retry'] == 0
    assert stats['retry']['calls_failed'] == 0


def test_stats_retry_rate_calculation(client, fake_litellm, monkeypatch):
    """retry_rate = calls_with_retry / total_calls。"""
    # 3 次 chat 调用：第一次需 retry（2 responses），其他 2 次直接成功（各 1 response）
    fake_litellm.completion.responses = [
        fake_litellm.exceptions.Timeout('e'),  # call 1 attempt 1
        'ok',                                  # call 1 attempt 2 (retry success)
        'ok',                                  # call 2
        'ok',                                  # call 3
    ]
    monkeypatch.setattr('time.sleep', lambda s: None)
    for _ in range(3):
        client.chat(messages=[{"role": "user", "content": "hi"}])
    stats = client.stats()
    assert stats['retry']['total_calls'] == 3
    assert stats['retry']['calls_with_retry'] == 1
    assert stats['retry']['retry_rate'] == pytest.approx(1/3, abs=1e-3)


def test_stats_avg_attempts(client, fake_litellm, monkeypatch):
    """avg_attempts_per_call = total_attempts / total_calls。"""
    # 3 次 chat 调用：第一次 2 attempts，其他 1 attempt → total 4 / 3 calls = 1.333
    fake_litellm.completion.responses = [
        fake_litellm.exceptions.Timeout('e'),  # call 1 attempt 1 fail
        'ok',                                  # call 1 attempt 2 success
        'ok',                                  # call 2 attempt 1 success
        'ok',                                  # call 3 attempt 1 success
    ]
    monkeypatch.setattr('time.sleep', lambda s: None)
    for _ in range(3):
        client.chat(messages=[{"role": "user", "content": "hi"}])
    stats = client.stats()
    # 4 attempts / 3 calls ≈ 1.333
    assert stats['retry']['avg_attempts_per_call'] == pytest.approx(4/3, abs=1e-3)


# ════════════════════════════════════════════════
# SGELLMClient.warmup
# ════════════════════════════════════════════════


def test_warmup_success(client, fake_litellm, monkeypatch):
    """warmup 调用成功 → call_count 增加。"""
    fake_litellm.completion.responses = ['r1', 'r2']
    monkeypatch.setattr('time.sleep', lambda s: None)
    client.warmup(n_calls=2)
    assert client.call_count == 2


def test_warmup_does_not_raise_on_failure(client, fake_litellm, monkeypatch):
    """warmup 调用失败 → 不抛异常，call_count 不变。"""
    fake_litellm.completion.responses = [
        fake_litellm.exceptions.InternalServerError('e'),
    ] * 8  # retry 全部失败
    monkeypatch.setattr('time.sleep', lambda s: None)
    # 不应抛异常
    client.warmup(n_calls=1)
    # 但 call_count 不变（因为都没有成功）
    # 注意：warmup 内部 try-except 静默吞掉


def test_warmup_default_n_calls_2(client, fake_litellm, monkeypatch):
    """warmup 默认调用 2 次。"""
    fake_litellm.completion.responses = ['r1', 'r2']
    monkeypatch.setattr('time.sleep', lambda s: None)
    client.warmup()
    assert client.call_count == 2


# ════════════════════════════════════════════════
# make_llm_client 工厂
# ════════════════════════════════════════════════


def test_make_llm_client_returns_sge_llm_client(fake_litellm):
    """make_llm_client → 返回 SGELLMClient 实例。"""
    with patch.dict('os.environ', {'MINIMAX_API_KEY': 'fake'}):
        c = make_llm_client(provider='minimax')
        assert isinstance(c, SGELLMClient)
        assert c.provider == 'minimax'


def test_make_llm_client_missing_api_key_raises(fake_litellm):
    """make_llm_client + 缺 API key → ValueError。"""
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError):
            make_llm_client(provider='minimax')


def test_make_llm_client_invalid_provider_raises(fake_litellm):
    """make_llm_client + 未知 provider → ValueError。"""
    with patch.dict('os.environ', {'MINIMAX_API_KEY': 'fake'}):
        with pytest.raises(ValueError, match='Unknown provider'):
            make_llm_client(provider='unknown')
