"""sge.session pytest 单元测试 — TwinSession / 生命周期 / SessionLock / 集成。

Phase 3.2 conversion 第三批 4/4。
覆盖:
  1. 异常类（SessionError / SessionLockedError / SessionNotFoundError）
  2. 完整生命周期（create → session1 → 5 events → close → session2 → 续跑）
  3. process_event 单步验证（epoch 推进 + auto_save_every=0 不增量）
  4. close 后 state 一致性（value_state 6 维全等）
  5. SessionLock 同 student 防并发 + close 后可重开
  6. 不同 student 并发
  7. auto_save_every 增量保存 + with 退出 on_close
  8. 未注册 student → StudentNotFoundError
  9. 全新 student fresh 构建
 10. close(save=False) 丢弃状态
 11. process_event 默认 epoch（None）
 12. process_event on closed session → SessionError
 13. add_conversation 累积 + 创建 list
 14. _student_exists / _build_orchestrator_from_state（直接调用）
 15. _save_incremental 失败不抛
 16. __del__ warning（未 close 销毁）
"""

from __future__ import annotations

import os
import tempfile

import pytest

from sge.session import (
    TwinSession,
    SessionError,
    SessionLockedError,
    SessionNotFoundError,
    _session_registry,
)
from sge.persistence import TwinStateDB, StudentNotFoundError
from sge.baseline import (
    Agent, DriveMetabolism, ValueLayer, HawkingDecay, MemoryCrystallizer,
    SGE_DEFAULT_DRIVES, SGE_DEFAULT_VALUES,
)
from sge.event import EventGenerator
from sge.identity import IdentityLayer
from sge.narrative import NarrativeBuilder
from sge.orchestrator import SGEOrchestrator


def _make_minimal_components():
    """构造一个最小的 SGEOrchestrator 组件集合（用于 session 测试）。"""
    drives = list(SGE_DEFAULT_DRIVES)
    value_layer = ValueLayer(values=list(SGE_DEFAULT_VALUES))
    hawking = HawkingDecay(gamma=0.01, clock=0.0)
    crystallizer = MemoryCrystallizer(n_dims=11)
    agent = Agent(
        seed=42, drives=drives,
        value_layer=value_layer, hawking=hawking,
        crystallizer=crystallizer, crystallize_every=10,
    )
    drive_metabolism = DriveMetabolism(drives=drives)
    event_generator = EventGenerator(baby_id='test_baby', seed=42)
    identity_layer = IdentityLayer(crystallize_every_n_epochs=20)
    narrative_builder = NarrativeBuilder(build_every_n_epochs=50)
    return agent, value_layer, drive_metabolism, event_generator, identity_layer, narrative_builder, hawking, crystallizer


def _create_test_student(db, student_id='stu_test', app_state=None):
    """用 orchestrator 创建学生 + 写入初始 state。"""
    components = _make_minimal_components()
    orch = SGEOrchestrator(
        *components[:6], hawking=components[6], crystallizer=components[7],
        db=db, student_id=student_id, checkpoint_every=100,
        app_state=app_state or {},
    )
    orch.session_end()
    return components


# ════════════════════════════════════════════════
# 异常类
# ════════════════════════════════════════════════


def test_session_error_is_exception():
    """SessionError 是 Exception 子类。"""
    assert issubclass(SessionError, Exception)


def test_session_locked_error_is_session_error():
    """SessionLockedError 继承 SessionError。"""
    assert issubclass(SessionLockedError, SessionError)


def test_session_not_found_error_is_session_error():
    """SessionNotFoundError 继承 SessionError。"""
    assert issubclass(SessionNotFoundError, SessionError)


# ════════════════════════════════════════════════
# 完整生命周期
# ════════════════════════════════════════════════


def test_full_lifecycle_init_5_events_close_reopen(tmp_db_path):
    """完整生命周期：init → 5 events → close → 重新 open → state 一致。"""
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_lifecycle_001', app_state={'grade': 7, 'subject': 'math'})
        # session1 跑 5 epoch + checkpoint
        with TwinStateDB(tmp_db_path) as db:
            from sge.session import _session_registry
            assert 'stu_lifecycle_001' not in _session_registry
            session1 = TwinSession('stu_lifecycle_001', twin_db=db, auto_save_every=2)
            for ep in range(5):
                session1.process_event(epoch=ep)
            session1.close()
            assert 'stu_lifecycle_001' not in _session_registry

    # 跨连接 session2
    with TwinStateDB(tmp_db_path) as db:
        session2 = TwinSession('stu_lifecycle_001', twin_db=db)
        assert session2.current_epoch == 5
        assert session2.app_state.get('grade') == 7
        # 再跑 1 epoch
        trace = session2.process_event(epoch=5)
        assert trace.epoch == 5
        session2.close()


