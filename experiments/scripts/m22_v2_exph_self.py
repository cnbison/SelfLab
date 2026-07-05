"""
M2.2 v2 补跑 — 1000 epoch × Experience Encoder + H_self（洞察 34/35 验证）

目的：
  在 E4 (M22_TRIPLETS_REPORT.md) 已验证的 1000 epoch × 真实 LLM 三胞胎人格分化基础上，
  补建 Phase 3 架构落地的两项加法模块的数据：
  - Experience Encoder（Step 2.5）：跟踪 meaning 字段演化（每 50 epoch 采样）
  - H_self 度量（Step 16）：跟踪 H_self / H_value / H_identity / H_narrative 全曲线

相对 E4 的改动（增量，不破坏 E4）：
  - 输出目录：m22_v2_exph_self/（与 E4 m22_triplets/ 并列）
  - timeseries 增加 H_self / H_value / H_identity / H_narrative
  - 新增 meaning_samples 数组（每 50 epoch 1 个 meaning）
  - 结果 dict 增加 H_self_start / H_self_end / H_self_reduction_rate

执行模式（沿用 E4 验证有效的 4 × 250 chunk 模式）：
  - 每个 chunk 独立 SGELLMClient（fresh server session）
  - Chunk 间 sleep 5 分钟让 server 恢复
  - 每 100 epoch checkpoint JSON
  - 用 run_chunks_v2.sh 串行 12 chunks

CLI：
  # 单 chunk（烟测用）
  python m22_v2_exph_self.py --baby encouraged --chunk-index 0

  # 全部
  ./run_chunks_v2.sh

关联：
  - [sge/RUNTIME_AUDIT.md](../../sge/RUNTIME_AUDIT.md)
  - [SGE-Key-Insights 洞察 34/35](../../SGE-Key-Insights.md)
  - [M22_TRIPLETS_REPORT.md](../M22_TRIPLETS_REPORT.md)（E4 原始版本对照）
"""

import argparse
import json
import sys
import math
import time
from collections import Counter
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "sge"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sge.baseline import (
    Agent, DriveMetabolism, ValueLayer, HawkingDecay, MemoryCrystallizer,
    SGE_DEFAULT_VALUES, _load_drives,
)
from sge.event import EventGenerator
from sge.identity import IdentityLayer
from sge.narrative import NarrativeBuilder
from sge.orchestrator import SGEOrchestrator
from sge.metrics import compute_self_entropy, entropy_reduction_rate
from sge.llm_client import make_llm_client
from m22_triplet_config import load_triplet_config, TRIPLET_CONFIGS


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "m22_v2_exph_self"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# 沿用 E4 seed 分配（让事件流差异成为唯一变量，与 E4 可比）
SEEDS = {
    'encouraged': 42,
    'challenged': 7,
    'uncertain': 123,
}


