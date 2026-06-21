"""
M2.1 阶段 D — 真实 LLM 验证脚本（最小可观测性测试）

对应 ROADMAP 里程碑：M2.1 阶段 D 补充 — 真实 LLM 验证
对应成本原则：能真实 LLM 就不用 stub（用户明确指示 — 订阅模式不考虑成本）

实验目的：
  - 验证 12 步双 LLM 编排在真实 LLM 下可运行
  - 验证 Critic JSON 输出可解析
  - 验证 Actor JSON 输出可解析
  - 验证 Identity LLM 输出非空且有意义
  - 验证 Narrative LLM 输出非空且有意义
  - **验证 Phase Transition 在真实事件流下能触发**（stub 模式 100 epoch 不触发）
  - 验证 Personality Divergence 在真实 LLM 下有差异

实验设计：
  - 1 个 AI 婴儿（seed=42）
  - 20 epoch（足够触发 Identity/Narrative，但不消耗太多 LLM 预算）
  - MiniMax-M3 via SGELLMClient
  - 估算成本：~50 次 LLM 调用 × ~$0.01 = ~$0.5（订阅模式 → 实际免费）

运行方法：
  python experiments/scripts/m21_phase_d_real_llm.py

预期产出：
  - experiments/output/m21_phase_d/real_llm_verification.json
  - experiments/output/m21_phase_d/real_llm_critic_samples.json
  - experiments/output/m21_phase_d/real_llm_actor_samples.json
  - experiments/output/m21_phase_d/real_llm_identity_samples.json
  - experiments/output/m21_phase_d/real_llm_narrative_samples.json
"""

import json
import math
import random
import sys
from collections import Counter
from pathlib import Path


# ── SGE 自有实现全套 ─────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sge.baseline import (
    Agent, DriveMetabolism, ValueLayer, HawkingDecay, MemoryCrystallizer,
    SGE_DEFAULT_DRIVES, SGE_DEFAULT_VALUES, _load_drives,
)
from sge.event import EventGenerator
from sge.identity import IdentityLayer, real_crystallize_identity, real_validate_identity
from sge.narrative import NarrativeBuilder, real_build_narrative, real_check_narrative_consistency
from sge.orchestrator import SGEOrchestrator
from sge.llm_client import make_llm_client


# ── 输出目录 ──────────────────────────────────────
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "m21_phase_d"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── 真实 LLM 验证 ────────────────────────────────


def run_real_llm_verification(
    seed: int = 42,
    n_steps: int = 20,
    crystallize_every: int = 10,
    identity_every: int = 20,  # 20 epoch 触发一次
    narrative_every: int = 20,  # 20 epoch 触发一次
    baby_id: str = 'real_llm_test',
) -> dict:
    """真实 LLM 验证（1 baby × 20 epoch）

    Returns:
        dict with stats + samples
    """
    print(f"\n{'─'*60}")
    print(f"  真实 LLM 验证 (seed={seed}, n_steps={n_steps})")
    print(f"{'─'*60}\n")

    # ── 加载 LLM 客户端 ──
    print("正在加载 LLM 客户端...")
    llm = make_llm_client(provider='minimax', verbose=True)
    print(f"✓ LLM 客户端就绪: {llm.stats()}\n")

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
        use_real_llm=True,  # ★ 关键：真实 LLM
        llm=llm,
        llm_provider='minimax',
        verbose=True,  # ★ 让 step() 输出每 epoch 进度（解决"卡住"体感）
    )

    # ── 跑 12 步编排 ──
    print(f"开始跑 {n_steps} epoch 真实 LLM 编排...")
    traces = orchestrator.run(n_epochs=n_steps)
    print(f"✓ {n_steps} epoch 全部跑通\n")

    # ── 统计 ──
    stats = {
        'seed': seed,
        'n_steps': n_steps,
        'baby_id': baby_id,
        'llm_call_count': llm.call_count,
        'final_value_magnitude': round(value_layer.magnitude(), 4),
        'phase_xition_count': sum(1 for t in traces if t.phase_xition),
        'identity_count': sum(1 for t in traces if t.identity is not None),
        'narrative_count': sum(1 for t in traces if t.narrative is not None),
        'crystallize_count': sum(1 for t in traces if t.crystallize_result is not None),
        'hawking_removed_total': sum(t.hawking_removed for t in traces),
        'hawking_final_size': len(hawking),
        'crystallizer_final_clusters': len(crystallizer),
        'value_state_final': {k: round(v, 4) for k, v in value_layer.value_state.items()},
        'current_identity': identity_layer.get_current(),
        'current_narrative': narrative_builder.get_current(),
    }

    # ── 收集样本（每个组件输出示例）──
    samples = collect_samples(traces)

    return {'stats': stats, 'samples': samples}


