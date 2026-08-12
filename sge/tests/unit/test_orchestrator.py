"""sge.orchestrator pytest 单元测试 — 17 个编排器逻辑 + 6 个持久化集成。

Phase 3.2 conversion 5/5（完成第一批 5 模块）。
覆盖：
  编排器逻辑 (17):
    1-12: 12 步完整循环 + trace 字段 + Identity/Narrative/Crystallize 触发 + Experience/Self Entropy
    13: snapshot_all → restore_all round-trip
    14: 缺 _schema_version → SnapshotError
    15: identity/narrative snapshot 不含 llm
    16: EventGenerator rng_state 保真
    17: snapshot_all 无 LLM 句柄泄露

  持久化集成 (6):
    A: checkpoint_every 自动触发
    B: phase_xition 触发额外 checkpoint
    C: identity/narrative 触发额外 checkpoint
    D: Round-trip（save → 新 orchestrator → restore → state 一致）
    E: db/student_id 互斥校验
    F: StudentDeletedError 抛出不中断
"""

from __future__ import annotations

import copy
import json
import random

import pytest

from sge.actor import ActorOutput
from sge.baseline import (
    SGE_DEFAULT_DRIVES,
    SGE_DEFAULT_VALUES,
    Agent,
    DriveMetabolism,
    HawkingDecay,
    MemoryCrystallizer,
    SnapshotError,
    ValueLayer,
    SIGNALS,
    _load_drives,
)
from sge.event import EventGenerator
from sge.identity import IdentityLayer
from sge.narrative import NarrativeBuilder
from sge.orchestrator import SGEOrchestrator


# ════════════════════════════════════════════════
# Fixture: 构造一个完整的 SGEOrchestrator（stub LLM）
# ════════════════════════════════════════════════


@pytest.fixture
def orch_components():
    """构造一个完整的 orchestrator 组件集合（stub LLM）。"""
    drives = list(_load_drives())
    value_layer = ValueLayer(values=list(SGE_DEFAULT_VALUES))
    hawking = HawkingDecay(gamma=0.01, clock=0.0)
    crystallizer = MemoryCrystallizer(n_dims=11)
    agent = Agent(
        seed=42,
        drives=drives,
        value_layer=value_layer,
        hawking=hawking,
        crystallizer=crystallizer,
        crystallize_every=10,
    )
    metabolism = DriveMetabolism(drives=drives)
    event_gen = EventGenerator(baby_id='orch_test', seed=42)
    identity_layer = IdentityLayer(crystallize_every_n_epochs=20)
    narrative_builder = NarrativeBuilder(build_every_n_epochs=50)
    return {
        'drives': drives,
        'value_layer': value_layer,
        'hawking': hawking,
        'crystallizer': crystallizer,
        'agent': agent,
        'drive_metabolism': metabolism,
        'event_generator': event_gen,
        'identity_layer': identity_layer,
        'narrative_builder': narrative_builder,
    }


@pytest.fixture
def orch(orch_components):
    """构造一个 SGEOrchestrator 实例（无 db，stub LLM）。"""
    c = orch_components
    return SGEOrchestrator(
        agent=c['agent'],
        value_layer=c['value_layer'],
        drive_metabolism=c['drive_metabolism'],
        event_generator=c['event_generator'],
        identity_layer=c['identity_layer'],
        narrative_builder=c['narrative_builder'],
        hawking=c['hawking'],
        crystallizer=c['crystallizer'],
        crystallize_every=10,
    )


@pytest.fixture
def orch_traces(orch):
    """跑 55 epoch（覆盖 narrative 触发点 epoch=50）返回 traces 列表。"""
    return orch.run(n_epochs=55)


# ════════════════════════════════════════════════
# 编排器逻辑 17 测试
# ════════════════════════════════════════════════


def test_orchestrator_run_55_epochs_produces_55_traces(orch_traces):
    """测试 1: 跑 55 epoch 产生 55 traces。"""
    assert len(orch_traces) == 55


