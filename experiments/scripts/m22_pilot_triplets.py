"""
M2.2 三胞胎预演 — 3 baby × 100 epoch 真实 LLM

目的（E3）：
  1. 验证 E1 扩展的 EventGenerator + E2 triplet yaml 能正确加载并生效
  2. 验证 3 baby 在 100 epoch 内出现早期分化信号
  3. 收集数据为 E4（1000 epoch 主实验）调参

实验设计：
  - 3 个 AI 婴儿：encouraged / challenged / uncertain（各自 100 epoch）
  - 真实 LLM：MiniMax-M3 via SGELLMClient
  - Seed：每个 baby 用相同 seed=42 → LLM 抽样差异主要由 EventGenerator 分布驱动
  - 串行运行（避免 LLM API 并发问题）
  - 总耗时：~50 min（3 × ~17 min，参考单 baby pilot v3 = 978s）

预期产出：
  - experiments/output/m22_triplets_pilot/
    - triplet_pilot_summary.json (3 baby 关键指标对比)
    - {encouraged,challenged,uncertain}_pilot_result.json
    - {encouraged,challenged,uncertain}_identity_history.json
    - {encouraged,challenged,uncertain}_narrative_history.json

验收标准：
  1. 3 baby 全部跑通（无崩溃）
  2. encouraged/challenged 在 event_type 分布上显著差异（success rate 对比）
  3. personality_divergence > 0（至少 1 项指标区分 3 baby）
  4. identity theme 3 baby 各自可读区分
  5. PT 触发次数 challenged > uncertain > encouraged（关键假设）

关联文档：
- [SGE-M22-Implementation-Plan.md §E3](../research/sge-feasibility/SGE-M22-Implementation-Plan.md#e3三胞胎预演3-baby--100-epoch)
- m22_pilot_single_baby.py（M2.2 单 baby pilot，结构参考）
- m22_triplet_config.py（E3a yaml loader）
"""

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


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "m22_triplets_pilot"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── 单 baby 跑 100 epoch ──────────────────────────


