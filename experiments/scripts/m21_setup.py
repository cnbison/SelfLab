"""
M2.1 阶段 A：SGE 基线冒烟测试

对应 ROADMAP 里程碑：M2.1（完整 SGE 架构）— 阶段 A 前置
对应 PRD 需求：FR-8（Time Metabolism）, FR-9（Thermodynamic Noise）, FR-10（双 LLM 架构核心循环）
对应 ARCH 模块：§3 Memory / Time Layer, §3 Hebbian Learning
对应研究文档：research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md §五 阶段 A

实验目的：验证从 AiBeing 借鉴的 4 个核心机制在 SGE 实验环境中可独立运行
实验设计：5 步最小循环，stub LLM，5D drives（AiBeing 原生）
运行方法：python experiments/scripts/m21_setup.py
预期产出：stdout 状态快照 + experiments/output/m21_baseline_setup.json
归档策略：实验完成后归档到 experiments/archive/2026-06-m21/（暂不归档）

借鉴来源（不复制到 SelfLab 仓库）：
- ~/project/AiBeing/engine/genome/drive_metabolism.py — Time Metabolism + Thermodynamic Noise
- ~/project/AiBeing/engine/genome/genome_engine.py — Agent + Hebbian Learning + Phase Transition
- ~/project/genome/style_memory.py — KNN + Hawking + Crystallization (M2.1 阶段 B 才用)
- ~/project/genome/critic.py — Critic LLM 感知 (M2.1 阶段 B 才用)
- ~/project/agent/evermemos_mixin.py — Relationship EMA (M2.1 阶段 B 才用)
"""

import json
import math
import os
import random
import sys
import time
from pathlib import Path


# ── 把 AiBeing 项目加入 sys.path ──────────────────────────────
# AiBeing 是外部项目（Bisen 本地管理），不在 SelfLab 仓库。
# 本脚本通过 sys.path 引用其 engine/ 包，不复制代码到 SelfLab。
AIBEING_PATH = Path("/Users/loubicheng/project/AiBeing").resolve()
if not AIBEING_PATH.exists():
    sys.exit(f"[ERROR] AiBeing 项目路径不存在: {AIBEING_PATH}")
if str(AIBEING_PATH) not in sys.path:
    sys.path.insert(0, str(AIBEING_PATH))


# ── 借鉴 1: Time Metabolism + Thermodynamic Noise ──────────────
from engine.genome.drive_metabolism import DriveMetabolism

# ── 借鉴 2: Agent 神经网络 + Hebbian Learning + Phase Transition ─
from engine.genome.genome_engine import Agent, DRIVES, SIGNALS, CONTEXT_FEATURES

# ── 借鉴 3: KNN + Hawking + Crystallization（M2.1 阶段 A 仅 import 验证）──
from engine.genome.style_memory import (
    ContinuousStyleMemory,
    HAWKING_GAMMA,
    CONTEXT_KEYS,
)

# ── 借鉴 4: Critic LLM 感知（阶段 A 仅 import 验证，阶段 B 才调用）──
from engine.genome.critic import critic_sense, _CRITIC_CONTEXT_KEYS

# ── 借鉴 5: Relationship EMA（阶段 A 仅 import 验证）──
# 注：_apply_relationship_ema 在 agent/evermemos_mixin.py 中，是 ChatAgent 的方法
# M2.1 阶段 A 不实例化 ChatAgent（避免依赖完整 LLM 栈），仅验证模块可访问
try:
    from agent.evermemos_mixin import EverMemOSMixin  # 仅验证可 import
    EMA_AVAILABLE = True
    EMA_SKIP_REASON = ""
except ImportError as e:
    EMA_AVAILABLE = False
    EMA_SKIP_REASON = f"missing dep: {e.name if hasattr(e, 'name') else e}"


# ── 输出目录 ──────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "m21_baseline"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def make_stub_context(seed: int = 0) -> dict:
    """
    构造一个 stub 的 context（12D，来自 AiBeing CONTEXT_FEATURES）。
    阶段 A 不调用真实 LLM，用固定值代替 Critic 输出。
    """
    rng = random.Random(seed)
    return {
        # 8D Critic context
        'user_emotion': 0.3,
        'topic_intimacy': 0.5,
        'time_of_day': 0.5,
        'conversation_depth': 0.5,
        'user_engagement': 0.7,
        'conflict_level': rng.uniform(0.0, 0.3),
        'novelty_level': 0.4,
        'user_vulnerability': 0.4,
        # 4D EverMemOS（基线阶段暂用 0）
        'relationship_depth': 0.0,
        'emotional_valence': 0.0,
        'trust_level': 0.0,
        'pending_foresight': 0.0,
    }


def make_stub_reward(step: int) -> float:
    """
    构造一个 stub 的 reward：偶数步正、奇数步负，用于观察 Hebbian 学习。
    """
    return 0.3 if step % 2 == 0 else -0.15


def snapshot_state(agent: Agent, metabolism: DriveMetabolism, step: int) -> dict:
    """捕获当前状态快照（用于输出和后续对比）。"""
    return {
        'step': step,
        'drive_state': dict(agent.drive_state),
        'drive_baseline': dict(agent.drive_baseline),
        'recurrent_state': list(agent.recurrent_state),
        'signal_history_len': len(agent.signal_history),
        'total_reward': round(agent.total_reward, 4),
        'frustration': {d: round(metabolism.frustration[d], 4) for d in DRIVES},
        'frustration_total': round(metabolism.total(), 4),
        'temperature': round(metabolism.temperature(), 4),
        'last_phase_transition': agent._last_phase_transition,
    }


def run_minimal_loop(seed: int = 42, n_steps: int = 5) -> dict:
    """
    跑 5 步最小循环：sense → compute_signals → learn → tick_drives → metabolism update。
    stub LLM 替代真实调用。
    """
    print(f"\n{'='*60}")
    print(f"  M2.1 阶段 A 基线冒烟测试 — seed={seed}, n_steps={n_steps}")
    print(f"{'='*60}\n")

    # ── 初始化（直接复用 AiBeing 类的 __init__）──
    agent = Agent(seed=seed)
    metabolism = DriveMetabolism(clock=time.time())
    snapshots = []

    print(f"  [init] agent seed={agent.seed}, drives={DRIVES}")
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

        print(f"  [step {step}] reward={reward:+.3f} | "
              f"frust={metabolism.total():.3f} | "
              f"temp={metabolism.temperature():.3f} | "
              f"dominant_signal={max(signals, key=signals.get)}={signals[max(signals, key=signals.get)]:.3f} | "
              f"phase_xition={snap['last_phase_transition']}")

    return {
        'seed': seed,
        'n_steps': n_steps,
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
    return diff > 0.0  # 至少有一些变化


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
    print(f"\n  AiBeing 路径: {AIBEING_PATH}")
    print(f"  借鉴模块验证:")
    print(f"    ✓ drive_metabolism.DriveMetabolism")
    print(f"    ✓ genome_engine.Agent / DRIVES / SIGNALS")
    print(f"    ✓ style_memory.ContinuousStyleMemory / HAWKING_GAMMA={HAWKING_GAMMA}/h")
    print(f"    ✓ critic.critic_sense / {_CRITIC_CONTEXT_KEYS}")
    print(f"    {'✓' if EMA_AVAILABLE else '⊘'} agent.evermemos_mixin (EMA)"
          f"{f' — {EMA_SKIP_REASON}' if not EMA_AVAILABLE else ''}")

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
    print(f"\n  总体: {'✅ PASS — 基线可运行' if all_ok else '❌ FAIL — 检查日志'}")

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