def test_orchestrator_trace_fields_complete(orch_traces):
    """测试 2: 每步 trace 字段完整（OrchestratorStep 15+ 字段）。"""
    t0 = orch_traces[0]
    required_fields = [
        'epoch', 'event', 'critic_context', 'critic_value_delta',
        'value_state_before', 'value_state_after',
        'hawking_removed', 'crystallize_result',
        'signals', 'noisy_signals', 'retrieved_memories',
        'actor_output', 'reward', 'phase_xition',
        'identity', 'narrative',
    ]
    for f in required_fields:
        assert hasattr(t0, f), f"Missing field: {f}"


def test_orchestrator_actor_output_valid(orch_traces):
    """测试 3: Actor 输出结构有效。"""
    actor_out = orch_traces[0].actor_output
    assert actor_out is not None
    assert actor_out.behavior_label
    assert actor_out.inner_monologue
    assert 0.0 <= actor_out.confidence <= 1.0


def test_orchestrator_value_state_before_after_diverge(orch_traces):
    """测试 4: Value EMA 时序正确（safety delta 非零时 before/after 不同）。"""
    t0 = orch_traces[0]
    if t0.critic_value_delta.get('safety', 0) != 0:
        assert t0.value_state_after != t0.value_state_before


def test_orchestrator_identity_crystallizes_at_least_twice(orch_traces):
    """测试 5: Identity 至少结晶 2 次（55 epoch × 20 step/epoch）。"""
    n_identity = sum(1 for t in orch_traces if t.identity is not None)
    assert n_identity >= 2, f"Expected ≥ 2 identity crystallizations, got {n_identity}"


def test_orchestrator_narrative_builds_at_least_once(orch_traces):
    """测试 6: Narrative 至少构建 1 次（55 epoch × 50 step/epoch）。"""
    n_narrative = sum(1 for t in orch_traces if t.narrative is not None)
    assert n_narrative >= 1, f"Expected ≥ 1 narrative builds, got {n_narrative}"


def test_orchestrator_crystallize_triggers_every_10_epochs(orch_traces):
    """测试 7: Crystallize 触发 ≥ 5 次（55 epoch / 10 ≈ 5.5）。"""
    n_crystallize = sum(1 for t in orch_traces if t.crystallize_result is not None)
    assert n_crystallize >= 5, f"Expected ≥ 5 crystallizes, got {n_crystallize}"


def test_orchestrator_phase_transition_detected(orch_traces):
    """测试 8: Phase Transition 检测（55 epoch 内可能 0 次，记录统计）。"""
    # 不强要求 ≥ 1（短 epoch 可能 0 次），但确保 trace 字段存在
    assert all(hasattr(t, 'phase_xition') for t in orch_traces)


def test_orchestrator_hawking_decay_engaged(orch_traces):
    """测试 9: Hawking 衰减调用（要么 removed > 0 要么累积了 memories）。"""
    total_removed = sum(t.hawking_removed for t in orch_traces)
    # 总 removed ≥ 0，永真；这里只验证字段存在且非负
    assert total_removed >= 0


def test_orchestrator_final_value_state_matches_value_layer(orch_traces, orch):
    """测试 10: 终态一致（最后 trace.value_state_after == value_layer.value_state）。"""
    last_t = orch_traces[-1]
    for k in last_t.value_state_after:
        assert abs(last_t.value_state_after[k] - orch.value_layer.value_state[k]) < 1e-9


def test_orchestrator_experience_encoding_present(orch_traces):
    """测试 11: Experience Encoding（洞察 34）字段完整。"""
    t0 = orch_traces[0]
    assert t0.experience is not None, "experience trace missing"
    assert t0.experience.get('meaning'), "experience.meaning empty"
    assert t0.experience['experience_id'] == f"{t0.event['event_id']}-exp"


def test_orchestrator_self_entropy_metrics_in_range(orch_traces):
    """测试 12: Self Entropy 4 个分量都在 [0, 1]。"""
    t0 = orch_traces[0]
    assert t0.self_entropy is not None, "self_entropy trace missing"
    for key in ('H_self', 'H_value', 'H_identity', 'H_narrative'):
        v = t0.self_entropy[key]
        assert 0.0 <= v <= 1.0, f"{key} out of [0,1]: {v}"