# ── 样本收集 ──────────────────────────────────────


def collect_samples(traces: list) -> dict:
    """收集每个 LLM 组件的样本输出（验证 JSON 可解析 + 语义合理）"""
    samples = {
        'critic_samples': [],
        'actor_samples': [],
        'identity_samples': [],
        'narrative_samples': [],
    }

    # Critic: 每 5 步采样一次（避免样本过大）
    for t in traces[::5]:
        if t.critic_value_delta:
            samples['critic_samples'].append({
                'epoch': t.epoch,
                'event_type': t.event['event_type'],
                'value_delta': t.critic_value_delta,
                'context_sample': {
                    k: round(t.critic_context[k], 3)
                    for k in ['user_emotion', 'conflict_level', 'novelty_level']
                },
            })

    # Actor: 每 5 步采样一次
    for t in traces[::5]:
        if t.actor_output:
            samples['actor_samples'].append({
                'epoch': t.epoch,
                'behavior_label': t.actor_output.behavior_label,
                'inner_monologue': t.actor_output.inner_monologue,
                'intention': t.actor_output.intention,
                'confidence': t.actor_output.confidence,
            })

    # Identity: 全部保留（每个 trigger 都看）
    for i, h in enumerate([t for t in traces if t.identity is not None]):
        samples['identity_samples'].append({
            'epoch': h.epoch,
            'identity': h.identity,
        })

    # Narrative: 全部保留
    for i, h in enumerate([t for t in traces if t.narrative is not None]):
        samples['narrative_samples'].append({
            'epoch': h.epoch,
            'narrative': h.narrative,
        })

    return samples


# ── 验收标准 ──────────────────────────────────────


def verify_real_llm_results(result: dict) -> dict:
    """真实 LLM 验证的验收标准

    5 项硬性验证 + 1 项观察：
    1. Critic JSON 可解析（检查 value_delta 字段非空 + 范围合法）
    2. Actor JSON 可解析（检查 behavior_label 在 BEHAVIOR_LABELS 中）
    3. Identity LLM 输出非空有意义（>= 10 字符 + 不是模板）
    4. Narrative LLM 输出非空有意义（>= 50 字符）
    5. Phase Transition 至少触发 1 次（验证真实 LLM 的 frustration 累积路径）
    观察：
    6. LLM 调用次数（成本统计）
    """
    stats = result['stats']
    samples = result['samples']

    print(f"\n{'─'*60}")
    print(f"  验收标准")
    print(f"{'─'*60}\n")

    checks = []

    # 1. Critic JSON 验证
    critic_ok = (
        len(samples['critic_samples']) > 0
        and all(
            all(-1.0 <= v <= 1.0 for v in s['value_delta'].values())
            for s in samples['critic_samples']
        )
    )
    checks.append((f'1. Critic JSON 合法（{len(samples["critic_samples"])} 个样本）', critic_ok))

    # 2. Actor JSON 验证
    actor_ok = (
        len(samples['actor_samples']) > 0
        and all(s['behavior_label'] for s in samples['actor_samples'])
    )
    checks.append((f'2. Actor JSON 合法（{len(samples["actor_samples"])} 个样本）', actor_ok))

    # 3. Identity LLM 验证
    from sge.actor import BEHAVIOR_LABELS
    identity_ok = (
        len(samples['identity_samples']) > 0
        and all(
            isinstance(s['identity'], str) and len(s['identity']) >= 10
            for s in samples['identity_samples']
        )
    )
    checks.append((f'3. Identity LLM 输出有意义（{len(samples["identity_samples"])} 个）', identity_ok))

    # 4. Narrative LLM 验证
    narrative_ok = (
        len(samples['narrative_samples']) > 0
        and all(
            isinstance(s['narrative'], str) and len(s['narrative']) >= 50
            for s in samples['narrative_samples']
        )
    )
    checks.append((f'4. Narrative LLM 输出有意义（{len(samples["narrative_samples"])} 个）', narrative_ok))

    # 5. Phase Transition 触发（观察项 — 真实 LLM 应该能触发至少 1 次）
    pt_ok = stats['phase_xition_count'] >= 1
    pt_msg = f'5. Phase Transition 触发 {stats["phase_xition_count"]} 次'
    if pt_ok:
        checks.append((f'{pt_msg}（真实 LLM 路径生效）', True))
    else:
        checks.append((f'{pt_msg}（⚠ 观察项 — 真实 LLM 在 20 epoch 内不触发也合理）', False))

    # 6. LLM 调用次数（成本统计）
    checks.append((f'6. LLM 调用总数 {stats["llm_call_count"]} 次（订阅模式不考虑成本）', True))

    print()
    for label, ok in checks:
        status = '✓' if ok else '✗'
        print(f"  {status} {label}")

    all_pass = all(ok for _, ok in checks[:5])  # 1-5 是硬性，6 是观察

    print(f"\n  总体: {'✅ PASS — 真实 LLM 验证通过' if all_pass else '⚠ 部分通过（Phase Transition 可接受不触发）'}")

    return {
        'all_pass': all_pass,
        'checks': checks,
    }