def test_process_event_advances_epoch(tmp_db_path):
    """process_event 单步推进 epoch。"""
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_proc_001')
        session = TwinSession('stu_proc_001', twin_db=db, auto_save_every=0)
        assert session.current_epoch == 0
        trace = session.process_event(epoch=0)
        assert trace.epoch == 0
        assert session.current_epoch == 1
        trace = session.process_event(epoch=1)
        assert trace.epoch == 1
        assert session.current_epoch == 2
        session.close()


def test_process_event_auto_save_zero_no_incremental(tmp_db_path):
    """auto_save_every=0 → 不增量保存。"""
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_noauto_001')
        session = TwinSession('stu_noauto_001', twin_db=db, auto_save_every=0)
        for ep in range(3):
            session.process_event(epoch=ep)
        # DB 中应只有初始 session_end checkpoint（无 auto_N）
        history = db.get_checkpoint_history('stu_noauto_001')
        triggers = {h['trigger'] for h in history}
        assert 'auto_1' not in triggers
        assert 'auto_2' not in triggers
        assert 'auto_3' not in triggers
        session.close()


def test_close_preserves_value_state(tmp_db_path):
    """close 后 value_state 6 维全等。"""
    with TwinStateDB(tmp_db_path) as db:
        # 1. 创建学生 + 跑 10 epoch + 记录 expected value_state
        components = _make_minimal_components()
        orch0 = SGEOrchestrator(
            *components[:6], hawking=components[6], crystallizer=components[7],
            db=db, student_id='stu_vs_001', checkpoint_every=100,
        )
        orch0.run(n_epochs=10)
        expected_value_state = dict(orch0.value_layer.value_state)
        orch0.session_end()

        # 2. 重新打开 session + close(save=False)
        session = TwinSession('stu_vs_001', twin_db=db, auto_save_every=0)
        # 重建后 value_state 应一致
        assert len(session.orchestrator.value_layer.value_state) == 6
        for k, v in expected_value_state.items():
            assert abs(session.orchestrator.value_layer.value_state.get(k, 0) - v) < 1e-9
        session.close(save=False)


# ════════════════════════════════════════════════
# SessionLock
# ════════════════════════════════════════════════


def test_session_lock_same_student_raises(tmp_db_path):
    """同 student 重复打开 → SessionLockedError。"""
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_lock_001')
        session_a = TwinSession('stu_lock_001', twin_db=db)
        try:
            with pytest.raises(SessionLockedError, match='已有 active session'):
                TwinSession('stu_lock_001', twin_db=db)
        finally:
            session_a.close()


def test_session_lock_released_on_close(tmp_db_path):
    """close 后可重新打开同 student。"""
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_relock_001')
        session_a = TwinSession('stu_relock_001', twin_db=db)
        session_a.close()
        # 现在应能重新打开
        session_b = TwinSession('stu_relock_001', twin_db=db)
        session_b.close()


def test_different_students_concurrent(tmp_db_path):
    """不同 student 同时开 session → 互不影响。"""
    with TwinStateDB(tmp_db_path) as db:
        for sid in ['stu_concurrent_A', 'stu_concurrent_B']:
            _create_test_student(db, sid)
        # 同时开 2 个
        session_a = TwinSession('stu_concurrent_A', twin_db=db)
        session_b = TwinSession('stu_concurrent_B', twin_db=db)
        assert session_a.student_id == 'stu_concurrent_A'
        assert session_b.student_id == 'stu_concurrent_B'
        trace_a = session_a.process_event(epoch=0)
        trace_b = session_b.process_event(epoch=0)
        assert trace_a.epoch == 0
        assert trace_b.epoch == 0
        session_a.close()
        session_b.close()


# ════════════════════════════════════════════════
# auto_save_every + with
# ════════════════════════════════════════════════


