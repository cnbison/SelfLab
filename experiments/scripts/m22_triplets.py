"""
M2.2 主实验（E4）— 3 baby × 1000 epoch 真实 LLM 串行（分 chunk 模式）

目的：
  验证"经历 → 解释 → 人格"假设在 1000 epoch × 真实 LLM 下成立。
  3 个 AI 婴儿在不同事件流下形成显著不同的人格。

执行模式（v3.1 — chunk 模式）：
  - 单次跑 1000 epoch 已被验证不稳定（MiniMax server 长时间后 SSL EOF/timeout）
  - 改为 4 chunks × 250 epochs，每个 chunk 独立 SGELLMClient（fresh server session）
  - Chunk 间 sleep 5 分钟让 server 恢复
  - 每个 chunk 输出到 {name}_chunk{N}_*.json
  - 跑完后用 aggregate_chunks.py 合并成最终 {name}_result.json

CLI 用法：
  # 单 chunk
  python m22_triplets.py --baby encouraged --chunk-index 0

  # 全部 12 chunks（用 wrapper）
  ./run_chunks.sh

关联：[SGE-M22-Implementation-Plan.md §E4](../research/sge-feasibility/SGE-M22-Implementation-Plan.md)
"""

import argparse
import json
import sys
import math
import time
from collections import Counter
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sge_baseline import (
    Agent, DriveMetabolism, ValueLayer, HawkingDecay, MemoryCrystallizer,
    SGE_DEFAULT_VALUES, _load_drives,
)
from _sge_event import EventGenerator
from _sge_identity import IdentityLayer
from _sge_narrative import NarrativeBuilder
from _sge_orchestrator import SGEOrchestrator
from _sge_llm_client import make_llm_client
from m22_triplet_config import load_triplet_config, TRIPLET_CONFIGS


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "m22_triplets"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# E4 seed 分配：每个 baby 不同 seed，让事件流差异成为唯一变量
SEEDS = {
    'encouraged': 42,
    'challenged': 7,
    'uncertain': 123,
}


# ── 单 baby 跑 1000 epoch ─────────────────────────


