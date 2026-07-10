"""
M2.2 v6 — 公式 A3 + PHASE_THRESHOLD=0.5 联调验证（语义聚类版）

组合（v5 修复 + 公式 A3 升级）：
  1. sge/sge/metrics.py: H_self 公式 A3（基于 char-bigram 语义聚类，2026-07-10）
     - 替代公式 A2（字符串 unique，反映"多样性"而非"形成度"）
     - char-bigram overlap coefficient 聚类 + cluster 数套用 A2 框架
     - threshold=0.5, ngram_size=2, 零依赖
  2. sge/sge/baseline.py: PHASE_THRESHOLD 2.0 → 0.5
  3. sge/sge/llm_client.py: timeout 30→60s, retry 5→8（v5 重跑新增）

相对 v5 的差异：
  - H_self 公式：A2（字符串 unique）→ A3（语义聚类，自动生效，因 compute_self_entropy 默认使用 A3）
  - 其他参数与 v5 完全一致
  - 输出目录：m22_v6_exph_self/（隔离 v5/v2/v3/v4）

执行：
  python experiments/scripts/m22_v6_exph_self.py --baby encouraged --chunk-index 0 --force

验收（PRD §6）：
  - H_self reduction_rate > 0.30
  - phase_xition_count ≥ 1

关联：
- 公式 A3 实现：sge/sge/metrics.py:_semantic_diversity()
- v5 完整 250 epoch 报告：experiments/M22_V5_REPORT.md
- v5 partial run 偏差修正：discussions/2026-07-10-v5-full-rerun-correction.md
- 公式 A3 commit: 88f3863
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

OUTPUT_DIR_V6 = Path(__file__).resolve().parent.parent / "output" / "m22_v6_exph_self"


def main() -> int:
    """策略：与 v5 相同的 monkey-patch 模式，把 output_dir 强制改到 v6 目录

    公式 A3 已默认启用（compute_self_entropy 在 v6 启动时自动使用）
    PHASE_THRESHOLD 0.5 已在 baseline.py 持久化
    """
    OUTPUT_DIR_V6.mkdir(parents=True, exist_ok=True)

    import m22_v2_exph_self as v2
    original_base = v2.OUTPUT_DIR_BASE
    original_dedup = v2.OUTPUT_DIR_DEDUP
    original_dedup_v4 = v2.OUTPUT_DIR_DEDUP_V4
    v2.OUTPUT_DIR_BASE = OUTPUT_DIR_V6
    v2.OUTPUT_DIR_DEDUP = OUTPUT_DIR_V6
    v2.OUTPUT_DIR_DEDUP_V4 = OUTPUT_DIR_V6

    print("═" * 60)
    print("  M2.2 v6 — 公式 A3（语义聚类）+ PHASE_THRESHOLD=0.5")
    print("═" * 60)
    print(f"  H_self 公式: A3 (char-bigram Jaccard 聚类, threshold=0.5)")
    print(f"  PHASE_THRESHOLD: 0.5（vs v2/v3/v4 默认 2.0）")
    print(f"  LLM timeout: 60s / retry 8（vs v5 partial 30s/5）")
    print(f"  Output dir: {OUTPUT_DIR_V6}")
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
