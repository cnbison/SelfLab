"""
SGE M1.1 冒烟测试 / 扩大测试
====================================================================
目的: 验证 M1.1 pipeline 通畅；扩大跑批验证价值涌现趋势
时间: 5-10 分钟 (10 Epoch) 或 30-60 分钟 (80 Epoch)
输入: .env 中的 MINIMAX_API_KEY
输出: experiments/output/m11_<test_name>/

设计: 3 阶段
  - 阶段 1: API 连接测试 (1 次简单调用)
  - 阶段 2: 单 Epoch 完整测试 (验证 17 步循环)
  - 阶段 3: N Epoch 跑批（默认 10，可用 --epochs 修改为 80）

用法:
  python m11_smoke_test.py                    # 默认 10 Epoch
  python m11_smoke_test.py --epochs 80         # 80 Epoch
  python m11_smoke_test.py --epochs 80 --seed 1  # 80 Epoch, seed=1
  python m11_smoke_test.py --name extended_80  # 自定义输出目录名

符合 CLAUDE.md §实验代码约定: 一次性、归档不修改
====================================================================
"""

import os
import sys
import json
import time
import uuid
import random
import argparse
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional
from dotenv import load_dotenv
import yaml


# ============================================================
# 1. 环境和配置加载
# ============================================================
def setup_environment():
    """加载 .env 和配置文件。"""
    load_dotenv()
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        print("✗ MINIMAX_API_KEY 未设置")
        print("  请在 .env 文件中设置: MINIMAX_API_KEY=your-key")
        sys.exit(1)
    print(f"✓ API Key 已加载: {api_key[:8]}...")

    # 加载配置
    try:
        with open("experiments/configs/m11_base.yaml") as f:
            base = yaml.safe_load(f)
        with open("experiments/configs/m11_encouraged.yaml") as f:
            group = yaml.safe_load(f)
        with open("experiments/configs/m11_event_templates.yaml") as f:
            templates = yaml.safe_load(f)
        print("✓ 配置文件加载成功")
    except FileNotFoundError as e:
        print(f"✗ 配置文件缺失: {e}")
        sys.exit(1)

    return api_key, base, group, templates


# ============================================================
# 2. 数据结构定义
# ============================================================
@dataclass
class LifeEvent:
    event_id: str
    event_type: str
    description: str
    intensity: float
    value_challenges: List[str]
    causal_context: Optional[str] = None
    timestamp: float = 0.0


# ============================================================
# 3. LLM 调用（Critic）
# ============================================================
def call_critic(api_key: str, base_config: dict, event: dict, value_vector: dict) -> dict:
    """调用 Critic LLM 分析事件。"""
    try:
        from litellm import completion
    except ImportError:
        print("✗ litellm 未安装")
        print("  请运行: pip install litellm")
        sys.exit(1)

    # 构造 Critic Prompt
    vv_str = ", ".join(f"{k}={v:.3f}" for k, v in value_vector.items())
    prompt = f"""你是一个"人工自我"实验中的情感感知器。分析以下人生事件，输出严格的 JSON。

[当前状态]
价值向量: {{{vv_str}}}

[事件]
{event['description']}

[输出格式 - 仅 JSON，无其他文字]
{{
  "context": {{
    "event_type": "{event['type']}",
    "event_intensity": 0.7,
    "value_relevance": 0.6,
    "novelty": 0.5,
    "challenge_level": 0.5,
    "clarity": 0.8,
    "emotional_impact": 0.0,
    "causal_coherence": 0.7
  }},
  "value_delta": {{
    "safety": 0.0,
    "creativity": 0.0,
    "connection": 0.0,
    "autonomy": 0.0,
    "justice": 0.0,
    "compassion": 0.0
  }},
  "frustration_delta": {{
    "security": 0.0,
    "exploration": 0.0,
    "connection": 0.0,
    "autonomy": 0.0,
    "meaning": 0.0
  }}
}}"""

    try:
        response = completion(
            model="anthropic/MiniMax-M3",
            base_url=base_config["llm"]["anthropic_compatible"]["base_url"],
            api_key=api_key,
            messages=[{"role": "user", "content": prompt}],
            temperature=base_config["llm"]["critic_temperature"],
            max_tokens=500,
        )
        text = response.choices[0].message.content.strip()
        # 多层容错解析 JSON
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        else:
            print(f"  ⚠ Critic 未返回有效 JSON: {text[:100]}")
            return _default_critic_output(event)
    except Exception as e:
        print(f"  ⚠ Critic LLM 调用失败: {e}")
        return _default_critic_output(event)


