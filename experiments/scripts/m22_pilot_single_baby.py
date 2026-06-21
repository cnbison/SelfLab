"""
M2.2 Pilot — 1 baby × 100 epoch 真实 LLM（稳定性预演）

目的（M2.2 启动前的预演）：
  1. 验证 D6 修复的 3 个 bug（off-by-one / per-epoch 进度 / 防御式 JSON 解析）
     在 100 epoch 量级稳定（不是 20 epoch）
  2. 收集 frustration 时间序列 — 看 100 epoch 内 frustration 累积曲线
     （回答：D6 报告里 PT 0/20 是 epoch 不够，还是 bug？）
  3. 收集 identity 5 次重写（epoch 19/39/59/79/99）— 看重写质量是否漂移
  4. 收集 narrative 累积（epoch 19/39/59/79/99 触发 build/check_consistency）
  5. 观测 Hawking 衰减是否开始（100h 后 weight ≈ exp(-1) ≈ 0.37，仍 > 1e-4）

预算估算：
  - LLM 调用：~50 critic + ~50 actor + ~5 identity + ~5 narrative build +
    ~5 narrative consistency = ~115 次调用 × ~3s = ~345s ≈ 5.7 min

为什么先做 pilot 再开 M2.2：
  - D6 只跑了 20 epoch，没有 100 epoch 级稳定性证据
  - M2.2 是 1000 epoch × 3 baby ≈ 6600 LLM 调用 — 出问题 debug 成本太高
  - Pilot 用 ~115 调用换 M2.2 风险下降

关联文档：
  - SGE-M21-Phase-D-Implementation-Plan.md §D6（上一个真实 LLM 验证）
  - SGE-M22-Implementation-Plan.md（待写）
"""

import json
import sys
from pathlib import Path


# ── SGE 自有实现全套 ─────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sge.baseline import (
    Agent, DriveMetabolism, ValueLayer, HawkingDecay, MemoryCrystallizer,
    SGE_DEFAULT_VALUES, _load_drives,
)
from sge.event import EventGenerator
from sge.identity import IdentityLayer
from sge.narrative import NarrativeBuilder
from sge.orchestrator import SGEOrchestrator
from sge.llm_client import make_llm_client


# ── 输出目录 ──────────────────────────────────────
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "m22_pilot"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Pilot 主函数 ──────────────────────────────────


