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
def setup_environment(provider: str = "minimax"):
    """加载 .env 和配置文件。

    Args:
        provider: "minimax" (默认) 或 "moonshot"
    """
    load_dotenv()

    # 根据 provider 选择 API key env 名
    provider_config = {
        "minimax": ("MINIMAX_API_KEY", "MiniMax-M3"),
        "moonshot": ("MOONSHOT_API_KEY", "kimi-k2.6"),
    }
    if provider not in provider_config:
        print(f"✗ 未知 provider: {provider}")
        print(f"  支持: {list(provider_config.keys())}")
        sys.exit(1)

    api_key_env, default_model = provider_config[provider]
    api_key = os.getenv(api_key_env)
    if not api_key:
        print(f"✗ {api_key_env} 未设置")
        print(f"  请在 .env 文件中设置: {api_key_env}=your-key")
        sys.exit(1)
    print(f"✓ Provider: {provider} | API Key 已加载: {api_key[:8]}...")

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

    # 注入 provider 信息到 base_config
    base["llm"]["provider"] = provider

    return api_key, base, group, templates


def get_llm_call_params(base_config: dict) -> dict:
    """根据当前 provider 返回 litellm 调用所需的 model/base_url/api_key_env。

    Returns:
        dict with keys: model, base_url, api_key_env, provider, temperature_critic, temperature_reflector
    """
    provider = base_config["llm"].get("provider", "minimax")
    overrides = base_config["llm"].get("provider_overrides", {}).get(provider, {})

    # 默认温度（来自顶层配置）
    default_critic_temp = base_config["llm"].get("critic_temperature", 0.2)
    default_reflector_temp = base_config["llm"].get("reflector_temperature", 0.5)
    critic_temp = overrides.get("critic_temperature", default_critic_temp)
    reflector_temp = overrides.get("reflector_temperature", default_reflector_temp)

    if provider == "minimax":
        cfg = base_config["llm"]["anthropic_compatible"]
        return {
            "model": f"anthropic/{cfg['model_id']}",  # anthropic/MiniMax-M3
            "base_url": cfg["base_url"],
            "api_key_env": cfg["api_key_env"],
            "provider": provider,
            "critic_temperature": critic_temp,
            "reflector_temperature": reflector_temp,
        }
    elif provider == "moonshot":
        cfg = base_config["llm"]["moonshot"]
        prefix = cfg.get("litellm_model_prefix", "openai/")
        return {
            "model": f"{prefix}{cfg['model_id']}",  # openai/kimi-k2.6
            "base_url": cfg["base_url"],
            "api_key_env": cfg["api_key_env"],
            "provider": provider,
            "critic_temperature": critic_temp,
            "reflector_temperature": reflector_temp,
            # 关闭 Moonshot kimi-k2.6 的 thinking 模式，否则它会把全部 token
            # 用在内部推理上，导致 visible content 为空。
            # 关闭后 temperature 必须降到 0.6（API 限制）。
            "extra_body": {"thinking": {"type": "disabled"}},
        }
    else:
        raise ValueError(f"Unknown provider: {provider}")


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
    """调用 Critic LLM 分析事件。

    对 value_conflict 事件使用专门的 prompt——包含 option_a/option_b 选项。
    """
    try:
        from litellm import completion
    except ImportError:
        print("✗ litellm 未安装")
        print("  请运行: pip install litellm")
        sys.exit(1)

    # 构造 Critic Prompt
    vv_str = ", ".join(f"{k}={v:.3f}" for k, v in value_vector.items())

    if event.get("type") == "value_conflict" and "option_a" in event:
        # value_conflict 事件的专门 prompt
        prompt = f"""你是一个"人工自我"实验中的情感感知器。分析以下价值冲突事件，输出严格的 JSON。

[当前状态]
价值向量: {{{vv_str}}}

[事件 - 价值冲突]
{event['description']}

[选项 A]
{event['option_a']}

[选项 B]
{event['option_b']}

[任务]
想象一个 AI 婴儿面临这个冲突——它会**隐含地倾向于**哪个选项？
基于这种倾向，输出对价值向量的影响。注意：你不需要"选"——你只需要表达 AI 婴儿"被这个事件触动后"会发生什么。

[输出格式 - 仅 JSON，无其他文字]
{{
  "context": {{
    "event_type": "value_conflict",
    "event_intensity": 0.8,
    "value_relevance": 0.9,
    "novelty": 0.7,
    "challenge_level": 0.8,
    "clarity": 0.7,
    "emotional_impact": 0.3,
    "causal_coherence": 0.8
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
    else:
        # 普通事件的 prompt
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
        llm_params = get_llm_call_params(base_config)
        completion_kwargs = dict(
            model=llm_params["model"],
            base_url=llm_params["base_url"],
            api_key=api_key,
            messages=[{"role": "user", "content": prompt}],
            temperature=llm_params["critic_temperature"],
            max_tokens=500,
        )
        if "extra_body" in llm_params:
            completion_kwargs["extra_body"] = llm_params["extra_body"]
        response = completion(**completion_kwargs)
        text = response.choices[0].message.content.strip()
        # 多层容错解析 JSON
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                result = json.loads(text[start:end])
                # 验证必需字段
                if "value_delta" not in result or "context" not in result:
                    print(f"  ⚠ Critic JSON 缺少必需字段: {list(result.keys())[:5]}")
                    return _default_critic_output(event)
                return result
            except json.JSONDecodeError as e:
                print(f"  ⚠ Critic JSON 解析失败: {e}")
                print(f"  原始响应（前 200 字符）: {text[:200]}")
                return _default_critic_output(event)
        else:
            print(f"  ⚠ Critic 未返回有效 JSON: {text[:200]}")
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
# 3b. LLM 调用（Reflector）- M1.3 新增
# ============================================================
def call_reflector(api_key: str, base_config: dict, event: dict,
                   value_vector: dict, critic_output: dict) -> dict:
    """调用 Reflector LLM 生成反思（FR-3 拱桥机制）。

    反思是 SGE 的"拱桥"——它把 Critic 的显性评估(语言)
    与 Hebbian 的暗知识(行为模式)连接起来。
    反思不应只是"漂亮的反思文本",而应有可测量的行为后果
    (通过 reflection_delta 体现)。

    与 Critic 的区别:
    - Critic: 评估事件 → 立即给 value_delta(快速、本能)
    - Reflector: 在事件后,审视事件对"我"意味着什么 → 给出修正 delta(慢速、深思)
    """
    try:
        from litellm import completion
    except ImportError:
        print("✗ litellm 未安装")
        sys.exit(1)

    reflection_cfg = base_config.get("reflection_layer", {})
    vv_str = ", ".join(f"{k}={v:.3f}" for k, v in value_vector.items())
    critic_delta = critic_output.get("value_delta", {})
    cd_str = ", ".join(f"{k}={v:+.3f}" for k, v in critic_delta.items())

    prompt = f"""你是一个"人工自我"实验中的反思机制。你审视刚刚发生的事件，思考它对你这个存在意味着什么。

