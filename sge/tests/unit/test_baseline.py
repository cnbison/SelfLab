"""sge.baseline pytest 单元测试 — 9 个 snapshot/restore round-trip 测试。

Phase 3.2 conversion 4/5。
覆盖:
  1. agent_round_trip
  2. agent_nn_weights
  3. agent_recurrent_state_isolation
  4. value_layer_round_trip
  5. drive_metabolism_round_trip
  6. hawking_round_trip
  7. crystallizer_round_trip
  8. restore_strict_missing
  9. snapshot_no_llm_leak
"""

from __future__ import annotations

import json
import random

import pytest

from sge.baseline import (
    Agent,
    DriveMetabolism,
    HawkingDecay,
    MemoryCrystallizer,
    SnapshotError,
    ValueLayer,
    CONTEXT_FEATURES,
    HIDDEN_SIZE,
    N_SIGNALS,
    SIGNALS,
)


DRIVES = ['exploration', 'safety', 'creativity', 'connection', 'autonomy']
VALUES = ['safety', 'creativity', 'connection', 'autonomy', 'justice', 'compassion']


def _make_full_ctx() -> dict:
    """构造完整 11D context（覆盖 CONTEXT_FEATURES 全字段）。"""
    ctx = {'user_emotion': 0.5, 'topic_intimacy': 0.3}
    for f in CONTEXT_FEATURES:
        ctx.setdefault(f, 0.0)
    return ctx


def _make_agent_with_state(seed: int = 42) -> Agent:
    """构造一个跑过 5 步、state 有变化的 Agent。"""
    vl = ValueLayer(values=VALUES, alpha=0.3)
    agent = Agent(seed=seed, drives=DRIVES, value_layer=vl, crystallize_every=10)
    for _ in range(5):
        agent.compute_signals(_make_full_ctx())
        agent.learn({s: 0.5 for s in SIGNALS}, reward=-0.1)
        agent.tick_drives()
    return agent


# ════════════════════════════════════════════════
# 测试 4: ValueLayer round-trip
# ════════════════════════════════════════════════


def test_value_layer_round_trip():
    """ValueLayer snapshot/restore 全字段一致（含 alpha）。"""
    vl1 = ValueLayer(values=VALUES, alpha=0.3)
    vl1.value_state['safety'] = 0.42
    vl1.value_state['creativity'] = -0.31
    snap = vl1.snapshot()
    vl2 = ValueLayer(values=VALUES, alpha=0.5)  # 不同初始 alpha
    vl2.restore(snap)
    assert vl2.alpha == 0.3
    assert abs(vl2.value_state['safety'] - 0.42) < 1e-9
    assert abs(vl2.value_state['creativity'] - (-0.31)) < 1e-9
    assert vl2.values == VALUES


# ════════════════════════════════════════════════
# 测试 5: DriveMetabolism round-trip
# ════════════════════════════════════════════════


def test_drive_metabolism_round_trip():
    """DriveMetabolism snapshot/restore 后 frustration + _last_tick 一致。"""
    dm1 = DriveMetabolism(drives=DRIVES, clock=3.5)
    dm1.frustration['connection'] = 1.5
    dm1.time_metabolism(now=5.0)
    snap = dm1.snapshot()
    dm2 = DriveMetabolism(drives=DRIVES, clock=0.0)
    dm2.restore(snap)
    assert dm2.drives == DRIVES
    assert abs(dm2._last_tick - 5.0) < 1e-9
    assert dm2.frustration['connection'] > 0.0
    assert 'connection' in dm2.hunger_rates


# ════════════════════════════════════════════════
# 测试 6: HawkingDecay round-trip
# ════════════════════════════════════════════════


def test_hawking_round_trip():
    """HawkingDecay snapshot/restore 含嵌套 content dict 全等，且独立。"""
    hk1 = HawkingDecay(gamma=0.01)
    hk1.insert(content={'epoch': 1, 'critic_context': {'safety': 0.5}}, weight=1.0, now=1.0)
    hk1.insert(content={'epoch': 2, 'critic_context': {'safety': 0.7}}, weight=0.8, now=2.0)
    snap = hk1.snapshot()
    hk2 = HawkingDecay(gamma=0.05)
    hk2.restore(snap)
    assert abs(hk2.gamma - 0.01) < 1e-9
    assert len(hk2.memory) == 2
    assert hk2.memory[0]['content']['critic_context']['safety'] == 0.5
    assert abs(hk2.memory[1]['weight'] - 0.8) < 1e-9
    # 独立性
    hk1.insert(content={'epoch': 99}, weight=1.0, now=99.0)
    assert len(hk2.memory) == 2


# ════════════════════════════════════════════════
# 测试 7: MemoryCrystallizer round-trip
# ════════════════════════════════════════════════


def test_crystallizer_round_trip():
    """MemoryCrystallizer snapshot/restore 2 memories + vec 全等。"""
    cr1 = MemoryCrystallizer(n_dims=11)
    cr1.insert_or_merge(vec=[0.1] * 11, weight=1.0)
    cr1.insert_or_merge(vec=[0.2] * 11, weight=1.0)
    snap = cr1.snapshot()
    cr2 = MemoryCrystallizer(n_dims=11)
    cr2.restore(snap)
    assert cr2.n_dims == 11
    assert len(cr2.memories) == 2
    assert len(cr2.memories[0]['vec']) == 11
    assert abs(cr2.memories[0]['vec'][0] - 0.1) < 1e-9