def run_one_baby(
    name: str,
    yaml_path: str,
    seed: int,
    n_steps: int = 1000,
    sample_every: int = 50,  # 1000 epoch / 50 = 20 个采样点
    chunk_idx: int = 0,  # 0-indexed chunk 编号
    start_epoch: int = 0,  # 此 chunk 开始的 epoch（0/250/500/750）
) -> dict:
    """跑 1 个 triplet baby 的 N epochs 真实 LLM（chunk 模式）

    Args:
        name: baby 名（encouraged/challenged/uncertain）
        yaml_path: triplet yaml 路径
        seed: baby seed
        n_steps: 此 chunk 跑多少 epoch（默认 250）
        sample_every: 每 N epoch 采样一次
        chunk_idx: chunk 编号（0/1/2/3），用于文件命名
        start_epoch: 此 chunk 在 1000 epoch 中的起始位置
    """
    print(f"\n{'═'*60}")
    print(f"  Baby: {name}  (seed={seed}, chunk={chunk_idx}, "
          f"epochs={start_epoch}-{start_epoch+n_steps-1})")
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

    # ── 跑 1000 epoch（手动循环 + live timeseries + checkpoint writes）──
    print(f"\n  开始跑 {n_steps} epoch...")
    orchestrator._n_epochs_hint = n_steps
    timeseries_live = []
    traces = []
    identity_so_far_list = []   # 累积 identity 触发（checkpoint 用）
    narrative_so_far_list = []  # 累积 narrative 触发（checkpoint 用）
    checkpoint_interval = 100   # 每 100 epoch 写一次 checkpoint JSON（M2.2 E4 hang 教训）
    t0 = time.time()
    for epoch_idx in range(n_steps):
        # chunk 模式：orchestrator 收到的是真实 epoch 号（0-999）
        # 而非 chunk 内的相对编号（0-249）
        absolute_epoch = epoch_idx + start_epoch
        trace = orchestrator.step(absolute_epoch)
        traces.append(trace)

        # 累积 identity/narrative（每步都检查，简单且数据量小）
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
            timeseries_live.append({
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
            })
            elapsed_so_far = time.time() - t0
            s = llm.retry_stats
            retry_pct = (s['calls_with_retry'] / s['total_calls'] * 100) if s['total_calls'] > 0 else 0
            print(
                f"  [checkpoint epoch {absolute_epoch+1}/{start_epoch+n_steps}] "
                f"|val|={value_layer.magnitude():.3f} "
                f"frustration={metabolism.total():.2f} "
                f"PT={sum(1 for tt in traces if tt.phase_xition)} "
                f"calls={llm.call_count} retry={retry_pct:.1f}%",
                flush=True,
            )

        # ── Checkpoint 写入（每 100 epoch）──
        # 即使后续 hang/kill，最多丢 100 epoch 数据（约 17 min @ 10s/epoch）
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

    # ── 关键 epoch 节点的 value_state（用于跨 baby 对比）──
    key_epochs = [99, 299, 499, 699, 999]  # 0-indexed: epoch 100/300/500/700/1000
    key_snapshots = {}
    for ke in key_epochs:
        if ke < len(traces):
            vs = traces[ke].value_state_after
            key_snapshots[ke + 1] = {k: round(v, 4) for k, v in vs.items()}

    # ── 收集结果 ──
    result = {
        'name': name,
        'baby_id': cfg['baby_id'],
        'seed': seed,
        'n_steps': n_steps,
        'elapsed_seconds': round(elapsed, 1),
        'llm_call_count': llm.call_count,
        'llm_stats': llm.stats(),  # 含 retry stats
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

    # ── 写输出（chunk 模式：含 chunk_idx）──
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
    # 清理 chunk checkpoint（成功完成时）
    (OUTPUT_DIR / f"{name}_chunk{chunk_idx}_checkpoint.json").unlink(missing_ok=True)

    print(f"\n  ✓ {name} chunk {chunk_idx} 完成 "
          f"(epochs {start_epoch}-{start_epoch+n_steps-1}, "
          f"{elapsed:.1f}s = {elapsed/n_steps:.1f}s/epoch, "
          f"{llm.call_count} LLM 调用)")
    print(f"    |val|={result['value_magnitude_final']}, "
          f"PT={result['phase_xition_count']}, "
          f"success_rate={result['success_rate']:.1%}, "
          f"failure_rate={result['failure_rate']:.1%}")
    s = llm.retry_stats
    print(f"    retry: {s['calls_with_retry']}/{s['total_calls']} calls needed retry "
          f"({s['calls_with_retry']/s['total_calls']*100:.1f}%), "
          f"total wait {s['total_wait_seconds']:.1f}s")

    return result


# ── 三胞胎对比 ─────────────────────────────────────


def compute_personality_divergence(results: list) -> dict:
    """计算 3 baby 间 personality_divergence"""
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
        description='M2.2 E4 — 3 baby × 1000 epoch 真实 LLM (chunk 模式)',
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
                        help='只跑聚合（不跑新 chunks），适合最后阶段')
    args = parser.parse_args()

    print("═" * 60)
    print("  M2.2 主实验（E4）— 3 baby × 1000 epoch 真实 LLM")
    print("═" * 60)
    print(f"  执行模式: 串行 chunk（chunk_size={args.chunk_size}）")
    print(f"  Seed 分配: {SEEDS}")
    print()

    if args.aggregate_only:
        print("  --aggregate-only: 跳过 chunk 运行，只做聚合")
        return aggregate_results()

    # ── 决定要跑哪些 (baby, chunk) 对 ──
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
            chunks_to_run = [0, 1, 2, 3]  # 全部 4 个 chunks

        for chunk_idx in chunks_to_run:
            # Skip 已有 _chunk{N}_result.json 的 chunk（已完成）
            result_path = OUTPUT_DIR / f"{baby_name}_chunk{chunk_idx}_result.json"
            if result_path.exists():
                print(f"\n  ⊙ Skip {baby_name} chunk {chunk_idx}（已有 {result_path.name}）")
                continue

            # 计算 start_epoch 和 n_steps
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
                # 不 break — 让 wrapper 决定是否继续下一个 chunk

    total_elapsed = time.time() - total_t0

    if all_results:
        print(f"\n  ✓ {len(all_results)} chunks 完成 ({total_elapsed/60:.1f} min)")
    if failed:
        print(f"  ⚠ {len(failed)} chunks 失败")

    print(f"\n  下一步: 运行 aggregate_chunks.py 合并结果")
    return 0


def aggregate_results() -> int:
    """合并所有 chunks 的 JSON 成最终 per-baby result"""
    print("\n  聚合 chunks...")
    # 此函数实现聚合逻辑（具体由 aggregate_chunks.py 完成）
    # 这里只做简单的占位
    print("  请使用 aggregate_chunks.py 进行合并")
    return 0