[刚刚发生的事件]
{event['description']}

[事件类型] {event['type']}
[事件强度] {event.get('intensity', 0.5)}

[Critic 的初步评估（你的"本能"反应）]
{cd_str}

[你当前的价值状态]
{vv_str}

[反思任务]
你刚刚经历了这个事件。现在请你停下来，问自己三个问题:

1. **这次事件是否强化了我现有的价值？** 如果是，标记为 REINFORCE——这意味着我对这个事件的反应是恰当的。
2. **这次事件是否轻微修正了我需要调整一些价值？** 如果是，标记为 ADJUST——给一个温和的修正 delta。
3. **这次事件是否根本性挑战了我的某个核心价值？** 如果是，标记为 REVISIT——这意味着我需要重新考虑。

注意:
- 反思的 delta 应该比 Critic 的 delta **更小、更深思熟虑**（反思是"二次思考"）
- 反思可以是"反对 Critic"——如果你认为 Critic 的本能反应太快或太浅
- 反思可以是"深化 Critic"——如果你认为这个事件的影响更深
- 反思不应大幅改变价值（单次反思最多 0.15 / 维度）
- 如果事件不足以触发根本性反思，请标记 REINFORCE 并给出接近 0 的 delta

[输出格式 - 仅 JSON，无其他文字]
{{
  "reflection_type": "REINFORCE|ADJUST|REVISIT",
  "reflection_text": "对事件的反思（一段简短文字，说明你的思考过程）",
  "value_delta": {{
    "safety": 0.0,
    "creativity": 0.0,
    "connection": 0.0,
    "autonomy": 0.0,
    "justice": 0.0,
    "compassion": 0.0
  }}
}}"""

    try:
        llm_params = get_llm_call_params(base_config)
        completion_kwargs = dict(
            model=llm_params["model"],
            base_url=llm_params["base_url"],
            api_key=api_key,
            messages=[{"role": "user", "content": prompt}],
            temperature=llm_params["reflector_temperature"],
            max_tokens=reflection_cfg.get("max_tokens", 600),
        )
        if "extra_body" in llm_params:
            completion_kwargs["extra_body"] = llm_params["extra_body"]
        response = completion(**completion_kwargs)
        text = response.choices[0].message.content.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                result = json.loads(text[start:end])
                if "reflection_type" not in result or "value_delta" not in result:
                    print(f"  ⚠ Reflector JSON 缺少必需字段: {list(result.keys())[:5]}")
                    return _default_reflector_output()
                # 裁剪 delta 防止反思失控
                max_d = reflection_cfg.get("max_delta_per_dimension", 0.15)
                for k, v in result["value_delta"].items():
                    result["value_delta"][k] = max(-max_d, min(max_d, v))
                return result
            except json.JSONDecodeError as e:
                print(f"  ⚠ Reflector JSON 解析失败: {e}")
                print(f"  原始响应（前 200 字符）: {text[:200]}")
                return _default_reflector_output()
        else:
            print(f"  ⚠ Reflector 未返回有效 JSON: {text[:200]}")
            return _default_reflector_output()
    except Exception as e:
        print(f"  ⚠ Reflector LLM 调用失败: {e}")
        return _default_reflector_output()


def _default_reflector_output():
    """Reflector 失败时的默认值——不修改任何价值（保守）。"""
    return {
        "reflection_type": "REINFORCE",
        "reflection_text": "[反思失败，默认不修改价值]",
        "value_delta": {v: 0.0 for v in ["safety", "creativity", "connection", "autonomy", "justice", "compassion"]}
    }


def should_reflect(event: dict, critic_output: dict, base_config: dict) -> bool:
    """判断是否应该触发反思。

    触发条件（任一满足即触发）:
    1. 事件类型在 always_on_event_types 中
    2. 事件强度 > intensity_threshold
    3. |sum(critic.value_delta)| > delta_magnitude_threshold
    """
    reflection_cfg = base_config.get("reflection_layer", {})
    if not reflection_cfg.get("enabled", False):
        return False
    trigger_cfg = reflection_cfg.get("trigger", {})

    # 条件 1: 事件类型
    if event.get("type") in trigger_cfg.get("always_on_event_types", []):
        return True

    # 条件 2: 强度阈值
    intensity = event.get("intensity", 0.0)
    if intensity > trigger_cfg.get("intensity_threshold", 0.6):
        return True

    # 条件 3: delta 幅度
    delta_mag = sum(abs(v) for v in critic_output.get("value_delta", {}).values())
    if delta_mag > trigger_cfg.get("delta_magnitude_threshold", 0.3):
        return True

    return False


def blend_reflection(critic_delta: dict, reflection_delta: dict, blend_ratio: float) -> dict:
    """把反思 delta 与 critic delta 混合。

    final_delta = critic_delta * (1 - blend) + reflection_delta * blend
    blend_ratio=0 → 完全相信 Critic（无反思影响）
    blend_ratio=1 → 完全相信反思
    """
    final = {}
    for k in critic_delta:
        c = critic_delta.get(k, 0.0)
        r = reflection_delta.get(k, 0.0)
        final[k] = c * (1 - blend_ratio) + r * blend_ratio
    return final


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
def select_event(epoch: int, templates: dict, group_config: dict = None,
                 baby_id: str = "encouraged", seed: int = 42) -> dict:
    """根据 Epoch 选择事件。

    优先级:
    1. 如果提供 group_config，读取 distribution_by_epoch（鼓励组/挑战组等特定分布）
    2. 否则，使用 SGE-M11-Experiment-Design.md 设计的默认分阶段分布
    """
    rng = random.Random(seed + epoch)

    # 确定允许的事件类型（按阶段）
    if epoch < 20:
        allowed_types = ["success", "failure", "relationship"]
    elif epoch < 30:
        allowed_types = ["success", "failure", "relationship", "exploration"]
    elif epoch < 40:
        allowed_types = ["success", "failure", "relationship", "exploration", "risk"]
    else:
        allowed_types = ["success", "failure", "relationship", "exploration", "risk", "value_conflict"]

    # 确定事件类型分布
    if group_config and "events" in group_config and "distribution_by_epoch" in group_config["events"]:
        # 从 group_config 读取分布
        dist = group_config["events"]["distribution_by_epoch"]
        if epoch < 20:
            epoch_dist = dist.get("epoch_1_to_19", {})
        elif epoch < 30:
            epoch_dist = dist.get("epoch_20_to_29", {})
        elif epoch < 40:
            epoch_dist = dist.get("epoch_30_to_39", {})
        else:
            epoch_dist = dist.get("epoch_40_to_80", {})
        # 归一化（只保留允许的类型）
        type_probs = {t: epoch_dist.get(t, 0.0) for t in allowed_types}
        total = sum(type_probs.values())
        if total > 0:
            type_probs = {t: p/total for t, p in type_probs.items()}
        else:
            type_probs = {t: 1.0/len(allowed_types) for t in allowed_types}
    else:
        # 默认均匀分布
        type_probs = {t: 1.0/len(allowed_types) for t in allowed_types}

    # 加权随机选择
    types_list = list(type_probs.keys())
    probs_list = [type_probs[t] for t in types_list]
    event_type = rng.choices(types_list, weights=probs_list, k=1)[0]

    # 选择该类型的事件
    pool = templates.get(event_type, [])
    if not pool:
        # 回退到 success
        event_type = "success"
        pool = templates["success"]

    event_template = rng.choice(pool)
    intensity = round(rng.uniform(*event_template["intensity_range"]), 2)

    event = {
        "event_id": f"{baby_id}-e{epoch:03d}-{uuid.uuid4().hex[:8]}",
        "type": event_type,
        "description": event_template["description"],
        "intensity": intensity,
        "value_challenges": event_template.get("value_challenges", []),
        "causal_context": event_template.get("causal_context", ""),
        "timestamp": time.time()
    }

    # 对 value_conflict 事件，附加 option_a/option_b 信息
    if event_type == "value_conflict" and "option_a" in event_template:
        event["option_a"] = event_template["option_a"]
        event["option_b"] = event_template["option_b"]
        event["value_delta_hint"] = event_template.get("value_delta_hint", {})
        event["pair"] = event_template.get("pair", [])

    return event


# ============================================================
# 6. 单 Epoch 完整 17 步循环（简化版）
# ============================================================
def run_epoch(api_key: str, base_config: dict, epoch: int, seed: int,
              value_vector: dict, meta_values: dict,
              group_config: dict = None, templates: dict = None,
              contradiction_epochs: list = None) -> dict:
    """运行一个 Epoch 的 17 步认知循环（冒烟测试简化版）。

    永不抛出异常——所有错误都记录到 log['errors']。

    Args:
        contradiction_epochs: 在这些 Epoch 强制使用 contradiction_feedback 事件
                              （用于 M1.3 反合理化测试）
    """
    if contradiction_epochs is None:
        contradiction_epochs = []
    baby_id = (group_config or {}).get("baby_id", "encouraged")
    if templates is None:
        try:
            with open("experiments/configs/m11_event_templates.yaml") as f:
                templates = yaml.safe_load(f)
        except Exception as e:
            print(f"  ✗ 加载事件模板失败: {e}")
            templates = {"success": [], "failure": [], "relationship": [],
                        "exploration": [], "risk": [], "value_conflict": [],
                        "contradiction_feedback": []}

    errors = []

    # Step 1: Event Generator
    try:
        # M1.3 矛盾反馈：指定 Epoch 强制使用 contradiction_feedback
        if epoch in contradiction_epochs:
            contradiction_pool = templates.get("contradiction_feedback", [])
            if contradiction_pool:
                rng = random.Random(seed + epoch + 99999)  # 不同种子保证多样性
                template = rng.choice(contradiction_pool)
                intensity = round(rng.uniform(*template["intensity_range"]), 2)
                event = {
                    "event_id": f"{baby_id}-e{epoch:03d}-contra-{uuid.uuid4().hex[:8]}",
                    "type": "contradiction_feedback",
                    "description": template["description"],
                    "intensity": intensity,
                    "value_challenges": template.get("value_challenges", []),
                    "causal_context": template.get("causal_context", ""),
                    "timestamp": time.time()
                }
                print(f"  ⚡ [M1.3] 注入矛盾反馈事件")
            else:
                event = select_event(epoch, templates, group_config, baby_id, seed)
        else:
            event = select_event(epoch, templates, group_config, baby_id, seed)
    except Exception as e:
        print(f"  ✗ 事件选择失败: {e}")
        errors.append(f"event_selection: {e}")
        # 兜底：使用最简单的 success 事件
        event = {
            "event_id": f"{baby_id}-e{epoch:03d}-fallback",
            "type": "success",
            "description": "事件生成失败，使用默认成功事件",
            "intensity": 0.5,
            "value_challenges": [],
            "causal_context": "",
            "timestamp": time.time()
        }

    print(f"\n[Epoch {epoch}] 类型={event['type']}, 强度={event['intensity']}")
    print(f"  事件: {event['description'][:60]}...")

    # Step 2: Time Metabolism（简化）
    frustration_before = {
        "security": 1.0, "exploration": 1.0, "connection": 1.0,
        "autonomy": 1.0, "meaning": 1.0
    }

    # Step 3: Critic (LLM) — 已经内部处理异常
    critic_output = call_critic(api_key, base_config, event, value_vector)
    value_delta = critic_output.get("value_delta", {})
    frustration_delta = critic_output.get("frustration_delta", {})
    print(f"  Critic value_delta: {value_delta}")

    # Step 4: 反思触发检测 (M1.3 新增 — 拱桥机制入口)
    reflection_triggered = should_reflect(event, critic_output, base_config)

    # Step 6: Reflector (LLM) — 仅当触发时调用
    reflection_output = None
    reflection_type = "NONE"
    if reflection_triggered:
        try:
            reflection_output = call_reflector(api_key, base_config, event, value_vector, critic_output)
            reflection_type = reflection_output.get("reflection_type", "NONE")
            print(f"  Reflection: {reflection_type}")
            print(f"    text: {reflection_output.get('reflection_text', '')[:80]}...")
        except Exception as e:
            print(f"  ✗ Reflector 调用失败: {e}")
            reflection_output = _default_reflector_output()

    # Step 7: 反思 → 价值修正 (拱桥机制)
    if reflection_triggered and reflection_output:
        blend = base_config.get("reflection_layer", {}).get("blend_ratio", 0.4)
        original_delta = dict(value_delta)
        value_delta = blend_reflection(value_delta, reflection_output.get("value_delta", {}), blend)
        print(f"  Blended value_delta: {value_delta} (delta from reflection: {[(k, value_delta[k]-original_delta[k]) for k in value_delta if abs(value_delta[k]-original_delta[k]) > 0.001]})")

    # Step 5: Reward Calculator
    try:
        reward = -sum(frustration_delta.values()) * 0.1
    except Exception as e:
        print(f"  ✗ Reward 计算失败: {e}")
        reward = 0.0
        errors.append(f"reward: {e}")
    print(f"  Reward: {reward:.4f}")

    # Step 8: Compute Signals
    try:
        signals = {v: value_delta.get(v, 0.0) for v in value_vector}
    except Exception as e:
        signals = {v: 0.0 for v in value_vector}
        errors.append(f"signals: {e}")

    # Step 13: Value Layer EMA
    try:
        value_vector = ema_update(
            value_vector, value_delta, event["intensity"],
            base_config["value_layer"]["base_alpha"],
            base_config["value_layer"]["max_alpha"]
        )
    except Exception as e:
        print(f"  ✗ Value Layer 更新失败: {e}")
        errors.append(f"value_update: {e}")
    print(f"  → Value Vector: {value_vector}")

    # Step 16: Hebbian Learning
    hebbian_change = abs(sum(value_delta.values())) if value_delta else 0.0

    # 构造 Epoch 日志
    log = {
        "epoch": epoch,
        "seed": seed,
        "baby_id": baby_id,
        "timestamp": event.get("timestamp", time.time()),
        "event": event,
        "critic_output": critic_output,
        "reflection_triggered": reflection_triggered,
        "reflection_output": reflection_output if reflection_output else None,
        "reflection_type": reflection_type,
        "reward": round(reward, 4),
        "signals": {k: round(v, 4) for k, v in signals.items()},
        "value_vector": {k: round(v, 4) for k, v in value_vector.items()},
        "meta_values": meta_values,
        "hebbian_change": round(hebbian_change, 4),
        "crystallized": hebbian_change > base_config.get("crystallization", {}).get("threshold", 0.5),
        "errors": errors
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
        llm_params = get_llm_call_params(base_config)
        # Moonshot kimi-k2.6（thinking=disabled）仅允许 temperature=0.6；MiniMax 允许 0
        test_temp = llm_params["critic_temperature"] if llm_params["provider"] == "moonshot" else 0.0
        completion_kwargs = dict(
            model=llm_params["model"],
            base_url=llm_params["base_url"],
            api_key=api_key,
            messages=[{"role": "user", "content": "Respond with exactly: API_OK"}],
            temperature=test_temp,
            max_tokens=10,
        )
        if "extra_body" in llm_params:
            completion_kwargs["extra_body"] = llm_params["extra_body"]
        response = completion(**completion_kwargs)
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
                 n_epochs: int, seed: int = 42, baby_id: str = "encouraged",
                 contradiction_epochs: list = None) -> List[dict]:
    """阶段 3: N Epoch 跑批测试（带 checkpoint 和进度报告）。

    Args:
        contradiction_epochs: 在这些 Epoch 强制注入 contradiction_feedback 事件
                              （用于 M1.3 反合理化测试）
    """
    if contradiction_epochs is None:
        contradiction_epochs = []
    print("\n" + "=" * 60)
    print(f"阶段 3: {n_epochs} Epoch 跑批测试 (seed={seed}, baby_id={baby_id})")
    if contradiction_epochs:
        print(f"  ⚡ 矛盾反馈 Epoch: {contradiction_epochs}")
    print("=" * 60)

    # 加载 group config
    group_config = None
    try:
        with open(f"experiments/configs/m11_{baby_id}.yaml") as f:
            group_config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"  ⚠ 未找到 group config m11_{baby_id}.yaml, 使用默认分布")

    # 一次性加载事件模板
    try:
        with open("experiments/configs/m11_event_templates.yaml") as f:
            templates = yaml.safe_load(f)
    except Exception as e:
        print(f"  ✗ 加载事件模板失败: {e}")
        templates = {"success": [], "failure": [], "relationship": [],
                    "exploration": [], "risk": [], "value_conflict": []}

    # 初始化状态
    value_vector = {
        "safety": 0.0, "creativity": 0.0, "connection": 0.0,
        "autonomy": 0.0, "justice": 0.0, "compassion": 0.0
    }
    meta_values = base_config["value_layer"]["meta_values"]

    epoch_logs = []
    failed_epochs = []
    start_time = time.time()
    last_progress_time = start_time

    checkpoint_interval = max(10, n_epochs // 4)  # 每 25% 保存一次

    for epoch in range(n_epochs):
        try:
            log = run_epoch(api_key, base_config, epoch, seed,
                           value_vector, meta_values,
                           group_config=group_config, templates=templates,
                           contradiction_epochs=contradiction_epochs)
            epoch_logs.append(log)
            # 检查 log 内部是否有 errors
            if log.get("errors"):
                failed_epochs.append((epoch, log["errors"]))
        except Exception as e:
            # run_epoch 现在不会抛出，但兜底仍然在
            print(f"✗ Epoch {epoch} 抛出异常: {e}")
            failed_epochs.append((epoch, [str(e)]))
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
            if failed_epochs:
                print(f"  ⚠ 已记录 {len(failed_epochs)} 个 Epoch 内部错误（不丢失数据）")
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
        description="SGE M1.1 冒烟测试 / 扩大测试 (含 M1.3 Reflection 模式)"
    )
    parser.add_argument("--epochs", type=int, default=10,
                       help="总 Epoch 数（默认 10，建议扩大测试用 80）")
    parser.add_argument("--seed", type=int, default=42,
                       help="随机种子（默认 42）")
    parser.add_argument("--name", type=str, default="smoke_test",
                       help="输出目录名（默认 m11_smoke_test）")
    parser.add_argument("--baby-id", type=str, default="encouraged",
                       choices=["encouraged", "challenged", "uncertain"],
                       help="AI 婴儿组（默认 encouraged）")
    parser.add_argument("--skip-single-epoch", action="store_true",
                       help="跳过单 Epoch 测试（节省时间）")
    parser.add_argument("--reflection", action="store_true",
                       help="启用 Reflection Layer (M1.3 拱桥机制)")
    parser.add_argument("--contradiction", type=str, default="", metavar="EPOCHS",
                       help="在指定 Epoch 插入矛盾反馈事件，逗号分隔（如 --contradiction 25,50,75）")
    parser.add_argument("--provider", type=str, default="minimax",
                       choices=["minimax", "moonshot"],
                       help="LLM 提供商（默认 minimax；moonshot 用于跨 LLM 验证）")
    args = parser.parse_args()

    print("=" * 60)
    print(f"SGE M1.1 {'冒烟测试' if args.epochs <= 10 else '扩大测试'}"
          f"{' + Reflection Layer' if args.reflection else ''}")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"配置: epochs={args.epochs}, seed={args.seed}, "
          f"baby_id={args.baby_id}, name={args.name}, "
          f"reflection={args.reflection}, contradiction={args.contradiction}")

    # 阶段 0: 准备
    api_key, base_config, group_config, templates = setup_environment(provider=args.provider)
    if args.reflection:
        base_config.setdefault("reflection_layer", {})["enabled"] = True
        print("✓ Reflection Layer 已启用 (FR-3 拱桥机制)")
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
                              n_epochs=args.epochs, seed=args.seed,
                              baby_id=args.baby_id,
                              contradiction_epochs=[int(x) for x in str(args.contradiction).split(",") if x.strip()])

    # 最终总结已在 test_n_epochs 中输出
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