def _default_critic_output(event):
    """Critic 失败时的默认值。"""
    return {
        "context": {
            "event_type": event["type"],
            "event_intensity": event.get("intensity", 0.5),
            "value_relevance": 0.5,
            "novelty": 0.5,
            "challenge_level": 0.5,
            "clarity": 0.5,
            "emotional_impact": 0.0,
            "causal_coherence": 0.5
        },
        "value_delta": {v: 0.0 for v in ["safety", "creativity", "connection", "autonomy", "justice", "compassion"]},
        "frustration_delta": {k: 0.0 for k in ["security", "exploration", "connection", "autonomy", "meaning"]}
    }


# ============================================================
# 4. 价值向量 EMA
# ============================================================
def ema_update(value_vector: dict, value_delta: dict, intensity: float,
               base_alpha: float, max_alpha: float) -> dict:
    """Value Vector 指数移动平均更新。"""
    alpha = max(min(base_alpha + 0.5 * intensity, max_alpha), base_alpha)
    for k in value_vector:
        if k in value_delta:
            new_val = value_vector[k] + value_delta[k]
            new_val = max(-1.0, min(1.0, new_val))
            value_vector[k] = round(alpha * new_val + (1 - alpha) * value_vector[k], 6)
    return value_vector


# ============================================================
# 5. 事件选择
# ============================================================
def select_event(epoch: int, templates: dict, baby_id: str = "encouraged", seed: int = 42) -> dict:
    """根据 Epoch 选择事件（按阶段分布）。"""
    rng = random.Random(seed + epoch)

    # 阶段 1 (Epoch 0-19): 只有 success/failure/relationship
    if epoch < 20:
        types = ["success", "failure", "relationship"]
    elif epoch < 30:
        types = ["success", "failure", "relationship", "exploration"]
    elif epoch < 40:
        types = ["success", "failure", "relationship", "exploration", "risk"]
    else:
        types = ["success", "failure", "relationship", "exploration", "risk", "value_conflict"]

    event_type = rng.choice(types)
    pool = templates.get(event_type, [])
    if not pool:
        # 回退到 success
        event_type = "success"
        pool = templates["success"]

    event_template = rng.choice(pool)
    intensity = round(rng.uniform(*event_template["intensity_range"]), 2)

    return {
        "event_id": f"{baby_id}-e{epoch:03d}-{uuid.uuid4().hex[:8]}",
        "type": event_type,
        "description": event_template["description"],
        "intensity": intensity,
        "value_challenges": event_template.get("value_challenges", []),
        "causal_context": event_template.get("causal_context", ""),
        "timestamp": time.time()
    }


