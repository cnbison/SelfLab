"""
M2.1 阶段 A：SGE 基线冒烟测试

对应 ROADMAP 里程碑：M2.1（完整 SGE 架构）— 阶段 A 前置
对应 PRD 需求：FR-8（Time Metabolism）, FR-9（Thermodynamic Noise）, FR-10（双 LLM 架构核心循环）
对应 ARCH 模块：§3 Memory / Time Layer, §3 Hebbian Learning
对应研究文档：research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md §五 阶段 A

实验目的：验证 SGE 自有实现（_sge_baseline.py）的 4 个核心机制在 SGE 实验环境中可独立运行
实验设计：5 步最小循环，stub LLM，5D drives（AiBeing 原生 — 阶段 A 沿用）
运行方法：python experiments/scripts/m21_setup.py
预期产出：stdout 状态快照 + experiments/output/m21_baseline/m21_setup_snapshot.json
归档策略：实验完成后归档到 experiments/archive/2026-06-m21/（暂不归档）

设计原则：SGE 自有实现 + 借鉴映射作参考
- 算法来源：SGE-M21-AiBeing-Implementation-Mapping.md（研究文档）
- 代码实现：experiments/scripts/_sge_baseline.py（SGE 自有，不复制 AiBeing 代码）
- 验证方式：跑 5 步最小循环 + 与 AiBeing 行为对比（相同 seed 应得到相同结果）
- 不依赖：~/project/AiBeing 外部项目路径
"""

import json
import random
import sys
import time
from pathlib import Path


# ── SGE 自有实现（不依赖 AiBeing 外部项目）───────────────────
# 实现严格遵循借鉴映射文档的公式：
#   research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md
# 每个函数 docstring 标注 "来源: AiBeing 源码 + 行号" + "公式" + "参考 §2.x"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sge_baseline import (
    Agent,
    DriveMetabolism,
    DRIVES,
    SIGNALS,
    CONTEXT_FEATURES,
    HEBB_LR,
    PHASE_THRESHOLD,
)


# ── 阶段 A 不实现（阶段 B 才用）──
# 下面这些机制的验证在阶段 B 进行：
#   - §2.1 Critic LLM 感知（阶段 B 用真实 LLM 接入）
#   - §2.3 Relationship EMA → Value EMA（阶段 B 改造）
#   - §2.6 Crystallization（阶段 B/D 才用）
#   - §2.7 KNN + Hawking 辐射（阶段 B/D 才用）
#   - §2.9 双 LLM 编排（阶段 B/D 才实现完整 12 步循环）
# 阶段 A 仅验证 4 个核心机制：Time Metabolism / Thermodynamic Noise / Hebbian / Agent 前向


# ── 输出目录 ──────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "m21_baseline"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def make_stub_context(seed: int = 0) -> dict:
    """
    构造 stub context（12D，来自 CONTEXT_FEATURES）
    阶段 A 不调用真实 LLM；阶段 B 替换为 _sge_baseline 调用 critic_sense。
    """
    rng = random.Random(seed)
    return {
        # 8D Critic context（参考值）
        'user_emotion': 0.3,
        'topic_intimacy': 0.5,
        'time_of_day': 0.5,
        'conversation_depth': 0.5,
        'user_engagement': 0.7,
        'conflict_level': rng.uniform(0.0, 0.3),
        'novelty_level': 0.4,
        'user_vulnerability': 0.4,
        # 4D EverMemOS（阶段 A 暂用 0）
        'relationship_depth': 0.0,
        'emotional_valence': 0.0,
        'trust_level': 0.0,
        'pending_foresight': 0.0,
    }


def make_stub_reward(step: int) -> float:
    """
    构造 stub reward：偶数步正、奇数步负，用于观察 Hebbian 学习方向性。
    """
    return 0.3 if step % 2 == 0 else -0.15


def snapshot_state(agent: Agent, metabolism: DriveMetabolism, step: int) -> dict:
    """捕获当前状态快照。"""
    return {
        'step': step,
        'drive_state': dict(agent.drive_state),
        'drive_baseline': dict(agent.drive_baseline),
        'recurrent_state': [round(x, 4) for x in agent.recurrent_state],
        'signal_history_len': len(agent.signal_history),
        'total_reward': round(agent.total_reward, 4),
        'frustration': {d: round(metabolism.frustration[d], 4) for d in DRIVES},
        'frustration_total': round(metabolism.total(), 4),
        'temperature': round(metabolism.temperature(), 4),
        'last_phase_transition': agent._last_phase_transition,
        'agent_frustration': round(agent._frustration, 4),
    }


