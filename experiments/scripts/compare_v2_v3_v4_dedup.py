"""
三向比对 v2 baseline vs v3 jaccard dedup vs v4 ngram dedup
（chunk 0 only）

输出：experiments/output/m22_v4_dedup/comparison_chunk0.md
"""

import json
import sys
from pathlib import Path

V2_DIR = Path(__file__).resolve().parent.parent / "output" / "m22_v2_exph_self"
V3_DIR = Path(__file__).resolve().parent.parent / "output" / "m22_v3_dedup"
V4_DIR = Path(__file__).resolve().parent.parent / "output" / "m22_v4_dedup"


def load_chunk(dir_path: Path, baby: str, chunk_idx: int = 0):
    r = json.loads((dir_path / f"{baby}_chunk{chunk_idx}_result.json").read_text())
    ih = json.loads((dir_path / f"{baby}_chunk{chunk_idx}_identity_history.json").read_text())
    nh = json.loads((dir_path / f"{baby}_chunk{chunk_idx}_narrative_history.json").read_text())
    return r, ih, nh


def compare(baby: str = "encouraged") -> str:
    out = []
    out.append(f"# M2.2 三向 dedup 对比 — {baby} chunk 0\n")
    out.append(f"对比窗口：250 epoch（H_self 演化 + 去重率）\n")
    out.append("v2 = no dedup  v3 = jaccard@0.3  v4 = ngram(1,2)@0.3\n")
    out.append("")

    v2_r, v2_ih, v2_nh = load_chunk(V2_DIR, baby, 0)
    v3_r, v3_ih, v3_nh = load_chunk(V3_DIR, baby, 0)
    v4_r, v4_ih, v4_nh = load_chunk(V4_DIR, baby, 0)

    # ── 1. 关键指标 ──
    out.append("## 1. 关键指标\n")
    out.append("| 指标 | v2 (no dedup) | v3 (jaccard) | v4 (ngram) |")
    out.append("|------|---------------|--------------|------------|")

    rows = [
        ("H_self start", v2_r['H_self_start'], v3_r['H_self_start'], v4_r['H_self_start']),
        ("H_self end", v2_r['H_self_end'], v3_r['H_self_end'], v4_r['H_self_end']),
        ("H_self Δ", v2_r['H_self_end'] - v2_r['H_self_start'],
                      v3_r['H_self_end'] - v3_r['H_self_start'],
                      v4_r['H_self_end'] - v4_r['H_self_start']),
        ("|val| final", v2_r['value_magnitude_final'],
                       v3_r['value_magnitude_final'],
                       v4_r['value_magnitude_final']),
        ("identity raw count", v2_r['identity_count'], v3_r['identity_count'], v4_r['identity_count']),
        ("identity unique", len(set(x['identity'] for x in v2_ih)),
                            len(set(x['identity'] for x in v3_ih)),
                            len(set(x['identity'] for x in v4_ih))),
        ("narrative raw count", v2_r['narrative_count'], v3_r['narrative_count'], v4_r['narrative_count']),
        ("narrative unique", len(set(x['narrative'] for x in v2_nh)),
                             len(set(x['narrative'] for x in v3_nh)),
                             len(set(x['narrative'] for x in v4_nh))),
        ("PT count", v2_r['phase_xition_count'], v3_r['phase_xition_count'], v4_r['phase_xition_count']),
    ]
    for label, v2, v3, v4 in rows:
        if isinstance(v2, float):
            out.append(f"| {label} | {v2:.4f} | {v3:.4f} | {v4:.4f} |")
        else:
            out.append(f"| {label} | {v2} | {v3} | {v4} |")
    out.append("")

    # ── 2. 去重效果 ──
    def dedup_rate(raw, hist):
        if raw == 0:
            return 0.0
        return 1 - len(set(x['identity'] if 'identity' in x else x['narrative']
                            for x in hist)) / raw

    v2_id_dup = dedup_rate(v2_r['identity_count'], v2_ih)
    v3_id_dup = dedup_rate(v3_r['identity_count'], v3_ih)
    v4_id_dup = dedup_rate(v4_r['identity_count'], v4_ih)
    v2_na_dup = dedup_rate(v2_r['narrative_count'], v2_nh)
    v3_na_dup = dedup_rate(v3_r['narrative_count'], v3_nh)
    v4_na_dup = dedup_rate(v4_r['narrative_count'], v4_nh)

    out.append("## 2. 去重效果\n")
    out.append("| 维度 | v2 | v3 (jaccard) | v4 (ngram) | v4 相对 v3 提升 |")
    out.append("|------|----|--------------|------------|----------------|")
    out.append(f"| identity | {v2_id_dup*100:.1f}% | {v3_id_dup*100:.1f}% | {v4_id_dup*100:.1f}% | "
               f"{(v4_id_dup-v3_id_dup)*100:+.1f} pp |")
    out.append(f"| narrative | {v2_na_dup*100:.1f}% | {v3_na_dup*100:.1f}% | {v4_na_dup*100:.1f}% | "
               f"{(v4_na_dup-v3_na_dup)*100:+.1f} pp |")
    out.append("")

    # ── 3. H_self 演化曲线 ──
    v2_ts = v2_r.get('timeseries', [])
    v3_ts = v3_r.get('timeseries', [])
    v4_ts = v4_r.get('timeseries', [])
    out.append("## 3. H_self 演化曲线（每 50 epoch）\n")
    out.append("| epoch | v2 H_self | v3 H_self | v4 H_self |")
    out.append("|------:|----------:|----------:|----------:|")
    for s2, s3, s4 in zip(v2_ts, v3_ts, v4_ts):
        ep = s2['epoch']
        out.append(f"| {ep} | {s2['H_self']:.4f} | {s3['H_self']:.4f} | {s4['H_self']:.4f} |")
    out.append("")

    # ── 4. 结论 ──
    out.append("## 4. 结论\n")

    # Identity dedup 提升
    id_improve = v4_id_dup - v3_id_dup
    if id_improve > 0.1:
        out.append(f"- ✅ **Identity 去重率提升**：v3 {v3_id_dup*100:.1f}% → v4 {v4_id_dup*100:.1f}% "
                   f"（+{id_improve*100:.1f} pp）—— ngram 显著优于 jaccard")
    elif id_improve > 0:
        out.append(f"- ⚠️ **Identity 去重率轻微提升**：v3 {v3_id_dup*100:.1f}% → v4 {v4_id_dup*100:.1f}% "
                   f"（+{id_improve*100:.1f} pp）—— ngram 略优于 jaccard")
    else:
        out.append(f"- ❌ **Identity 去重率未提升**：v3 {v3_id_dup*100:.1f}% → v4 {v4_id_dup*100:.1f}% "
                   f"（{id_improve*100:+.1f} pp）—— ngram 无效")

    # H_self 改善
    v4_h_delta = v4_r['H_self_end'] - v4_r['H_self_start']
    v2_h_delta = v2_r['H_self_end'] - v2_r['H_self_start']
    if v4_h_delta < v2_h_delta:
        out.append(f"- ✅ **H_self 上升幅度减小**：v2 {v2_h_delta:+.4f}, v4 {v4_h_delta:+.4f} "
                   f"（Δ {(v4_h_delta-v2_h_delta):+.4f}）")
    else:
        out.append(f"- ❌ **H_self 上升幅度未减小**：v2 {v2_h_delta:+.4f}, v4 {v4_h_delta:+.4f} "
                   f"（Δ {(v4_h_delta-v2_h_delta):+.4f}）")

    # |val| 变化
    v4_val = v4_r['value_magnitude_final']
    v2_val = v2_r['value_magnitude_final']
    if v4_val < v2_val:
        out.append(f"- ✅ **|val| 下降**：v2 {v2_val:.4f} → v4 {v4_val:.4f}（{v4_val-v2_val:+.4f}）")
    else:
        out.append(f"- ❌ **|val| 未下降**：v2 {v2_val:.4f} → v4 {v4_val:.4f}（{v4_val-v2_val:+.4f}）")

    return "\n".join(out)


def main():
    if not (V4_DIR / "encouraged_chunk0_result.json").exists():
        print(f"⚠ v4 dedup 数据未生成（路径 {V4_DIR}/encouraged_chunk0_result.json）")
        return 1

    text = compare("encouraged")
    out_path = V4_DIR / "comparison_chunk0.md"
    out_path.write_text(text, encoding="utf-8")
    print(text)
    print(f"\n✓ 写入: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())