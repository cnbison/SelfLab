"""Phase 3.2 共享 fixtures。"""

from __future__ import annotations

import os
import tempfile
from typing import Iterator

import pytest

from sge import TwinStateDB


@pytest.fixture
def tmp_db_path() -> Iterator[str]:
    """临时 SQLite DB 路径（自动清理）。

    返回 .db 文件路径，配合 TwinStateDB(path) 使用。
    用法：
        def test_x(tmp_db_path):
            with TwinStateDB(tmp_db_path) as db:
                ...
    """
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def tmp_db(tmp_db_path: str) -> Iterator[TwinStateDB]:
    """临时 TwinStateDB 实例（自动 cleanup + close）。"""
    db = TwinStateDB(tmp_db_path)
    try:
        yield db
    finally:
        try:
            db.close()
        except Exception:
            pass


@pytest.fixture
def stub_llm():
    """Stub SGELLMClient（确定性响应）。

    Phase 3.2 优先跑 stub 路径的测试，real LLM 留给 e2e/。
    """
    from unittest.mock import MagicMock

    client = MagicMock()

    def fake_chat_json(messages, temperature=0.5, max_tokens=1024, **kwargs):
        # 简化：返回固定 identity + actor 输出
        msg = str(messages)
        if 'value_vector' in msg or '内心独白' in msg:
            return {
                'inner_monologue': '我保持现状',
                'behavior_label': '敷衍回应',
                'intention': '想观察局势',
                'confidence': 0.5,
            }
        if 'emotion' in msg.lower() or '情感感知' in msg:
            return {
                'context': {
                    'user_emotion': 0.5, 'topic_intimacy': 0.5,
                    'conversation_depth': 0.5, 'user_engagement': 0.5,
                    'conflict_level': 0.0, 'novelty_level': 0.5,
                    'user_vulnerability': 0.0, 'time_of_day': 0.5,
                },
                'value_delta': {f: 0.0 for f in [
                    'safety', 'creativity', 'connection', 'autonomy', 'justice', 'compassion',
                ]},
            }
        return None  # fallback to stub

    client.chat_json.side_effect = fake_chat_json
    client.chat.side_effect = lambda *a, **kw: '{}'
    client.stats.return_value = {'call_count': 0, 'retry': {}}
    return client


@pytest.fixture(autouse=True)
def _reset_session_registry():
    """TwinSession 进程内 registry 在每个测试后清理。

    TwinSession._session_registry 是模块级 dict，跨测试污染会导致 SessionLockedError。
    """
    from sge.session import _session_registry
    yield
    for sid in list(_session_registry):
        try:
            sess = _session_registry[sid]
            if not sess._closed:
                sess.close(save=False)
        except Exception:
            pass
        _session_registry.pop(sid, None)