def run_minimal_loop(seed: int = 42, n_steps: int = 5) -> dict:
    """
    跑 5 步最小循环：sense → compute_signals → learn → tick_drives → metabolism update。
    stub LLM 替代真实调用。
    """
    print(f"\n{'='*60}")
    print(f"  M2.1 阶段 A 基线冒烟测试 — seed={seed}, n_steps={n_steps}")
    print(f"{'='*60}\n")

    # ── 初始化（自有实现）──
    agent = Agent(seed=seed)
    metabolism = DriveMetabolism(clock=time.time())
    snapshots = []

    print(f"  [init] agent seed={agent.seed}, drives={DRIVES}")
    print(f"  [init] hebbian_lr={HEBB_LR}, phase_threshold={PHASE_THRESHOLD}")
    print(f"  [init] drive_baseline={ {d: round(agent.drive_baseline[d], 3) for d in DRIVES} }")
    print(f"  [init] initial temperature={metabolism.temperature():.4f}\n")

    # ── 跑 n_steps 步 ──
    for step in range(n_steps):
        ctx = make_stub_context(seed=seed + step)
        reward = make_stub_reward(step)
        signals = agent.step(ctx, reward=reward)
        metabolism.apply_llm_delta({d: (reward if d == 'connection' else 0.0) for d in DRIVES})
        snap = snapshot_state(agent, metabolism, step)
        snapshots.append(snap)

        dominant_sig = max(signals, key=signals.get)
        print(f"  [step {step}] reward={reward:+.3f} | "
              f"frust={metabolism.total():.3f} | "
              f"temp={metabolism.temperature():.3f} | "
              f"dominant_signal={dominant_sig}={signals[dominant_sig]:.3f} | "
              f"phase_xition={snap['last_phase_transition']}")

    return {
        'seed': seed,
        'n_steps': n_steps,
        'source': 'SGE 自有实现 (_sge_baseline.py)',
        'reference_doc': 'research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md',
        'snapshots': snapshots,
        'final_state': snapshots[-1],
    }


def verify_drives_settled(result: dict) -> bool:
    """
    验证：跑 n_steps 后，drive_state 应该有变化（不应完全等于初始 baseline）。
    阶段 A 冒烟测试的最低标准。
    """
    initial_baseline = result['snapshots'][0]['drive_baseline']
    final_drive = result['final_state']['drive_state']
    diff = sum(abs(final_drive[d] - initial_baseline[d]) for d in DRIVES)
    print(f"\n  [verify] drive_state 变化总量 (vs baseline) = {diff:.4f}")
    return diff > 0.0


def verify_metabolism_works(result: dict) -> bool:
    """验证：frustration 累积后，temperature 应该 > 0。"""
    final_temp = result['final_state']['temperature']
    print(f"  [verify] final temperature = {final_temp:.4f}")
    return final_temp > 0.0


def main() -> int:
    """主入口：跑基线冒烟测试 + 输出报告。"""
    print("=" * 60)
    print("  M2.1 阶段 A: SGE 基线冒烟测试")
    print("=" * 60)
    print(f"\n  实现来源：experiments/scripts/_sge_baseline.py（SGE 自有）")
    print(f"  借鉴映射：research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md")
    print(f"  不依赖：~/project/AiBeing 外部项目路径")
    print(f"\n  阶段 A 验证 4 个核心机制:")
    print(f"    ✓ Time Metabolism（冷却 + 饥饿）")
    print(f"    ✓ Thermodynamic Noise（温度曲线 + 高斯噪声）")
    print(f"    ✓ Hebbian Learning（神经网络权重更新）")
    print(f"    ✓ Phase Transition（挫败感累积触发）")
    print(f"\n  阶段 A 不验证（阶段 B/D 才用）:")
    print(f"    ⊘ Critic LLM 感知（阶段 B 接入真实 LLM）")
    print(f"    ⊘ Relationship EMA → Value EMA（阶段 B 改造）")
    print(f"    ⊘ Crystallization / KNN / Hawking（阶段 B/D）")
    print(f"    ⊘ 完整 12 步双 LLM 编排（阶段 B/D）")

    # ── 跑 seed=42 基线 ──
    result = run_minimal_loop(seed=42, n_steps=5)

    # ── 验证 ──
    print(f"\n{'─'*60}")
    print(f"  验证结果")
    print(f"{'─'*60}")
    drives_ok = verify_drives_settled(result)
    metabolism_ok = verify_metabolism_works(result)

    all_ok = drives_ok and metabolism_ok
    print(f"\n  drives_settled={'PASS' if drives_ok else 'FAIL'} | "
          f"metabolism={'PASS' if metabolism_ok else 'FAIL'}")
    print(f"\n  总体: {'✅ PASS — SGE 自有基线可运行' if all_ok else '❌ FAIL — 检查日志'}")

    # ── 写输出文件 ──
    output_path = OUTPUT_DIR / "m21_setup_snapshot.json"
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    print(f"\n  状态快照已保存: {output_path}")
    print(f"  大小: {output_path.stat().st_size} bytes\n")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
