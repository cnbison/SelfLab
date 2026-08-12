"""
SGE 会话管理（TwinSession）

Phase 3.1 · 动作 2 — 单次学生与 twin 交互的 session 生命周期。

设计 SSOT：[research/phase3/10-engineering/02-session.md](../../research/phase3/10-engineering/02-session.md)

职责：
1. 启动时从 TwinStateDB 加载完整 state
2. 重建 SGEOrchestrator（stub / 真实 LLM 模式）
3. process_event：处理 1 个 epoch + 增量持久化
4. close：全量持久化 + cleanup

多 session 并发：
- 同一 student 不能并发（数据竞争）→ SessionLock（in-memory + DB INSERT）
- 不同 student 可以并发（DB 层隔离，R10 已覆盖）

应用层集成：
- TwinSession.process_event(epoch) 返回 OrchestratorStep
- App 层（SubjectMasteryState / conversation history）由调用方在 process_event 前后维护
"""

from __future__ import annotations

import sys
from typing import Optional, TYPE_CHECKING

from .baseline import (
    Agent, DriveMetabolism, ValueLayer, HawkingDecay, MemoryCrystallizer,
    SGE_DEFAULT_DRIVES, SGE_DEFAULT_VALUES,
)
from .event import EventGenerator
from .identity import IdentityLayer
from .narrative import NarrativeBuilder
from .orchestrator import SGEOrchestrator, OrchestratorStep
from .persistence import StudentNotFoundError

if TYPE_CHECKING:
    from .persistence import TwinStateDB


# ══════════════════════════════════════════════
# 异常类
# ══════════════════════════════════════════════


class SessionError(Exception):
    """TwinSession 错误基础类。"""


class SessionLockedError(SessionError):
    """同一 student 已有 active session。"""


class SessionNotFoundError(SessionError):
    """session 未注册或已 close。"""


# ══════════════════════════════════════════════
# Session Registry（进程内锁）
# ══════════════════════════════════════════════
#
# 设计权衡：
# - 进程内：dict[student_id, TwinSession]（同一进程内防并发）
# - 跨进程：DB 表 session_locks（不在本次范围，留给 M3.x 持久化锁）
#
# 当前实现：仅进程内锁。跨进程并发由 SQLite WAL 串行化保证（同一 DB 文件），
# 但严格意义上的"防并发"需后续 DB 级锁。本次 1.5 天范围聚焦核心骨架。


_session_registry: dict[str, "TwinSession"] = {}


# ══════════════════════════════════════════════
# TwinSession
# ══════════════════════════════════════════════


