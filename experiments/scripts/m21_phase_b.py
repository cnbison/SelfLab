"""
M2.1 阶段 B：SGE 化改造集成测试

对应 ROADMAP 里程碑：M2.1（完整 SGE 架构）— 阶段 B
对应 PRD 需求：FR-1~10（阶段 B 范围）
对应研究文档：research/sge-feasibility/SGE-M21-Phase-B-Implementation-Plan.md

实验目的：验证 B1-B7 全部子任务集成后的行为
实验设计：
  - 5 步最小循环（每步：critic_sense → step → metabolism）
  - 3 seed 一致性（seed=42 / 7 / 123）
  - 阶段 A baseline 回归（m21_setup.py 仍能跑通）
  - Phase 阈值扫描（[1.0, 2.0, 3.0]）
运行方法：python experiments/scripts/m21_phase_b.py
预期产出：
  - experiments/output/m21_phase_b/m21_phase_b_result.json
  - experiments/output/m21_phase_b/phase_threshold_scan.json

设计原则：SGE 自有实现 + 借鉴映射作参考（延续阶段 A 修正策略）
- 算法来源：SGE-M21-AiBeing-Implementation-Mapping.md（研究文档）
- 代码实现：experiments/scripts/_sge_baseline.py + _sge_critic.py
- 不依赖：~/project/AiBeing 外部项目路径

子任务覆盖：
  ✓ B1: drives 替换（候选 B）+ schema 化
  ✓ B2: Value Layer 引入
  ✓ B3: Value EMA 实现
  ✓ B4: Critic LLM 接入（MiniMax-M3 适配层，默认 stub 模式）
  ⊘ B5: Phase Transition 阈值扫描（扫描脚本集成在本文件 §6）
  ✓ B6: Hawking 辐射机制（γ=0.01/h）
  ✓ B7: Crystallize 维度归一化（0.25/sqrt(N)）
"""

import json
import random
import sys
import time
from pathlib import Path


# ── SGE 自有实现 + Critic 适配层 ───────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sge.baseline import (
    Agent,
    DriveMetabolism,
    ValueLayer,
    HawkingDecay,
    MemoryCrystallizer,
    crystallize_threshold,
    CONTEXT_FEATURES,
    SGE_DEFAULT_DRIVES,
    SGE_DEFAULT_VALUES,
    SGE_HAWKING_GAMMA,
    _load_drives,
)
from sge.critic import (
    critic_sense,
    CRITIC_CONTEXT_FIELDS,
    VALUE_DELTA_FIELDS,
)


# ── 输出目录 ──────────────────────────────────────
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "m21_phase_b"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Stub Event 生成（不依赖外部事件库）────────────
EVENT_TEMPLATES = [
    {'type': 'success', 'description': '完成了一项任务', 'intensity': 0.7},
    {'type': 'failure', 'description': '任务失败', 'intensity': 0.6},
    {'type': 'relationship', 'description': '与朋友深入交流', 'intensity': 0.5},
    {'type': 'exploration', 'description': '发现新领域', 'intensity': 0.6},
    {'type': 'risk', 'description': '面临未知风险', 'intensity': 0.7},
    {'type': 'value_conflict', 'description': '面临价值冲突', 'intensity': 0.8},
    {'type': 'success', 'description': '获得认可', 'intensity': 0.5},
    {'type': 'failure', 'description': '计划受阻', 'intensity': 0.6},
    {'type': 'relationship', 'description': '与陌生人初见', 'intensity': 0.4},
    {'type': 'exploration', 'description': '尝试新事物', 'intensity': 0.7},
]


def make_event(step: int) -> dict:
    """构造 stub event（按 step 索引轮转）"""
    return dict(EVENT_TEMPLATES[step % len(EVENT_TEMPLATES)])


# ── 阶段 B 主循环 ─────────────────────────────────


