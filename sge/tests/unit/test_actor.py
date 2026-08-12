"""sge.actor pytest 单元测试 — stub_actor_express 的 8 条规则 + 字段结构。

Phase 3.2 conversion 2/N。
"""

from __future__ import annotations

import pytest

from sge.actor import (
    stub_actor_express,
    ActorOutput,
    BEHAVIOR_LABELS,
)


BASE_SIGNALS = {
    'directness': 0.5, 'vulnerability': 0.5, 'playfulness': 0.5,
    'initiative': 0.5, 'depth': 0.5, 'warmth': 0.5,
    'defiance': 0.5, 'curiosity': 0.5,
}


@pytest.mark.parametrize("signals,expected,label", [
    ({**BASE_SIGNALS, 'initiative': 0.7}, '主动引导', 'initiative 高'),
    ({**BASE_SIGNALS, 'warmth': 0.7}, '关怀回应', 'warmth 高'),
    ({**BASE_SIGNALS, 'playfulness': 0.7}, '玩闹撒娇', 'playfulness 高'),
    ({**BASE_SIGNALS, 'curiosity': 0.7, 'depth': 0.6}, '深度提问', 'curiosity + depth 高'),
    ({**BASE_SIGNALS, 'defiance': 0.7}, '反抗嘴硬', 'defiance 高'),
    ({**BASE_SIGNALS, 'vulnerability': 0.7}, '袒露脆弱', 'vulnerability 高'),
    ({**BASE_SIGNALS, 'directness': 0.2}, '委婉暗示', 'directness 低'),
    ({**BASE_SIGNALS, 'playfulness': 0.2, 'depth': 0.7}, '认真严肃', 'playfulness 低 + depth 高'),
    ({k: 0.2 for k in BASE_SIGNALS}, '沉默不语', '全部低'),
    ({**BASE_SIGNALS, 'initiative': 0.5, 'warmth': 0.5}, '敷衍回应', '全部中等'),
])
def test_stub_actor_express_behavior_selection(signals, expected, label):
    out = stub_actor_express(signals=signals, value_vector={'safety': 0.5}, seed=42)
    assert out.behavior_label == expected, f"[{label}] got {out.behavior_label}"


def test_stub_actor_express_field_structure():
    out = stub_actor_express(signals=BASE_SIGNALS, value_vector={'safety': 0.5}, seed=42)
    assert out.inner_monologue is not None
    assert out.behavior_label in BEHAVIOR_LABELS
    assert out.intention is not None
    assert 0.0 <= out.confidence <= 1.0


def test_stub_actor_express_to_dict_serialization():
    out = stub_actor_express(signals=BASE_SIGNALS, value_vector={'safety': 0.5}, seed=42)
    d = out.to_dict()
    assert set(d.keys()) == {'inner_monologue', 'behavior_label', 'intention', 'confidence'}


def test_stub_actor_express_handles_missing_signal_fields():
    """signals 缺字段时使用默认值 0.5。"""
    out = stub_actor_express(signals={}, value_vector=None, seed=0)
    assert out.behavior_label in BEHAVIOR_LABELS
    assert 0.0 <= out.confidence <= 1.0


def test_stub_actor_express_confidence_clamped_to_valid_range():
    """极端信号值下 confidence 仍在 [0.1, 1.0]。"""
    # dominant signal = 1.0 → confidence = 0.5 + 0.5 * (1.0 - 0.5) = 0.75
    out_high = stub_actor_express(signals={**BASE_SIGNALS, 'warmth': 1.0}, seed=0)
    assert 0.1 <= out_high.confidence <= 1.0
    # dominant signal = 0.4 (低于 0.4 阈值时全部低分支触发；选 0.45 测试中间值)
    out_mid = stub_actor_express(signals={**BASE_SIGNALS, 'warmth': 0.45}, seed=0)
    assert 0.1 <= out_mid.confidence <= 1.0


def test_actor_output_dataclass_default_values():
    """ActorOutput dataclass 字段默认值合理性（即使 stub_actor 不调用也安全）。"""
    a = ActorOutput(inner_monologue='', behavior_label='敷衍回应', intention='', confidence=0.5)
    assert a.behavior_label == '敷衍回应'


def test_bhavior_labels_includes_all_required_categories():
    """BEHAVIOR_LABELS 集合完整性。"""
    required = {'主动引导', '关怀回应', '玩闹撒娇', '深度提问', '反抗嘴硬',
                '袒露脆弱', '委婉暗示', '认真严肃', '沉默不语', '敷衍回应'}
    assert required.issubset(set(BEHAVIOR_LABELS))