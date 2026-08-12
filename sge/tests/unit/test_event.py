"""sge.event pytest 单元测试 — LifeEvent / make_event_id / EventGenerator / generate_value_conflict。

Phase 3.2 conversion 第二批 2/4。
覆盖:
  1. LifeEvent dataclass + to_dict round-trip
  2. make_event_id 格式正确
  3. EVENT_TEMPLATES / VALUE_CONFLICT_TEMPLATES 完整性
  4. EventGenerator 30/70 概率分布
  5. value_conflict 触发逻辑
  6. 因果上下文构建
  7. _identify_value_strengths 边界（ValueLayer/dict/None/fallback）
  8. distribution_by_epoch 配置生效
  9. snapshot/restore round-trip（含 rng_state 保真）
  10. restore 缺字段抛 SnapshotError
"""

from __future__ import annotations

import random

import pytest

from sge.event import (
    LifeEvent,
    make_event_id,
    generate_value_conflict,
    EventGenerator,
    EVENT_TEMPLATES,
    VALUE_CONFLICT_TEMPLATES,
)


# ════════════════════════════════════════════════
# LifeEvent dataclass
# ════════════════════════════════════════════════


def test_life_event_dataclass_basic_construction():
    """LifeEvent dataclass 构造。"""
    event = LifeEvent(
        event_id='test-e0001-abc12345',
        event_type='success',
        description='完成了一项任务',
        intensity=0.7,
        value_challenges=['safety', 'creativity'],
        causal_context='前置: E0 success',
        timestamp=10.0,
        epoch=1,
    )
    assert event.event_id == 'test-e0001-abc12345'
    assert event.event_type == 'success'
    assert event.intensity == 0.7


def test_life_event_to_dict_round_trip():
    """LifeEvent.to_dict 字段完整 + 可重建。"""
    event = LifeEvent(
        event_id='test-e0001-abc12345',
        event_type='relationship',
        description='与朋友深入交流',
        intensity=0.8,
        value_challenges=['connection'],
        causal_context='前置: E0 success',
        timestamp=20.0,
        epoch=5,
    )
    d = event.to_dict()
    assert d['event_id'] == 'test-e0001-abc12345'
    assert d['event_type'] == 'relationship'
    assert d['description'] == '与朋友深入交流'
    assert d['intensity'] == 0.8
    assert d['value_challenges'] == ['connection']
    # 重建
    event2 = LifeEvent(**d)
    assert event2 == event


def test_life_event_to_dict_copies_list():
    """to_dict 复制 value_challenges 列表（避免外部修改污染）。"""
    challenges = ['safety', 'creativity']
    event = LifeEvent(
        event_id='x', event_type='risk', description='d',
        intensity=0.5, value_challenges=challenges,
        causal_context='c', timestamp=0.0,
    )
    d = event.to_dict()
    d['value_challenges'].append('connection')
    # 原 event 不受影响
    assert len(event.value_challenges) == 2


def test_make_event_id_format():
    """make_event_id 格式: "{baby_id}-e{epoch:04d}-{uuid8}"。"""
    eid = make_event_id('alice', 1)
    assert eid.startswith('alice-e0001-')
    assert len(eid.split('-')[-1]) == 8  # uuid8 hex


def test_make_event_id_unique_across_calls():
    """同 epoch 同 baby_id 调用 → UUID 不同 → event_id 不同。"""
    ids = {make_event_id('alice', 1) for _ in range(100)}
    assert len(ids) == 100  # 全部唯一


def test_make_event_id_zero_padding():
    """epoch < 10 时 0 填充到 4 位。"""
    eid = make_event_id('b', 5)
    assert 'e0005' in eid


# ════════════════════════════════════════════════
# 模板完整性
# ════════════════════════════════════════════════