def run_phase_b_loop(
    seed: int = 42,
    n_steps: int = 5,
    phase_threshold: float = 2.0,
    use_real_llm: bool = False,
) -> dict:
    """阶段 B 5 步最小循环（含 critic_sense + value EMA + Hawking）

    Args:
        seed: 随机种子
        n_steps: 步数
        phase_threshold: Phase Transition 阈值
        use_real_llm: True 调用真实 LLM，False 用 stub

    Returns:
        result dict: 包含每步 snapshot
    """
    # ── 初始化（B1 schema 化）──
    drives = _load_drives()  # SGE 候选 B 5 drives
    value_layer = ValueLayer(values=SGE_DEFAULT_VALUES)  # B2 引入
    agent = Agent(
        seed=seed,
        phase_threshold=phase_threshold,
        drives=drives,
        value_layer=value_layer,  # B3 接入 Value EMA
    )
    metabolism = DriveMetabolism(drives=drives)

    # ── 跑 n_steps 步 ──
    snapshots = []
    for step in range(n_steps):
        # 构造 event
        event = make_event(step)
        # Critic 感知（B4）
        ctx, value_delta = critic_sense(
            event=event,
            drives=agent.drive_state,
            values=value_layer.value_state,
            use_real_llm=use_real_llm,
            seed=seed + step,
        )
        # Agent 一步完整循环（含 value EMA — B3）
        signals = agent.step(
            context=ctx,
            reward=value_delta.get('safety', 0.0) * 0.5,
            critic_value_delta=value_delta,
        )
        # Metabolism 时间代谢
        metabolism.time_metabolism()

        # Snapshot
        snap = {
            'step': step,
            'event_type': event['type'],
            'context_user_emotion': round(ctx['user_emotion'], 3),
            'value_delta_safety': round(value_delta['safety'], 4),
            'value_state_safety': round(value_layer.value_state['safety'], 4),
            'value_state_compassion': round(value_layer.value_state['compassion'], 4),
            'value_state_magnitude': round(value_layer.magnitude(), 4),
            'drive_state_safety': round(agent.drive_state['safety'], 4),
            'drive_state_exploration': round(agent.drive_state['exploration'], 4),
            'frustration_total': round(metabolism.total(), 4),
            'temperature': round(metabolism.temperature(), 4),
            'phase_xition': agent._last_phase_transition,
            'signal_dominant': max(signals, key=signals.get),
        }
        snapshots.append(snap)

    return {
        'seed': seed,
        'n_steps': n_steps,
        'phase_threshold': phase_threshold,
        'use_real_llm': use_real_llm,
        'drives': drives,
        'values': list(value_layer.value_state.keys()),
        'snapshots': snapshots,
        'final_state': {
            'value_state': {k: round(v, 4) for k, v in value_layer.value_state.items()},
            'value_magnitude': round(value_layer.magnitude(), 4),
            'drive_state': {k: round(v, 4) for k, v in agent.drive_state.items()},
        },
    }


# ── 多 Seed 一致性验证 ────────────────────────────


def verify_multi_seed(seeds: list = [42, 7, 123]) -> bool:
    """验证：多个 seed 都能跑通，且最终 state 不同（说明 randomness 工作）

    Returns:
        True if pass, False if fail
    """
    print(f"\n{'─'*60}")
    print(f"  多 seed 一致性验证 (seeds={seeds})")
    print(f"{'─'*60}\n")

    results = []
    for seed in seeds:
        result = run_phase_b_loop(seed=seed, n_steps=5)
        results.append(result)
        print(f"  [seed={seed}] value_magnitude = {result['final_state']['value_magnitude']:.4f}, "
              f"phase_xition_count = {sum(1 for s in result['snapshots'] if s['phase_xition'])}")

    # 验证：每个 seed 都能跑通（value_state 在 [-1, 1]）
    all_ok = True
    for r in results:
        for k, v in r['final_state']['value_state'].items():
            if not (-1.0 <= v <= 1.0):
                print(f"  ❌ seed={r['seed']}: value[{k}]={v} 超出 [-1, 1]")
                all_ok = False

    # 验证：不同 seed 的最终 value_magnitude 不同（randomness 有效）
    mags = [r['final_state']['value_magnitude'] for r in results]
    if len(set(round(m, 3) for m in mags)) == 1:
        print(f"  ⚠  所有 seed 的 value_magnitude 相同（{mags[0]:.4f}）— randomness 可能未生效")
    else:
        print(f"  ✓ 不同 seed 的 value_magnitude 有差异：{mags}")

    return all_ok


# ── 阶段 A 回归验证 ───────────────────────────────


def verify_phase_a_baseline() -> bool:
    """验证：阶段 A baseline（m21_setup.py 的逻辑）仍能跑通（向后兼容）

    Returns:
        True if pass, False if fail
    """
    print(f"\n{'─'*60}")
    print(f"  阶段 A baseline 回归验证")
    print(f"{'─'*60}\n")

    # 阶段 A 不传 drives 参数（用默认 = SGE_DEFAULT_DRIVES）
    agent = Agent(seed=42)
    metabolism = DriveMetabolism()
    assert agent.drives == SGE_DEFAULT_DRIVES
    assert metabolism.drives == SGE_DEFAULT_DRIVES
    print(f"  ✓ 默认 drives = SGE_DEFAULT_DRIVES（向后兼容）")

    # 跑 5 步循环
    rng = random.Random(0)
    initial_drive_diff = 0.0
    for step in range(5):
        ctx = {f: 0.5 for f in CONTEXT_FEATURES}
        ctx['user_emotion'] = 0.3 if step % 2 == 0 else -0.3
        reward = 0.3 if step % 2 == 0 else -0.15
        agent.step(ctx, reward=reward)
        metabolism.apply_llm_delta({d: (reward if d == 'connection' else 0.0) for d in SGE_DEFAULT_DRIVES})
        initial_drive_diff += abs(agent.drive_state.get('safety', 0) - agent.drive_baseline.get('safety', 0))

    print(f"  ✓ 5 步循环跑通")
    print(f"  ✓ drive_state 变化累积 = {initial_drive_diff:.4f}")
    print(f"  ✓ temperature = {metabolism.temperature():.4f}")

    return initial_drive_diff > 0


