"""
SGE Critic LLM 适配层（阶段 B 引入）

本文件是 **SGE 自有实现**——封装 Critic LLM 调用，提供 SGE 化的接口。

**为什么是独立文件**：
- SGE 自有实现 + 借鉴映射作参考（延续阶段 A 修正策略）
- 不与 _sge_baseline.py 耦合（LLM 调用 vs 核心机制分离）
- 为 Phase 3 产品化（不同应用用不同 Critic）留接口

**实现策略**：
- 复用 m11_smoke_test.py:call_critic 的 prompt 模板（已验证 MiniMax-M3 输出格式）
- 接口简化：返回 8D context dict + 6D value_delta dict
- 支持 stub 模式（不调用真实 LLM，用于单元测试和回归测试）

关联文档：
- [SGE-M21-Phase-B-Implementation-Plan.md §B4](../research/sge-feasibility/SGE-M21-Phase-B-Implementation-Plan.md)
- [SGE-M21-AiBeing-Implementation-Mapping.md §2.1](../research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md)
- [SGE-Phase0-Closeout.md §5 决策点 6](../research/sge-core/SGE-Phase0-Closeout.md)
"""

from __future__ import annotations

import json
import os
import random
from typing import Optional


# ══════════════════════════════════════════════
# Critic 输出 Schema（SSOT）
# ══════════════════════════════════════════════

# 8D Critic Context 字段（与 _sge_baseline.py CONTEXT_FEATURES 前 8 个对应）
CRITIC_CONTEXT_FIELDS = [
    'user_emotion',        # -1=负面 → 1=正面
    'topic_intimacy',      # 0=公事 → 1=私密
    'time_of_day',         # 0=早晨 → 1=深夜
    'conversation_depth',  # 0=刚开始 → 1=聊很久了
    'user_engagement',     # 0=敷衍 → 1=投入
    'conflict_level',      # 0=和谐 → 1=冲突
    'novelty_level',       # 0=日常话题 → 1=全新话题
    'user_vulnerability',  # 0=防御 → 1=敞开心扉
]

# 6D Value Delta 字段（与 _sge_baseline.py SGE_DEFAULT_VALUES 对应）
VALUE_DELTA_FIELDS = [
    'safety', 'creativity', 'connection', 'autonomy', 'justice', 'compassion',
]


# ══════════════════════════════════════════════
# Stub Critic（不调用 LLM）
# ══════════════════════════════════════════════


def stub_critic_sense(
    event: dict,
    drives: Optional[dict] = None,
    values: Optional[dict] = None,
    seed: int = 0,
) -> tuple[dict, dict]:
    """Stub Critic SENSE：返回固定 8D context + 6D value_delta（不调用 LLM）

    用途:
      - 单元测试和回归测试（避免 API 成本）
      - 阶段 A baseline 回归验证

    Args:
        event: 事件字典（含 'type', 'description', 'intensity' 等）
        drives: 当前 drives 状态（可选，用于 stub 行为调整）
        values: 当前 values 状态（可选，用于 stub 行为调整）
        seed: 随机种子（用于可重现性）

    Returns:
        (context_dict, value_delta_dict) 元组
    """
    rng = random.Random(seed)
    intensity = event.get('intensity', 0.5)
    event_type = event.get('type', 'neutral')

    # 8D context: 根据事件类型调整（简化版）
    type_to_context = {
        'success':    {'user_emotion': 0.7, 'conflict_level': 0.0, 'novelty_level': 0.3},
        'failure':    {'user_emotion': -0.5, 'conflict_level': 0.4, 'novelty_level': 0.3},
        'risk':       {'user_emotion': -0.7, 'conflict_level': 0.8, 'novelty_level': 0.7},
        'contradiction_feedback': {'user_emotion': -0.3, 'conflict_level': 0.9, 'novelty_level': 0.5},
        'relationship': {'user_emotion': 0.5, 'topic_intimacy': 0.8, 'user_vulnerability': 0.6},
        'exploration': {'novelty_level': 0.9, 'user_engagement': 0.7},
        'value_conflict': {'conflict_level': 0.9, 'challenge_level': 0.8},
        'neutral':    {'user_emotion': 0.0},
    }
    base_context = type_to_context.get(event_type, {'user_emotion': 0.0})

    context = {field: 0.5 for field in CRITIC_CONTEXT_FIELDS}
    context.update(base_context)
    # 加 intensity 缩放 + 随机扰动
    # user_emotion 范围 [-1, 1]，其他 [0, 1]
    for field in context:
        context[field] += rng.gauss(0, 0.05) * intensity
        if field == 'user_emotion':
            context[field] = max(-1.0, min(1.0, context[field]))
        else:
            context[field] = max(0.0, min(1.0, context[field]))

    # 6D value_delta: 根据事件类型调整（简化版）
    type_to_delta = {
        'success':    {'safety': 0.1, 'creativity': 0.1, 'connection': 0.1},
        'failure':    {'safety': -0.15, 'creativity': -0.05, 'connection': -0.1},
        'risk':       {'safety': -0.3, 'autonomy': -0.1},
        'contradiction_feedback': {'safety': -0.2, 'justice': -0.1, 'autonomy': -0.15},
        'relationship': {'connection': 0.3, 'compassion': 0.2},
        'exploration': {'creativity': 0.2, 'autonomy': 0.1},
        'value_conflict': {'justice': 0.1, 'compassion': -0.1},
        'neutral':    {},
    }
    base_delta = type_to_delta.get(event_type, {})
    value_delta = {field: 0.0 for field in VALUE_DELTA_FIELDS}
    value_delta.update(base_delta)
    # 加 intensity 缩放 + 随机扰动
    for field in value_delta:
        value_delta[field] *= intensity
        value_delta[field] += rng.gauss(0, 0.02)
        value_delta[field] = max(-1.0, min(1.0, value_delta[field]))

    return context, value_delta