def run_pilot(
    seed: int = 42,
    n_steps: int = 100,
    crystallize_every: int = 10,
    identity_every: int = 20,
    narrative_every: int = 20,
    sample_every: int = 10,  # 时间序列采样间隔
    baby_id: str = 'm22_pilot',
) -> dict:
    """Pilot：1 baby × 100 epoch 真实 LLM"""
    print(f"\n{'─'*60}")
    print(f"  M2.2 Pilot — 1 baby × {n_steps} epoch 真实 LLM")
    print(f"{'─'*60}\n")

    # ── 加载 LLM 客户端 ──
    llm = make_llm_client(provider='minimax', verbose=False)
    print(f"✓ LLM 客户端就绪: {llm.stats()}\n")

    # ── 预热连接（mitigation 3）──
    llm.warmup(n_calls=2)

    # ── 初始化组件 ──
    drives = _load_drives()
    value_layer = ValueLayer(values=SGE_DEFAULT_VALUES)
    hawking = HawkingDecay(gamma=0.01, clock=0.0)
    crystallizer = MemoryCrystallizer(n_dims=11)
    agent = Agent(
        seed=seed,
        drives=drives,
        value_layer=value_layer,
        hawking=hawking,
        crystallizer=crystallizer,
        crystallize_every=crystallize_every,
    )
    metabolism = DriveMetabolism(drives=drives)
    event_gen = EventGenerator(baby_id=baby_id, seed=seed)
    identity_layer = IdentityLayer(crystallize_every_n_epochs=identity_every)
    narrative_builder = NarrativeBuilder(build_every_n_epochs=narrative_every)

    orchestrator = SGEOrchestrator(
        agent=agent,
        value_layer=value_layer,
        drive_metabolism=metabolism,
        event_generator=event_gen,
        identity_layer=identity_layer,
        narrative_builder=narrative_builder,
        hawking=hawking,
        crystallizer=crystallizer,
        crystallize_every=crystallize_every,
        use_real_llm=True,
        llm=llm,
        llm_provider='minimax',
        verbose=True,
    )

    # ── 跑 100 epoch（手动循环以采集 per-step 时间序列）──
    # 上一次 pilot 用 orchestrator.run() 然后才采样，导致 timeseries 全是终态。
    # 这里改成手动 step() 循环，每步采样 value/frustration/hawking。
    print(f"开始跑 {n_steps} epoch...")
    import time
    t0 = time.time()
    # 设 _n_epochs_hint 让 step() 的 progress 行显示正确分母
    orchestrator._n_epochs_hint = n_steps
    timeseries_live = []
    traces = []
    for epoch_idx in range(n_steps):
        trace = orchestrator.step(epoch_idx)
        traces.append(trace)

        # 每 sample_every 步采样一次（per-step 实时采样，不是事后）
        if (epoch_idx + 1) % sample_every == 0 or epoch_idx == 0:
            timeseries_live.append({
                'epoch': epoch_idx,
                'value_magnitude': round(value_layer.magnitude(), 4),
                'frustration_total': round(metabolism.total(), 4),
                'frustration_per_drive': {d: round(v, 4) for d, v in metabolism.frustration.items()},
                'hawking_size': len(hawking),
                'crystallize_clusters': len(crystallizer),
                'phase_xition_so_far': sum(1 for tt in traces if tt.phase_xition),
                'identity_so_far': sum(1 for tt in traces if tt.identity is not None),
                'narrative_so_far': sum(1 for tt in traces if tt.narrative is not None),
                'retrieved_count': len(trace.retrieved_memories),
            })

    elapsed = time.time() - t0
    print(f"\n✓ {n_steps} epoch 全部跑通 ({elapsed:.1f}s = {elapsed/n_steps:.1f}s/epoch)\n")

    # ── 收集最终 stats ──
    final_stats = {
        'seed': seed,
        'n_steps': n_steps,
        'baby_id': baby_id,
        'elapsed_seconds': round(elapsed, 1),
        'llm_call_count': llm.call_count,
        'final_value_magnitude': round(value_layer.magnitude(), 4),
        'phase_xition_count': sum(1 for t in traces if t.phase_xition),
        'identity_count': sum(1 for t in traces if t.identity is not None),
        'narrative_count': sum(1 for t in traces if t.narrative is not None),
        'crystallize_count': sum(1 for t in traces if t.crystallize_result is not None),
        'hawking_final_size': len(hawking),
        'crystallizer_final_clusters': len(crystallizer),
        'final_frustration_total': round(metabolism.total(), 4),
        'final_frustration_per_drive': {d: round(v, 4) for d, v in metabolism.frustration.items()},
        'final_value_state': {k: round(v, 4) for k, v in value_layer.value_state.items()},
    }

    # ── 时间序列采样 ──
    # 用 run 期间实时采集的 timeseries_live（覆盖之前的"事后采样"bug）
    timeseries = timeseries_live

    # ── Identity 历史（全部保留，看 5 次重写是否质量漂移）──
    identity_history = []
    for t in traces:
        if t.identity is not None:
            identity_history.append({
                'epoch': t.epoch,
                'identity': t.identity,
                'length_chars': len(t.identity),
            })

    # ── Narrative 历史（全部保留）──
    narrative_history = []
    for t in traces:
        if t.narrative is not None:
            narrative_history.append({
                'epoch': t.epoch,
                'narrative': t.narrative,
                'length_chars': len(t.narrative),
            })

    return {
        'final_stats': final_stats,
        'timeseries': timeseries,
        'identity_history': identity_history,
        'narrative_history': narrative_history,
    }


# ── Pilot 验收标准 ──────────────────────────────────


