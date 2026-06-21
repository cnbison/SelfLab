"""
M2.3 补充 — Identity 主题漂移自动检测

输入：M2.2 的 3 baby × 50 次 identity 重写（identity_history.json）
输出：每 baby 的连续相似度曲线 + 漂移点检测 + 跨 baby 对比

算法：
- 两种相似度：
  * difflib.SequenceMatcher.ratio()（标准文本相似度）
  * 中文字符 bigram Jaccard（捕捉字面重叠，对中文友好）
- 连续相似度 = identity[i] vs identity[i+1]
- 漂移点 = 相似度 < 阈值（如 0.3）或相对前一个点下降 > 50%

无需外部依赖（只用 difflib）。

用法：
  python m23_identity_drift.py
"""

import json
import sys
from pathlib import Path
from difflib import SequenceMatcher


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "m22_triplets"


def char_bigrams(text: str) -> set:
    """中文字符 bigram 集合（用于 Jaccard 相似度）"""
    # 去除标点和空白
    text = ''.join(c for c in text if c.strip() and not c.isspace())
    return set(text[i:i+2] for i in range(len(text) - 1))


def jaccard_similarity(a: str, b: str) -> float:
    """Jaccard 相似度（基于字符 bigram 集合）"""
    bigrams_a = char_bigrams(a)
    bigrams_b = char_bigrams(b)
    if not bigrams_a or not bigrams_b:
        return 0.0
    intersection = bigrams_a & bigrams_b
    union = bigrams_a | bigrams_b
    return len(intersection) / len(union)


def text_similarity(a: str, b: str) -> dict:
    """计算两个文本的两种相似度"""
    return {
        'difflib': SequenceMatcher(None, a, b).ratio(),
        'jaccard_bigram': jaccard_similarity(a, b),
    }


def analyze_baby(baby: str) -> dict:
    """分析一个 baby 的 identity 历史，输出漂移检测结果"""
    path = OUTPUT_DIR / f"{baby}_identity_history.json"
    if not path.exists():
        return {'error': f'{path} not found'}

    with open(path) as f:
        identities = json.load(f)

    if len(identities) < 2:
        return {'error': f'{baby}: only {len(identities)} identities'}

    # ── 连续相似度 ──
    consecutive = []
    for i in range(len(identities) - 1):
        curr = identities[i]
        next_id = identities[i + 1]
        sims = text_similarity(curr['identity'], next_id['identity'])
        consecutive.append({
            'from_epoch': curr['epoch'] + 1,
            'to_epoch': next_id['epoch'] + 1,
            **sims,
        })

    # ── 统计 ──
    avg_d = sum(c['difflib'] for c in consecutive) / len(consecutive)
    avg_j = sum(c['jaccard_bigram'] for c in consecutive) / len(consecutive)
    std_d = (sum((c['difflib'] - avg_d) ** 2 for c in consecutive) / len(consecutive)) ** 0.5

    # ── 漂移点检测（相对异常：similarity 显著低于本 baby 平均）──
    # 注：中文短文本 (20-40 字) difflib 基线 ~0.3，所以 mean-2*std 太严 → 用 mean-1*std
    # 解读：低 similarity = 高 variation = 主题漂移信号
    drift_threshold = avg_d - 1 * std_d
    drift_points = []
    for c in consecutive:
        if c['difflib'] < drift_threshold:
            drift_points.append({
                'from_epoch': c['from_epoch'],
                'to_epoch': c['to_epoch'],
                'difflib': c['difflib'],
                'jaccard_bigram': c['jaccard_bigram'],
                'reason': 'below_1std',
            })

    # Top-5 最不同配对（按 difflib 升序）+ 实际 identity 文本
    sorted_consecutive = sorted(consecutive, key=lambda c: c['difflib'])
    extreme_pairs = []
    for c in sorted_consecutive[:5] if len(sorted_consecutive) >= 5 else sorted_consecutive:
        # 找到对应的 identity 文本
        from_idx = next((i for i, id_ in enumerate(identities)
                         if id_['epoch'] + 1 == c['from_epoch']), None)
        to_idx = next((i for i, id_ in enumerate(identities)
                       if id_['epoch'] + 1 == c['to_epoch']), None)
        extreme_pairs.append({
            **c,
            'from_identity': identities[from_idx]['identity'] if from_idx is not None else '',
            'to_identity': identities[to_idx]['identity'] if to_idx is not None else '',
        })

    return {
        'baby': baby,
        'n_identities': len(identities),
        'n_consecutive_pairs': len(consecutive),
        'avg_similarity_difflib': round(avg_d, 4),
        'avg_similarity_jaccard': round(avg_j, 4),
        'std_similarity_difflib': round(std_d, 4),
        'drift_threshold': round(drift_threshold, 4),
        'n_drift_points': len(drift_points),
        'drift_rate': round(len(drift_points) / len(consecutive), 4),
        'drift_points': drift_points,
        'extreme_pairs': extreme_pairs,
        'consecutive_similarities': consecutive,
    }


