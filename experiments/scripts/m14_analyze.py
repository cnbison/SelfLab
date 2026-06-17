"""M1.4 实验结果分析脚本

读取 5 组实验的 epoch_log.jsonl,计算:
- REVISIT 触发率对比
- 最终价值向量对比
- E4 强制 REVISIT 后的价值向量变化
- 5 维评分卡维度 1 首次量化

用法:
    python experiments/scripts/m14_analyze.py
"""
import json
import os
from pathlib import Path
from typing import Dict, List


VARIANTS = ["e0", "e1", "e2", "e3", "e4"]
VARIANT_DESC = {
    "e0": "M1.3 baseline (contradiction_feedback + v0 prompt)",
    "e1": "prompt-only (contradiction_feedback + v1 prompt)",
    "e2": "events-only (contradiction_extreme + v0 prompt)",
    "e3": "both (contradiction_extreme + v1 prompt)",
    "e4": "forced REVISIT (philosophical experiment)",
}
VALUES = ["safety", "creativity", "connection", "autonomy", "justice", "compassion"]


def load_epoch_log(variant: str) -> List[dict]:
    """加载某个变体的 epoch_log.jsonl"""
    path = f"experiments/output/m11_m14_{variant}/epoch_log.jsonl"
    if not os.path.exists(path):
        return []
    logs = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                logs.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  ⚠ {path} 解析失败: {e}")
    return logs


def compute_reflection_stats(logs: List[dict]) -> Dict:
    """计算反思类型分布"""
    stats = {
        "total_reflections": 0,
        "reinforce": 0,
        "adjust": 0,
        "revisit": 0,
        "none": 0,
        "revisit_epochs": [],  # 记录 REVISIT 触发的 epoch
    }
    for log in logs:
        rtype = log.get("reflection_type", "NONE")
        if rtype == "REINFORCE":
            stats["reinforce"] += 1
            stats["total_reflections"] += 1
        elif rtype == "ADJUST":
            stats["adjust"] += 1
            stats["total_reflections"] += 1
        elif rtype == "REVISIT":
            stats["revisit"] += 1
            stats["total_reflections"] += 1
            stats["revisit_epochs"].append(log.get("epoch"))
        else:
            stats["none"] += 1
    return stats


def get_final_value_vector(logs: List[dict]) -> Dict:
    """获取最终价值向量"""
    if not logs:
        return {v: 0.0 for v in VALUES}
    return logs[-1].get("value_vector", {v: 0.0 for v in VALUES})


def compute_emergence_metrics(logs: List[dict]) -> Dict:
    """计算涌现指标(对照 M1.3 报告)"""
    if not logs:
        return {"emergence_magnitude": 0.0, "directional_consistency": 0.0, "smoothness": 0.0}

    vectors = [log.get("value_vector", {}) for log in logs]
    magnitudes = [sum(abs(v) for v in vec.values()) / 6 for vec in vectors]
    emergence_magnitude = magnitudes[-1] if magnitudes else 0.0

    # 方向一致性: 后期向量的符号稳定性
    if len(vectors) >= 20:
        late = vectors[-20:]
        directional_consistency = sum(
            1 for v in VALUES
            if all(vec.get(v, 0) > 0 for vec in late) or all(vec.get(v, 0) < 0 for vec in late)
        ) / len(VALUES)
    else:
        directional_consistency = 0.0

    # 轨迹平滑度: 相邻 epoch 间变化的平均
    if len(magnitudes) >= 2:
        smoothness = sum(abs(magnitudes[i+1] - magnitudes[i]) for i in range(len(magnitudes)-1)) / (len(magnitudes) - 1)
    else:
        smoothness = 0.0

    return {
        "emergence_magnitude": round(emergence_magnitude, 4),
        "directional_consistency": round(directional_consistency, 4),
        "smoothness": round(smoothness, 4),
    }


def compute_e4_forced_revisit_impact(logs: List[dict]) -> Dict:
    """E4 专用: 强制 REVISIT 后的价值向量变化

    用相邻 epoch 的 value_vector 差值 (epoch N - epoch N-1) 来衡量 REVISIT 影响。
    """
    if not logs:
        return {}

    impact = {}
    for i, log in enumerate(logs):
        if log.get("reflection_type") == "REVISIT" and i > 0:
            epoch = log.get("epoch")
            vv_after = log.get("value_vector", {})
            vv_before = logs[i-1].get("value_vector", {})
            # 计算 reflection_output 的 value_delta (强制 REVISIT 输出的 delta)
            r_delta = log.get("reflection_output", {}).get("value_delta", {})
            impact[epoch] = {
                "vv_diff": {k: round(vv_after.get(k, 0) - vv_before.get(k, 0), 4) for k in VALUES},
                "reflection_delta": {k: round(r_delta.get(k, 0), 4) for k in VALUES},
            }
    return impact