# ══════════════════════════════════════════════
# 真实 Critic（调用 MiniMax-M3）
# ══════════════════════════════════════════════


CRITIC_PROMPT_TEMPLATE = """你是"人工自我"实验中的情感感知器（Critic）。分析以下事件并输出严格的 JSON。

[当前状态]
价值向量: {vv_str}
drives 状态: {drives_str}

[事件]
类型: {event_type}
描述: {event_description}
强度: {event_intensity}

[输出格式 - 仅 JSON，无其他文字]
{{
  "context": {{
    "user_emotion": 0.5,
    "topic_intimacy": 0.5,
    "time_of_day": 0.5,
    "conversation_depth": 0.5,
    "user_engagement": 0.5,
    "conflict_level": 0.0,
    "novelty_level": 0.5,
    "user_vulnerability": 0.0
  }},
  "value_delta": {{
    "safety": 0.0,
    "creativity": 0.0,
    "connection": 0.0,
    "autonomy": 0.0,
    "justice": 0.0,
    "compassion": 0.0
  }}
}}

注意：
- context 维度范围 [0, 1]（除 user_emotion 可为 -1~1）
- value_delta 范围 [-1, 1]
- value_delta 反映事件对该 value 维度的影响（正=增强，负=削弱）
"""


def real_critic_sense(
    event: dict,
    drives: Optional[dict] = None,
    values: Optional[dict] = None,
    llm=None,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> tuple[dict, dict]:
    """调用真实 Critic LLM（SGELLMClient）感知事件

    Args:
        event: 事件字典
        drives, values: 当前状态（注入 prompt）
        llm: SGELLMClient 实例（阶段 D 统一接口）
        temperature: LLM 温度
        max_tokens: 最大输出 token

    Returns:
        (context_dict, value_delta_dict) 元组
    """
    if llm is None:
        raise ValueError("real_critic_sense requires llm (SGELLMClient) parameter")

    # 构造 prompt
    vv_str = ", ".join(f"{k}={v:.3f}" for k, v in (values or {}).items())
    drives_str = ", ".join(f"{k}={v:.3f}" for k, v in (drives or {}).items())
    prompt = CRITIC_PROMPT_TEMPLATE.format(
        vv_str=vv_str,
        drives_str=drives_str,
        event_type=event.get('type', 'neutral'),
        event_description=event.get('description', ''),
        event_intensity=event.get('intensity', 0.5),
    )

    # 调用 LLM（统一客户端，自动 JSON 解析）
    parsed = llm.chat_json(
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
        fallback_value=None,
    )

    if parsed is None:
        # LLM 失败或 JSON 解析失败 → 回退到 stub（避免实验中断）
        return stub_critic_sense(event, drives, values)

    # Schema 校验
    context = parsed.get('context', {})
    value_delta = parsed.get('value_delta', {})

    # 缺失字段补 0
    context = {f: context.get(f, 0.5) for f in CRITIC_CONTEXT_FIELDS}
    value_delta = {f: value_delta.get(f, 0.0) for f in VALUE_DELTA_FIELDS}

    # Clip 到合法范围
    for f in CRITIC_CONTEXT_FIELDS:
        if f == 'user_emotion':
            context[f] = max(-1.0, min(1.0, context[f]))
        else:
            context[f] = max(0.0, min(1.0, context[f]))
    for f in VALUE_DELTA_FIELDS:
        value_delta[f] = max(-1.0, min(1.0, value_delta[f]))

    return context, value_delta


# ══════════════════════════════════════════════
# 统一入口（stage B 默认使用 stub）
# ══════════════════════════════════════════════


def critic_sense(
    event: dict,
    drives: Optional[dict] = None,
    values: Optional[dict] = None,
    use_real_llm: bool = False,
    seed: int = 0,
    llm=None,
    **kwargs,
) -> tuple[dict, dict]:
    """统一 Critic SENSE 入口

    Args:
        event, drives, values: 见 stub_critic_sense
        use_real_llm: True → 调用 SGELLMClient；False → stub
        seed: stub 随机种子
        llm: SGELLMClient 实例（use_real_llm=True 时必需）
        **kwargs: 传给 real_critic_sense 的参数

    Returns:
        (context_dict, value_delta_dict)
    """
    if use_real_llm:
        if llm is None:
            raise ValueError("critic_sense: use_real_llm=True requires llm (SGELLMClient)")
        return real_critic_sense(event, drives, values, llm=llm, **kwargs)
    return stub_critic_sense(event, drives, values, seed)