class TwinSession:
    """单次学生与 twin 交互的 session 生命周期。

    用法：
        session = TwinSession(student_id='stu_001', twin_db=db)
        for student_event in events:
            trace = session.process_event(epoch=session.current_epoch)
            # App 层：更新 SubjectMasteryState + conversation history
            session.app_state['conversations'].append({...})
        session.close()  # 全量保存到 DB

    跨进程恢复：
        session1 = TwinSession('stu_001', db)  # 第一次
        session1.process_event(epoch=0)
        session1.close()

        session2 = TwinSession('stu_001', db)  # 第二次（不同进程/重启）
        # session2 自动从 DB 加载 state（current_epoch 等于 session1.close 时的 epoch）
        session2.process_event(epoch=session2.current_epoch)  # 从上次继续

    Args:
        student_id: 学生 ID（必须已在 DB 中 create_student）
        twin_db: TwinStateDB 实例
        use_real_llm: 是否使用真实 LLM（默认 stub）
        llm: SGELLMClient 实例（use_real_llm=True 时可选）
        auto_save_every: 每 N epoch 增量保存（默认 10；0 = 禁用）
    """

    # 类属性：构造失败（如 SessionLockedError）时 __del__ 不会误报未保存
    _closed: bool = True

    def __init__(
        self,
        student_id: str,
        twin_db: 'TwinStateDB',
        use_real_llm: bool = False,
        llm: Optional[object] = None,
        auto_save_every: int = 10,
    ):
        if not student_id or not isinstance(student_id, str):
            raise ValueError(f"student_id 必须是非空字符串，得到: {student_id!r}")
        if auto_save_every < 0:
            raise ValueError(f"auto_save_every 必须 >= 0，得到: {auto_save_every}")

        # SessionLock 校验（进程内）
        if student_id in _session_registry:
            raise SessionLockedError(
                f"student_id '{student_id}' 已有 active session（先 close 再开新）"
            )

        self.student_id = student_id
        self.db = twin_db
        self.use_real_llm = use_real_llm
        self.llm = llm
        self.auto_save_every = auto_save_every

        # 1. 从 DB 加载 state
        sge_state, app_state, current_epoch = twin_db.load_full_state(student_id)
        # load_full_state 对未注册学生返回 ({}, {}, 0)，无法与"已注册但没跑过 epoch"
        # 区分；这里显式查一次 students 表，未注册直接 fail-fast（R10：不静默 INSERT）
        if not sge_state and not self._student_exists(twin_db, student_id):
            raise StudentNotFoundError(
                f"TwinSession: student_id '{student_id}' 未注册；"
                f"请先调用 db.create_student('{student_id}')"
            )
        self.sge_state: dict = sge_state
        self.app_state: dict = app_state if app_state is not None else {}
        self.current_epoch: int = current_epoch

        # 2. 重建 SGEOrchestrator
        self.orchestrator = self._build_orchestrator_from_state(sge_state)
        self.orchestrator._n_epochs_hint = current_epoch
        self.orchestrator.current_epoch = current_epoch

        # 3. 注册到 session registry
        _session_registry[student_id] = self
        self._closed = False

    def process_event(
        self,
        epoch: Optional[int] = None,
        extra_critic_context: Optional[dict] = None,
        extra_actor_context: Optional[str] = None,
    ) -> OrchestratorStep:
        """处理一个 epoch（step + 增量持久化）。

        Args:
            epoch: 当前 epoch（None = self.current_epoch）
            extra_critic_context: App 层注入（SSOT §3.1）— 透传给 orchestrator.step
            extra_actor_context: App 层注入 system prompt（SSOT §3.1）

        Returns:
            OrchestratorStep（完整 trace）

        Raises:
            SessionError: session 已 close
        """
        if self._closed:
            raise SessionError(
                f"session 已 close（student_id={self.student_id!r}），"
                f"需要重新 TwinSession(...) 打开新 session"
            )

        ep = epoch if epoch is not None else self.current_epoch
        trace = self.orchestrator.step(
            epoch=ep,
            extra_critic_context=extra_critic_context,
            extra_actor_context=extra_actor_context,
        )
        self.current_epoch = ep + 1

        # 增量持久化：每 N epoch（auto_save_every > 0 且 current_epoch % N == 0）
        if self.auto_save_every > 0 and self.current_epoch % self.auto_save_every == 0:
            self._save_incremental(trigger=f"auto_{self.current_epoch}")

        return trace

    def close(self, save: bool = True) -> None:
        """关闭 session（全量保存 + cleanup）。

        Args:
            save: 是否保存到 DB（默认 True；False 用于纯只读 session）
        """
        if self._closed:
            return  # 幂等

        if save:
            # 1. 同步 orchestrator state → self.sge_state
            self._sync_state_from_orchestrator()
            # 2. 全量保存
            try:
                self.db.save_full_state(
                    student_id=self.student_id,
                    sge_state=self.sge_state,
                    app_state=self.app_state,
                    epoch=self.current_epoch,
                    trigger='on_close',
                )
                self.db.log_access(
                    student_id=self.student_id,
                    accessor_id='session',
                    operation='on_close',
                    ip_address=None,
                )
            except Exception as e:
                sys.stderr.write(
                    f"[TwinSession] close save failed: {type(e).__name__}: {e}\n"
                )

        # 3. 从 registry 注销
        _session_registry.pop(self.student_id, None)
        self._closed = True

    def __enter__(self) -> 'TwinSession':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close(save=True)

    def __del__(self) -> None:
        # 兜底：对象销毁时若未 close，记录 stderr（不强制 save，因为可能 double-close）
        if not self._closed:
            sys.stderr.write(
                f"[TwinSession] warning: session for '{self.student_id}' "
                f"destroyed without close() — state may not be saved\n"
            )

    # ── 内部方法 ──

    @staticmethod
    def _student_exists(twin_db: 'TwinStateDB', student_id: str) -> bool:
        row = twin_db.conn.execute(
            "SELECT 1 FROM students WHERE student_id=?", (student_id,)
        ).fetchone()
        return row is not None

    def _build_orchestrator_from_state(self, sge_state: dict) -> SGEOrchestrator:
        """从持久化 state 重建 SGEOrchestrator（§4 难点）。

        关键设计：
        1. 先用 snapshot 字段构造默认组件（stub 模式，无 LLM）
        2. 用 restore(snap) 把每个组件恢复到目标 state
        3. 最后构造 SGEOrchestrator，传入已恢复的组件
        4. 不用 snapshot_all() 一次恢复（更灵活，逐组件控制）

        sge_state 为空（学生刚 create_student，还没跑过 epoch）时走 fresh 分支：
        用默认参数构造全套组件，等价于一个全新的 twin。
        """
        is_fresh = not sge_state

        # 1. 从 metadata 提取核心参数
        metadata = sge_state.get('metadata', {})
        crystallize_every = int(metadata.get('crystallize_every', 10))
        hours_per_epoch = float(metadata.get('hours_per_epoch', 1.0))
        # use_real_llm 不能从 snapshot 读取（False 永远不变更安全）

        # 2. 重建 Agent + 神经网络
        agent_snap = sge_state.get('agent', {})
        seed = int(agent_snap.get('seed', 42))
        drives = list(agent_snap.get('drives', SGE_DEFAULT_DRIVES))

        # 3. 重建 ValueLayer
        value_layer = ValueLayer(values=list(SGE_DEFAULT_VALUES))
        if 'value_state' in agent_snap:
            # ValueLayer 不在 agent snapshot 中，直接用 value_layer snapshot
            pass
        if 'value_layer' in sge_state:
            vl_snap = sge_state['value_layer']
            value_layer = ValueLayer(values=vl_snap.get('values', SGE_DEFAULT_VALUES))
            value_layer.alpha = float(vl_snap.get('alpha', 0.3))
            value_layer.value_state = dict(vl_snap.get('value_state', {}))

        # 4. 重建 DriveMetabolism
        drive_metabolism = DriveMetabolism(drives=drives)
        if 'drive_metabolism' in sge_state:
            dm_snap = sge_state['drive_metabolism']
            drive_metabolism.drives = list(dm_snap.get('drives', drives))
            drive_metabolism.frustration = dict(dm_snap.get('frustration', {}))
            drive_metabolism.hunger_rates = dict(dm_snap.get('hunger_rates', {}))
            drive_metabolism.decay_rate = float(dm_snap.get('decay_rate', 0.1))
            drive_metabolism._last_tick = float(dm_snap.get('_last_tick', 0.0))
            drive_metabolism.decay_lambda = float(dm_snap.get('decay_lambda', 0.08))
            drive_metabolism.temp_coeff = float(dm_snap.get('temp_coeff', 0.12))
            drive_metabolism.temp_floor = float(dm_snap.get('temp_floor', 0.03))

        # 5. 重建 EventGenerator
        event_generator = EventGenerator(
            baby_id=metadata.get('baby_id', self.student_id),
            seed=seed,
        )
        if 'event_generator' in sge_state:
            eg_snap = sge_state['event_generator']
            event_generator.baby_id = eg_snap.get('baby_id', event_generator.baby_id)
            event_generator.value_conflict_prob = float(
                eg_snap.get('value_conflict_prob', 0.3)
            )
            event_generator._clock = float(eg_snap.get('_clock', 0.0))
            # event_history + rng_state 由 event_generator.restore() 恢复
            event_generator.restore(eg_snap)

        # 6. 重建 HawkingDecay（fresh state 用默认值）
        hawking = None
        if sge_state.get('hawking') is not None:
            hawking_snap = sge_state['hawking']
            hawking = HawkingDecay(
                gamma=float(hawking_snap.get('gamma', 0.01)),
                remove_threshold=float(hawking_snap.get('remove_threshold', 1e-4)),
            )
            hawking.memory = list(hawking_snap.get('memory', []))
            hawking._last_tick = float(hawking_snap.get('_last_tick', 0.0))
        elif is_fresh:
            hawking = HawkingDecay(clock=0.0)

        # 7. 重建 MemoryCrystallizer（fresh state 用默认值）
        crystallizer = None
        if sge_state.get('crystallizer') is not None:
            cr_snap = sge_state['crystallizer']
            crystallizer = MemoryCrystallizer(n_dims=int(cr_snap.get('n_dims', 11)))
            crystallizer.restore(cr_snap)
        elif is_fresh:
            crystallizer = MemoryCrystallizer(n_dims=11)

        # 8. 重建 Agent（神经网络 + Hebbian state）
        agent = Agent(
            seed=seed,
            drives=drives,
            value_layer=value_layer,
            hawking=hawking,
            crystallizer=crystallizer,
            crystallize_every=crystallize_every,
        )
        if agent_snap:
            agent.restore(agent_snap)

        # 9. 重建 IdentityLayer + NarrativeBuilder
        identity_layer = IdentityLayer(
            crystallize_every_n_epochs=crystallize_every,
            use_real_llm=False,  # session 默认 stub，调用方可覆盖
        )
        if 'identity_layer' in sge_state:
            identity_layer.restore(sge_state['identity_layer'], llm=self.llm)

        narrative_builder = NarrativeBuilder(
            build_every_n_epochs=crystallize_every * 5,  # 默认 50
            use_real_llm=False,
        )
        if 'narrative_builder' in sge_state:
            narrative_builder.restore(sge_state['narrative_builder'], llm=self.llm)

        # 10. 构造 SGEOrchestrator
        orchestrator = SGEOrchestrator(
            agent=agent,
            value_layer=value_layer,
            drive_metabolism=drive_metabolism,
            event_generator=event_generator,
            identity_layer=identity_layer,
            narrative_builder=narrative_builder,
            hawking=hawking,
            crystallizer=crystallizer,
            crystallize_every=crystallize_every,
            hours_per_epoch=hours_per_epoch,
            use_real_llm=self.use_real_llm,
            llm=self.llm,
        )
        return orchestrator

    def _sync_state_from_orchestrator(self) -> None:
        """从 orchestrator 提取最新 state 到 self.sge_state。

        用 orchestrator.snapshot_all() 一次提取，赋给 self.sge_state。
        下次 close()/增量 save 时使用最新 state。
        """
        self.sge_state = self.orchestrator.snapshot_all()

    def _save_incremental(self, trigger: str = 'auto_save') -> None:
        """增量保存（每 N epoch）。

        全量 save + access_log 审计。
        失败不抛异常（与 SGEOrchestrator._save_checkpoint 一致）。
        """
        self._sync_state_from_orchestrator()
        try:
            self.db.save_full_state(
                student_id=self.student_id,
                sge_state=self.sge_state,
                app_state=self.app_state,
                epoch=self.current_epoch,
                trigger=trigger,
            )
            self.db.log_access(
                student_id=self.student_id,
                accessor_id='session',
                operation=f'incremental_{trigger}',
                ip_address=None,
            )
        except Exception as e:
            sys.stderr.write(
                f"[TwinSession] incremental save failed: {type(e).__name__}: {e}\n"
            )

    # ── 应用层辅助 ──

    def add_conversation(self, entry: dict) -> None:
        """追加一条对话记录到 app_state['conversations']。

        App 层在 process_event 后调用此方法累积对话历史。
        Args:
            entry: dict（包含 student_event / actor_output / mastery 等字段）
        """
        if 'conversations' not in self.app_state:
            self.app_state['conversations'] = []
        self.app_state['conversations'].append(entry)


# ══════════════════════════════════════════════
# 单元测试
# ══════════════════════════════════════════════


def _run_unit_tests() -> bool:
    """兼容层：转调 pytest（Phase 3.2 起的测试已在 sge/tests/unit/test_session.py）。"""
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, '-m', 'pytest',
         'tests/unit/test_session.py', '-v', '--tb=short'],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_unit_tests() else 1)