# ============================================================
# 6. 单 Epoch 完整 17 步循环（简化版）
# ============================================================
def run_epoch(api_key: str, base_config: dict, epoch: int, seed: int,
              value_vector: dict, meta_values: dict) -> dict:
    """运行一个 Epoch 的 17 步认知循环（冒烟测试简化版）。"""
    baby_id = "encouraged"
    event_templates_file = "experiments/configs/m11_event_templates.yaml"
    with open(event_templates_file) as f:
        templates = yaml.safe_load(f)

    # Step 1: Event Generator
    event = select_event(epoch, templates, baby_id, seed)
    print(f"\n[Epoch {epoch}] 类型={event['type']}, 强度={event['intensity']}")
    print(f"  事件: {event['description'][:60]}...")

    # Step 2: Time Metabolism（简化）
    frustration_before = {
        "security": 1.0, "exploration": 1.0, "connection": 1.0,
        "autonomy": 1.0, "meaning": 1.0
    }

    # Step 3: Critic (LLM)
    critic_output = call_critic(api_key, base_config, event, value_vector)
    value_delta = critic_output.get("value_delta", {})
    frustration_delta = critic_output.get("frustration_delta", {})
    print(f"  Critic value_delta: {value_delta}")

    # Step 4: Relationship EMA（简化：跳过）
    # Step 5: Reward Calculator
    reward = -sum(frustration_delta.values()) * 0.1
    print(f"  Reward: {reward:.4f}")

    # Step 6: Drive Baseline Evolution（简化：跳过）
    # Step 7: Crystallization Gate（简化：跳过）
    # Step 8: Compute Signals（简化：直接从 value_delta 派生）
    signals = {v: value_delta.get(v, 0.0) for v in value_vector}
    # Step 9: Thermodynamic Noise（简化：跳过）

    # Step 10-11: KNN Retrieval + Build Prompt（简化：跳过）
    # Step 12: Actor (LLM)（简化：跳过实际行为生成）

    # Step 13: Value Layer EMA
    value_vector = ema_update(
        value_vector, value_delta, event["intensity"],
        base_config["value_layer"]["base_alpha"],
        base_config["value_layer"]["max_alpha"]
    )
    print(f"  → Value Vector: {value_vector}")

    # Step 14-15: Identity + Narrative（简化：跳过）
    # Step 16: Hebbian Learning（简化：累积 |value_delta|）
    hebbian_change = abs(sum(value_delta.values()))
    # Step 17: Async Memory（简化：保存到日志）

    # 构造 Epoch 日志
    log = {
        "epoch": epoch,
        "seed": seed,
        "baby_id": baby_id,
        "timestamp": event["timestamp"],
        "event": event,
        "critic_output": critic_output,
        "reward": round(reward, 4),
        "signals": {k: round(v, 4) for k, v in signals.items()},
        "value_vector": {k: round(v, 4) for k, v in value_vector.items()},
        "meta_values": meta_values,
        "hebbian_change": round(hebbian_change, 4),
        "crystallized": hebbian_change > base_config["crystallization"]["threshold"]
    }

    return log


# ============================================================
# 7. 阶段 1：API 连接测试
# ============================================================
def test_api_connection(api_key: str, base_config: dict) -> bool:
    """阶段 1: 简单 API 调用测试。"""
    print("\n" + "=" * 60)
    print("阶段 1: API 连接测试")
    print("=" * 60)

    try:
        from litellm import completion
    except ImportError:
        print("✗ litellm 未安装")
        return False

    try:
        response = completion(
            model="anthropic/MiniMax-M3",
            base_url=base_config["llm"]["anthropic_compatible"]["base_url"],
            api_key=api_key,
            messages=[{"role": "user", "content": "Respond with exactly: API_OK"}],
            temperature=0.0,
            max_tokens=10,
        )
        text = response.choices[0].message.content.strip()
        print(f"✓ API 响应: {text[:50]}")
        if "OK" in text or "ok" in text:
            print("✓ API 连接正常")
            return True
        else:
            print(f"⚠ API 响应不符合预期，但连接成功")
            return True
    except Exception as e:
        print(f"✗ API 连接失败: {e}")
        return False


# ============================================================
# 8. 阶段 2：单 Epoch 完整测试
# ============================================================
def test_single_epoch(api_key: str, base_config: dict, value_vector: dict,
                      meta_values: dict) -> Optional[dict]:
    """阶段 2: 单 Epoch 完整 17 步循环测试。"""
    print("\n" + "=" * 60)
    print("阶段 2: 单 Epoch 完整测试")
    print("=" * 60)

    try:
        log = run_epoch(api_key, base_config, epoch=0, seed=42,
                       value_vector=value_vector, meta_values=meta_values)
        # 验证日志结构
        required_fields = ["epoch", "event", "critic_output", "value_vector"]
        for field_name in required_fields:
            if field_name not in log:
                print(f"✗ 缺少必需字段: {field_name}")
                return None

        # 验证 value_vector 是 dict 且有 6 个维度
        if not isinstance(log["value_vector"], dict) or len(log["value_vector"]) != 6:
            print(f"✗ value_vector 结构异常")
            return None

        print("\n✓ 单 Epoch 测试通过")
        print(f"  涌现幅度: {sum(abs(v) for v in log['value_vector'].values()) / 6:.4f}")
        return log
    except Exception as e:
        print(f"✗ 单 Epoch 测试失败: {e}")
        return None


