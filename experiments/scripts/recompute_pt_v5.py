"""
P0-3 修复方案验证：PT 触发机制最小实验

目标：基于 v4 数据 + 模拟事件流，确定 PT 触发修复的最佳方案。

诊断回顾（M22_H_SELF_DIAGNOSIS.md §3）：
  - 现状：scalar `self._frustration` 在 success-heavy 流下永远 < 2.0
  - PT 触发数 = 0（v2/v3/v4 三轮一致）

候选方案：
  D. 降低 PHASE_THRESHOLD: 2.0 → 0.5（ad-hoc）
  E. 改用 drive-level frustration（探索 max > 阈值）
  F. 重设 frustration dynamics
  G. 新触发信号：H_self 长时间平台期 / |val| 高波动期

本脚本：
  1. 用 v4 数据验证当前 `_frustration` 行为（数学推导 + 反推）
  2. 评估方案 D/E/G 的预期触发数
  3. 推荐最佳方案
"""

import json
from pathlib import Path

V4_DIR = Path(__file__).resolve().parent.parent / "output" / "m22_v4_dedup"


def load_v4(baby: str = "encouraged", chunk_idx: int = 0):
    r = json.loads((V4_DIR / f"{baby}_chunk{chunk_idx}_result.json").read_text())
    return r


def analyze_current_frustration(r: dict) -> dict:
    """反推 _frustration 动力学在 v4 实验中的行为

    关键数据：
      - 250 epoch 内 event 分布：success 164, value_conflict 41, relationship 22,
        exploration 11, failure 12（共 250）
      - _frustration dynamics:
          if reward < -0.1: _frustration += |reward|   (累积)
          else: _frustration = max(0, _frustration - reward * 0.5)  (衰减)
      - reward = safety_delta * 0.5

    safety_delta 由 critic_value_delta 提供（来自 LLM critic）。
    M21 经验：safety_delta 典型范围 [-0.15, +0.15]，故 reward 范围 [-0.075, +0.075]
    → 累积条件 reward < -0.1 几乎永不满足
    """
    # M21 经验参数
    reward_pos_typical = 0.04  # success/relationship/exploration 平均 reward
    reward_neg_typical = -0.05  # value_conflict/failure 平均 reward

    events = r.get('event_distribution', {})
    n_success = events.get('success', 0) + events.get('relationship', 0) + events.get('exploration', 0)
    n_negative = events.get('value_conflict', 0) + events.get('failure', 0)
    total = sum(events.values())

    # 累积贡献（reward < -0.1 才累积，但实际典型 -0.05 < -0.1 不触发）
    # 用最坏情况假设：value_conflict = -0.1, failure = -0.15
    accum_value_conflict = events.get('value_conflict', 0) * 0.1  # 恰好不触发
    accum_failure = events.get('failure', 0) * 0.15
    total_accum = accum_value_conflict + accum_failure

    # 衰减贡献（每个正 reward 都衰减）
    decay_per_pos = 0.04 * 0.5  # = 0.02
    total_decay = n_success * decay_per_pos

    return {
        'total_events': total,
        'n_positive': n_success,
        'n_negative': n_negative,
        'expected_total_accum': round(total_accum, 3),
        'expected_total_decay': round(total_decay, 3),
        'net_change': round(total_accum - total_decay, 3),
        'conclusion': (
            '✅ D 方案可行（降阈值到 0.5）' if total_accum > 0.5 * 5 else
            '❌ D 方案不够：即使累积从未达到 2.0 也几乎不可能 0.5；'
            '需要 ad-hoc 触发'
        ),
    }


def simulate_alternative_triggers(r: dict) -> dict:
    """模拟不同 PT 触发信号在 v4 数据上的行为

    信号 G1: H_self 平台期（H_self 长时间不下降）
    信号 G2: |val| 高波动（value_magnitude std 突增）
    信号 G3: 连续 N 步 value_conflict / failure
    """
    ts = r.get('timeseries', [])
    n_checkpoints = len(ts)

    # H_self 平台期信号
    h_self_values = [t['H_self'] for t in ts]
    plateau_episodes = 0
    plateau_threshold = 0.05
    for i in range(1, len(h_self_values)):
        if abs(h_self_values[i] - h_self_values[i-1]) < plateau_threshold:
            plateau_episodes += 1

    # |val| 高波动信号
    val_magnitudes = [t.get('value_magnitude', 0) for t in ts]
    val_volatility = max(val_magnitudes) - min(val_magnitudes)

    # Identity 摇摆信号（重复生成新 identity）
    identity_so_far = ts[-1].get('identity_so_far', 0)
    identity_per_checkpoint = identity_so_far / max(n_checkpoints - 1, 1)

    return {
        'G1_H_self_plateau_episodes': plateau_episodes,
        'G1_plateau_threshold': plateau_threshold,
        'G2_val_volatility': round(val_volatility, 4),
        'G2_val_trajectory': val_magnitudes,
        'G3_identity_per_checkpoint': round(identity_per_checkpoint, 2),
        'n_checkpoints': n_checkpoints,
    }


def recommend_fix(analysis: dict, alternatives: dict) -> str:
    """基于分析结果推荐最佳 PT 修复方案"""
    if alternatives['G1_H_self_plateau_episodes'] >= 2:
        msg = (
            "推荐方案 G1（H_self 平台期触发）："
            "当 H_self 在连续 K 个 checkpoint 内变化 < threshold 时触发 PT。\n"
            "理由：H_self 平台期直接对应『自我未在演化』状态，"
            "比 scalar reward 更准确地捕捉 SGE 的核心目标函数停滞信号。"
        )
    elif analysis['expected_total_accum'] > 1.0:
        msg = (
            "推荐方案 D（降 PHASE_THRESHOLD）："
            f"累积期望 {analysis['expected_total_accum']}，降阈值到 0.5 可触发。"
        )
    else:
        msg = (
            "推荐方案 F（重设 dynamics）："
            "改用 H_self 平台期 + drive frustration 复合触发，"
            "重设累积/衰减机制使其能反映真实的『演化停滞』信号。"
        )
    return msg


def main():
    r = load_v4()

    print("=" * 60)
    print("P0-3 PT 触发机制修复方案验证")
    print("=" * 60)

    # 1. 当前 dynamics 行为反推
    analysis = analyze_current_frustration(r)
    print("\n## 1. 当前 _frustration dynamics 行为（v4 encouraged chunk 0）")
    for k, v in analysis.items():
        print(f"  {k}: {v}")

    # 2. 替代触发信号评估
    alternatives = simulate_alternative_triggers(r)
    print("\n## 2. 替代触发信号评估")
    for k, v in alternatives.items():
        if isinstance(v, list):
            print(f"  {k}: {v}")
        else:
            print(f"  {k}: {v}")

    # 3. 推荐
    print("\n## 3. 修复建议")
    print(recommend_fix(analysis, alternatives))

    # 4. 保存 JSON
    output_path = V4_DIR.parent / "m22_v6_pt_analysis" / "pt_analysis.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({
        'analysis': analysis,
        'alternatives': alternatives,
    }, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"\n✓ 写入: {output_path}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())