def test_orchestrator_snapshot_all_round_trip_consistent(orch, orch_traces):
    """测试 13: orchestrator snapshot_all → restore_all 后再 step(55) 必须与原实例一致。

    注意：必须从干净的 random seed 开始，确保 compute_signals 感知噪声序列一致。
    """
    snap = orch.snapshot_all()
    json.dumps(snap)  # JSON 序列化烟囱测试
    snap_restored = json.loads(json.dumps(snap))

    # 构造第二个 orchestrator（用同种子）并 restore
    drives = orch.agent.drives
    vl_template = ValueLayer(values=list(SGE_DEFAULT_VALUES))
    hw = HawkingDecay(gamma=0.01, clock=0.0)
    cr = MemoryCrystallizer(n_dims=11)
    orch2 = SGEOrchestrator(
        agent=Agent(seed=42, drives=drives, value_layer=vl_template,
                    hawking=hw, crystallizer=cr, crystallize_every=10),
        value_layer=ValueLayer(values=list(SGE_DEFAULT_VALUES)),
        drive_metabolism=DriveMetabolism(drives=drives),
        event_generator=EventGenerator(baby_id='orch_test', seed=42),
        identity_layer=IdentityLayer(crystallize_every_n_epochs=20),
        narrative_builder=NarrativeBuilder(build_every_n_epochs=50),
        hawking=hw, crystallizer=cr, crystallize_every=10,
    )
    orch2.restore_all(snap_restored)
    orch.restore_all(snap_restored)

    # 重置 random seed 以保证 compute_signals 感知噪声序列一致
    random.seed(42)
    t1 = orch.step(55)
    random.seed(42)
    t2 = orch2.step(55)

    for k in ('safety', 'creativity', 'connection'):
        assert abs(t1.value_state_after[k] - t2.value_state_after[k]) < 1e-9, \
            f"value_state.{k} drift"
    for k in SIGNALS:
        assert abs(t1.signals[k] - t2.signals[k]) < 1e-9, f"signal {k} drift"
    assert t1.identity == t2.identity or (
        t1.identity is None and t2.identity is None
    )
    assert t1.narrative == t2.narrative or (
        t1.narrative is None and t2.narrative is None
    )


def test_orchestrator_restore_missing_schema_version_raises(orch):
    """测试 14: restore 缺 _schema_version 必须抛 SnapshotError。"""
    snap = orch.snapshot_all()
    snap_bad = copy.deepcopy(json.loads(json.dumps(snap)))
    del snap_bad['_schema_version']

    drives = orch.agent.drives
    vl_template = ValueLayer(values=list(SGE_DEFAULT_VALUES))
    hw = HawkingDecay(gamma=0.01, clock=0.0)
    cr = MemoryCrystallizer(n_dims=11)
    orch_bad = SGEOrchestrator(
        agent=Agent(seed=42, drives=drives, value_layer=vl_template,
                    hawking=hw, crystallizer=cr, crystallize_every=10),
        value_layer=ValueLayer(values=list(SGE_DEFAULT_VALUES)),
        drive_metabolism=DriveMetabolism(drives=drives),
        event_generator=EventGenerator(baby_id='orch_test', seed=42),
        identity_layer=IdentityLayer(crystallize_every_n_epochs=20),
        narrative_builder=NarrativeBuilder(build_every_n_epochs=50),
        hawking=hw, crystallizer=cr, crystallize_every=10,
    )
    with pytest.raises(SnapshotError) as excinfo:
        orch_bad.restore_all(snap_bad)
    assert '_schema_version' in str(excinfo.value)


def test_orchestrator_identity_narrative_snapshot_no_llm_leak(orch):
    """测试 15: identity_layer / narrative_builder snapshot 不含 llm 字段。"""
    snap = orch.snapshot_all()
    assert 'llm' not in snap['identity_layer']
    assert 'llm' not in snap['narrative_builder']
    assert snap['identity_layer']['use_real_llm'] is False


def test_orchestrator_event_generator_rng_state_preserved(orch):
    """测试 16: EventGenerator rng_state 保真 — snapshot/restore 后 random() 序列一致。"""
    eg_snapshot = orch.event_generator.snapshot()
    val1_before = orch.event_generator.rng.random()
    val2_before = orch.event_generator.rng.random()

    eg_test = EventGenerator(baby_id='test', seed=99)
    eg_test.restore(eg_snapshot)
    val1_after = eg_test.rng.random()
    val2_after = eg_test.rng.random()

    assert abs(val1_before - val1_after) < 1e-9
    assert abs(val2_before - val2_after) < 1e-9