def test_event_templates_covers_six_types():
    """EVENT_TEMPLATES 覆盖 success/failure/relationship/exploration/risk 5 种常规类型。"""
    assert 'success' in EVENT_TEMPLATES
    assert 'failure' in EVENT_TEMPLATES
    assert 'relationship' in EVENT_TEMPLATES
    assert 'exploration' in EVENT_TEMPLATES
    assert 'risk' in EVENT_TEMPLATES


def test_event_templates_each_type_has_multiple():
    """每个常规类型至少 3 个模板（多样性）。"""
    for etype, templates in EVENT_TEMPLATES.items():
        assert len(templates) >= 3, f"{etype} only has {len(templates)} templates"


def test_value_conflict_templates_covers_ten_pairs():
    """VALUE_CONFLICT_TEMPLATES 覆盖 10 对 value 组合。"""
    assert len(VALUE_CONFLICT_TEMPLATES) >= 10


def test_value_conflict_templates_each_pair_has_descriptions():
    """每对 value 组合至少 1 个模板。"""
    for pair, templates in VALUE_CONFLICT_TEMPLATES.items():
        assert len(templates) >= 1, f"{pair} has no templates"


# ════════════════════════════════════════════════
# generate_value_conflict
# ════════════════════════════════════════════════


def test_generate_value_conflict_basic():
    """generate_value_conflict 产出 LifeEvent(value_conflict, intensity [0.7, 1.0])。"""
    rng = random.Random(42)
    event = generate_value_conflict(
        challenge_value='safety',
        alternative_value='connection',
        event_id='e1',
        epoch=1,
        timestamp=10.0,
        rng=rng,
    )
    assert event.event_type == 'value_conflict'
    assert 0.7 <= event.intensity <= 1.0
    assert 'safety' in event.value_challenges
    assert 'connection' in event.value_challenges


def test_generate_value_conflict_bidirectional_lookup():
    """(a, b) 与 (b, a) 都查得到（双向 fallback）。"""
    rng = random.Random(42)
    e1 = generate_value_conflict('safety', 'connection', 'e1', 1, 0.0, rng)
    rng2 = random.Random(42)
    e2 = generate_value_conflict('connection', 'safety', 'e2', 1, 0.0, rng2)
    # 同 seed 同模板 → 描述应相同
    assert e1.description == e2.description


def test_generate_value_conflict_unknown_pair_fallback():
    """未知 value 对 → 通用冲突模板。"""
    rng = random.Random(42)
    event = generate_value_conflict(
        challenge_value='unknown_v1',
        alternative_value='unknown_v2',
        event_id='e1',
        epoch=1,
        timestamp=10.0,
        rng=rng,
    )
    assert event.event_type == 'value_conflict'
    # description 应包含两个 value 名
    assert 'unknown_v1' in event.description
    assert 'unknown_v2' in event.description


# ════════════════════════════════════════════════
# EventGenerator
# ════════════════════════════════════════════════


def test_event_generator_initialization():
    """EventGenerator 初始化。"""
    eg = EventGenerator(baby_id='alice', seed=42)
    assert eg.baby_id == 'alice'
    assert eg.value_conflict_prob == 0.3  # DESIGN §2.2 默认
    assert len(eg) == 0


def test_event_generator_generate_event_basic():
    """generate 返回 LifeEvent 且 history 增长。"""
    eg = EventGenerator(baby_id='alice', seed=42)
    event = eg.generate(epoch=0)
    assert isinstance(event, LifeEvent)
    assert len(eg) == 1


def test_event_generator_history_grows():
    """连续 generate → history 长度递增。"""
    eg = EventGenerator(baby_id='alice', seed=42)
    for i in range(5):
        eg.generate(epoch=i)
    assert len(eg) == 5


def test_event_generator_event_id_uses_baby_id_and_epoch():
    """event_id 包含 baby_id + epoch。"""
    eg = EventGenerator(baby_id='alice', seed=42)
    event = eg.generate(epoch=42)
    assert event.event_id.startswith('alice-e0042-')