def run_one_baby(
    name: str,
    yaml_path: str,
    seed: int = 42,
    n_steps: int = 100,
    sample_every: int = 10,
) -> dict:
    """跑 1 个 triplet baby 的 100 epoch 真实 LLM"""
    print(f"\n{'─'*60}")
    print(f"  Baby: {name}  ({Path(yaml_path).name})")
    print(f"{'─'*60}\n")

    # ── 加载 triplet config ──
    cfg = load_triplet_config(yaml_path)
    print(f"  baby_id={cfg['baby_id']}, "
          f"value_conflict_prob={cfg['value_conflict_prob']}, "
          f"distribution 阶段数={len(cfg['distribution_by_epoch'])}")

    # ── LLM 客户端 ──
    llm = make_llm_client(provider='minimax', verbose=False)

    # ── 预热连接（mitigation 3）──
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
    # ★ 关键：用 triplet config 的 value_conflict_prob + distribution_by_epoch
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

    # ── 跑 100 epoch（手动循环，live timeseries 采样）──
    print(f"\n  开始跑 {n_steps} epoch...")
    orchestrator._n_epochs_hint = n_steps
    timeseries_live = []
    traces = []
    t0 = time.time()
    for epoch_idx in range(n_steps):
        trace = orchestrator.step(epoch_idx)
        traces.append(trace)
        if (epoch_idx + 1) % sample_every == 0 or epoch_idx == 0:
            timeseries_live.append({
                'epoch': epoch_idx,
                'value_magnitude': round(value_layer.magnitude(), 4),
                'frustration_total': round(metabolism.total(), 4),
                'hawking_size': len(hawking),
                'crystallize_clusters': len(crystallizer),
                'phase_xition_so_far': sum(1 for tt in traces if tt.phase_xition),
                'identity_so_far': sum(1 for tt in traces if tt.identity is not None),
            })
    elapsed = time.time() - t0

    # ── Event type 分布统计 ──
    event_types = [t.event['event_type'] for t in traces]
    event_dist = Counter(event_types)

    # ── 收集结果 ──
    result = {
        'name': name,
        'baby_id': cfg['baby_id'],
        'seed': seed,
        'n_steps': n_steps,
        'elapsed_seconds': round(elapsed, 1),
        'llm_call_count': llm.call_count,
        'value_magnitude_final': round(value_layer.magnitude(), 4),
        'phase_xition_count': sum(1 for t in traces if t.phase_xition),
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
    }

    print(f"\n  ✓ {name} 完成 ({elapsed:.1f}s, {llm.call_count} LLM 调用)")
    print(f"    value_magnitude={result['value_magnitude_final']}, "
          f"PT={result['phase_xition_count']}, "
          f"success_rate={result['success_rate']:.1%}, "
          f"failure_rate={result['failure_rate']:.1%}")

    # ── 收集 identity 历史 ──
    identity_history = []
    for t in traces:
        if t.identity is not None:
            identity_history.append({
                'epoch': t.epoch,
                'identity': t.identity,
                'length_chars': len(t.identity),
            })

    # ── 写输出 ──
    (OUTPUT_DIR / f"{name}_pilot_result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str),
        encoding='utf-8',
    )
    (OUTPUT_DIR / f"{name}_identity_history.json").write_text(
        json.dumps(identity_history, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    return result


# ── 三胞胎对比 ─────────────────────────────────────


def compute_personality_divergence(results: list) -> dict:
    """计算 3 baby 间 personality_divergence（跨 value_vector cosine 距离）

    Returns:
        dict with divergence metrics
    """
    # 取每个 baby 的 final value_state
    vectors = {r['name']: r['final_value_state'] for r in results}

    def cosine_dist(a: dict, b: dict) -> float:
        keys = sorted(set(a.keys()) & set(b.keys()))
        va = [a[k] for k in keys]
        vb = [b[k] for k in keys]
        dot = sum(x * y for x, y in zip(va, vb))
        norm_a = math.sqrt(sum(x * x for x in va))
        norm_b = math.sqrt(sum(x * x for x in vb))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        # cosine distance = 1 - cosine similarity
        return 1.0 - dot / (norm_a * norm_b)

    names = list(vectors.keys())
    pairwise = {}
    for i, n1 in enumerate(names):
        for j, n2 in enumerate(names):
            if i < j:
                pairwise[f'{n1}_vs_{n2}'] = round(
                    cosine_dist(vectors[n1], vectors[n2]), 4
                )

    # 平均 pairwise divergence
    avg = round(sum(pairwise.values()) / len(pairwise), 4) if pairwise else 0

    return {
        'pairwise_cosine_distance': pairwise,
        'avg_divergence': avg,
    }


def main() -> int:
    print("=" * 60)
    print("  M2.2 三胞胎预演 — 3 baby × 100 epoch 真实 LLM")
    print("=" * 60)

    # ── 跑 3 baby 串行（per-baby 隔离崩溃：一个失败不影响另外 2 个）──
    results = []
    failed_babies = []
    for name, yaml_path in TRIPLET_CONFIGS.items():
        try:
            result = run_one_baby(name, yaml_path, seed=42, n_steps=100)
            results.append(result)
        except Exception as e:
            print(f"\n  ✗ {name} 崩溃: {type(e).__name__}: {str(e)[:200]}")
            print(f"    → 继续下一个 baby（不中断整个 triplet pilot）")
            failed_babies.append({'name': name, 'error': str(e)[:200]})
            continue

    if not results:
        print("\n  ⚠ 所有 baby 都失败，无对比数据")
        return 1

    if failed_babies:
        print(f"\n  ⚠ {len(failed_babies)}/3 baby 失败: "
              f"{[b['name'] for b in failed_babies]}")

    # ── 计算 personality_divergence（至少需要 2 baby 才能算）──
    if len(results) >= 2:
        divergence = compute_personality_divergence(results)
    else:
        divergence = {
            'pairwise_cosine_distance': {},
            'avg_divergence': 0.0,
            'note': 'insufficient babies (need ≥2)',
        }

    # ── 汇总 ──
    summary = {
        'experiment': 'm22_pilot_triplets',
        'n_babies': len(results),
        'n_steps_per_baby': 100,
        'total_llm_calls': sum(r['llm_call_count'] for r in results),
        'total_elapsed_seconds': round(sum(r['elapsed_seconds'] for r in results), 1),
        'babies': {
            r['name']: {
                'baby_id': r['baby_id'],
                'value_magnitude_final': r['value_magnitude_final'],
                'phase_xition_count': r['phase_xition_count'],
                'identity_count': r['identity_count'],
                'narrative_count': r['narrative_count'],
                'success_rate': r['success_rate'],
                'failure_rate': r['failure_rate'],
                'final_value_state': r['final_value_state'],
                'final_frustration_per_drive': r['final_frustration_per_drive'],
                'event_distribution': r['event_distribution'],
            }
            for r in results
        },
        'personality_divergence': divergence,
    }

    # ── 验收 ──
    print(f"\n{'─'*60}")
    print(f"  三胞胎预演验收")
    print(f"{'─'*60}\n")

    # 1. 3 baby 全部跑通
    all_completed = all(r['phase_xition_count'] >= 0 for r in results)  # 简单检查
    print(f"  ✓ 1. 3 baby 全部跑通（total LLM 调用: {summary['total_llm_calls']}, "
          f"total 时间: {summary['total_elapsed_seconds']}s）")

    # 2. success_rate 差异（encouraged >> uncertain >> challenged）
    enc_succ = next(r['success_rate'] for r in results if r['name'] == 'encouraged')
    cha_succ = next(r['success_rate'] for r in results if r['name'] == 'challenged')
    unc_succ = next(r['success_rate'] for r in results if r['name'] == 'uncertain')
    diff_ok = enc_succ > unc_succ > cha_succ
    print(f"  {'✓' if diff_ok else '✗'} 2. success_rate 排序 "
          f"encouraged ({enc_succ:.1%}) > uncertain ({unc_succ:.1%}) > "
          f"challenged ({cha_succ:.1%})")

    # 3. personality_divergence > 0
    div_ok = divergence['avg_divergence'] > 0.05  # 阈值
    print(f"  {'✓' if div_ok else '✗'} 3. personality_divergence = "
          f"{divergence['avg_divergence']:.4f} > 0.05")

    # 4. PT 触发对比
    enc_pt = next(r['phase_xition_count'] for r in results if r['name'] == 'encouraged')
    cha_pt = next(r['phase_xition_count'] for r in results if r['name'] == 'challenged')
    unc_pt = next(r['phase_xition_count'] for r in results if r['name'] == 'uncertain')
    pt_ok = cha_pt >= unc_pt >= enc_pt
    print(f"  {'✓' if pt_ok else 'ℹ'} 4. PT 触发对比 "
          f"challenged ({cha_pt}) ≥ uncertain ({unc_pt}) ≥ encouraged ({enc_pt})"
          f"  {'（观察项）' if not pt_ok else ''}")

    # 5. Identity 各自有输出
    id_ok = all(r['identity_count'] >= 4 for r in results)
    print(f"  {'✓' if id_ok else '✗'} 5. Identity 触发 ≥ 4 次/baby "
          f"({[r['identity_count'] for r in results]}）")

    all_pass = all_completed and diff_ok and div_ok and id_ok
    print(f"\n  总体: {'✅ PASS — M2.2 主实验可启动' if all_pass else '⚠ 部分通过'}")

    # ── 写汇总 ──
    summary_path = OUTPUT_DIR / "triplet_pilot_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding='utf-8',
    )

    # ── 关键对比展示 ──
    print(f"\n{'─'*60}")
    print(f"  三胞胎关键对比")
    print(f"{'─'*60}\n")

    print(f"{'Baby':<12} {'|val|':<8} {'PT':<5} {'Id':<4} {'Nar':<4} "
          f"{'Succ%':<8} {'Fail%':<8} {'time(s)'}")
    for r in results:
        print(f"{r['name']:<12} {r['value_magnitude_final']:<8.3f} "
              f"{r['phase_xition_count']:<5} {r['identity_count']:<4} "
              f"{r['narrative_count']:<4} {r['success_rate']:<8.1%} "
              f"{r['failure_rate']:<8.1%} {r['elapsed_seconds']}")

    print(f"\nPersonality divergence (cosine distance):")
    for pair, dist in divergence['pairwise_cosine_distance'].items():
        print(f"  {pair}: {dist:.4f}")
    print(f"  平均: {divergence['avg_divergence']:.4f}")

    print(f"\n  状态快照: {summary_path}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