def verify_pilot_results(result: dict) -> dict:
    """Pilot 验收：稳定性 + 累积曲线 + 重写质量"""
    stats = result['final_stats']
    timeseries = result['timeseries']
    identity_hist = result['identity_history']
    narrative_hist = result['narrative_history']

    print(f"\n{'─'*60}")
    print(f"  M2.2 Pilot 验收")
    print(f"{'─'*60}\n")

    checks = []

    # 1. LLM 调用稳定（无崩溃/卡死）
    checks.append((
        f'1. LLM 调用 {stats["llm_call_count"]} 次全部完成（无崩溃）',
        stats['llm_call_count'] > 80,  # 100 epoch 至少 80 次 critic+actor
    ))

    # 2. Identity 触发 ≥ 4 次（100 epoch / 20 = 5 次，至少 4 次不崩溃）
    checks.append((
        f'2. Identity 触发 {stats["identity_count"]} 次（预期 5/100）',
        stats['identity_count'] >= 4,
    ))

    # 3. Narrative 触发 ≥ 4 次
    checks.append((
        f'3. Narrative 触发 {stats["narrative_count"]} 次（预期 5/100）',
        stats['narrative_count'] >= 4,
    ))

    # 4. Phase Transition 触发观测（关键 — D6 是 0/20）
    pt = stats['phase_xition_count']
    checks.append((
        f'4. Phase Transition 触发 {pt} 次（100 epoch 真实 LLM 下是否触发 PT？）',
        pt >= 0,  # 观察项，记录即可
    ))

    # 5. Identity 5 次重写长度不崩溃（≥ 10 字符，无质量漂移到空字符串）
    if len(identity_hist) >= 2:
        first_len = identity_hist[0]['length_chars']
        last_len = identity_hist[-1]['length_chars']
        no_drift = all(h['length_chars'] >= 10 for h in identity_hist)
        checks.append((
            f'5. Identity 5 次重写无质量漂移（{first_len}→{last_len} 字符，全部 ≥ 10）',
            no_drift,
        ))
    else:
        checks.append(('5. Identity 重写次数不足 2，跳过', False))

    # 6. Hawking 衰减观测
    initial_weight = timeseries[0]['hawking_size'] if timeseries else 0
    final_weight = stats['hawking_final_size']
    checks.append((
        f'6. Hawking 大小 {initial_weight} → {final_weight}（100 epoch 衰减观测）',
        True,  # 观察项
    ))

    # 7. Frustration 累积曲线（最后 10 epoch 总 frustration）
    if timeseries:
        last_frustration = timeseries[-1]['frustration_total']
        # 检查 frustration 累积到 PT 阈值附近（2.0）
        pt_proximity = last_frustration / 2.0  # 1.0 = 正好达到阈值
        checks.append((
            f'7. Frustration 累积 = {last_frustration:.2f}（PT 阈值 2.0 的 {pt_proximity:.0%}）',
            True,  # 观察项 — 决定 M2.2 是否需要更长 epoch
        ))

    print()
    for label, ok in checks:
        status = '✓' if ok else '✗'
        print(f'  {status} {label}')

    # 硬性 PASS 标准：1+2+3+5 PASS，4+6+7 是观察项
    hard_pass = all(ok for label, ok in checks if label.startswith(('1', '2', '3', '5')))

    print(f"\n  总体: {'✅ PASS — M2.2 可启动' if hard_pass else '⚠ 部分通过 — 需要排查'}")

    return {
        'hard_pass': hard_pass,
        'checks': checks,
    }


# ── 主入口 ────────────────────────────────────────


def main() -> int:
    print("=" * 60)
    print("  M2.2 Pilot — 1 baby × 100 epoch 真实 LLM（稳定性预演）")
    print("=" * 60)

    # ── 跑 pilot ──
    result = run_pilot(seed=42, n_steps=100)

    # ── 验收 ──
    verification = verify_pilot_results(result)

    # ── 写输出 ──
    output_path = OUTPUT_DIR / "m22_pilot_result.json"
    output_path.write_text(
        json.dumps(
            {
                'final_stats': result['final_stats'],
                'timeseries': result['timeseries'],
                'verification': [list(c) for c in verification['checks']],
                'identity_count': len(result['identity_history']),
                'narrative_count': len(result['narrative_history']),
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding='utf-8',
    )

    # Identity/Narrative 历史单独输出
    (OUTPUT_DIR / "identity_history.json").write_text(
        json.dumps(result['identity_history'], indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    (OUTPUT_DIR / "narrative_history.json").write_text(
        json.dumps(result['narrative_history'], indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    # ── 关键输出展示 ──
    print(f"\n{'─'*60}")
    print(f"  关键观察")
    print(f"{'─'*60}\n")

    print("Frustration 累积曲线（每 10 epoch）:")
    print(f"  {'Epoch':<8} {'|val|':<10} {'frustration':<15} {'hawking':<10} {'PT (cum)':<10}")
    for ts in result['timeseries']:
        print(f"  {ts['epoch']+1:<8} {ts['value_magnitude']:<10} "
              f"{ts['frustration_total']:<15.3f} {ts['hawking_size']:<10} "
              f"{ts['phase_xition_so_far']:<10}")

    if result['identity_history']:
        print(f"\nIdentity 历史（{len(result['identity_history'])} 次重写）:")
        for h in result['identity_history']:
            print(f"  Epoch {h['epoch']+1} ({h['length_chars']} 字): {h['identity'][:80]}...")

    print(f"\n  状态快照: {output_path}")

    return 0 if verification['hard_pass'] else 1


if __name__ == "__main__":
    sys.exit(main())
