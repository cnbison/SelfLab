"""
M2.3 补充 — Hawking 1000h 衰减深度分析

输入：M2.2 的 timeseries 数据（3 baby × 24 采样点 × hawking_size/min_weight）
输出：衰减曲线 + 删除记忆数 + 重要 bug 发现

关键发现：
  1. Hawking 衰减在 M2.2 中几乎没发生（unit mismatch bug）
  2. Chunk 模式导致 Hawking 状态不连续（每个 chunk 新实例）
  3. 设计预期 vs 实测对比

用法：
  python m23_hawking_decay_analysis.py
"""

import json
import sys
import math
from pathlib import Path


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "m22_triplets"


def expected_decay(gamma: float, total_hours: float) -> float:
    """设计预期 weight: exp(-γ * total_hours)"""
    return math.exp(-gamma * total_hours)


def analyze_baby(baby: str) -> dict:
    """分析一个 baby 的 Hawking 数据"""
    path = OUTPUT_DIR / f"{baby}_result.json"
    if not path.exists():
        return {'error': f'{path} not found'}

    with open(path) as f:
        result = json.load(f)

    ts = result.get('timeseries', [])
    if not ts:
        return {'error': f'{baby}: no timeseries'}

    # ── Hawking size growth ──
    size_curve = [(row['epoch'] + 1, row['hawking_size']) for row in ts]
    min_weight_curve = [(row['epoch'] + 1, row.get('hawking_min_weight', 0)) for row in ts]

    # ── 理论预期 vs 实测 ──
    gamma = 0.01
    total_epochs = max(epoch for epoch, _ in size_curve)
    total_hours_designed = total_epochs * 1.0  # 1 hour per epoch (设计意图)
    total_hours_actual = total_epochs * (1.0 / 3600.0)  # 实际（unit bug）

    weight_expected_designed = expected_decay(gamma, total_hours_designed)
    weight_expected_actual = expected_decay(gamma, total_hours_actual)

    # ── 实测 final state ──
    final_size = result['hawking_final_size']
    final_min_weight = min_weight_curve[-1][1] if min_weight_curve else 0

    # ── 设计 vs 实测 ──
    # 设计：1000h 后 memory weight 应该 = exp(-10) ≈ 4.5e-5
    # 应该删除所有 1000 之前的 memory（除最近 ~921 之内）
    # 实测：几乎不删除（weight ≈ 0.997）

    return {
        'baby': baby,
        'gamma': gamma,
        'total_epochs': total_epochs,
        'total_hours_designed': total_hours_designed,
        'weight_expected_designed': weight_expected_designed,
        'total_hours_actual_unit_bug': total_hours_actual,
        'weight_expected_actual': weight_expected_actual,
        'final_hawking_size': final_size,
        'final_min_weight': final_min_weight,
        'expected_size_designed': 'should retain last ~921 memories',
        'actual_size': final_size,
        'size_curve': size_curve,
        'min_weight_curve': min_weight_curve,
        'bug_finding_1_unit_mismatch': {
            'description': 'timestamp 在 epoch 单位，但 /3600 当成秒处理',
            'impact': f'decay_factor/epoch = exp(-0.01 × 1/3600) ≈ 0.999997',
            'expected_factor': 'exp(-0.01 × 1) = 0.99 (设计意图)',
        },
        'bug_finding_2_chunk_reset': {
            'description': '每个 chunk 独立 Python 进程，Hawking 实例不连续',
            'impact': 'final hawking_size=250 是 chunk 3 内部累积，不是 1000 epoch 累积',
            'evidence': 'observed hawking_size 在 chunk 边界 (250/500/750) 突降',
        },
    }


def main() -> int:
    print("=" * 60)
    print("  M2.3 — Hawking 1000h 衰减深度分析")
    print("=" * 60)
    print()

    babies = ['encouraged', 'challenged', 'uncertain']
    results = {}

    for baby in babies:
        print(f"  分析 {baby}...")
        r = analyze_baby(baby)
        if 'error' in r:
            print(f"    ✗ {r['error']}")
            continue
        results[baby] = r

        print(f"    总 epoch: {r['total_epochs']}")
        print(f"    最终 hawking_size: {r['final_hawking_size']}")
        print(f"    最终最小 weight: {r['final_min_weight']:.6f}")
        print(f"    设计预期 weight (1000h): {r['weight_expected_designed']:.2e}")
        print(f"    设计预期 weight (unit-bug): {r['weight_expected_actual']:.6f}")
        print()

    # ── 跨 baby 对比 ──
    print(f"{'─'*60}")
    print(f"  Hawking 衰减跨 baby 对比")
    print(f"{'─'*60}\n")

    print(f"{'Baby':<14} {'final_size':<12} {'min_weight':<14} {'设计预期':<15}")
    for baby, r in results.items():
        print(f"{baby:<14} {r['final_hawking_size']:<12} "
              f"{r['final_min_weight']:<14.6f} "
              f"{r['weight_expected_designed']:<15.2e}")

    # ── Bug 影响分析 ──
    print(f"\n{'─'*60}")
    print(f"  ⚠ 重大 bug 发现")
    print(f"{'─'*60}\n")

    print(f"  Bug 1: Timestamp unit mismatch")
    print(f"    代码: delta_hours = (now - _last_tick) / 3600")
    print(f"    问题: timestamp = epoch (单位=epoch), 不是秒")
    print(f"    实际: delta_hours = 1/3600 ≈ 2.78e-4 hours/epoch")
    print(f"    设计: delta_hours = 1 hour/epoch")
    print(f"    后果: decay_factor 0.999997/epoch (而非 0.99/epoch)")
    print(f"    影响: 1000h 后 weight 应 = 4.5e-5，实际 = 0.997 (几乎没衰减)")
    print()
    print(f"  Bug 2: Hawking 状态不跨 chunk 连续")
    print(f"    代码: 每个 chunk 独立 Python 进程 → 新 HawkingDecay()")
    print(f"    问题: 状态在 chunk 边界 (epoch 250/500/750) 完全丢失")
    print(f"    后果: final_hawking_size=250 只是 chunk 3 内部累积")
    print(f"    影响: 无法观测完整 1000 epoch 的衰减曲线")
    print()

    # ── 推荐修复 ──
    print(f"{'─'*60}")
    print(f"  推荐修复")
    print(f"{'─'*60}\n")
    print(f"  Bug 1 (unit): 在 _sge_baseline.py HawkingDecay.tick() 改:")
    print(f"    delta_hours = max(0.0, (now - self._last_tick))  # 去掉 /3600")
    print(f"    或 timestamp 在 orchestrator 改为 epoch * 3600 (转秒)")
    print()
    print(f"  Bug 2 (chunk reset): 短期 — 序列化 Hawking 状态到 checkpoint")
    print(f"    长期 — 不 chunk，单次跑完（需要 server 稳定性保障）")
    print()

    # ── 写输出 ──
    output_path = OUTPUT_DIR / "hawking_decay_analysis.json"
    output_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False, default=str),
        encoding='utf-8',
    )
    print(f"  状态快照: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