def test_auto_save_every_incremental(tmp_db_path):
    """auto_save_every=3 → 每 3 epoch 触发 auto_N checkpoint。"""
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_auto_001')
        with TwinSession('stu_auto_001', twin_db=db, auto_save_every=3) as session:
            for ep in range(6):
                session.process_event(epoch=ep)
            assert session.current_epoch == 6

        triggers = {h['trigger'] for h in db.get_checkpoint_history('stu_auto_001')}
        assert 'auto_3' in triggers
        assert 'auto_6' in triggers
        assert 'on_close' in triggers


def test_context_manager_releases_registry(tmp_db_path):
    """with 退出后 registry 已释放。"""
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_ctx_001')
        with TwinSession('stu_ctx_001', twin_db=db) as session:
            assert session.student_id in _session_registry
        assert 'stu_ctx_001' not in _session_registry


# ════════════════════════════════════════════════
# 异常场景
# ════════════════════════════════════════════════


def test_unregistered_student_raises(tmp_db_path):
    """未注册 student → StudentNotFoundError。"""
    with TwinStateDB(tmp_db_path) as db:
        with pytest.raises(StudentNotFoundError, match='未注册'):
            TwinSession('stu_never', twin_db=db)


def test_unregistered_does_not_pollute_registry(tmp_db_path):
    """失败构造不应留下 registry 残留。"""
    with TwinStateDB(tmp_db_path) as db:
        try:
            TwinSession('stu_never', twin_db=db)
        except StudentNotFoundError:
            pass
        assert 'stu_never' not in _session_registry


def test_process_event_on_closed_session_raises(tmp_db_path):
    """close 后 process_event → SessionError。"""
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_closed_001')
        session = TwinSession('stu_closed_001', twin_db=db)
        session.close()
        with pytest.raises(SessionError, match='session 已 close'):
            session.process_event()


def test_invalid_student_id_raises():
    """空 student_id → ValueError。"""
    with TwinStateDB(':memory:') as db:
        with pytest.raises(ValueError, match='student_id'):
            TwinSession('', twin_db=db)


def test_negative_auto_save_every_raises():
    """auto_save_every < 0 → ValueError。"""
    with TwinStateDB(':memory:') as db:
        with pytest.raises(ValueError, match='auto_save_every'):
            TwinSession('any_id', twin_db=db, auto_save_every=-1)


# ════════════════════════════════════════════════
# 全新 student（fresh state）
# ════════════════════════════════════════════════


def test_fresh_student_no_sge_state(tmp_db_path):
    """全新 student（create_student 后无 state）→ fresh 构建。"""
    with TwinStateDB(tmp_db_path) as db:
        db.create_student('stu_fresh_001', name='Fresh', app_state={'grade': 6})
        session = TwinSession('stu_fresh_001', twin_db=db, auto_save_every=0)
        assert session.current_epoch == 0
        assert session.app_state.get('grade') == 6
        assert session.orchestrator.hawking is not None
        assert session.orchestrator.crystallizer is not None
        for ep in range(3):
            session.process_event(epoch=ep)
        session.close()
        # 重开 epoch 续上
        session2 = TwinSession('stu_fresh_001', twin_db=db, auto_save_every=0)
        assert session2.current_epoch == 3
        session2.close()


def test_close_save_false_discards_state(tmp_db_path):
    """close(save=False) 丢弃本次 session 的推进。"""
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_discard_001')
        session = TwinSession('stu_discard_001', twin_db=db, auto_save_every=0)
        initial_epoch = session.current_epoch
        for ep in range(3):
            session.process_event(epoch=session.current_epoch)
        assert session.current_epoch == initial_epoch + 3
        session.close(save=False)
        # 重开后 epoch 应仍是初始值（close(save=False) 没保存）
        session2 = TwinSession('stu_discard_001', twin_db=db, auto_save_every=0)
        assert session2.current_epoch == initial_epoch
        session2.close()


# ════════════════════════════════════════════════
# add_conversation
# ════════════════════════════════════════════════


def test_add_conversation_creates_list(tmp_db_path):
    """add_conversation 在空 conversations 上创建 list。"""
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_add_001')
        session = TwinSession('stu_add_001', twin_db=db, auto_save_every=0)
        assert 'conversations' not in session.app_state
        session.add_conversation({'epoch': 0, 'msg': 'hello'})
        assert 'conversations' in session.app_state
        assert len(session.app_state['conversations']) == 1
        session.close()