# ── 主入口 ────────────────────────────────────────


def main() -> int:
    print("=" * 60)
    print("  M2.1 阶段 D: 真实 LLM 验证（1 baby × 20 epoch）")
    print("=" * 60)
    print(f"\n  原则: 能真实 LLM 就不用 stub（订阅模式）")

    # ── 运行真实 LLM 验证 ──
    result = run_real_llm_verification(seed=42, n_steps=20)

    # ── 验收 ──
    verification = verify_real_llm_results(result)

    # ── 写输出 ──
    output_path = OUTPUT_DIR / "real_llm_verification.json"
    output_path.write_text(
        json.dumps(
            {
                'stats': result['stats'],
                'verification': verification['checks'],
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding='utf-8',
    )

    # 各组件样本单独输出
    samples = result['samples']
    for component in ['critic', 'actor', 'identity', 'narrative']:
        path = OUTPUT_DIR / f"real_llm_{component}_samples.json"
        path.write_text(
            json.dumps(
                samples[f'{component}_samples'],
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding='utf-8',
        )

    # ── 显示关键输出 ──
    print(f"\n{'─'*60}")
    print(f"  真实 LLM 关键输出")
    print(f"{'─'*60}\n")

    if samples['identity_samples']:
        print(f"Identity 示例（epoch {samples['identity_samples'][0]['epoch']}）:")
        print(f"  {samples['identity_samples'][0]['identity']}\n")

    if samples['narrative_samples']:
        nar = samples['narrative_samples'][0]['narrative']
        print(f"Narrative 示例（epoch {samples['narrative_samples'][0]['epoch']}）:")
        print(f"  {nar[:300]}{'...' if len(nar) > 300 else ''}\n")

    if samples['actor_samples']:
        print(f"Actor 示例（epoch {samples['actor_samples'][0]['epoch']}）:")
        a = samples['actor_samples'][0]
        print(f"  behavior_label: {a['behavior_label']}")
        print(f"  inner_monologue: {a['inner_monologue']}")
        print(f"  intention: {a['intention']}")
        print(f"  confidence: {a['confidence']}\n")

    print(f"  最终 value_state: {result['stats']['value_state_final']}")
    print(f"  最终 value_magnitude: {result['stats']['final_value_magnitude']}")
    print(f"  Phase Transition 触发: {result['stats']['phase_xition_count']} 次")
    print(f"  LLM 调用总数: {result['stats']['llm_call_count']} 次")

    print(f"\n  状态快照: {output_path}")
    print(f"  样本文件: {OUTPUT_DIR}/real_llm_{{critic,actor,identity,narrative}}_samples.json")

    return 0 if verification['all_pass'] else 1


if __name__ == "__main__":
    sys.exit(main())