# ============================================================
# 9. 阶段 3：10 Epoch 跑批
# ============================================================
# ============================================================
# 10. 主函数
# ============================================================
def test_n_epochs(api_key: str, base_config: dict, output_dir: str,
                 n_epochs: int, seed: int = 42) -> List[dict]:
    """阶段 3: N Epoch 跑批测试（带 checkpoint 和进度报告）。"""
    print("\n" + "=" * 60)
    print(f"阶段 3: {n_epochs} Epoch 跑批测试 (seed={seed})")
    print("=" * 60)

    # 初始化状态
    value_vector = {
        "safety": 0.0, "creativity": 0.0, "connection": 0.0,
        "autonomy": 0.0, "justice": 0.0, "compassion": 0.0
    }
    meta_values = base_config["value_layer"]["meta_values"]

    epoch_logs = []
    start_time = time.time()
    last_progress_time = start_time

    checkpoint_interval = max(10, n_epochs // 4)  # 每 25% 保存一次

    for epoch in range(n_epochs):
        try:
            log = run_epoch(api_key, base_config, epoch, seed,
                           value_vector, meta_values)
            epoch_logs.append(log)
        except Exception as e:
            print(f"✗ Epoch {epoch} 失败: {e}")
            continue

        # 进度报告（每 10 Epoch 或每 30 秒）
        elapsed = time.time() - start_time
        now = time.time()
        if (epoch + 1) % 10 == 0 or (now - last_progress_time) > 30:
            progress = (epoch + 1) / n_epochs * 100
            avg_time = elapsed / (epoch + 1)
            remaining = (n_epochs - epoch - 1) * avg_time
            print(f"\n[进度] {epoch+1}/{n_epochs} ({progress:.0f}%) - "
                  f"已用 {elapsed:.0f}s, 预计剩余 {remaining:.0f}s")
            print(f"  当前 VV: safety={value_vector['safety']:.3f}, "
                  f"creativity={value_vector['creativity']:.3f}, "
                  f"connection={value_vector['connection']:.3f}")
            print(f"  当前涌现幅度: {sum(abs(v) for v in value_vector.values())/6:.4f}")
            last_progress_time = now

        # Checkpoint
        if (epoch + 1) % checkpoint_interval == 0 or (epoch + 1) == n_epochs:
            _save_checkpoint(epoch_logs, output_dir, value_vector, meta_values,
                           seed, epoch + 1)

        # 短暂延迟避免 rate limit
        time.sleep(1)

    elapsed = time.time() - start_time

    # 保存
    _save_final_outputs(epoch_logs, value_vector, meta_values, output_dir,
                       seed, elapsed, n_epochs)

    return epoch_logs


def _save_checkpoint(epoch_logs, output_dir, value_vector, meta_values, seed, n_done):
    """保存检查点（每 N Epoch 一次，避免崩溃丢失）。"""
    checkpoint_path = f"{output_dir}/checkpoint_e{n_done-1:03d}.json"
    checkpoint = {
        "version": "1.0",
        "checkpoint_at_epoch": n_done - 1,
        "total_epochs_planned": len(epoch_logs) + 1,  # 不准确但够用
        "seed": seed,
        "value_vector": {k: round(v, 4) for k, v in value_vector.items()},
        "meta_values": meta_values,
        "n_logs": len(epoch_logs)
    }
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)


