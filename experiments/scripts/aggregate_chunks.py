"""
M2.2 E4 chunk aggregator — 合并 4 个 chunk 的 JSON 成最终 per-baby result

读取：experiments/output/m22_triplets/{baby}_chunk{0,1,2,3}_*.json
输出：experiments/output/m22_triplets/{baby}_result.json + identity/narrative history
      + triplets_summary.json（3 baby 对比）

合并规则：
- timeseries：按 epoch 排序拼接
- identity_history / narrative_history：按 epoch 排序去重
- final_*：用 chunk 3 的最终值
- phase_xition_epochs：4 个 chunk 拼接
- llm_stats：累加各 chunk

用法：
    python aggregate_chunks.py
"""

import json
import sys
from pathlib import Path


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "m22_triplets"
BABIES = ["encouraged", "challenged", "uncertain"]
CHUNKS = [0, 1, 2, 3]


def load_chunk(baby: str, chunk_idx: int) -> dict | None:
    """加载单 chunk result JSON，若不存在返回 None"""
    path = OUTPUT_DIR / f"{baby}_chunk{chunk_idx}_result.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def load_chunk_identity_history(baby: str, chunk_idx: int) -> list | None:
    path = OUTPUT_DIR / f"{baby}_chunk{chunk_idx}_identity_history.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def load_chunk_narrative_history(baby: str, chunk_idx: int) -> list | None:
    path = OUTPUT_DIR / f"{baby}_chunk{chunk_idx}_narrative_history.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def aggregate_baby(baby: str) -> dict | None:
    """合并某 baby 的所有 chunks"""
    chunks = []
    for ci in CHUNKS:
        c = load_chunk(baby, ci)
        if c is None:
            print(f"  ⚠ {baby} chunk {ci} 缺失")
            continue
        chunks.append((ci, c))

    if not chunks:
        print(f"  ✗ {baby} 无任何 chunk")
        return None

    print(f"  ✓ {baby}: 合并 {len(chunks)} chunks ({[c[0] for c in chunks]})")

    # 排序按 chunk index
    chunks.sort(key=lambda x: x[0])
    last_ci, last_chunk = chunks[-1]

    # ── Timeseries 拼接（按 epoch 排序）──
    timeseries = []
    for ci, c in chunks:
        for row in c.get('timeseries', []):
            timeseries.append(row)
    timeseries.sort(key=lambda x: x['epoch'])

    # ── Identity/Narrative history 拼接 ──
    identity_history = []
    narrative_history = []
    for ci in CHUNKS:
        ih = load_chunk_identity_history(baby, ci)
        if ih:
            identity_history.extend(ih)
        nh = load_chunk_narrative_history(baby, ci)
        if nh:
            narrative_history.extend(nh)
    identity_history.sort(key=lambda x: x['epoch'])
    narrative_history.sort(key=lambda x: x['epoch'])

    # ── Phase transition epochs 拼接 ──
    phase_xition_epochs = []
    for ci, c in chunks:
        phase_xition_epochs.extend(c.get('phase_xition_epochs', []))
    phase_xition_epochs.sort()

    # ── LLM stats 累加 ──
    total_calls = sum(c['llm_call_count'] for ci, c in chunks)
    # retry_stats 取最后一个 chunk 的（最完整）
    llm_stats = last_chunk.get('llm_stats', {})

    # ── Final state 用最后一个 chunk 的最终值 ──
    # ── Event distribution 累加 ──
    event_dist = {}
    for ci, c in chunks:
        for k, v in c.get('event_distribution', {}).items():
            event_dist[k] = event_dist.get(k, 0) + v
    total_events = sum(event_dist.values())
    success_rate = round(event_dist.get('success', 0) / total_events, 4) if total_events > 0 else 0
    failure_rate = round(event_dist.get('failure', 0) / total_events, 4) if total_events > 0 else 0

    aggregated = {
        'baby': baby,
        'n_chunks': len(chunks),
        'chunk_indices': [ci for ci, _ in chunks],
        'total_llm_calls': total_calls,
        'llm_stats': llm_stats,
        # Final state from last chunk
        'value_magnitude_final': last_chunk['value_magnitude_final'],
        'phase_xition_count': len(phase_xition_epochs),
        'phase_xition_epochs': phase_xition_epochs,
        'identity_count': len(identity_history),
        'narrative_count': len(narrative_history),
        'crystallize_count': sum(c['crystallize_count'] for ci, c in chunks),
        'hawking_final_size': last_chunk['hawking_final_size'],
        'crystallizer_final_clusters': last_chunk['crystallizer_final_clusters'],
        'final_frustration_per_drive': last_chunk['final_frustration_per_drive'],
        'final_value_state': last_chunk['final_value_state'],
        'event_distribution': event_dist,
        'success_rate': success_rate,
        'failure_rate': failure_rate,
        'timeseries': timeseries,
        'identity_history': identity_history,
        'narrative_history': narrative_history,
        # Per-chunk summary
        'per_chunk_summary': [
            {
                'chunk_idx': ci,
                'elapsed_seconds': c['elapsed_seconds'],
                'llm_call_count': c['llm_call_count'],
                'pt_count': c['phase_xition_count'],
                'identity_count': c['identity_count'],
                'narrative_count': c['narrative_count'],
            }
            for ci, c in chunks
        ],
    }
    return aggregated


