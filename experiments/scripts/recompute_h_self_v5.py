"""
最小验证实验：用候选公式 A2 重算 v2/v3/v4 的 H_self 轨迹

公式 A2（绝对熵归一化）：
  H_identity = N_unique == 0 ? 1.0 :
               N_unique == 1 ? 0.0 :
               min(1.0, (N_unique - 1) / (N_max - 1))
  H_narrative = 同上
  H_self = 0.4·H_value + 0.3·H_identity + 0.3·H_narrative

目的：无需重跑 250 epoch 实验，从已有 history 数据验证新公式能否：
1. 反映 dedup 效果（v3/v4 应比 v2 低）
2. 让 H_self 有真实下降空间
3. 让 PRD §6 "下降率 > 30%" 目标数学上可达

输出：experiments/output/m22_v5_recompute/comparison_v2v3v4.md
"""

import json
import sys
from pathlib import Path

V2_DIR = Path(__file__).resolve().parent.parent / "output" / "m22_v2_exph_self"
V3_DIR = Path(__file__).resolve().parent.parent / "output" / "m22_v3_dedup"
V4_DIR = Path(__file__).resolve().parent.parent / "output" / "m22_v4_dedup"

# 候选公式参数
N_MAX = 20  # "完全发散"的阈值（>20 unique identity 视为 H=1.0）


def h_unique(n_unique: int, n_max: int = N_MAX) -> float:
    """新公式 A2：绝对熵归一化
    N=0 → 1.0（未形成 = 最大不确定性）
    N=1 → 0.0（完全稳定）
    N=2..N_max → 线性上升 (N-1)/(N_max-1)
    N>N_max → 1.0
    """
    if n_unique == 0:
        return 1.0
    if n_unique == 1:
        return 0.0
    return min(1.0, (n_unique - 1) / (n_max - 1))


def load_chunk_data(dir_path: Path, baby: str, chunk_idx: int = 0):
    r = json.loads((dir_path / f"{baby}_chunk{chunk_idx}_result.json").read_text())
    ih = json.loads((dir_path / f"{baby}_chunk{chunk_idx}_identity_history.json").read_text())
    nh = json.loads((dir_path / f"{baby}_chunk{chunk_idx}_narrative_history.json").read_text())
    return r, ih, nh


def reconstruct_at_checkpoint(history: list, max_epoch: int) -> list:
    """重构某 checkpoint 时的 history（仅含 epoch <= max_epoch 的项）"""
    return [h for h in history if h['epoch'] <= max_epoch]


def recompute_h_self_for_variant(r: dict, ih: list, nh: list, weights=(0.4, 0.3, 0.3)) -> list:
    """对单个变体（v2/v3/v4）重算所有 checkpoint 的 H_self"""
    w_v, w_i, w_n = weights
    ts = r.get('timeseries', [])
    out = []
    for s in ts:
        ep = s['epoch']
        # 从 result.json 取 H_value（这是真实计算结果）
        h_value = s.get('H_value', 0.0)

        # 重构该 checkpoint 的 history
        ih_at = reconstruct_at_checkpoint(ih, ep)
        nh_at = reconstruct_at_checkpoint(nh, ep)

        n_unique_id = len(set(h['identity'] for h in ih_at))
        n_unique_na = len(set(h['narrative'] for h in nh_at))

        # 应用新公式
        new_h_id = h_unique(n_unique_id)
        new_h_na = h_unique(n_unique_na)

        new_h_self = w_v * h_value + w_i * new_h_id + w_n * new_h_na

        out.append({
            'epoch': ep,
            'H_value_orig': h_value,
            'H_self_orig': s['H_self'],
            'n_id_total': len(ih_at),
            'n_id_unique': n_unique_id,
            'n_na_total': len(nh_at),
            'n_na_unique': n_unique_na,
            'new_H_id': new_h_id,
            'new_H_na': new_h_na,
            'new_H_self': new_h_self,
        })
    return out