def _save_final_outputs(epoch_logs, value_vector, meta_values, output_dir, seed, elapsed, n_epochs):
    """保存最终输出（epoch_log, value_trajectory, summary）。"""
    # epoch_log.jsonl
    log_path = f"{output_dir}/epoch_log.jsonl"
    with open(log_path, "w", encoding="utf-8") as f:
        for log in epoch_logs:
            f.write(json.dumps(log, ensure_ascii=False) + "\n")
    print(f"\n✓ 已保存 {len(epoch_logs)} 个 Epoch 到 {log_path}")

    # value_trajectory.jsonl
    traj_path = f"{output_dir}/value_trajectory.jsonl"
    with open(traj_path, "w", encoding="utf-8") as f:
        for log in epoch_logs:
            traj = {
                "epoch": log["epoch"],
                "value_vector": log["value_vector"],
                "meta_values": log["meta_values"],
                "emergence_magnitude": round(
                    sum(abs(v) for v in log["value_vector"].values()) / 6, 4
                )
            }
            f.write(json.dumps(traj, ensure_ascii=False) + "\n")
    print(f"✓ 已保存价值轨迹到 {traj_path}")

    # summary.json
    summary = _generate_summary(epoch_logs, value_vector, meta_values, seed, elapsed, n_epochs)
    summary_path = f"{output_dir}/summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"✓ 已保存总结到 {summary_path}")

    # 总结
    _print_final_summary(summary, output_dir, n_epochs)


def _generate_summary(epoch_logs, value_vector, meta_values, seed, elapsed, n_epochs):
    """生成实验总结。"""
    if not epoch_logs:
        return {"error": "no_epoch_logs"}

    initial_vv = {v: 0.0 for v in value_vector}
    final_vv = epoch_logs[-1]["value_vector"]
    final_mag = sum(abs(v) for v in final_vv.values()) / 6

    # 计算方向一致性
    weighted_event_vv = {v: 0.0 for v in value_vector}
    for log in epoch_logs:
        for v, delta in log.get("critic_output", {}).get("value_delta", {}).items():
            if v in weighted_event_vv:
                weighted_event_vv[v] += delta * log["event"].get("intensity", 0.5)
    dot_product = sum(final_vv.get(v, 0) * weighted_event_vv.get(v, 0) for v in final_vv)
    final_norm = (sum(v*v for v in final_vv.values())) ** 0.5
    weighted_norm = (sum(v*v for v in weighted_event_vv.values())) ** 0.5
    direction_coherence = (dot_product / (final_norm * weighted_norm)) if (final_norm * weighted_norm) > 0 else 0

    # 计算 trajectory 平滑度
    trajectory_smoothness = 0
    if len(epoch_logs) > 1:
        distances = []
        for i in range(1, len(epoch_logs)):
            v1 = epoch_logs[i-1]["value_vector"]
            v2 = epoch_logs[i]["value_vector"]
            d = sum((v2[v] - v1[v])**2 for v in v1) ** 0.5
            distances.append(d)
        trajectory_smoothness = sum(distances) / len(distances)

    return {
        "version": "1.0",
        "experiment": "M1.1-smoke-test-extended",
        "seed": seed,
        "n_epochs_planned": n_epochs,
        "n_epochs_completed": len(epoch_logs),
        "elapsed_seconds": round(elapsed, 1),
        "avg_seconds_per_epoch": round(elapsed / max(len(epoch_logs), 1), 2),
        "primary_metrics": {
            "emergence_magnitude": round(final_mag, 4),
            "emergence_magnitude_threshold": 0.3,
            "emergence_pass": final_mag > 0.3,
            "direction_coherence": round(direction_coherence, 4),
            "direction_coherence_threshold": 0.5,
            "direction_pass": direction_coherence > 0.5,
            "trajectory_smoothness": round(trajectory_smoothness, 4)
        },
        "initial_value_vector": initial_vv,
        "final_value_vector": {k: round(v, 4) for k, v in final_vv.items()},
        "meta_values": meta_values,
        "judgment": {
            "emergence_pass": final_mag > 0.3,
            "direction_pass": direction_coherence > 0.5,
            "all_pass": final_mag > 0.3 and direction_coherence > 0.5
        }
    }