def test_event_generator_value_conflict_requires_value_vector():
    """value_vector=None 时不触发 value_conflict（即使概率命中）。"""
    eg = EventGenerator(baby_id='alice', seed=42, value_conflict_prob=1.0)
    event = eg.generate(epoch=0, value_vector=None)
    # value_vector=None → 不会触发 value_conflict
    assert event.event_type != 'value_conflict'


def test_event_generator_value_conflict_triggered_with_prob_1():
    """value_conflict_prob=1.0 + value_vector 存在 → 必定触发 value_conflict。"""
    eg = EventGenerator(baby_id='alice', seed=42, value_conflict_prob=1.0)
    vl = {'safety': 0.8, 'connection': -0.5, 'creativity': 0.0,
          'autonomy': 0.0, 'justice': 0.0, 'compassion': 0.0}
    event = eg.generate(epoch=0, value_vector=vl)
    assert event.event_type == 'value_conflict'


def test_event_generator_routine_event_with_prob_0():
    """value_conflict_prob=0.0 → 只产生常规事件。"""
    eg = EventGenerator(baby_id='alice', seed=42, value_conflict_prob=0.0)
    vl = {'safety': 0.8, 'connection': -0.5}
    for i in range(20):
        event = eg.generate(epoch=i, value_vector=vl)
        assert event.event_type != 'value_conflict'
        assert event.event_type in ('success', 'failure', 'relationship',
                                     'exploration', 'risk')


def test_event_generator_identify_value_strengths_from_value_layer():
    """_identify_value_strengths 接受 ValueLayer-like 对象。"""
    class FakeVL:
        def __init__(self, vs):
            self.value_state = vs
    eg = EventGenerator(baby_id='alice', seed=42)
    strongest, weakest = eg._identify_value_strengths(
        FakeVL({'safety': 0.8, 'connection': -0.5, 'creativity': 0.3})
    )
    assert strongest == 'safety'
    assert weakest == 'connection'


def test_event_generator_identify_value_strengths_from_dict():
    """_identify_value_strengths 接受 dict。"""
    eg = EventGenerator(baby_id='alice', seed=42)
    strongest, weakest = eg._identify_value_strengths(
        {'a': 1.0, 'b': -1.0, 'c': 0.0}
    )
    assert strongest == 'a'
    assert weakest == 'b'


def test_event_generator_identify_value_strengths_fallback():
    """空 value_vector → fallback ('safety', 'connection')。"""
    eg = EventGenerator(baby_id='alice', seed=42)
    strongest, weakest = eg._identify_value_strengths({})
    assert strongest == 'safety'
    assert weakest == 'connection'


def test_event_generator_causal_context_empty_history():
    """空 history → causal_context = "初始事件，暂无历史因果"。"""
    eg = EventGenerator(baby_id='alice', seed=42)
    ctx = eg._build_causal_context()
    assert '初始' in ctx


def test_event_generator_causal_context_includes_recent():
    """非空 history → causal_context 引用最近 N 个事件。"""
    eg = EventGenerator(baby_id='alice', seed=42)
    eg.generate(epoch=0)
    eg.generate(epoch=1)
    eg.generate(epoch=2)
    ctx = eg._build_causal_context()
    assert '前置事件' in ctx


def test_event_generator_distribution_by_epoch():
    """distribution_by_epoch 配置生效。"""
    distribution = {0: {'success': 1.0, 'failure': 0.0, 'relationship': 0.0,
                         'exploration': 0.0, 'risk': 0.0}}
    eg = EventGenerator(
        baby_id='alice', seed=42, value_conflict_prob=0.0,
        distribution_by_epoch=distribution,
    )
    # 跑 10 epoch，0~9 都匹配 distribution 的 epoch=0 配置
    types = [eg.generate(epoch=i).event_type for i in range(10)]
    # 全 success（配置中 success=1.0）
    assert all(t == 'success' for t in types), f"got {types}"