def test_add_conversation_appends(tmp_db_path):
    """多次 add_conversation → 累积到 list。"""
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_add_002')
        session = TwinSession('stu_add_002', twin_db=db, auto_save_every=0)
        for i in range(5):
            session.add_conversation({'epoch': i, 'msg': f'msg{i}'})
        assert len(session.app_state['conversations']) == 5
        session.close()


# ════════════════════════════════════════════════
# process_event 边界
# ════════════════════════════════════════════════


def test_process_event_default_epoch_none(tmp_db_path):
    """process_event() 无参 → 用 self.current_epoch。"""
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_def_001')
        session = TwinSession('stu_def_001', twin_db=db, auto_save_every=0)
        trace = session.process_event()  # epoch=None → self.current_epoch=0
        assert trace.epoch == 0
        assert session.current_epoch == 1
        session.close()


def test_process_event_extra_contexts_passed_to_orchestrator(tmp_db_path):
    """process_event 接受 extra_critic_context + extra_actor_context。"""
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_extra_001')
        session = TwinSession('stu_extra_001', twin_db=db, auto_save_every=0)
        # 不抛错即可（具体行为由 orchestrator 决定）
        trace = session.process_event(
            epoch=0,
            extra_critic_context={'student_name': 'Alice'},
            extra_actor_context='extra context',
        )
        assert trace is not None
        session.close()


# ════════════════════════════════════════════════
# __del__ warning
# ════════════════════════════════════════════════


def test_del_warning_on_unclosed_session(tmp_db_path, capsys):
    """未 close 销毁 → stderr warning。"""
    import gc
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_del_001')
        session = TwinSession('stu_del_001', twin_db=db, auto_save_every=0)
        sid = session.student_id
        # 从 registry 移除（否则对象还有引用，__del__ 不会触发）
        _session_registry.pop(sid, None)
        # 强制销毁
        del session
        gc.collect()
        captured = capsys.readouterr()
        assert 'destroyed without close' in captured.err


# ════════════════════════════════════════════════
# close() 幂等性
# ════════════════════════════════════════════════


def test_close_is_idempotent(tmp_db_path):
    """close() 多次调用安全（幂等）。"""
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_idem_001')
        session = TwinSession('stu_idem_001', twin_db=db, auto_save_every=0)
        session.close()
        # 第二次 close 不抛错
        session.close()
        # 第三次
        session.close()
        assert 'stu_idem_001' not in _session_registry


# ════════════════════════════════════════════════
# _student_exists（static method）
# ════════════════════════════════════════════════


def test_student_exists_returns_true(tmp_db_path):
    """_student_exists 已注册学生 → True。"""
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_exists_001')
        assert TwinSession._student_exists(db, 'stu_exists_001') is True


def test_student_exists_returns_false(tmp_db_path):
    """_student_exists 未注册学生 → False。"""
    with TwinStateDB(tmp_db_path) as db:
        assert TwinSession._student_exists(db, 'stu_nonexistent') is False


# ════════════════════════════════════════════════
# _save_incremental 错误处理
# ════════════════════════════════════════════════


def test_save_incremental_swallows_exceptions(tmp_db_path, capsys):
    """_save_incremental 失败时写 stderr，不抛异常。"""
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_save_err_001')
        session = TwinSession('stu_save_err_001', twin_db=db, auto_save_every=0)
        # mock save_full_state 抛异常
        original_save = session.db.save_full_state
        def bad_save(*args, **kwargs):
            raise RuntimeError('simulated DB error')
        session.db.save_full_state = bad_save
        # _save_incremental 应捕获异常，写 stderr
        session._save_incremental(trigger='test_err')
        captured = capsys.readouterr()
        assert 'incremental save failed' in captured.err
        session.db.save_full_state = original_save
        session.close()


# ════════════════════════════════════════════════
# close() 错误处理
# ════════════════════════════════════════════════


def test_close_save_failure_swallows_exception(tmp_db_path, capsys):
    """close(save=True) 时 save 失败 → 不抛异常，写 stderr。"""
    with TwinStateDB(tmp_db_path) as db:
        _create_test_student(db, 'stu_close_err_001')
        session = TwinSession('stu_close_err_001', twin_db=db, auto_save_every=0)
        def bad_save(*args, **kwargs):
            raise RuntimeError('close save failed')
        session.db.save_full_state = bad_save
        # close 应不抛
        session.close(save=True)
        captured = capsys.readouterr()
        assert 'close save failed' in captured.err