def main():
    output_dir = Path(__file__).resolve().parent.parent / "output" / "m22_v5_recompute"
    output_dir.mkdir(parents=True, exist_ok=True)

    baby = "encouraged"

    # 检查所有 v2/v3/v4 数据存在
    for label, dir_path in [("v2", V2_DIR), ("v3", V3_DIR), ("v4", V4_DIR)]:
        if not (dir_path / f"{baby}_chunk0_result.json").exists():
            print(f"⚠ {label} 数据未生成（{dir_path}/{baby}_chunk0_result.json）")
            return 1

    v2_r, v2_ih, v2_nh = load_chunk_data(V2_DIR, baby, 0)
    v3_r, v3_ih, v3_nh = load_chunk_data(V3_DIR, baby, 0)
    v4_r, v4_ih, v4_nh = load_chunk_data(V4_DIR, baby, 0)

    v2_recomputed = recompute_h_self_for_variant(v2_r, v2_ih, v2_nh)
    v3_recomputed = recompute_h_self_for_variant(v3_r, v3_ih, v3_nh)
    v4_recomputed = recompute_h_self_for_variant(v4_r, v4_ih, v4_nh)

    # 生成 Markdown 报告
    lines = []
    lines.append(f"# M2.2 v5 — H_self 公式 A2 最小验证实验\n")
    lines.append(f"**日期**: 2026-07-08\n")
    lines.append(f"**目的**: 验证新公式能否反映 dedup 效果 + 让 H_self 数学可达下降 30%\n")
    lines.append("")
    lines.append(f"## 候选公式\n")
    lines.append("```python")
    lines.append("H_identity = N_unique == 0 ? 1.0 :")
    lines.append("             N_unique == 1 ? 0.0 :")
    lines.append("             min(1.0, (N_unique - 1) / (N_MAX - 1))")
    lines.append("H_narrative = 同上")
    lines.append("H_self = 0.4·H_value + 0.3·H_identity + 0.3·H_narrative")
    lines.append(f"N_MAX = {N_MAX}（>20 unique identity 视为 H=1.0 完全发散）")
    lines.append("```")
    lines.append("")
    lines.append("## 关键洞察\n")
    lines.append("- 原公式归一化基准 = log2(N_total)，全 unique → 永远 = 1.0")
    lines.append("- 新公式基于 N_unique（实际收敛度），1 unique → 0.0 完全稳定")
    lines.append("- N=0 → 1.0（未形成 = 最大不确定性，保持原语义）")
    lines.append("")

    # ── 1. 各变体的 unique 数轨迹 ──
    lines.append("## 1. Identity/Narrative Unique 数轨迹\n")
    lines.append("| epoch | v2 n_id_u | v3 n_id_u | v4 n_id_u | v2 n_na_u | v3 n_na_u | v4 n_na_u |")
    lines.append("|------:|----------:|----------:|----------:|----------:|----------:|----------:|")
    for r2, r3, r4 in zip(v2_recomputed, v3_recomputed, v4_recomputed):
        lines.append(f"| {r2['epoch']} | {r2['n_id_unique']} | {r3['n_id_unique']} | "
                     f"{r4['n_id_unique']} | {r2['n_na_unique']} | {r3['n_na_unique']} | "
                     f"{r4['n_na_unique']} |")
    lines.append("")

    # ── 2. 新 H_self 轨迹 ──
    lines.append("## 2. 新 H_self 轨迹对比（公式 A2 vs 原公式）\n")
    lines.append("| epoch | v2 原 | v2 新 | v3 原 | v3 新 | v4 原 | v4 新 |")
    lines.append("|------:|------:|------:|------:|------:|------:|------:|")
    for r2, r3, r4 in zip(v2_recomputed, v3_recomputed, v4_recomputed):
        lines.append(f"| {r2['epoch']} | {r2['H_self_orig']:.4f} | {r2['new_H_self']:.4f} | "
                     f"{r3['H_self_orig']:.4f} | {r3['new_H_self']:.4f} | "
                     f"{r4['H_self_orig']:.4f} | {r4['new_H_self']:.4f} |")
    lines.append("")

    # ── 3. 新 H_identity/H_narrative 分量 ──
    lines.append("## 3. 新公式 H_identity/H_narrative 分量\n")
    lines.append("| epoch | v3 H_id | v3 H_na | v4 H_id | v4 H_na |")
    lines.append("|------:|--------:|--------:|--------:|--------:|")
    for r3, r4 in zip(v3_recomputed, v4_recomputed):
        lines.append(f"| {r3['epoch']} | {r3['new_H_id']:.4f} | {r3['new_H_na']:.4f} | "
                     f"{r4['new_H_id']:.4f} | {r4['new_H_na']:.4f} |")
    lines.append("")

    # ── 4. 关键指标对比 ──
    lines.append("## 4. 关键指标\n")
    lines.append("| 指标 | v2 原 | v2 新 | v3 原 | v3 新 | v4 原 | v4 新 |")
    lines.append("|------|------:|------:|------:|------:|------:|------:|")

    def start_end(rows, key):
        return rows[0][key], rows[-1][key]

    v2_o_s, v2_o_e = start_end(v2_recomputed, 'H_self_orig')
    v2_n_s, v2_n_e = start_end(v2_recomputed, 'new_H_self')
    v3_o_s, v3_o_e = start_end(v3_recomputed, 'H_self_orig')
    v3_n_s, v3_n_e = start_end(v3_recomputed, 'new_H_self')
    v4_o_s, v4_o_e = start_end(v4_recomputed, 'H_self_orig')
    v4_n_s, v4_n_e = start_end(v4_recomputed, 'new_H_self')

    lines.append(f"| H_self start | {v2_o_s:.4f} | {v2_n_s:.4f} | {v3_o_s:.4f} | "
                 f"{v3_n_s:.4f} | {v4_o_s:.4f} | {v4_n_s:.4f} |")
    lines.append(f"| H_self end | {v2_o_e:.4f} | {v2_n_e:.4f} | {v3_o_e:.4f} | "
                 f"{v3_n_e:.4f} | {v4_o_e:.4f} | {v4_n_e:.4f} |")

    v2_o_delta = v2_o_e - v2_o_s
    v2_n_delta = v2_n_e - v2_n_s
    v3_o_delta = v3_o_e - v3_o_s
    v3_n_delta = v3_n_e - v3_n_s
    v4_o_delta = v4_o_e - v4_o_s
    v4_n_delta = v4_n_e - v4_n_s

    lines.append(f"| H_self Δ | {v2_o_delta:+.4f} | {v2_n_delta:+.4f} | "
                 f"{v3_o_delta:+.4f} | {v3_n_delta:+.4f} | "
                 f"{v4_o_delta:+.4f} | {v4_n_delta:+.4f} |")

    # Reduction rate
    def red_rate(s, e):
        if s <= 0:
            return 0.0
        return (s - e) / s

    v2_o_rr = red_rate(v2_o_s, v2_o_e)
    v2_n_rr = red_rate(v2_n_s, v2_n_e)
    v3_o_rr = red_rate(v3_o_s, v3_o_e)
    v3_n_rr = red_rate(v3_n_s, v3_n_e)
    v4_o_rr = red_rate(v4_o_s, v4_o_e)
    v4_n_rr = red_rate(v4_n_s, v4_n_e)

    lines.append(f"| Reduction rate | {v2_o_rr:+.4f} | {v2_n_rr:+.4f} | "
                 f"{v3_o_rr:+.4f} | {v3_n_rr:+.4f} | "
                 f"{v4_o_rr:+.4f} | {v4_n_rr:+.4f} |")
    lines.append("")

    # ── 5. PRD §6 验收检查 ──
    lines.append("## 5. PRD §6 验收检查（reduction rate > 30%）\n")
    lines.append("| 变体 | 原公式 reduction | 新公式 reduction | 是否达标（原/新） |")
    lines.append("|------|------------------|------------------|-------------------|")
    for label, o_rr, n_rr in [("v2", v2_o_rr, v2_n_rr),
                                ("v3", v3_o_rr, v3_n_rr),
                                ("v4", v4_o_rr, v4_n_rr)]:
        o_pass = "✅" if o_rr > 0.30 else "❌"
        n_pass = "✅" if n_rr > 0.30 else "❌"
        lines.append(f"| {label} | {o_rr:+.4f} | {n_rr:+.4f} | {o_pass} / {n_pass} |")
    lines.append("")

    # ── 6. 结论 ──
    lines.append("## 6. 结论\n")

    # 新公式能否反映 dedup？
    if v2_n_e > v3_n_e > v4_n_e:
        lines.append(f"- ✅ **新公式反映 dedup 效果**：H_self 终点 v2 ({v2_n_e:.4f}) > v3 ({v3_n_e:.4f}) > v4 ({v4_n_e:.4f})")
    else:
        lines.append(f"- ❌ **新公式未能反映 dedup 效果**：v2 ({v2_n_e:.4f}), v3 ({v3_n_e:.4f}), v4 ({v4_n_e:.4f})")

    # 新公式是否提供真实下降空间？
    v4_n_reduction = v4_n_rr
    if v4_n_reduction > 0.30:
        lines.append(f"- ✅ **新公式让 H_self 下降 > 30%**：v4 reduction = {v4_n_reduction:+.4f}")
    elif v4_n_reduction > 0:
        lines.append(f"- ⚠️ **新公式让 H_self 有下降但 < 30%**：v4 reduction = {v4_n_reduction:+.4f}")
    else:
        lines.append(f"- ❌ **新公式仍未让 H_self 下降**：v4 reduction = {v4_n_reduction:+.4f}")

    # 数学下界对比
    lines.append(f"- 新公式 H_self 数学下界 ≈ 0（当 N_unique_id = N_unique_na = 1 且 H_value = 0）")
    lines.append(f"- 原公式 H_self 数学下界 = 0.6（H_identity = H_narrative 永远 ≥ 1.0 × 0.3）")
    lines.append("")

    # ── 7. 数据保存（JSON 格式供后续分析）──
    output_json = {
        'formula': 'A2_absolute_normalized',
        'N_MAX': N_MAX,
        'weights': [0.4, 0.3, 0.3],
        'v2': v2_recomputed,
        'v3': v3_recomputed,
        'v4': v4_recomputed,
    }
    output_path_json = output_dir / "recomputed_h_self.json"
    output_path_json.write_text(json.dumps(output_json, indent=2, ensure_ascii=False),
                                 encoding='utf-8')

    output_path_md = output_dir / "comparison_v2v3v4.md"
    output_path_md.write_text("\n".join(lines), encoding='utf-8')

    print("\n".join(lines))
    print(f"\n✓ 写入: {output_path_md}")
    print(f"✓ 写入: {output_path_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())