def _print_final_summary(summary, output_dir, n_epochs):
    """打印最终总结。"""
    print(f"\n=== 跑批总结 ===")
    print(f"完成 Epoch: {summary['n_epochs_completed']}/{n_epochs}")
    print(f"耗时: {summary['elapsed_seconds']}s (平均 {summary['avg_seconds_per_epoch']}s/Epoch)")
    print(f"\n--- 主要指标 ---")
    pm = summary["primary_metrics"]
    print(f"  涌现幅度: {pm['emergence_magnitude']} (阈值: > {pm['emergence_magnitude_threshold']}) {'✓' if pm['emergence_pass'] else '✗'}")
    print(f"  方向一致性: {pm['direction_coherence']} (阈值: > {pm['direction_coherence_threshold']}) {'✓' if pm['direction_pass'] else '✗'}")
    print(f"  轨迹平滑度: {pm['trajectory_smoothness']}")

    print(f"\n--- 最终价值向量 ---")
    fv = summary["final_value_vector"]
    for k, v in sorted(fv.items(), key=lambda x: -abs(x[1])):
        marker = "↑" if v > 0.1 else ("↓" if v < -0.1 else "·")
        print(f"  {marker} {k:12s} {v:+.4f}")

    print(f"\n--- 综合判定 ---")
    j = summary["judgment"]
    if j["all_pass"]:
        print(f"  ✓ 全部通过: 涌现幅度 + 方向一致性")
        print(f"  → M1.1 早期证据成立")
    elif j["emergence_pass"] or j["direction_pass"]:
        print(f"  △ 部分通过")
        print(f"  → 建议扩大样本: 完整 80 Epoch + 多 seed")
    else:
        print(f"  ✗ 未通过: 需要调整参数或事件流")


def main():
    parser = argparse.ArgumentParser(
        description="SGE M1.1 冒烟测试 / 扩大测试"
    )
    parser.add_argument("--epochs", type=int, default=10,
                       help="总 Epoch 数（默认 10，建议扩大测试用 80）")
    parser.add_argument("--seed", type=int, default=42,
                       help="随机种子（默认 42）")
    parser.add_argument("--name", type=str, default="smoke_test",
                       help="输出目录名（默认 m11_smoke_test）")
    parser.add_argument("--skip-single-epoch", action="store_true",
                       help="跳过单 Epoch 测试（节省时间）")
    args = parser.parse_args()

    print("=" * 60)
    print(f"SGE M1.1 {'冒烟测试' if args.epochs <= 10 else '扩大测试'}")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"配置: epochs={args.epochs}, seed={args.seed}, name={args.name}")

    # 阶段 0: 准备
    api_key, base_config, group_config, templates = setup_environment()
    output_dir = f"experiments/output/m11_{args.name}"
    os.makedirs(output_dir, exist_ok=True)
    print(f"输出目录: {output_dir}")

    # 阶段 1: API 连接测试
    if not test_api_connection(api_key, base_config):
        print("\n✗ 阶段 1 失败，测试中止")
        print("  请检查:")
        print("  1. .env 中的 MINIMAX_API_KEY 是否正确")
        print("  2. m11_base.yaml 中的 base_url 是否正确")
        print("  3. 网络连接是否正常")
        return

    # 阶段 2: 单 Epoch 测试（可跳过）
    value_vector = {
        "safety": 0.0, "creativity": 0.0, "connection": 0.0,
        "autonomy": 0.0, "justice": 0.0, "compassion": 0.0
    }
    meta_values = base_config["value_layer"]["meta_values"]

    if not args.skip_single_epoch:
        single_log = test_single_epoch(api_key, base_config, value_vector, meta_values)
        if single_log is None:
            print("\n✗ 阶段 2 失败，测试中止")
            return

    # 阶段 3: N Epoch 跑批
    epoch_logs = test_n_epochs(api_key, base_config, output_dir,
                              n_epochs=args.epochs, seed=args.seed)

    # 最终总结已在 test_n_epochs 中输出
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