def run_one_baby(
    name: str,
    yaml_path: str,
    seed: int,
    n_steps: int = 250,
    sample_every: int = 50,
    chunk_idx: int = 0,
    start_epoch: int = 0,
) -> dict:
    """跑 1 个 triplet baby 的 N epochs 真实 LLM（chunk 模式）

    在 E4 基础上新增：
      - H_self 写入 timeseries（每 sample_every epoch）
      - meaning_samples 数组（每 sample_every epoch 采 1 个）
    """
    print(f"\n{'═'*60}")
    print(f"  M2.2 v2 — Baby: {name}  (seed={seed}, chunk={chunk_idx}, "
          f"epochs={start_epoch}-{start_epoch+n_steps-1})")
    print(f"  跟踪: Experience.meaning + H_self")
    print(f"{'═'*60}\n")

    cfg = load_triplet_config(yaml_path)
    print(f"  baby_id={cfg['baby_id']}, "
          f"value_conflict_prob={cfg['value_conflict_prob']}, "
          f"distribution 阶段数={len(cfg['distribution_by_epoch'])}")

    # ── LLM 客户端 + 预热 ──
    llm = make_llm_client(provider='minimax', verbose=False)
    print(f"  ✓ LLM 客户端就绪")
    llm.warmup(n_calls=2)

    # ── 初始化组件 ──
    drives = _load_drives()
    value_layer = ValueLayer(values=SGE_DEFAULT_VALUES)
    hawking = HawkingDecay(gamma=0.01, clock=0.0)
    crystallizer = MemoryCrystallizer(n_dims=11)
    agent = Agent(
        seed=seed, drives=drives, value_layer=value_layer,
        hawking=hawking, crystallizer=crystallizer, crystallize_every=10,
    )
    metabolism = DriveMetabolism(drives=drives)
    event_gen = EventGenerator(
        baby_id=cfg['baby_id'],
        seed=seed,
        value_conflict_prob=cfg['value_conflict_prob'],
        distribution_by_epoch=cfg['distribution_by_epoch'],
    )
    identity_layer = IdentityLayer(crystallize_every_n_epochs=20)
    narrative_builder = NarrativeBuilder(build_every_n_epochs=20)

    orchestrator = SGEOrchestrator(
        agent=agent, value_layer=value_layer,
        drive_metabolism=metabolism, event_generator=event_gen,
        identity_layer=identity_layer, narrative_builder=narrative_builder,
        hawking=hawking, crystallizer=crystallizer, crystallize_every=10,
        use_real_llm=True, llm=llm, llm_provider='minimax',
        verbose=True,
    )

    # ── 跑 N epochs（手动循环 + live timeseries + checkpoint writes）──
    print(f"\n  开始跑 {n_steps} epoch...")
    orchestrator._n_epochs_hint = n_steps
    timeseries_live = []
    meaning_samples = []  # 新增：每 sample_every 采 1 个
    traces = []
    identity_so_far_list = []
    narrative_so_far_list = []
    checkpoint_interval = 100
    t0 = time.time()

    # 记录起点 H_self（用于 reduction_rate）
    h_self_start = None
    h_self_end = None

    for epoch_idx in range(n_steps):
        absolute_epoch = epoch_idx + start_epoch
        trace = orchestrator.step(absolute_epoch)
        traces.append(trace)

        # 累积 identity/narrative
        if trace.identity is not None:
            identity_so_far_list.append({
                'epoch': trace.epoch, 'identity': trace.identity,
                'length_chars': len(trace.identity),
            })
        if trace.narrative is not None:
            narrative_so_far_list.append({
                'epoch': trace.epoch, 'narrative': trace.narrative,
                'length_chars': len(trace.narrative),
            })

        # ── 采样点（每 sample_every）──
        if (epoch_idx + 1) % sample_every == 0 or epoch_idx == 0:
            se = trace.self_entropy or compute_self_entropy(
                value_layer=value_layer,
                identity_layer=identity_layer,
                narrative_builder=narrative_builder,
            )
            sample = {
                'epoch': absolute_epoch,
                'value_magnitude': round(value_layer.magnitude(), 4),
                'frustration_total': round(metabolism.total(), 4),
                'frustration_per_drive': {d: round(v, 4) for d, v in metabolism.frustration.items()},
                'hawking_size': len(hawking),
                'hawking_min_weight': min((m['weight'] for m in hawking.memory), default=0.0),
                'crystallize_clusters': len(crystallizer),
                'phase_xition_so_far': sum(1 for tt in traces if tt.phase_xition),
                'identity_so_far': sum(1 for tt in traces if tt.identity is not None),
                'narrative_so_far': sum(1 for tt in traces if tt.narrative is not None),
                # ★ 新增 H_self 系列
                'H_self': round(se['H_self'], 4),
                'H_value': round(se['H_value'], 4),
                'H_identity': round(se['H_identity'], 4),
                'H_narrative': round(se['H_narrative'], 4),
            }
            timeseries_live.append(sample)
            if h_self_start is None:
                h_self_start = se['H_self']
            h_self_end = se['H_self']

            # ★ 新增 meaning 采样
            meaning_samples.append({
                'epoch': absolute_epoch,
                'event_type': trace.event.get('event_type', 'unknown'),
                'meaning': (trace.experience or {}).get('meaning', ''),
                'emotion_valence': (trace.experience or {}).get('emotion', {}).get('valence'),
                'emotion_arousal': (trace.experience or {}).get('emotion', {}).get('arousal'),
                'uncertainty': (trace.experience or {}).get('uncertainty'),
            })

            elapsed_so_far = time.time() - t0
            s = llm.retry_stats
            retry_pct = (s['calls_with_retry'] / s['total_calls'] * 100) if s['total_calls'] > 0 else 0
            print(
                f"  [checkpoint epoch {absolute_epoch+1}/{start_epoch+n_steps}] "
                f"|val|={value_layer.magnitude():.3f} "
                f"H_self={se['H_self']:.3f} "
                f"PT={sum(1 for tt in traces if tt.phase_xition)} "
                f"calls={llm.call_count} retry={retry_pct:.1f}%",
                flush=True,
            )

        # ── Checkpoint 写入（每 100 epoch）──
        if (epoch_idx + 1) % checkpoint_interval == 0:
            checkpoint_path = OUTPUT_DIR / f"{name}_chunk{chunk_idx}_checkpoint.json"
            checkpoint_data = {
                'name': name,
                'baby_id': cfg['baby_id'],
                'seed': seed,
                'chunk_idx': chunk_idx,
                'start_epoch': start_epoch,
                'checkpoint_epoch': absolute_epoch + 1,
                'checkpoint_timestamp': time.time(),
                'elapsed_seconds_so_far': round(time.time() - t0, 1),
                'llm_call_count': llm.call_count,
                'value_magnitude_current': round(value_layer.magnitude(), 4),
                'phase_xition_count': sum(1 for tt in traces if tt.phase_xition),
                'identity_count': len(identity_so_far_list),
                'narrative_count': len(narrative_so_far_list),
                'crystallize_count': sum(1 for tt in traces if tt.crystallize_result is not None),
                'hawking_size': len(hawking),
                'hawking_min_weight': min((m['weight'] for m in hawking.memory), default=0.0),
                'crystallizer_clusters': len(crystallizer),
                'final_frustration_per_drive_so_far': {d: round(v, 4) for d, v in metabolism.frustration.items()},
                'final_value_state_so_far': {k: round(v, 4) for k, v in value_layer.value_state.items()},
                'identity_history_so_far': identity_so_far_list,
                'narrative_history_so_far': narrative_so_far_list,
                'llm_stats': llm.stats(),
                'status': 'in_progress',
                # ★ 新增：H_self 系列 + meaning 采样
                'h_self_so_far': h_self_end,
                'h_self_start': h_self_start,
                'meaning_samples_so_far': meaning_samples,
                'timeseries_so_far': timeseries_live,
            }
            checkpoint_path.write_text(
                json.dumps(checkpoint_data, indent=2, ensure_ascii=False, default=str),
                encoding='utf-8',
            )
            print(f"    [checkpoint saved] {checkpoint_path.name}", flush=True)

    elapsed = time.time() - t0

    # ── Event distribution ──
    event_types = [t.event['event_type'] for t in traces]
    event_dist = Counter(event_types)

    # ── 关键 epoch 节点的 value_state ──
    key_epochs = [49, 149, 249]  # chunk 内相对 epoch
    key_snapshots = {}
    for ke in key_epochs:
        if ke < len(traces):
            vs = traces[ke].value_state_after
            key_snapshots[ke + 1] = {k: round(v, 4) for k, v in vs.items()}

    # ── 收集结果 ──
    reduction_rate = entropy_reduction_rate(h_self_start or 0.0, h_self_end or 0.0)
    result = {
        'name': name,
        'baby_id': cfg['baby_id'],
        'seed': seed,
        'chunk_idx': chunk_idx,
        'start_epoch': start_epoch,
        'n_steps': n_steps,
        'elapsed_seconds': round(elapsed, 1),
        'llm_call_count': llm.call_count,
        'llm_stats': llm.stats(),
        'value_magnitude_final': round(value_layer.magnitude(), 4),
        'phase_xition_count': sum(1 for t in traces if t.phase_xition),
        'phase_xition_epochs': [t.epoch for t in traces if t.phase_xition],
        'identity_count': sum(1 for t in traces if t.identity is not None),
        'narrative_count': sum(1 for t in traces if t.narrative is not None),
        'crystallize_count': sum(1 for t in traces if t.crystallize_result is not None),
        'hawking_final_size': len(hawking),
        'crystallizer_final_clusters': len(crystallizer),
        'final_frustration_per_drive': {d: round(v, 4) for d, v in metabolism.frustration.items()},
        'final_value_state': {k: round(v, 4) for k, v in value_layer.value_state.items()},
        'event_distribution': dict(event_dist),
        'success_rate': round(event_dist.get('success', 0) / len(traces), 4),
        'failure_rate': round(event_dist.get('failure', 0) / len(traces), 4),
        'timeseries': timeseries_live,
        'key_value_snapshots': key_snapshots,
        # ★ 新增：H_self 系列
        'H_self_start': round(h_self_start or 0.0, 4),
        'H_self_end': round(h_self_end or 0.0, 4),
        'H_self_reduction_rate': round(reduction_rate, 4),
        # ★ 新增：meaning 采样
        'meaning_samples': meaning_samples,
    }

    # ── Identity/Narrative 历史 ──
    identity_history = [
        {'epoch': t.epoch, 'identity': t.identity, 'length_chars': len(t.identity)}
        for t in traces if t.identity is not None
    ]
    narrative_history = [
        {'epoch': t.epoch, 'narrative': t.narrative, 'length_chars': len(t.narrative)}
        for t in traces if t.narrative is not None
    ]

    # ── 写输出 ──
    (OUTPUT_DIR / f"{name}_chunk{chunk_idx}_result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str),
        encoding='utf-8',
    )
    (OUTPUT_DIR / f"{name}_chunk{chunk_idx}_identity_history.json").write_text(
        json.dumps(identity_history, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    (OUTPUT_DIR / f"{name}_chunk{chunk_idx}_narrative_history.json").write_text(
        json.dumps(narrative_history, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    (OUTPUT_DIR / f"{name}_chunk{chunk_idx}_meaning_samples.json").write_text(
        json.dumps(meaning_samples, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    (OUTPUT_DIR / f"{name}_chunk{chunk_idx}_checkpoint.json").unlink(missing_ok=True)

    print(f"\n  ✓ {name} chunk {chunk_idx} 完成 "
          f"(epochs {start_epoch}-{start_epoch+n_steps-1}, "
          f"{elapsed:.1f}s = {elapsed/n_steps:.1f}s/epoch, "
          f"{llm.call_count} LLM 调用)")
    print(f"    |val|={result['value_magnitude_final']}, "
          f"H_self: {h_self_start:.3f} → {h_self_end:.3f} "
          f"(ε降 {(reduction_rate*100):+.1f}%), "
          f"PT={result['phase_xition_count']}, "
          f"meaning_samples={len(meaning_samples)}")
    s = llm.retry_stats
    print(f"    retry: {s['calls_with_retry']}/{s['total_calls']} calls needed retry "
          f"({s['calls_with_retry']/s['total_calls']*100:.1f}%), "
          f"total wait {s['total_wait_seconds']:.1f}s")

    return result


def compute_personality_divergence(results: list) -> dict:
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

    vectors = {r['name']: r['final_value_state'] for r in results}
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
    parser = argparse.ArgumentParser(
        description='M2.2 v2 — 1000 epoch × Experience Encoder + H_self（chunk 模式）',
    )
    parser.add_argument('--baby', choices=['encouraged', 'challenged', 'uncertain'],
                        help='指定 baby（默认跑全部 3 个）')
    parser.add_argument('--chunk-index', type=int, default=None,
                        help='chunk 编号 (0/1/2/3)，未指定则跑该 baby 的全部 chunks')
    parser.add_argument('--start-epoch', type=int, default=None,
                        help='chunk 起始 epoch（默认从 0 或 chunk_index * chunk_size）')
    parser.add_argument('--n-steps', type=int, default=None,
                        help='此 chunk 跑多少 epoch（默认从 chunk_size 推算）')
    parser.add_argument('--chunk-size', type=int, default=250,
                        help='每个 chunk 的 epoch 数（默认 250）')
    parser.add_argument('--aggregate-only', action='store_true',
                        help='只跑聚合（不跑新 chunks）')
    parser.add_argument('--max-chunks-per-baby', type=int, default=4,
                        help='每 baby 最多跑几个 chunk（默认 4 = 全 1000 epoch）')
    args = parser.parse_args()

    print("═" * 60)
    print("  M2.2 v2 — Experience Encoder + H_self 补跑")
    print("═" * 60)
    print(f"  执行模式: 串行 chunk（chunk_size={args.chunk_size}）")
    print(f"  Seed 分配: {SEEDS}")
    print(f"  Output dir: {OUTPUT_DIR}")
    print()

    if args.aggregate_only:
        return aggregate_results()

    if args.baby:
        babies_to_run = [(args.baby, TRIPLET_CONFIGS[args.baby])]
    else:
        babies_to_run = list(TRIPLET_CONFIGS.items())

    total_t0 = time.time()
    all_results = []
    failed = []

    for baby_name, yaml_path in babies_to_run:
        if args.chunk_index is not None:
            chunks_to_run = [args.chunk_index]
        else:
            chunks_to_run = list(range(args.max_chunks_per_baby))

        for chunk_idx in chunks_to_run:
            result_path = OUTPUT_DIR / f"{baby_name}_chunk{chunk_idx}_result.json"
            if result_path.exists():
                print(f"\n  ⊙ Skip {baby_name} chunk {chunk_idx}（已有 {result_path.name}）")
                continue

            start_epoch = args.start_epoch if args.start_epoch is not None else chunk_idx * args.chunk_size
            n_steps = args.n_steps if args.n_steps is not None else args.chunk_size

            try:
                result = run_one_baby(
                    baby_name, yaml_path,
                    seed=SEEDS[baby_name],
                    n_steps=n_steps,
                    chunk_idx=chunk_idx,
                    start_epoch=start_epoch,
                )
                all_results.append(result)
            except Exception as e:
                print(f"\n  ✗ {baby_name} chunk {chunk_idx} 崩溃: "
                      f"{type(e).__name__}: {str(e)[:200]}")
                failed.append({'baby': baby_name, 'chunk': chunk_idx,
                               'error': str(e)[:200]})

    total_elapsed = time.time() - total_t0

    if all_results:
        print(f"\n  ✓ {len(all_results)} chunks 完成 ({total_elapsed/60:.1f} min)")
    if failed:
        print(f"  ⚠ {len(failed)} chunks 失败")

    print(f"\n  下一步: 运行 --aggregate-only 聚合结果")
    return 0


def aggregate_results() -> int:
    """合并所有 chunks 的 JSON 成最终 per-baby result"""
    print("\n  聚合 chunks...")

    babies = ['encouraged', 'challenged', 'uncertain']
    aggregated = {}

    for baby in babies:
        chunks = []
        for ci in range(4):
            p = OUTPUT_DIR / f"{baby}_chunk{ci}_result.json"
            if p.exists():
                chunks.append(json.loads(p.read_text(encoding='utf-8')))

        if not chunks:
            print(f"  ⊙ {baby}: 无 chunks 数据")
            continue

        # 合并 timeseries + meaning_samples + 重算 H_self reduction_rate
        all_ts = []
        all_meanings = []
        for c in chunks:
            all_ts.extend(c.get('timeseries', []))
            all_meanings.extend(c.get('meaning_samples', []))

        # 取首尾 sample 计算 H_self reduction
        h_start = chunks[0].get('H_self_start', 0.0)
        h_end = chunks[-1].get('H_self_end', 0.0)
        reduction = entropy_reduction_rate(h_start, h_end) if h_start > 0 else 0.0

        # 用最后一 chunk 的最终状态
        last = chunks[-1]
        aggregated[baby] = {
            'baby_id': last.get('baby_id'),
            'seed': last.get('seed'),
            'chunks_completed': len(chunks),
            'chunks_total': 4,
            'elapsed_seconds_total': sum(c.get('elapsed_seconds', 0) for c in chunks),
            'llm_call_count_total': sum(c.get('llm_call_count', 0) for c in chunks),
            'value_magnitude_final': last.get('value_magnitude_final'),
            'final_value_state': last.get('final_value_state'),
            'phase_xition_count': sum(c.get('phase_xition_count', 0) for c in chunks),
            'phase_xition_epochs': [e for c in chunks for e in c.get('phase_xition_epochs', [])],
            'identity_count': sum(c.get('identity_count', 0) for c in chunks),
            'narrative_count': sum(c.get('narrative_count', 0) for c in chunks),
            'crystallize_count': sum(c.get('crystallize_count', 0) for c in chunks),
            'success_rate': last.get('success_rate'),
            'failure_rate': last.get('failure_rate'),
            'event_distribution': dict(Counter(
                t for c in chunks for t in c.get('event_distribution', {}).keys()
            )),
            # ★ H_self 系列
            'H_self_start': h_start,
            'H_self_end': h_end,
            'H_self_reduction_rate': round(reduction, 4),
            'H_self_reduction_pct': round(reduction * 100, 2),
            'H_self_prd_6_passed': reduction > 0.30,  # PRD §6 验收
            'timeseries': all_ts,
            'meaning_samples': all_meanings,
            'meaning_count': len(all_meanings),
        }

    if not aggregated:
        print("  ✗ 无任何 baby 数据")
        return 1

    # Personality divergence（基于 final_value_state）
    divergence = compute_personality_divergence([
        {'name': k, 'final_value_state': v['final_value_state']}
        for k, v in aggregated.items() if v.get('final_value_state')
    ])

    summary = {
        'experiment': 'm22_v2_exph_self',
        'execution_mode': 'chunk',
        'chunk_size': 250,
        'aggregated': aggregated,
        'personality_divergence': divergence,
    }
    (OUTPUT_DIR / "v2_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding='utf-8',
    )

    print(f"\n  ── 聚合结果 ──")
    print(f"  {'Baby':<12} {'chunks':<8} {'H_self':<14} {'ε降%':<8} {'PRD§6':<8} {'|val|':<8}")
    for baby in babies:
        if baby not in aggregated:
            continue
        a = aggregated[baby]
        print(f"  {baby:<12} {a['chunks_completed']}/4      "
              f"{a['H_self_start']:.3f} → {a['H_self_end']:.3f}  "
              f"{a['H_self_reduction_pct']:>+6.1f}  "
              f"{'✓' if a['H_self_prd_6_passed'] else '✗'}      "
              f"{a['value_magnitude_final']:.3f}")
    if divergence.get('pairwise_cosine_distance'):
        print(f"\n  Personality divergence (avg): {divergence['avg_divergence']:.4f}")

    print(f"\n  状态快照: {OUTPUT_DIR}/v2_summary.json")
    return 0


if __name__ == "__main__":
    if '--aggregate-only' in sys.argv:
        sys.exit(aggregate_results())
    sys.exit(main())