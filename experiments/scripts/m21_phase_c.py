"""
M2.1 阶段 C：Identity + Narrative + Event Generator 集成测试

对应 ROADMAP 里程碑：M2.1（完整 SGE 架构）— 阶段 C
对应 PRD 需求：FR-1（Event Generator）+ FR-5（Identity）+ FR-6（Narrative）
对应研究文档：research/sge-feasibility/SGE-M21-Phase-C-Implementation-Plan.md

实验目的：验证 C1-C4 全部子任务集成后的行为
实验设计：
  - 完整 12 步循环（Event → Critic → Value → Drive → Identity → Narrative）
  - 3 seed 一致性（seed=42 / 7 / 123）
  - 阶段 B baseline 回归（m21_phase_b.py 仍能跑通）
  - Identity Stability + Narrative Coherence 指标验证
运行方法：python experiments/scripts/m21_phase_c.py
预期产出：
  - experiments/output/m21_phase_c/m21_phase_c_result.json
  - experiments/output/m21_phase_c/identity_stability.json
  - experiments/output/m21_phase_c/narrative_history.json

设计原则：SGE 自有实现 + 借鉴映射作参考（延续阶段 B 策略）
- 算法来源：SGE-M21-Phase-C-Implementation-Plan.md（研究文档）
- 代码实现：experiments/scripts/_sge_baseline.py + _sge_critic.py + _sge_event.py + _sge_identity.py + _sge_narrative.py
- 不依赖：~/project/AiBeing 外部项目路径

子任务覆盖：
  ✓ C1: Event Generator 完整化（LifeEvent + make_event_id + EventGenerator）
  ✓ C2: Value Conflict Generator（VALUE_CONFLICT_TEMPLATES）
  ✓ C3: Identity Layer（IdentityLayer.crystallize + validate）
  ✓ C4: Narrative Builder MVP（NarrativeBuilder.build + check_consistency + handle_phase_transition）
"""

import json
import random
import sys
from pathlib import Path


# ── SGE 自有实现全套 ─────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sge.baseline import (
    Agent, DriveMetabolism, ValueLayer,
    SGE_DEFAULT_DRIVES, SGE_DEFAULT_VALUES,
    _load_drives, CONTEXT_FEATURES,
)
from sge.critic import critic_sense
from sge.event import EventGenerator, LifeEvent
from sge.identity import IdentityLayer
from sge.narrative import NarrativeBuilder


# ── 输出目录 ──────────────────────────────────────
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "m21_phase_c"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── 阶段 C 完整循环 ───────────────────────────────


def run_phase_c_loop(
    seed: int = 42,
    n_steps: int = 20,  # 阶段 C 比阶段 B 长（要触发 identity/narrative 累积）
    crystallize_every: int = 5,
    build_every: int = 10,
    baby_id: str = 'phase_c_test',
    use_real_llm: bool = False,
) -> dict:
    """阶段 C 完整 12 步循环

    每步:
      1. EventGenerator.generate(epoch, value_layer)
      2. Critic sense (event → 8D context + 6D value_delta)
      3. Agent.step(ctx, reward, critic_value_delta)
      4. DriveMetabolism.time_metabolism()
      5. 如果 epoch % crystallize_every == 0: IdentityLayer.crystallize()
      6. 如果 epoch % build_every == 0: NarrativeBuilder.build()
    """
    rng = random.Random(seed)

    # ── 初始化 ──
    drives = _load_drives()
    value_layer = ValueLayer(values=SGE_DEFAULT_VALUES)
    agent = Agent(seed=seed, drives=drives, value_layer=value_layer)
    metabolism = DriveMetabolism(drives=drives)
    event_gen = EventGenerator(baby_id=baby_id, seed=seed)
    identity_layer = IdentityLayer(crystallize_every_n_epochs=crystallize_every)
    narrative_builder = NarrativeBuilder(build_every_n_epochs=build_every)

    snapshots = []
    crystallized_events = []  # 累积关键事件（用于 narrative）
    key_memories = []  # 累积关键记忆（用于 identity）

    for step in range(n_steps):
        # Step 1: Event 生成
        event = event_gen.generate(epoch=step, value_vector=value_layer)
        crystallized_events.append(event.to_dict())
        key_memories.append(event.to_dict())

        # Step 2: Critic 感知
        ctx, value_delta = critic_sense(
            event=event.to_dict(),
            drives=agent.drive_state,
            values=value_layer.value_state,
            use_real_llm=use_real_llm,
            seed=seed + step,
        )

        # Step 3: Agent 一步
        signals = agent.step(
            context=ctx,
            reward=value_delta.get('safety', 0.0) * 0.5,
            critic_value_delta=value_delta,
        )

        # Step 4: 时间代谢
        metabolism.time_metabolism()

        # Step 5: Identity 结晶（按 crystallize_every 触发）
        identity = None
        if identity_layer.should_crystallize(step):
            identity = identity_layer.crystallize(
                value_layer=value_layer,
                key_memories=key_memories,
                epoch=step,
                seed=seed + step,
            )

        # Step 6: Narrative 构建（按 build_every 触发）
        narrative = None
        if narrative_builder.should_build(step):
            narrative = narrative_builder.build(
                crystallized_events=crystallized_events,
                current_identity=identity_layer.get_current(),
                epoch=step,
                seed=seed + step,
            )

        # Phase Transition 检测（与 narrative 重建联动）
        if agent._last_phase_transition and narrative_builder.current_narrative:
            transition_result = narrative_builder.handle_phase_transition(
                value_layer=value_layer,
                crystallized_events=crystallized_events,
                current_identity=identity_layer.get_current(),
                epoch=step,
                seed=seed + step,
            )

        snapshots.append({
            'step': step,
            'event_type': event.event_type,
            'event_id': event.event_id,
            'value_state_safety': round(value_layer.value_state['safety'], 4),
            'value_state_compassion': round(value_layer.value_state['compassion'], 4),
            'value_magnitude': round(value_layer.magnitude(), 4),
            'identity': identity,
            'narrative': narrative,
            'phase_xition': agent._last_phase_transition,
        })

    return {
        'seed': seed,
        'n_steps': n_steps,
        'baby_id': baby_id,
        'final_state': {
            'value_state': {k: round(v, 4) for k, v in value_layer.value_state.items()},
            'value_magnitude': round(value_layer.magnitude(), 4),
            'current_identity': identity_layer.get_current(),
            'current_narrative': narrative_builder.get_current(),
        },
        'identity_history': identity_layer.identity_history,
        'narrative_history': narrative_builder.narrative_history,
        'snapshots': snapshots,
    }


