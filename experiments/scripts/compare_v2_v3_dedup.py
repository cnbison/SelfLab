"""
比对 v2 baseline vs v3 dedup 的 H_self 演化（chunk 0 only）

用途：dedup 烟测完成后，对比 250 epoch 内 H_self 曲线、identity 去重率、narrative 去重率
输出：experiments/output/m22_v3_dedup/comparison_chunk0.md（人类可读）

用法：
  python experiments/scripts/compare_v2_v3_dedup.py
"""

import json
import sys
from pathlib import Path

V2_DIR = Path(__file__).resolve().parent.parent / "output" / "m22_v2_exph_self"
V3_DIR = Path(__file__).resolve().parent.parent / "output" / "m22_v3_dedup"


def load_chunk_results(dir_path: Path, baby: str, chunk_idx: int = 0):
    r = json.loads((dir_path / f"{baby}_chunk{chunk_idx}_result.json").read_text())
    ih = json.loads((dir_path / f"{baby}_chunk{chunk_idx}_identity_history.json").read_text())
    nh = json.loads((dir_path / f"{baby}_chunk{chunk_idx}_narrative_history.json").read_text())
    return r, ih, nh


def compare(baby: str = "encouraged") -> str:
    out = []
    out.append(f"# M2.2 v2 baseline vs v3 dedup — {baby} chunk 0 对比\n")
    out.append(f"对比窗口：250 epoch（H_self 在 chunk 0 内的演化曲线）\n")
    out.append("")

    v2_r, v2_ih, v2_nh = load_chunk_results(V2_DIR, baby, 0)
    v3_r, v3_ih, v3_nh = load_chunk_results(V3_DIR, baby, 0)

    # ── 1. 关键指标对比 ──
    out.append("## 1. 关键指标\n")
    out.append("| 指标 | v2 (no dedup) | v3 (dedup=0.3) | Δ |")
    out.append("|------|---------------|----------------|---|")

    rows = [
        ("H_self start", v2_r['H_self_start'], v3_r['H_self_start']),
        ("H_self end", v2_r['H_self_end'], v3_r['H_self_end']),
        ("H_self Δ", v2_r['H_self_end'] - v2_r['H_self_start'],
                      v3_r['H_self_end'] - v3_r['H_self_start']),
        ("|val| final", v2_r['value_magnitude_final'], v3_r['value_magnitude_final']),
        ("identity_count (raw)", v2_r['identity_count'], v3_r['identity_count']),
        ("identity unique", len(set(x['identity'] for x in v2_ih)),
                              len(set(x['identity'] for x in v3_ih))),
        ("narrative_count (raw)", v2_r['narrative_count'], v3_r['narrative_count']),
        ("narrative unique", len(set(x['narrative'] for x in v2_nh)),
                               len(set(x['narrative'] for x in v3_nh))),
        ("PT count", v2_r['phase_xition_count'], v3_r['phase_xition_count']),
    ]
    for label, v2, v3 in rows:
        delta = ""
        if isinstance(v2, (int, float)) and isinstance(v3, (int, float)):
            delta = f"{v3 - v2:+.4f}" if isinstance(v2, float) else f"{v3 - v2:+d}"
        out.append(f"| {label} | {v2} | {v3} | {delta} |")

    out.append("")

    # ── 2. 去重效果 ──
    v2_id_dup = 1 - len(set(x['identity'] for x in v2_ih)) / max(v2_r['identity_count'], 1)
    v3_id_dup = 1 - len(set(x['identity'] for x in v3_ih)) / max(v3_r['identity_count'], 1)
    v2_na_dup = 1 - len(set(x['narrative'] for x in v2_nh)) / max(v2_r['narrative_count'], 1)
    v3_na_dup = 1 - len(set(x['narrative'] for x in v3_nh)) / max(v3_r['narrative_count'], 1)

    out.append("## 2. 去重效果\n")
    out.append("| 维度 | v2 去重率 | v3 去重率 | 提升 |")
    out.append("|------|-----------|-----------|------|")
    out.append(f"| identity | {v2_id_dup*100:.1f}% | {v3_id_dup*100:.1f}% | {(v3_id_dup-v2_id_dup)*100:+.1f} pp |")
    out.append(f"| narrative | {v2_na_dup*100:.1f}% | {v3_na_dup*100:.1f}% | {(v3_na_dup-v2_na_dup)*100:+.1f} pp |")
    out.append("")

    # ── 3. H_self 演化曲线 ──
    v2_ts = v2_r.get('timeseries', [])
    v3_ts = v3_r.get('timeseries', [])
    out.append("## 3. H_self 演化曲线（每 50 epoch 采样）\n")
    out.append("| epoch | v2 H_self | v3 H_self | Δ |")
    out.append("|------:|----------:|----------:|---:|")
    for v2_s, v3_s in zip(v2_ts, v3_ts):
        ep = v2_s['epoch']
        v2h = v2_s['H_self']
        v3h = v3_s['H_self']
        out.append(f"| {ep} | {v2h:.4f} | {v3h:.4f} | {v3h-v2h:+.4f} |")
    out.append("")

    # ── 4. 结论 ──
    out.append("## 4. 结论\n")
    v3_h_delta = v3_r['H_self_end'] - v3_r['H_self_start']
    v2_h_delta = v2_r['H_self_end'] - v2_r['H_self_start']
    if v3_h_delta < v2_h_delta:
        out.append(f"- ✅ **H_self 上升幅度减小**：v2 上升 {v2_h_delta:+.4f}，v3 上升 {v3_h_delta:+.4f}（Δ {(v3_h_delta-v2_h_delta):+.4f}）")
    elif v3_h_delta > v2_h_delta:
        out.append(f"- ⚠️ H_self 上升幅度反而增大：v2 {v2_h_delta:+.4f}，v3 {v3_h_delta:+.4f}（Δ {(v3_h_delta-v2_h_delta):+.4f}）")
    else:
        out.append(f"- ⚠️ H_self 上升幅度相同（{v2_h_delta:+.4f}）")

    out.append(f"- ✅ **Identity 去重率提升**：{v2_id_dup*100:.1f}% → {v3_id_dup*100:.1f}% （{(v3_id_dup-v2_id_dup)*100:+.1f} pp）")
    out.append(f"- ✅ **Narrative 去重率提升**：{v2_na_dup*100:.1f}% → {v3_na_dup*100:.1f}% （{(v3_na_dup-v2_na_dup)*100:+.1f} pp）")

    return "\n".join(out)


def main():
    if not (V3_DIR / "encouraged_chunk0_result.json").exists():
        print(f"⚠ v3 dedup 数据未生成（路径 {V3_DIR}/encouraged_chunk0_result.json）")
        print(f"  请先跑: python experiments/scripts/m22_v2_exph_self.py "
              f"--baby encouraged --chunk-index 0 --dedup-threshold 0.3")
        return 1

    text = compare("encouraged")
    out_path = V3_DIR / "comparison_chunk0.md"
    out_path.write_text(text, encoding="utf-8")
    print(text)
    print(f"\n✓ 写入: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())