def main() -> int:
    print("=" * 60)
    print("  M2.3 — Identity 主题漂移自动检测")
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
        print(f"    {r['n_identities']} identities")
        print(f"    平均相似度 (difflib): {r['avg_similarity_difflib']:.4f} ± {r['std_similarity_difflib']:.4f}")
        print(f"    平均相似度 (jaccard): {r['avg_similarity_jaccard']:.4f}")
        print(f"    漂移点数: {r['n_drift_points']} / {r['n_consecutive_pairs']} ({r['drift_rate']*100:.1f}%)")
        print(f"    漂移阈值 (mean-2*std): {r['drift_threshold']:.4f}")
        if r['drift_points']:
            print(f"    极端漂移 epoch: {[d['from_epoch'] for d in r['drift_points']]}")
        if r['extreme_pairs']:
            print(f"    Top-1 最不同配对 (epoch {r['extreme_pairs'][0]['from_epoch']} → {r['extreme_pairs'][0]['to_epoch']}):")
            print(f"      similarity = {r['extreme_pairs'][0]['difflib']:.4f}")

    # ── 跨 baby 对比 ──
    print(f"\n{'─'*60}")
    print(f"  跨 baby 漂移对比")
    print(f"{'─'*60}\n")

    # 注：低 avg_sim = 高 variation = 更多主题漂移（与直觉相反，注意解读）
    print(f"{'Baby':<14} {'avg_sim':<10} {'std':<8} {'drift_points':<15} {'drift_rate':<10}")
    for baby, r in results.items():
        if 'error' in r:
            continue
        print(f"{baby:<14} {r['avg_similarity_difflib']:<10.4f} "
              f"{r['std_similarity_difflib']:<8.4f} "
              f"{r['n_drift_points']}/{r['n_consecutive_pairs']:<10} "
              f"{r['drift_rate']*100:<10.1f}%")

    # ── 解读 ──
    print(f"\n  解读:")
    print(f"    avg_sim 越低 = 连续 identity 差异越大 = 主题漂移信号更强")
    print(f"    (avg_sim 高 = 主题稳定 / 低 = 主题多变)")

    # ── 验证 ──
    if 'challenged' in results and 'encouraged' in results:
        cha_sim = results['challenged']['avg_similarity_difflib']
        enc_sim = results['encouraged']['avg_similarity_difflib']
        print(f"\n  假设验证 (challenged 主题更不稳定 → avg_sim 应该更低):")
        if cha_sim < enc_sim:
            print(f"    ✓ 验证成功 (cha {cha_sim:.4f} < enc {enc_sim:.4f})")
        else:
            print(f"    ✗ 假设不成立 (cha {cha_sim:.4f} ≥ enc {enc_sim:.4f})")

    # ── Top extreme pairs（手动 review 候选漂移）──
    print(f"\n{'─'*60}")
    print(f"  Top-3 最不同配对（手动 review 候选漂移）")
    print(f"{'─'*60}\n")

    for baby, r in results.items():
        if 'error' in r or not r['extreme_pairs']:
            continue
        print(f"\n  [{baby}] 最低相似度 Top-3:")
        for ep in r['extreme_pairs'][:3]:
            print(f"\n    Epoch {ep['from_epoch']} → {ep['to_epoch']} (sim={ep['difflib']:.4f}):")
            print(f"      {ep['from_epoch']}: {ep['from_identity'][:80]}")
            print(f"      {ep['to_epoch']}:   {ep['to_identity'][:80]}")

    # ── 写输出 ──
    output_path = OUTPUT_DIR / "identity_drift_analysis.json"
    output_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False, default=str),
        encoding='utf-8',
    )
    print(f"\n  状态快照: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