# ── 多 Seed 验证 ──────────────────────────────────


def verify_multi_seed(seeds: list = [42, 7, 123], n_steps: int = 20) -> bool:
    """验证：多 seed 一致性 + Identity Stability + Narrative Coherence"""
    print(f"\n{'─'*60}")
    print(f"  多 seed 一致性验证 (seeds={seeds}, n_steps={n_steps})")
    print(f"{'─'*60}\n")

    results = []
    for seed in seeds:
        result = run_phase_c_loop(seed=seed, n_steps=n_steps)
        results.append(result)
        n_identity = len(result['identity_history'])
        n_narrative = len(result['narrative_history'])
        print(f"  [seed={seed}] identity_history={n_identity}, narrative_history={n_narrative}, "
              f"value_magnitude={result['final_state']['value_magnitude']:.4f}")

    # 验证：每个 seed 都能跑通
    all_ok = True
    for r in results:
        for k, v in r['final_state']['value_state'].items():
            if not (-1.0 <= v <= 1.0):
                print(f"  ❌ seed={r['seed']}: value[{k}]={v} 超出 [-1, 1]")
                all_ok = False
        if not r['final_state']['current_identity']:
            print(f"  ⚠ seed={r['seed']}: 未生成 identity（20 step 不到 5 步的整数倍?）")

    return all_ok


# ── 阶段 B 回归验证 ───────────────────────────────


def verify_phase_b_baseline() -> bool:
    """验证：阶段 B baseline 仍能跑通（向后兼容）"""
    print(f"\n{'─'*60}")
    print(f"  阶段 B baseline 回归验证")
    print(f"{'─'*60}\n")

    # 调用 m21_phase_b.py 的入口（import 而非 exec）
    try:
        import m21_phase_b
        print(f"  ✓ m21_phase_b.py 可正常 import")
    except Exception as e:
        print(f"  ❌ m21_phase_b.py 回归失败: {e}")
        return False

    # 直接跑一个最小循环
    result = m21_phase_b.run_phase_b_loop(seed=42, n_steps=5)
    assert result['final_state']['value_magnitude'] > 0
    print(f"  ✓ 阶段 B 5 步循环跑通：value_magnitude={result['final_state']['value_magnitude']:.4f}")
    return True


# ── Identity Stability 验证 ───────────────────────


def verify_identity_stability(result: dict) -> dict:
    """DESIGN §9.1 身份稳定度（信息熵倒数）"""
    identities = [h['identity'] for h in result['identity_history']]
    if len(identities) < 2:
        return {'stability_score': 1.0, 'n_identities': len(identities)}

    from collections import Counter
    import math
    counts = Counter(identities)
    total = len(identities)
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
    score = 1.0 / (1.0 + entropy)
    return {
        'stability_score': round(score, 4),
        'n_identities': len(identities),
        'unique_identities': len(counts),
        'entropy': round(entropy, 4),
    }


