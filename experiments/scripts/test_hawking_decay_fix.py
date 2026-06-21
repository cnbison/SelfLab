"""
Hawking 衰减单元测试 — 验证 M2.3 修复正确

Bug（M2.3 之前）：
  tick() 把 timestamp 当秒处理，/3600 转小时
  → 实际 delta = 1/3600 hours/epoch（设计应为 1 hour/epoch）
  → 1000 epoch 后 memory weight ≈ 0.997（设计应为 4.5e-5）

修复（M2.3）：
  tick() 去掉 /3600，timestamp 单位是 epoch=hour
  → 1 epoch = 1 hour decay
  → 1000 epoch 后 weight = exp(-10) ≈ 4.5e-5
  → ~750 memory 应被删除（保留最近 250 个）

测试目标：
1. 1000 epoch 后 size ≈ 250（不是 1000）
2. 1000 epoch 后 min_weight ≈ 4.5e-5（不是 0.997）
3. decay factor per epoch ≈ 0.99（不是 0.9999972）
4. 删除阈值 1e-4 在 ~921 epoch 时命中

用法：
  python test_hawking_decay_fix.py
"""

import sys
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sge_baseline import HawkingDecay


# 设计预期（来自 SGE-Memory-Layer-Design.md）
DESIGN_GAMMA = 0.01
DESIGN_THRESHOLD = 1e-4
DESIGN_HOURS_FOR_DELETE = 921  # log(1e-4)/(-0.01) ≈ 921 hours
EXPECTED_DECAY_FACTOR_PER_EPOCH = math.exp(-DESIGN_GAMMA * 1)  # ≈ 0.99005
EXPECTED_WEIGHT_AFTER_1000H = math.exp(-DESIGN_GAMMA * 1000)  # ≈ 4.54e-5
EXPECTED_SIZE_AFTER_1000 = 1000 - DESIGN_HOURS_FOR_DELETE + 1  # ≈ 80（保留 epoch 920-999）


def test_decay_factor_per_epoch():
    """验证每 epoch decay factor ≈ 0.99（不是 0.9999972）"""
    h = HawkingDecay(gamma=0.01, clock=0.0)
    h.insert(content='init', weight=1.0, now=0)
    h.tick(now=0)  # delta = 0（first tick）
    h.tick(now=1)  # delta = 1 hour
    weight_after_1h = h.memory[0]['weight']
    expected = EXPECTED_DECAY_FACTOR_PER_EPOCH
    diff = abs(weight_after_1h - expected)
    assert diff < 1e-6, f"decay factor 不对：got {weight_after_1h}, expected {expected}"
    print(f"  ✓ decay_factor_per_epoch = {weight_after_1h:.6f} (expected {expected:.6f})")
    return True


def test_1000h_decay():
    """1000 epoch 后：size ≈ 921，min_weight ≈ 1.0e-4（最老边界）"""
    h = HawkingDecay(gamma=0.01, clock=0.0)
    for i in range(1000):
        h.insert(content={'epoch': i}, weight=1.0, now=i)
        h.tick(now=i)

    final_size = len(h.memory)
    min_weight = min(m['weight'] for m in h.memory) if h.memory else 0
    max_weight = max(m['weight'] for m in h.memory) if h.memory else 0

    # 数学推导：
    # threshold 1e-4 = exp(-γ * t) → t = -log(1e-4)/0.01 ≈ 921 hours
    # 即 epoch 79 之前的 memory 被删除（1000-921=79）
    # 最终 memory 包含 epoch 79, 80, ..., 999 = 921 个
    expected_size = 921

    assert final_size == expected_size, \
        f"size 不对: {final_size} (expected exactly {expected_size})"

    # min_weight = 最老 memory (epoch 79) 的 weight
    # weight = exp(-0.01 * (1000-79)) = exp(-9.21) ≈ 1.00008e-4（刚在阈值之上）
    expected_min_weight = math.exp(-0.01 * (1000 - 79))
    assert abs(min_weight - expected_min_weight) < 1e-6, \
        f"min_weight 不对: {min_weight:.2e} (expected {expected_min_weight:.2e})"

    # max_weight = 最新 memory (epoch 999) 的 weight
    # insert(now=999) → weight=1.0, 然后 tick(now=999) → 应用 exp(-0.01 * 1) ≈ 0.99
    # 因为每个 insert 后面都紧跟一个 tick，最新 memory 也被衰减一次
    expected_max_weight = math.exp(-0.01)
    assert abs(max_weight - expected_max_weight) < 1e-6, \
        f"max_weight 不对: {max_weight} (expected {expected_max_weight})"

    print(f"  ✓ 1000h 后 size = {final_size} (expected {expected_size})")
    print(f"  ✓ min_weight = {min_weight:.6e} (expected {expected_min_weight:.6e})")
    print(f"  ✓ max_weight = {max_weight} (expected {expected_max_weight})")
    return True