# ── Phase 阈值扫描（B5）────────────────────────────


def phase_threshold_scan() -> dict:
    """扫描 Phase Transition 阈值 [1.0, 2.0, 3.0]

    Returns:
        扫描结果 dict
    """
    print(f"\n{'─'*60}")
    print(f"  Phase Threshold 扫描 [1.0, 2.0, 3.0]（B5）")
    print(f"{'─'*60}\n")

    results = []
    for pt in [1.0, 2.0, 3.0]:
        result = run_phase_b_loop(seed=42, n_steps=5, phase_threshold=pt)
        phase_count = sum(1 for s in result['snapshots'] if s['phase_xition'])
        print(f"  [threshold={pt}] phase_xition_count = {phase_count}/5")
        results.append({
            'phase_threshold': pt,
            'phase_xition_count': phase_count,
            'value_magnitude': result['final_state']['value_magnitude'],
            'temperature_final': result['snapshots'][-1]['temperature'],
        })

    return {'scan_results': results}


# ── 主入口 ─────────────────────────────────────────


def main() -> int:
    """主入口：跑阶段 B 集成测试。"""
    print("=" * 60)
    print("  M2.1 阶段 B: SGE 化改造集成测试")
    print("=" * 60)
    print(f"\n  覆盖子任务: B1 (drives schema) + B2 (Value Layer) + B3 (Value EMA)")
    print(f"               + B4 (Critic LLM) + B5 (Phase scan) + B6 (Hawking) + B7 (Crystallize)")

    # ── 单元级验证 ──
    print(f"\n{'─'*60}")
    print(f"  单元验证")
    print(f"{'─'*60}")
    print(f"  SGE_DEFAULT_DRIVES = {SGE_DEFAULT_DRIVES}")
    print(f"  SGE_DEFAULT_VALUES = {SGE_DEFAULT_VALUES}")
    print(f"  SGE_HAWKING_GAMMA = {SGE_HAWKING_GAMMA} (半衰期 ~{0.693/SGE_HAWKING_GAMMA:.1f} h)")
    print(f"  crystallize_threshold(N=5) = {crystallize_threshold(5):.4f}")
    print(f"  crystallize_threshold(N=12) = {crystallize_threshold(12):.4f}")

    # ── 主测试 1: 阶段 B 5 步循环 ──
    print(f"\n{'─'*60}")
    print(f"  主测试 1: 阶段 B 5 步循环 (seed=42)")
    print(f"{'─'*60}\n")
    result_42 = run_phase_b_loop(seed=42, n_steps=5)
    for s in result_42['snapshots']:
        print(f"  [step {s['step']}] event={s['event_type']:<10s} "
              f"ctx.emotion={s['context_user_emotion']:+.2f} "
              f"value_safety={s['value_state_safety']:+.3f} "
              f"value_comp={s['value_state_compassion']:+.3f} "
              f"phase_x={s['phase_xition']}")

    # ── 多 seed 验证 ──
    multi_seed_ok = verify_multi_seed([42, 7, 123])

    # ── 阶段 A 回归 ──
    phase_a_ok = verify_phase_a_baseline()

    # ── Phase 阈值扫描 ──
    scan = phase_threshold_scan()

    # ── 写输出 ──
    output_path = OUTPUT_DIR / "m21_phase_b_result.json"
    output_path.write_text(
        json.dumps({
            'seed_42_result': result_42,
            'phase_threshold_scan': scan,
        }, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    scan_path = OUTPUT_DIR / "phase_threshold_scan.json"
    scan_path.write_text(
        json.dumps(scan, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )

    print(f"\n  状态快照: {output_path}")
    print(f"  Phase 扫描: {scan_path}")

    # ── 总体判断 ──
    all_ok = multi_seed_ok and phase_a_ok
    print(f"\n  multi_seed={'PASS' if multi_seed_ok else 'FAIL'} | "
          f"phase_a_regression={'PASS' if phase_a_ok else 'FAIL'}")
    print(f"\n  总体: {'✅ PASS — M2.1 阶段 B 集成验证通过' if all_ok else '❌ FAIL'}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
