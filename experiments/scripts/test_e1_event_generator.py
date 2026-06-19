"""
E1 单元测试 — EventGenerator distribution_by_epoch 配置

5 项硬性测试：
1. distribution=None → 与原行为一致（uniform random）
2. distribution 全 success → 100% success
3. distribution 跨 epoch 边界（epoch_1_to_19 → epoch_20_to_29）→ 在 epoch 20 切换
4. weights 总和不为 1 → 自动归一化
5. value_conflict_prob 仍然生效（不受 distribution 影响）

运行：python test_e1_event_generator.py
预期：5/5 PASS
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _sge_event import EventGenerator


def test_1_distribution_none_unchanged():
    """distribution=None → 行为与 M2.1 一致（70% 均匀随机 5 种常规事件）"""
    gen = EventGenerator(baby_id='test', seed=42, distribution_by_epoch=None)

    # 跑 1000 个 event，统计常规事件类型分布（不含 value_conflict）
    types = []
    for i in range(1000):
        event = gen.generate(epoch=i, value_vector={'a': 0.5, 'b': 0.5})
        if event.event_type != 'value_conflict':
            types.append(event.event_type)

    # 5 种常规事件应该大致均匀（每种 ~20%）
    counts = Counter(types)
    assert len(counts) == 5, f"expected 5 types, got {len(counts)}"
    for t in ['success', 'failure', 'relationship', 'exploration', 'risk']:
        ratio = counts[t] / len(types)
        assert 0.10 < ratio < 0.30, f"{t} ratio {ratio:.2%} out of expected ~20%"

    return True, f"5 types balanced: {dict(counts)}"


def test_2_distribution_full_success():
    """distribution={success: 1.0} → 100% success（所有常规事件）"""
    gen = EventGenerator(
        baby_id='test',
        seed=42,
        distribution_by_epoch={1: {'success': 1.0}},
    )

    # 跑 1000 个 event
    regular_types = []
    for i in range(1000):
        event = gen.generate(epoch=i, value_vector={'a': 0.5, 'b': 0.5})
        if event.event_type != 'value_conflict':
            regular_types.append(event.event_type)

    # 所有常规事件都应该是 success
    counts = Counter(regular_types)
    assert counts['success'] == len(regular_types), \
        f"expected all success, got {dict(counts)}"
    assert len(counts) == 1, f"expected 1 type, got {len(counts)}"

    return True, f"{counts['success']}/{len(regular_types)} = 100% success"


def test_3_distribution_epoch_boundary():
    """跨 epoch 边界 → 在 epoch 20 切换分布"""
    gen = EventGenerator(
        baby_id='test',
        seed=42,
        value_conflict_prob=0.0,  # 关掉 value_conflict 排除干扰
        distribution_by_epoch={
            1: {'success': 1.0},    # epoch 1-19: 全 success
            20: {'failure': 1.0},   # epoch 20+: 全 failure
        },
    )

    early_types = []
    late_types = []
    for i in range(100):
        event = gen.generate(epoch=i, value_vector={'a': 0.5, 'b': 0.5})
        if i < 20:
            early_types.append(event.event_type)
        else:
            late_types.append(event.event_type)

    assert all(t == 'success' for t in early_types), \
        f"early (1-19) should be all success, got {set(early_types)}"
    assert all(t == 'failure' for t in late_types), \
        f"late (20+) should be all failure, got {set(late_types)}"

    return True, f"epoch 1-19: {len(early_types)} success; epoch 20+: {len(late_types)} failure"


def test_4_weights_not_normalized():
    """weights 总和不为 1（如 3.0）→ random.choices 自动归一化"""
    gen = EventGenerator(
        baby_id='test',
        seed=42,
        value_conflict_prob=0.0,
        distribution_by_epoch={
            1: {'success': 3.0, 'failure': 1.0},  # 总和 4.0，期望 success:failure = 3:1
        },
    )

    types = []
    for i in range(2000):
        event = gen.generate(epoch=i, value_vector={'a': 0.5, 'b': 0.5})
        types.append(event.event_type)

    counts = Counter(types)
    success_ratio = counts['success'] / len(types)
    failure_ratio = counts['failure'] / len(types)

    # 期望 ~75% success, ~25% failure（3:1）
    assert 0.70 < success_ratio < 0.80, \
        f"success ratio {success_ratio:.2%} not in [70%, 80%]"
    assert 0.20 < failure_ratio < 0.30, \
        f"failure ratio {failure_ratio:.2%} not in [20%, 30%]"

    return True, f"success:failure = {success_ratio:.1%}:{failure_ratio:.1%} (expect 3:1)"


def test_5_value_conflict_prob_still_works():
    """value_conflict_prob=0.5 → 50% value_conflict（不受 distribution 影响）"""
    gen = EventGenerator(
        baby_id='test',
        seed=42,
        value_conflict_prob=0.5,
        distribution_by_epoch={1: {'success': 1.0}},  # 即使全 success 配置
    )

    types = []
    for i in range(1000):
        event = gen.generate(epoch=i, value_vector={'a': 0.5, 'b': 0.5})
        types.append(event.event_type)

    counts = Counter(types)
    vc_ratio = counts['value_conflict'] / len(types)

    # 期望 ~50% value_conflict
    assert 0.45 < vc_ratio < 0.55, \
        f"value_conflict ratio {vc_ratio:.2%} not in [45%, 55%]"
    # 其余应该全是 success（distribution 生效）
    assert counts.get('success', 0) + counts['value_conflict'] == len(types), \
        f"only success + value_conflict expected, got {set(types)}"

    return True, f"value_conflict={vc_ratio:.1%}, success+vc=100%"


# ── 主入口 ────────────────────────────────────────


def main() -> int:
    tests = [
        ('1. distribution=None 行为一致', test_1_distribution_none_unchanged),
        ('2. distribution 全 success 100%', test_2_distribution_full_success),
        ('3. 跨 epoch 边界切换', test_3_distribution_epoch_boundary),
        ('4. weights 不归一自动归一化', test_4_weights_not_normalized),
        ('5. value_conflict_prob 独立生效', test_5_value_conflict_prob_still_works),
    ]

    print("=" * 60)
    print("  E1 单元测试 — EventGenerator distribution_by_epoch")
    print("=" * 60)
    print()

    passed = 0
    for label, test_fn in tests:
        try:
            ok, detail = test_fn()
            status = '✓' if ok else '✗'
            print(f'  {status} {label}')
            print(f'      {detail}')
            if ok:
                passed += 1
        except AssertionError as e:
            print(f'  ✗ {label}')
            print(f'      AssertionError: {e}')
        except Exception as e:
            print(f'  ✗ {label}')
            print(f'      {type(e).__name__}: {e}')

    print()
    print(f"  总体: {passed}/{len(tests)} {'PASS' if passed == len(tests) else 'FAIL'}")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