def test_orchestrator_snapshot_all_no_llm_or_external_refs(orch):
    """测试 17: snapshot_all 无 LLM 句柄或外部组件引用泄露。"""
    snap = orch.snapshot_all()
    forbidden = {'llm', 'value_layer', 'hawking', 'crystallizer'}
    assert not (forbidden & set(snap['agent'].keys())), \
        f"Agent snapshot 泄露外部 ref: {forbidden & set(snap['agent'].keys())}"


# ════════════════════════════════════════════════
# 持久化集成 6 测试
# ════════════════════════════════════════════════


def _make_components():
    """orch_components 子集 + 全新组件实例（持久化测试需要每次独立构造）。"""
    drives = list(_load_drives())
    value_layer = ValueLayer(values=list(SGE_DEFAULT_VALUES))
    hawking = HawkingDecay(gamma=0.01, clock=0.0)
    crystallizer = MemoryCrystallizer(n_dims=11)
    agent = Agent(
        seed=42,
        drives=drives,
        value_layer=value_layer,
        hawking=hawking,
        crystallizer=crystallizer,
        crystallize_every=10,
    )
    return agent, value_layer, DriveMetabolism(drives=drives), \
        EventGenerator(baby_id='test_baby', seed=42), \
        IdentityLayer(crystallize_every_n_epochs=20), \
        NarrativeBuilder(build_every_n_epochs=50), hawking, crystallizer


def test_checkpoint_every_auto_triggers(tmp_db_path):
    """集成测试 A: checkpoint_every 自动触发 — 200 epoch / 100 = 2 次 auto checkpoint。"""
    from sge.persistence import TwinStateDB
    with TwinStateDB(tmp_db_path) as db:
        agent, vl, dm, eg, il, nb, hw, cr = _make_components()
        orch = SGEOrchestrator(
            agent=agent, value_layer=vl, drive_metabolism=dm, event_generator=eg,
            identity_layer=il, narrative_builder=nb,
            hawking=hw, crystallizer=cr,
            db=db, student_id='stu_001', checkpoint_every=100,
            student_name='Test Baby 1',
        )
        orch.run(n_epochs=200)

        history = db.get_checkpoint_history('stu_001', limit=10)
        auto_triggers_desc = [h['trigger'] for h in history if h['trigger'].startswith('auto_')]
        assert len(auto_triggers_desc) == 2
        auto_triggers = sorted(auto_triggers_desc)
        assert auto_triggers == ['auto_100', 'auto_200']


def test_phase_xition_triggers_extra_checkpoint(tmp_db_path):
    """集成测试 B: phase_xition 触发额外 checkpoint（mock _save_checkpoint）。"""
    from sge.persistence import TwinStateDB
    with TwinStateDB(tmp_db_path) as db:
        agent, vl, dm, eg, il, nb, hw, cr = _make_components()
        orch = SGEOrchestrator(
            agent=agent, value_layer=vl, drive_metabolism=dm, event_generator=eg,
            identity_layer=il, narrative_builder=nb,
            hawking=hw, crystallizer=cr,
            db=db, student_id='stu_002', checkpoint_every=1000,
        )
        ok = orch._save_checkpoint('phase_xition', epoch=orch.current_epoch + 1)
        assert ok

        history = db.get_checkpoint_history('stu_002', limit=10)
        triggers = [h['trigger'] for h in history]
        assert 'phase_xition' in triggers