# ════════════════════════════════════════════════
# 测试 1: Agent round-trip（compute_signals 一致）
# ════════════════════════════════════════════════


def test_agent_round_trip_compute_signals_consistent():
    """Agent snapshot → JSON → restore → compute_signals 必须一致（≤1e-9）。"""
    agent1 = _make_agent_with_state(seed=42)
    snap = agent1.snapshot()
    json_restored = json.loads(json.dumps(snap))

    vl2 = ValueLayer(values=VALUES, alpha=0.3)
    agent2 = Agent(seed=999, drives=DRIVES, value_layer=vl2, crystallize_every=10)
    agent2.restore(json_restored)
    agent1.restore(json_restored)

    ctx = _make_full_ctx()
    random.seed(42)
    s1 = agent1.compute_signals(ctx)
    random.seed(42)
    s2 = agent2.compute_signals(ctx)
    for k in SIGNALS:
        assert abs(s1[k] - s2[k]) < 1e-9, f"signal {k} drift: {s1[k]} vs {s2[k]}"


# ════════════════════════════════════════════════
# 测试 2: Agent NN weights 逐元素一致
# ════════════════════════════════════════════════


def test_agent_nn_weights_element_wise_consistent():
    """Agent snapshot 后 W1/W2/b1/b2 逐元素一致。"""
    agent1 = _make_agent_with_state(seed=42)
    snap = agent1.snapshot()
    json_restored = json.loads(json.dumps(snap))

    vl2 = ValueLayer(values=VALUES, alpha=0.3)
    agent2 = Agent(seed=999, drives=DRIVES, value_layer=vl2, crystallize_every=10)
    agent2.restore(json_restored)

    assert len(agent2.W1) == len(agent1.W1) == HIDDEN_SIZE
    assert len(agent2.W2) == len(agent1.W2) == N_SIGNALS
    for i in range(HIDDEN_SIZE):
        for j in range(agent1.INPUT_SIZE):
            assert abs(agent2.W1[i][j] - agent1.W1[i][j]) < 1e-9
    for i in range(N_SIGNALS):
        assert abs(agent2.b2[i] - agent1.b2[i]) < 1e-9


# ════════════════════════════════════════════════
# 测试 3: Agent recurrent_state 独立
# ════════════════════════════════════════════════


def test_agent_recurrent_state_isolated_after_restore():
    """Agent snapshot 后两个实例 recurrent_state 独立。"""
    agent1 = _make_agent_with_state(seed=42)
    snap = agent1.snapshot()
    json_restored = json.loads(json.dumps(snap))

    vl2 = ValueLayer(values=VALUES, alpha=0.3)
    agent2 = Agent(seed=999, drives=DRIVES, value_layer=vl2, crystallize_every=10)
    agent2.restore(json_restored)
    agent1.restore(json_restored)

    # 修改 agent1 的 recurrent_state 不应影响 agent2
    agent1.recurrent_state[0] = 999.0
    assert agent2.recurrent_state[0] != 999.0


# ════════════════════════════════════════════════
# 测试 8: restore strict 缺字段 → SnapshotError
# ════════════════════════════════════════════════


def test_restore_strict_missing_field_raises_snapshot_error():
    """Agent.restore 缺字段（recurrent_state）必须抛 SnapshotError。"""
    agent = _make_agent_with_state(seed=42)
    snap = agent.snapshot()
    snap_bad = dict(snap)
    del snap_bad['recurrent_state']

    agent_bad = Agent(seed=1, drives=DRIVES, crystallize_every=10)
    with pytest.raises(SnapshotError) as excinfo:
        agent_bad.restore(snap_bad)
    assert 'recurrent_state' in str(excinfo.value)


# ════════════════════════════════════════════════
# 测试 9: snapshot 不泄露 LLM/外部引用
# ════════════════════════════════════════════════


def test_snapshot_does_not_leak_llm_or_external_refs():
    """5 类 snapshot 均不含 llm / value_layer / hawking / crystallizer 字段。"""
    # 构造所有 snapshot
    vl = ValueLayer(values=VALUES, alpha=0.3)
    vl.value_state['safety'] = 0.42
    snap_vl = vl.snapshot()

    dm = DriveMetabolism(drives=DRIVES, clock=3.5)
    dm.time_metabolism(now=5.0)
    snap_dm = dm.snapshot()

    hk = HawkingDecay(gamma=0.01)
    hk.insert(content={'epoch': 1}, weight=1.0, now=1.0)
    snap_hk = hk.snapshot()

    cr = MemoryCrystallizer(n_dims=11)
    cr.insert_or_merge(vec=[0.1] * 11, weight=1.0)
    snap_cr = cr.snapshot()

    agent = Agent(seed=42, drives=DRIVES, value_layer=vl, crystallize_every=10)
    snap_agent = agent.snapshot()

    # 没有任何 snapshot 应包含 'llm' 字段
    for name, keys in [
        ('ValueLayer', set(snap_vl.keys())),
        ('DriveMetabolism', set(snap_dm.keys())),
        ('HawkingDecay', set(snap_hk.keys())),
        ('MemoryCrystallizer', set(snap_cr.keys())),
        ('Agent', set(snap_agent.keys())),
    ]:
        assert 'llm' not in keys, f"{name} snapshot 泄露 llm 字段"

    # Agent snapshot 不应有外部引用字段
    agent_keys = set(snap_agent.keys())
    assert 'value_layer' not in agent_keys
    assert 'hawking' not in agent_keys
    assert 'crystallizer' not in agent_keys