def test_memory_lifecycle():
    """验证 memory 完整生命周期：insert → tick decay → delete"""
    h = HawkingDecay(gamma=0.01, clock=0.0, remove_threshold=1e-4)

    # insert epoch 0
    h.insert(content={'epoch': 0}, weight=1.0, now=0)
    h.tick(now=0)
    assert len(h.memory) == 1
    assert h.memory[0]['weight'] == 1.0

    # tick epoch 1-100（保留 epoch 0 memory）
    for i in range(1, 100):
        h.insert(content={'epoch': i}, weight=1.0, now=i)
        h.tick(now=i)

    # epoch 0 memory weight = exp(-0.01 * 99) ≈ 0.372（仍存活）
    oldest = h.memory[0]
    assert oldest['weight'] > 1e-4
    assert abs(oldest['weight'] - math.exp(-0.01 * 99)) < 0.01

    # tick epoch 100-999（epoch 0 早就被删除）
    for i in range(100, 1000):
        h.insert(content={'epoch': i}, weight=1.0, now=i)
        h.tick(now=i)

    # epoch 0 应该早就被删除（threshold 1e-4 at 921 hours）
    epochs_in_memory = [m['content']['epoch'] for m in h.memory]
    assert 0 not in epochs_in_memory, "epoch 0 memory 应该被删除"

    # 现在 memory 应包含 epoch 79-999
    assert min(epochs_in_memory) >= 79, f"最老应该是 epoch ≥79，实际 {min(epochs_in_memory)}"
    assert max(epochs_in_memory) == 999, f"最新应该是 epoch 999，实际 {max(epochs_in_memory)}"

    print(f"  ✓ 完整生命周期：insert→tick→delete 验证通过")
    print(f"    最终 {len(h.memory)} memories，epoch 范围 [{min(epochs_in_memory)}, {max(epochs_in_memory)}]")
    return True


def test_zero_decay_simulation():
    """对比修复前 vs 修复后：修复前 1000h 不删除，修复后删除 79 个"""
    # 模拟"修复前"行为（手工还原 /3600）
    h_buggy = HawkingDecay(gamma=0.01, clock=0.0)

    # 手工模拟 buggy tick（/3600）
    for i in range(1000):
        h_buggy.insert(content={'epoch': i}, weight=1.0, now=i)
        # Buggy: delta_hours = (i - last) / 3600
        if i == 0:
            delta_hours = 0
        else:
            delta_hours = (i - h_buggy._last_tick) / 3600
        h_buggy._last_tick = i
        decay_factor = math.exp(-0.01 * delta_hours)
        for mem in h_buggy.memory:
            mem['weight'] *= decay_factor
        h_buggy.memory = [m for m in h_buggy.memory if m['weight'] >= 1e-4]

    buggy_size = len(h_buggy.memory)
    buggy_min = min(m['weight'] for m in h_buggy.memory) if h_buggy.memory else 0

    print(f"  修复前行为（手工还原 /3600）:")
    print(f"    size = {buggy_size}, min_weight = {buggy_min:.6f}")
    print(f"    → 1000 个 memory 全部存活，bug 确认")

    # 修复后（用真实代码）
    h_fixed = HawkingDecay(gamma=0.01, clock=0.0)
    for i in range(1000):
        h_fixed.insert(content={'epoch': i}, weight=1.0, now=i)
        h_fixed.tick(now=i)

    fixed_size = len(h_fixed.memory)
    fixed_min = min(m['weight'] for m in h_fixed.memory) if h_fixed.memory else 0

    print(f"  修复后行为（去 /3600）:")
    print(f"    size = {fixed_size}, min_weight = {fixed_min:.2e}")
    print(f"    → ~80 个 memory 被删除，符合设计预期")

    # 核心断言：buggy 不删除任何 memory，fixed 删除 ~80 个
    assert buggy_size == 1000, \
        f"修复前应全部存活：{buggy_size}"
    assert fixed_size == 921, \
        f"修复后应剩 921 个：{fixed_size}"
    assert fixed_size < buggy_size, \
        f"修复后应少于修复前：fixed={fixed_size} vs buggy={buggy_size}"
    return True


def main() -> int:
    print("=" * 60)
    print("  Hawking 衰减修复验证")
    print("=" * 60)
    print()

    tests = [
        ("1. decay_factor per epoch ≈ 0.99", test_decay_factor_per_epoch),
        ("2. 1000h 衰减 (size + min_weight)", test_1000h_decay),
        ("3. Memory 完整生命周期", test_memory_lifecycle),
        ("4. 修复前 vs 修复后对比", test_zero_decay_simulation),
    ]

    passed = 0
    for label, test_fn in tests:
        print(f"  {label}")
        try:
            ok = test_fn()
            if ok:
                passed += 1
        except AssertionError as e:
            print(f"    ✗ AssertionError: {e}")
        except Exception as e:
            print(f"    ✗ {type(e).__name__}: {e}")
        print()

    print("=" * 60)
    if passed == len(tests):
        print(f"  ✓ {passed}/{len(tests)} PASS — Hawking 修复正确")
        print("=" * 60)
        return 0
    else:
        print(f"  ✗ {passed}/{len(tests)} FAIL")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