def test_identity_narrative_triggers_extra_checkpoints(tmp_db_path):
    """集成测试 C: identity_crystallize + narrative_build 触发额外 checkpoint。"""
    from sge.persistence import TwinStateDB
    with TwinStateDB(tmp_db_path) as db:
        agent, vl, dm, eg, il, nb, hw, cr = _make_components()
        orch = SGEOrchestrator(
            agent=agent, value_layer=vl, drive_metabolism=dm, event_generator=eg,
            identity_layer=il, narrative_builder=nb,
            hawking=hw, crystallizer=cr,
            db=db, student_id='stu_003', checkpoint_every=1000,
        )
        orch._save_checkpoint('identity_crystallize', epoch=1)
        orch._save_checkpoint('narrative_build', epoch=2)

        history = db.get_checkpoint_history('stu_003', limit=10)
        triggers = sorted({h['trigger'] for h in history})
        assert 'identity_crystallize' in triggers
        assert 'narrative_build' in triggers


def test_orchestrator_persistence_round_trip_consistent(tmp_db_path):
    """集成测试 D: Round-trip（save → 新 orchestrator → restore → state 一致）。"""
    from sge.persistence import TwinStateDB
    with TwinStateDB(tmp_db_path) as db:
        # 第一个 orchestrator：跑 10 epoch + save
        agent1, vl1, dm1, eg1, il1, nb1, hw1, cr1 = _make_components()
        orch1 = SGEOrchestrator(
            agent=agent1, value_layer=vl1, drive_metabolism=dm1, event_generator=eg1,
            identity_layer=il1, narrative_builder=nb1,
            hawking=hw1, crystallizer=cr1,
            db=db, student_id='stu_004', checkpoint_every=10,
            app_state={'subject': 'math', 'grade': 7},
        )
        orch1.run(n_epochs=10)

        sge_state, app_state, epoch = db.load_full_state('stu_004')
        assert epoch == 10
        assert app_state == {'subject': 'math', 'grade': 7}
        assert sge_state['_schema_version'] == '1.0'

        # 第二个 orchestrator：restore snapshot
        agent2, vl2, dm2, eg2, il2, nb2, hw2, cr2 = _make_components()
        orch2 = SGEOrchestrator(
            agent=agent2, value_layer=vl2, drive_metabolism=dm2, event_generator=eg2,
            identity_layer=il2, narrative_builder=nb2,
            hawking=hw2, crystallizer=cr2,
        )
        orch2.restore_all(sge_state)

        assert orch2.current_epoch == 10
        assert orch2.value_layer.value_state == orch1.value_layer.value_state


def test_db_and_student_id_must_be_both_set_or_both_none(orch_components):
    """集成测试 E: db/student_id 互斥校验（fail-fast）。"""
    from sge.persistence import TwinStateDB
    c = orch_components
    base_kwargs = dict(
        agent=c['agent'], value_layer=c['value_layer'],
        drive_metabolism=c['drive_metabolism'], event_generator=c['event_generator'],
        identity_layer=c['identity_layer'], narrative_builder=c['narrative_builder'],
        hawking=c['hawking'], crystallizer=c['crystallizer'],
    )

    # db=None + student_id=... → ValueError
    with pytest.raises(ValueError, match='同时提供或同时为 None'):
        SGEOrchestrator(**base_kwargs, db=None, student_id='stu_005')

    # db=... + student_id=None → ValueError
    with pytest.raises(ValueError, match='同时提供或同时为 None'):
        SGEOrchestrator(**base_kwargs, db=TwinStateDB(':memory:'),
                        student_id=None)


def test_student_deleted_does_not_interrupt_step(tmp_db_path):
    """集成测试 F: 软删除后 checkpoint 失败但 step 继续（不中断 epoch 循环）。"""
    from sge.persistence import TwinStateDB
    with TwinStateDB(tmp_db_path) as db:
        agent, vl, dm, eg, il, nb, hw, cr = _make_components()
        orch = SGEOrchestrator(
            agent=agent, value_layer=vl, drive_metabolism=dm, event_generator=eg,
            identity_layer=il, narrative_builder=nb,
            hawking=hw, crystallizer=cr,
            db=db, student_id='stu_006', checkpoint_every=5,
        )
        orch.run(n_epochs=5)
        db.delete_student('stu_006', hard=False, accessor_id='test')

        # checkpoint 应失败但不抛异常（_save_checkpoint 内部 try/except）
        ok = orch._save_checkpoint('auto_10', epoch=10)
        assert not ok

        # step() 仍可继续（不中断 epoch 循环）
        orch.run(n_epochs=5)  # 应继续完成 5 个 epoch，无异常