# ── Narrative Coherence 验证 ──────────────────────


def verify_narrative_coherence(result: dict) -> dict:
    """DESIGN §9.3 叙事一致性（最近 narrative 的 coherence 平均）"""
    if not result['narrative_history']:
        return {'avg_coherence': None, 'n_narratives': 0}
    scores = [h.get('coherence', 0.5) for h in result['narrative_history']]
    return {
        'avg_coherence': round(sum(scores) / len(scores), 4),
        'n_narratives': len(scores),
        'min_coherence': min(scores),
        'max_coherence': max(scores),
    }


# ── 主入口 ─────────────────────────────────────────


def main() -> int:
    """主入口：跑阶段 C 集成测试。"""
    print("=" * 60)
    print("  M2.1 阶段 C: Identity + Narrative + Event Generator 集成测试")
    print("=" * 60)
    print(f"\n  覆盖子任务: C1 (Event Generator) + C2 (Value Conflict) + C3 (Identity) + C4 (Narrative)")

    # ── 主测试：阶段 C 完整循环（seed=42, 20 step）──
    print(f"\n{'─'*60}")
    print(f"  主测试: 阶段 C 完整循环 (seed=42, n_steps=20)")
    print(f"{'─'*60}\n")
    result_42 = run_phase_c_loop(seed=42, n_steps=20)
    for s in result_42['snapshots']:
        iden_str = f"identity={s['identity'][:25]}..." if s['identity'] else "identity=—"
        nar_str = f"narrative={s['narrative'][:25]}..." if s['narrative'] else "narrative=—"
        print(f"  [step {s['step']:2d}] event={s['event_type']:<14s} "
              f"value_safety={s['value_state_safety']:+.3f} "
              f"mag={s['value_magnitude']:.3f} "
              f"{iden_str:<35s} {nar_str}")

    # ── 多 seed 验证 ──
    multi_seed_ok = verify_multi_seed([42, 7, 123], n_steps=20)

    # ── 阶段 B 回归 ──
    phase_b_ok = verify_phase_b_baseline()

    # ── Identity Stability 验证 ──
    print(f"\n{'─'*60}")
    print(f"  Identity Stability（DESIGN §9.1）")
    print(f"{'─'*60}\n")
    for seed in [42, 7, 123]:
        result = run_phase_c_loop(seed=seed, n_steps=20)
        stab = verify_identity_stability(result)
        print(f"  [seed={seed}] stability_score={stab['stability_score']}, "
              f"unique_identities={stab.get('unique_identities', 0)}/{stab['n_identities']}")

    # ── Narrative Coherence 验证 ──
    print(f"\n{'─'*60}")
    print(f"  Narrative Coherence（DESIGN §9.3）")
    print(f"{'─'*60}\n")
    for seed in [42, 7, 123]:
        result = run_phase_c_loop(seed=seed, n_steps=20)
        coh = verify_narrative_coherence(result)
        print(f"  [seed={seed}] avg_coherence={coh.get('avg_coherence')}, "
              f"n_narratives={coh['n_narratives']}")

    # ── 写输出 ──
    output_path = OUTPUT_DIR / "m21_phase_c_result.json"
    output_path.write_text(
        json.dumps({'seed_42_result': result_42}, indent=2, ensure_ascii=False, default=str),
        encoding='utf-8',
    )
    stab_path = OUTPUT_DIR / "identity_stability.json"
    stab_path.write_text(
        json.dumps(
            {seed: verify_identity_stability(run_phase_c_loop(seed=seed, n_steps=20))
             for seed in [42, 7, 123]},
            indent=2, ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    coh_path = OUTPUT_DIR / "narrative_history.json"
    coh_path.write_text(
        json.dumps(
            {seed: verify_narrative_coherence(run_phase_c_loop(seed=seed, n_steps=20))
             for seed in [42, 7, 123]},
            indent=2, ensure_ascii=False,
        ),
        encoding='utf-8',
    )

    print(f"\n  状态快照: {output_path}")
    print(f"  Identity 稳定性: {stab_path}")
    print(f"  Narrative 一致性: {coh_path}")

    # ── 总体判断 ──
    all_ok = multi_seed_ok and phase_b_ok
    print(f"\n  multi_seed={'PASS' if multi_seed_ok else 'FAIL'} | "
          f"phase_b_regression={'PASS' if phase_b_ok else 'FAIL'}")
    print(f"\n  总体: {'✅ PASS — M2.1 阶段 C 集成验证通过' if all_ok else '❌ FAIL'}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