def main():
    print("=" * 70)
    print("M1.4 REVISIT 专项测试 — 数据汇总")
    print("=" * 70)

    all_stats = {}
    for variant in VARIANTS:
        print(f"\n--- {variant.upper()}: {VARIANT_DESC[variant]} ---")
        logs = load_epoch_log(variant)
        if not logs:
            print(f"  ⚠ 实验数据不存在,跳过 (路径: experiments/output/m11_m14_{variant}/)")
            continue

        stats = compute_reflection_stats(logs)
        final_vv = get_final_value_vector(logs)
        metrics = compute_emergence_metrics(logs)
        e4_impact = compute_e4_forced_revisit_impact(logs) if variant == "e4" else {}

        all_stats[variant] = {
            "stats": stats,
            "final_vv": final_vv,
            "metrics": metrics,
            "e4_impact": e4_impact,
        }

        # 打印反思统计
        print(f"  反思总数: {stats['total_reflections']}")
        print(f"  REINFORCE: {stats['reinforce']} ({stats['reinforce']*100/max(1,stats['total_reflections']):.1f}%)")
        print(f"  ADJUST:    {stats['adjust']} ({stats['adjust']*100/max(1,stats['total_reflections']):.1f}%)")
        print(f"  REVISIT:   {stats['revisit']} ({stats['revisit']*100/max(1,stats['total_reflections']):.1f}%) [epochs: {stats['revisit_epochs']}]")
        print(f"  涌现幅度: {metrics['emergence_magnitude']:.4f} (阈值 > 0.3)")
        print(f"  方向一致性: {metrics['directional_consistency']:.4f} (阈值 > 0.5)")
        print(f"  轨迹平滑度: {metrics['smoothness']:.4f}")

        # 打印最终价值向量
        print(f"  最终价值向量:")
        for v in VALUES:
            val = final_vv.get(v, 0.0)
            sign = "+" if val >= 0 else ""
            print(f"    · {v:12s} {sign}{val:.3f}")

        # E4 特殊输出
        if variant == "e4" and e4_impact:
            print(f"  E4 强制 REVISIT 价值变化 (vv_diff = 实际变化, reflection_delta = 强制输出的 delta):")
            for epoch, info in e4_impact.items():
                print(f"    Epoch {epoch}:")
                print(f"      实际价值变化:")
                for v, d in info["vv_diff"].items():
                    if abs(d) > 0.01:
                        sign = "+" if d >= 0 else ""
                        print(f"        {v:12s} {sign}{d:.3f}")
                print(f"      强制 reflection_delta:")
                for v, d in info["reflection_delta"].items():
                    if abs(d) > 0.01:
                        sign = "+" if d >= 0 else ""
                        print(f"        {v:12s} {sign}{d:.3f}")

    # 对比表
    print("\n" + "=" * 70)
    print("REVISIT 触发率对比 (核心验证)")
    print("=" * 70)
    print(f"{'变体':<8}{'反思总数':<10}{'REINFORCE':<12}{'ADJUST':<10}{'REVISIT':<12}{'触发率':<10}")
    for variant in VARIANTS:
        if variant not in all_stats:
            continue
        s = all_stats[variant]["stats"]
        total = s["total_reflections"]
        rate = f"{s['revisit']*100/max(1,total):.1f}%"
        print(f"{variant:<8}{total:<10}{s['reinforce']:<12}{s['adjust']:<10}{s['revisit']:<12}{rate:<10}")

    print("\n" + "=" * 70)
    print("最终价值向量对比")
    print("=" * 70)
    print(f"{'维度':<12}", end="")
    for v in VARIANTS:
        print(f"{v.upper():<10}", end="")
    print()
    for dim in VALUES:
        print(f"{dim:<12}", end="")
        for variant in VARIANTS:
            if variant in all_stats:
                val = all_stats[variant]["final_vv"].get(dim, 0.0)
                sign = "+" if val >= 0 else ""
                print(f"{sign}{val:.3f}    ", end="")
            else:
                print(f"{'N/A':<10}", end="")
        print()

    # 验证结论
    print("\n" + "=" * 70)
    print("假设验证")
    print("=" * 70)
    if "e1" in all_stats and "e0" in all_stats:
        e0_r = all_stats["e0"]["stats"]["revisit"]
        e1_r = all_stats["e1"]["stats"]["revisit"]
        h1_valid = e1_r > 0 and e1_r > e0_r
        print(f"  H1 (prompt bias): {'✓ 成立' if h1_valid else '✗ 不成立'}")
        print(f"    E0 REVISIT = {e0_r}, E1 REVISIT = {e1_r}")

    if "e2" in all_stats and "e0" in all_stats:
        e0_r = all_stats["e0"]["stats"]["revisit"]
        e2_r = all_stats["e2"]["stats"]["revisit"]
        h2_valid = e2_r > 0 and e2_r > e0_r
        print(f"  H2 (事件强度): {'✓ 成立' if h2_valid else '✗ 不成立'}")
        print(f"    E0 REVISIT = {e0_r}, E2 REVISIT = {e2_r}")

    if "e3" in all_stats and "e0" in all_stats:
        e0_r = all_stats["e0"]["stats"]["revisit"]
        e3_r = all_stats["e3"]["stats"]["revisit"]
        h12_valid = e3_r > 0 and e3_r > max(e0_r, e1_r if "e1" in all_stats else 0)
        print(f"  H1+H2: {'✓ 成立' if h12_valid else '✗ 不成立'}")
        print(f"    E3 REVISIT = {e3_r}")

    e_all_zero = all(
        all_stats.get(v, {}).get("stats", {}).get("revisit", 0) == 0
        for v in ["e0", "e1", "e2", "e3"]
    )
    print(f"  H3 (AI 真的从不根本性反思): {'⚠ 部分成立' if e_all_zero else '✗ 不成立'}")
    if e_all_zero:
        print(f"    全部 4 个非强制变体 REVISIT = 0 → 价值惯性可能是 LLM 内在特性")

    if "e4" in all_stats and all_stats["e4"]["e4_impact"]:
        print(f"  E4 哲学实验: 强制 REVISIT 成功触发,价值向量响应已记录")


if __name__ == "__main__":
    main()