# ── 三胞胎对比（chunk 模式暂跳过，由 aggregator 处理）──

    # ── Personality divergence ──
    divergence = compute_personality_divergence(results) if len(results) >= 2 else {
        'pairwise_cosine_distance': {}, 'avg_divergence': 0.0, 'note': 'insufficient',
    }

    # ── 汇总 ──
    summary = {
        'experiment': 'm22_triplets',
        'execution_mode': 'serial',
        'n_steps_per_baby': 1000,
        'total_llm_calls': sum(r['llm_call_count'] for r in results),
        'total_elapsed_seconds': round(total_elapsed, 1),
        'babies': {
            r['name']: {
                'baby_id': r['baby_id'],
                'seed': r['seed'],
                'value_magnitude_final': r['value_magnitude_final'],
                'phase_xition_count': r['phase_xition_count'],
                'phase_xition_epochs': r['phase_xition_epochs'],
                'identity_count': r['identity_count'],
                'narrative_count': r['narrative_count'],
                'success_rate': r['success_rate'],
                'failure_rate': r['failure_rate'],
                'final_value_state': r['final_value_state'],
                'final_frustration_per_drive': r['final_frustration_per_drive'],
                'event_distribution': r['event_distribution'],
                'hawking_final_size': r['hawking_final_size'],
                'crystallizer_final_clusters': r['crystallizer_final_clusters'],
                'key_value_snapshots': r['key_value_snapshots'],
                'llm_stats': r['llm_stats'],
            }
            for r in results
        },
        'personality_divergence': divergence,
        'failed_babies': failed_babies,
    }

    # ── 验收 ──
    print(f"\n{'─'*60}")
    print(f"  E4 主实验验收")
    print(f"{'─'*60}\n")

    all_completed = len(results) == 3
    print(f"  {'✓' if all_completed else '✗'} 1. 3 baby 全部跑通（{len(results)}/3）")
    print(f"     total LLM 调用: {summary['total_llm_calls']}, "
          f"total 时间: {summary['total_elapsed_seconds']}s ({total_elapsed/3600:.1f} h)")

    if all_completed:
        enc_succ = next(r['success_rate'] for r in results if r['name'] == 'encouraged')
        cha_succ = next(r['success_rate'] for r in results if r['name'] == 'challenged')
        unc_succ = next(r['success_rate'] for r in results if r['name'] == 'uncertain')
        diff_ok = enc_succ > unc_succ > cha_succ
        print(f"  {'✓' if diff_ok else '✗'} 2. success_rate 排序 "
              f"encouraged ({enc_succ:.1%}) > uncertain ({unc_succ:.1%}) > "
              f"challenged ({cha_succ:.1%})")

        div_ok = divergence['avg_divergence'] > 0.5
        print(f"  {'✓' if div_ok else '✗'} 3. personality_divergence = "
              f"{divergence['avg_divergence']:.4f} > 0.5")

        enc_pt = next(r['phase_xition_count'] for r in results if r['name'] == 'encouraged')
        cha_pt = next(r['phase_xition_count'] for r in results if r['name'] == 'challenged')
        unc_pt = next(r['phase_xition_count'] for r in results if r['name'] == 'uncertain')
        pt_ok = cha_pt >= unc_pt >= enc_pt
        print(f"  {'✓' if pt_ok else 'ℹ'} 4. PT 触发对比 "
              f"challenged ({cha_pt}) ≥ uncertain ({unc_pt}) ≥ encouraged ({enc_pt})")

        hawking_decayed = any(r['hawking_final_size'] < r['crystallizer_final_clusters']
                              for r in results)
        print(f"  {'✓' if hawking_decayed else 'ℹ'} 5. Hawking 衰减 vs Crystallizer "
              f"({sum(r['hawking_final_size'] for r in results)} vs "
              f"{sum(r['crystallizer_final_clusters'] for r in results)})")

        id_ok = all(r['identity_count'] >= 40 for r in results)  # 1000/20 = 50
        print(f"  {'✓' if id_ok else 'ℹ'} 6. Identity 触发 ≥ 40 次/baby "
              f"({[r['identity_count'] for r in results]}，预期 ~50）")

        all_pass = all_completed and diff_ok and div_ok
    else:
        all_pass = False

    print(f"\n  总体: {'✅ PASS — M2.2 主实验验证通过' if all_pass else '⚠ 部分通过'}")

    # ── 写 summary ──
    (OUTPUT_DIR / "triplets_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding='utf-8',
    )

    # ── 三胞胎对比表 ──
    print(f"\n{'─'*60}")
    print(f"  三胞胎关键对比（1000 epoch）")
    print(f"{'─'*60}\n")

    print(f"{'Baby':<12} {'seed':<5} {'|val|':<8} {'PT':<5} {'Id':<5} {'Nar':<5} "
          f"{'Succ%':<8} {'Fail%':<8} {'retry%':<8} {'time(h)'}")
    for r in results:
        s = r['llm_stats']['retry']
        retry_pct = s['calls_with_retry'] / s['total_calls'] * 100 if s['total_calls'] > 0 else 0
        print(f"{r['name']:<12} {r['seed']:<5} {r['value_magnitude_final']:<8.3f} "
              f"{r['phase_xition_count']:<5} {r['identity_count']:<5} "
              f"{r['narrative_count']:<5} {r['success_rate']:<8.1%} "
              f"{r['failure_rate']:<8.1%} {retry_pct:<8.1f} {r['elapsed_seconds']/3600:.1f}")

    print(f"\nPersonality divergence (cosine distance on final value_state):")
    for pair, dist in divergence['pairwise_cosine_distance'].items():
        print(f"  {pair}: {dist:.4f}")
    print(f"  平均: {divergence['avg_divergence']:.4f}")

    print(f"\n  状态快照: {OUTPUT_DIR}/triplets_summary.json")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