def test_event_generator_distribution_by_epoch_uses_latest_key():
    """distribution_by_epoch 用最大 key ≤ epoch 的配置。"""
    distribution = {0: {'success': 1.0, 'failure': 0.0, 'relationship': 0.0,
                         'exploration': 0.0, 'risk': 0.0},
                    10: {'failure': 1.0, 'success': 0.0, 'relationship': 0.0,
                         'exploration': 0.0, 'risk': 0.0}}
    eg = EventGenerator(
        baby_id='alice', seed=42, value_conflict_prob=0.0,
        distribution_by_epoch=distribution,
    )
    # epoch=5 → 用 epoch=0 配置（success=1.0）
    assert eg.generate(epoch=5).event_type == 'success'
    # epoch=15 → 用 epoch=10 配置（failure=1.0）
    assert eg.generate(epoch=15).event_type == 'failure'


def test_event_generator_distribution_empty_or_zero_weights():
    """空分布或全 0 weights → fallback 均匀分布（不报错）。"""
    eg = EventGenerator(
        baby_id='alice', seed=42, value_conflict_prob=0.0,
        distribution_by_epoch={0: {}},
    )
    # 不报错即可
    event = eg.generate(epoch=0)
    assert event.event_type in ('success', 'failure', 'relationship',
                                 'exploration', 'risk')


def test_event_generator_distribution_filters_unknown_types():
    """distribution 包含未知类型 → 过滤后均匀采样。"""
    distribution = {0: {'success': 1.0, 'unknown_type': 1.0}}
    eg = EventGenerator(
        baby_id='alice', seed=42, value_conflict_prob=0.0,
        distribution_by_epoch=distribution,
    )
    event = eg.generate(epoch=0)
    assert event.event_type == 'success'  # unknown_type 被过滤


def test_event_generator_reset():
    """reset 清空 history + clock。"""
    eg = EventGenerator(baby_id='alice', seed=42)
    eg.generate(epoch=0)
    eg.generate(epoch=1)
    assert len(eg) == 2
    eg.reset()
    assert len(eg) == 0
    assert eg._clock == 0.0


# ════════════════════════════════════════════════
# Snapshot 协议
# ════════════════════════════════════════════════


def test_event_generator_snapshot_basic_fields():
    """snapshot 包含 _SNAPSHOT_FIELDS 全部字段。"""
    eg = EventGenerator(baby_id='alice', seed=42)
    eg.generate(epoch=0)
    snap = eg.snapshot()
    assert snap['baby_id'] == 'alice'
    assert snap['value_conflict_prob'] == 0.3
    assert 'event_history' in snap
    assert '_clock' in snap
    assert 'rng_state' in snap


def test_event_generator_snapshot_round_trip_preserves_rng_state():
    """snapshot/restore 后 rng 序列完全一致（精确保真）。

    snapshot 保存的是"当前 state"；restore 后 rng 处于这一 state。
    因此 restore 之后调用的 random() 等价于 snapshot 之前没调用的下一次 random()。
    """
    eg1 = EventGenerator(baby_id='alice', seed=42)
    val1_before = eg1.rng.random()  # 第 1 个 rng 值
    val2_before = eg1.rng.random()  # 第 2 个 rng 值
    # snapshot 之前：consumed 2 次；state 处于第 3 次的入口
    snap = eg1.snapshot()

    eg2 = EventGenerator(baby_id='bob', seed=999)  # 不同 seed
    eg2.restore(snap)
    # restore 后：state 与 eg1 一致；下一个 random() = eg1 在 snapshot 时的下一个
    val1_after = eg2.rng.random()
    val2_after = eg2.rng.random()
    # eg1 继续跑一次 random() 应当等于 val1_after（snapshot 后的下一个）
    val3_eg1 = eg1.rng.random()
    assert abs(val3_eg1 - val1_after) < 1e-9, \
        f"rng state drift: {val3_eg1} vs {val1_after}"
    assert abs(val2_after - eg1.rng.random()) < 1e-9


