"""
M2.2 v5 — 公式 A2 + PHASE_THRESHOLD=0.5 联调验证

组合修复：
  1. sge/sge/metrics.py: H_self 公式 A2（基于 N_unique 线性映射）
  2. sge/sge/baseline.py: PHASE_THRESHOLD 2.0 → 0.5

相对 v2/v3/v4 的差异：
  - H_self 公式：原 Shannon 归一化 → 新公式 A2（自动生效）
  - PHASE_THRESHOLD：原 2.0 → 新 0.5（自动生效）
  - 输出目录：m22_v5_exph_self/（隔离 v2/v3/v4）
  - dedup：关闭（与 v2 baseline 一致）

执行：
  python experiments/scripts/m22_v5_exph_self.py --baby encouraged --chunk-index 0

验收（PRD §6）：
  - H_self reduction_rate > 0.30
  - phase_xition_count ≥ 1

关联：
  - research/sge-feasibility/M22_H_SELF_DIAGNOSIS.md
  - M22_V4_DEDUP_REPORT.md
  - recompute_h_self_v5.py / simulate_pt_v6.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

OUTPUT_DIR_V5 = Path(__file__).resolve().parent.parent / "output" / "m22_v5_exph_self"


def main() -> int:
    """策略：修改 sys.argv 后委托 v2.main()，但把 output_dir 强制改到 v5 目录"""
    # 1. 确保 v5 输出目录存在（v2.main 会用 mkdir，但若已 mkdir 可避免竞态）
    OUTPUT_DIR_V5.mkdir(parents=True, exist_ok=True)

    # 2. Monkey-patch v2 的 output dir 选择：v2.main 内部按 args.dedup_threshold 选目录
    #    简单做法：把 v2 的三个 OUTPUT_DIR 全替换为 v5 目录，再恢复
    import m22_v2_exph_self as v2
    original_base = v2.OUTPUT_DIR_BASE
    original_dedup = v2.OUTPUT_DIR_DEDUP
    original_dedup_v4 = v2.OUTPUT_DIR_DEDUP_V4
    v2.OUTPUT_DIR_BASE = OUTPUT_DIR_V5
    v2.OUTPUT_DIR_DEDUP = OUTPUT_DIR_V5
    v2.OUTPUT_DIR_DEDUP_V4 = OUTPUT_DIR_V5

    print("═" * 60)
    print("  M2.2 v5 — 公式 A2 + PHASE_THRESHOLD=0.5")
    print("═" * 60)
    print(f"  H_self 公式: A2 (N_unique linear, N_MAX=20)")
    print(f"  PHASE_THRESHOLD: 0.5（vs v2/v3/v4 默认 2.0）")
    print(f"  Output dir: {OUTPUT_DIR_V5}")
    print()

    try:
        rc = v2.main()
    finally:
        v2.OUTPUT_DIR_BASE = original_base
        v2.OUTPUT_DIR_DEDUP = original_dedup
        v2.OUTPUT_DIR_DEDUP_V4 = original_dedup_v4
    return rc


if __name__ == "__main__":
    sys.exit(main())