def compute_personality_divergence(results: list) -> dict:
    """计算 3 baby 间 personality_divergence（cosine distance on final value_state）"""
    import math

    def cosine_dist(a: dict, b: dict) -> float:
        keys = sorted(set(a.keys()) & set(b.keys()))
        va = [a[k] for k in keys]
        vb = [b[k] for k in keys]
        dot = sum(x * y for x, y in zip(va, vb))
        norm_a = math.sqrt(sum(x * x for x in va))
        norm_b = math.sqrt(sum(x * x for x in vb))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return 1.0 - dot / (norm_a * norm_b)

    vectors = {r['baby']: r['final_value_state'] for r in results}
    names = list(vectors.keys())
    pairwise = {}
    for i, n1 in enumerate(names):
        for j, n2 in enumerate(names):
            if i < j:
                pairwise[f'{n1}_vs_{n2}'] = round(
                    cosine_dist(vectors[n1], vectors[n2]), 4
                )
    avg = round(sum(pairwise.values()) / len(pairwise), 4) if pairwise else 0
    return {'pairwise_cosine_distance': pairwise, 'avg_divergence': avg}


def main() -> int:
    print("=" * 60)
    print("  M2.2 E4 Chunk Aggregator")
    print("=" * 60)
    print(f"  Output dir: {OUTPUT_DIR}")
    print()

    results = []
    for baby in BABIES:
        print(f"  Aggregating {baby}...")
        agg = aggregate_baby(baby)
        if agg is not None:
            results.append(agg)
            # 写 per-baby result
            (OUTPUT_DIR / f"{baby}_result.json").write_text(
                json.dumps(agg, indent=2, ensure_ascii=False, default=str),
                encoding='utf-8',
            )
            # 单独写 identity/narrative history
            (OUTPUT_DIR / f"{baby}_identity_history.json").write_text(
                json.dumps(agg['identity_history'], indent=2, ensure_ascii=False),
                encoding='utf-8',
            )
            (OUTPUT_DIR / f"{baby}_narrative_history.json").write_text(
                json.dumps(agg['narrative_history'], indent=2, ensure_ascii=False),
                encoding='utf-8',
            )
            print(f"    → {baby}_result.json")

    if not results:
        print("\n  ⚠ 无任何 baby 数据")
        return 1

    # ── 三胞胎对比 summary ──
    divergence = compute_personality_divergence(results)

    summary = {
        'experiment': 'm22_triplets',
        'execution_mode': 'chunked_serial',
        'chunk_size': 250,
        'n_babies': len(results),
        'total_llm_calls': sum(r['total_llm_calls'] for r in results),
        'babies': {
            r['baby']: {
                'value_magnitude_final': r['value_magnitude_final'],
                'phase_xition_count': r['phase_xition_count'],
                'identity_count': r['identity_count'],
                'narrative_count': r['narrative_count'],
                'success_rate': r['success_rate'],
                'failure_rate': r['failure_rate'],
                'final_value_state': r['final_value_state'],
                'final_frustration_per_drive': r['final_frustration_per_drive'],
                'event_distribution': r['event_distribution'],
                'per_chunk_summary': r['per_chunk_summary'],
            }
            for r in results
        },
        'personality_divergence': divergence,
    }

    summary_path = OUTPUT_DIR / "triplets_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding='utf-8',
    )

    # ── 对比表 ──
    print(f"\n{'─'*60}")
    print(f"  M2.2 三胞胎对比")
    print(f"{'─'*60}\n")

    print(f"{'Baby':<12} {'chunks':<7} {'|val|':<8} {'PT':<5} {'Id':<5} {'Nar':<5} "
          f"{'Succ%':<8} {'Fail%':<8} {'calls'}")
    for r in results:
        n_chunks = r['n_chunks']
        print(f"{r['baby']:<12} {n_chunks:<7} {r['value_magnitude_final']:<8.3f} "
              f"{r['phase_xition_count']:<5} {r['identity_count']:<5} "
              f"{r['narrative_count']:<5} {r['success_rate']:<8.1%} "
              f"{r['failure_rate']:<8.1%} {r['total_llm_calls']}")

    print(f"\nPersonality divergence (cosine distance):")
    for pair, dist in divergence['pairwise_cosine_distance'].items():
        print(f"  {pair}: {dist:.4f}")
    print(f"  平均: {divergence['avg_divergence']:.4f}")

    print(f"\n  状态快照: {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