def test_event_generator_snapshot_json_serializable():
    """snapshot dict JSON 序列化无报错（rng_state 必须是 JSON-friendly）。"""
    import json
    eg = EventGenerator(baby_id='alice', seed=42)
    eg.generate(epoch=0)
    snap = eg.snapshot()
    json.dumps(snap)  # 不抛异常


def test_event_generator_snapshot_includes_event_history():
    """snapshot 包含 event_history（含 LifeEvent dict 展开）。"""
    eg = EventGenerator(baby_id='alice', seed=42)
    eg.generate(epoch=0)
    eg.generate(epoch=1)
    snap = eg.snapshot()
    assert len(snap['event_history']) == 2
    assert snap['event_history'][0]['epoch'] == 0
    assert 'event' in snap['event_history'][0]
    assert 'event_type' in snap['event_history'][0]['event']


def test_event_generator_snapshot_includes_distribution():
    """snapshot 保留 distribution_by_epoch 配置。"""
    distribution = {0: {'success': 1.0}}
    eg = EventGenerator(
        baby_id='alice', seed=42,
        distribution_by_epoch=distribution,
    )
    snap = eg.snapshot()
    assert snap['distribution_by_epoch'] is not None
    assert 0 in snap['distribution_by_epoch']
    assert snap['distribution_by_epoch'][0]['success'] == 1.0


def test_event_generator_snapshot_none_distribution_serialized_as_none():
    """distribution_by_epoch=None → snapshot 中为 None。"""
    eg = EventGenerator(baby_id='alice', seed=42)
    snap = eg.snapshot()
    assert snap['distribution_by_epoch'] is None


def test_event_generator_restore_strict_missing_field_raises():
    """restore 缺关键字段抛 SnapshotError。"""
    from sge.baseline import SnapshotError
    eg = EventGenerator(baby_id='alice', seed=42)
    snap = eg.snapshot()
    del snap['baby_id']
    with pytest.raises(SnapshotError, match='baby_id'):
        eg.restore(snap)


def test_event_generator_restore_rebuilds_history():
    """restore 重建 event_history 为 [(epoch, LifeEvent), ...]。"""
    eg1 = EventGenerator(baby_id='alice', seed=42)
    eg1.generate(epoch=0)
    eg1.generate(epoch=1)
    snap = eg1.snapshot()

    eg2 = EventGenerator(baby_id='alice', seed=42)
    eg2.restore(snap)
    assert len(eg2) == 2
    assert eg2.event_history[0][0] == 0  # epoch
    assert isinstance(eg2.event_history[0][1], LifeEvent)


def test_event_generator_serialize_rng_state_handles_none_gauss_next():
    """_serialize_rng_state 处理 gauss_next=None（未调用过 gauss）。"""
    import random
    rng = random.Random(0)
    state = rng.getstate()
    # 重新创建一个新 Random 触发 rng state 内部结构
    serialized = EventGenerator._serialize_rng_state(state)
    assert isinstance(serialized, list)
    assert len(serialized) == 3


def test_event_generator_deserialize_rng_state_handles_none_gauss_next():
    """_deserialize_rng_state 处理 gauss_next=None。"""
    from sge.event import EventGenerator
    serialized = [3, list(range(625)), None]
    state = EventGenerator._deserialize_rng_state(serialized)
    assert len(state) == 3
    assert state[2] == 0.0  # None → 0.0


def test_event_generator_init_with_clock():
    """clock 参数初始化 _clock。"""
    eg = EventGenerator(baby_id='alice', seed=42, clock=10.0)
    assert eg._clock == 10.0


def test_event_generator_init_clock_default_zero():
    """clock=None 默认 0.0。"""
    eg = EventGenerator(baby_id='alice', seed=42)
    assert eg._clock == 0.0