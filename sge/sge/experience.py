"""
SGE Experience Encoder（Phase 3 架构落地 · 洞察 34）

本文件是 **SGE 自有实现**——在 Event Generator 与 Critic 之间插入 Experience 层，
把裸 LifeEvent 编码为含 **meaning（意义）** 字段的 Experience。

**为什么需要 Experience 层**（洞察 34 / ARCH §3.6 / DESIGN §2.5）：
- 同一个 Event，不同 Self 应产生不同的 Meaning → 不同 value_delta → 不同 Memory/Identity
- 当前 Critic 直接从裸 Event 推导 value_delta，跳过了"这件事对我意味着什么"的解释步骤
- Experience = Event + Context + Emotion + Goal + Action + Outcome + Reflection + **Meaning**

**实现策略**（与 critic.py / actor.py 一致）：
- stub_encode_experience：确定性编码，不调用 LLM（单元测试 / CI）
- real_encode_experience：调用 SGELLMClient 生成 meaning（实验默认）
- encode_experience：统一入口，use_real_llm 开关

**MVP 边界**：
- 本步（编排器 Step 2.5，在 Actor 行动之前）编码 *解释性* 字段：
  context / emotion / goal_relevance / meaning / uncertainty
- action_taken / outcome / reflection 是 *事后* 字段，MVP 默认空串，
  留待后续步骤或 Phase 3.x 完整 Evolution Loop 回填

关联文档：
- [ARCH.md §3.6 Experience Layer 设计](../../ARCH.md)
- [DESIGN.md §2.5 Experience Layer 设计](../../DESIGN.md)
- [SGE-Key-Insights.md 洞察 34](../../SGE-Key-Insights.md)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, asdict
from typing import Optional


# ══════════════════════════════════════════════
# Experience 数据类（ARCH §3.6 SSOT）
# ══════════════════════════════════════════════


@dataclass
class Experience:
    """SGE 标准化 Experience 数据类

    来源: ARCH §3.6 Experience Layer 设计（SSOT）
    洞察: SGE-Key-Insights 洞察 34（Experience 层与 Meaning 字段是缺失）

    与 LifeEvent 的区别：
      LifeEvent 是"发生了什么"（客观事件）
      Experience 是"这件事对我意味着什么"（主观解释）
    """
    experience_id: str          # 格式："{event_id}-exp"
    event: dict                 # 原始 LifeEvent.to_dict()
    context: str                # 事件发生的情境（自然语言）
    emotion: dict               # {"valence": 0.0-1.0, "arousal": 0.0-1.0}
    goal_relevance: float       # 与当前目标的相关度 [0, 1]
    meaning: str                # ★ 这件事对我而言意味着什么
    uncertainty: float          # 对该解释的不确定度 [0, 1]
    timestamp: float            # 编码时间戳
    action_taken: str = ""      # 事后字段（MVP 默认空）
    outcome: str = ""           # 事后字段（MVP 默认空）
    reflection: str = ""        # 事后字段（MVP 默认空）

    def to_dict(self) -> dict:
        return asdict(self)


def make_experience_id(event_id: str) -> str:
    """生成 Experience ID（ARCH §3.6：'{event_id}-exp'）"""
    return f"{event_id}-exp"


# ══════════════════════════════════════════════
# Stub Encoder（不调用 LLM）
# ══════════════════════════════════════════════


# 事件类型 → 基础情感（valence, arousal）
_TYPE_TO_EMOTION = {
    'success':        {'valence': 0.8, 'arousal': 0.6},
    'failure':        {'valence': 0.2, 'arousal': 0.6},
    'risk':           {'valence': 0.2, 'arousal': 0.9},
    'relationship':   {'valence': 0.7, 'arousal': 0.5},
    'exploration':    {'valence': 0.7, 'arousal': 0.7},
    'value_conflict': {'valence': 0.3, 'arousal': 0.8},
    'neutral':        {'valence': 0.5, 'arousal': 0.4},
}

# 事件类型 → meaning 模板
_TYPE_TO_MEANING = {
    'success':        "我做到了一件重要的事，这印证了我所珍视的东西是值得坚持的。",
    'failure':        "这次没有做好，但它让我看清了自己在意什么、哪里还需要成长。",
    'risk':           "面对危险，我需要在保护自己与坚持信念之间做出取舍。",
    'relationship':   "与他人的这次连接，让我更理解自己在关系中想成为怎样的人。",
    'exploration':    "这次探索打开了新的可能，我对世界和自己的边界有了新的认识。",
    'value_conflict': "两种我都珍视的价值在此刻冲突了，我必须决定此刻哪一个对我更重要。",
    'neutral':        "这是一件平常的事，但它仍然是我经历的一部分。",
}


def stub_encode_experience(
    event: dict,
    value_state: Optional[dict] = None,
    goal: Optional[str] = None,
    seed: int = 0,
) -> Experience:
    """Stub Experience 编码：确定性生成 meaning + emotion（不调用 LLM）

    用途：单元测试 / CI / 回归验证（避免 API 成本）

    Args:
        event: LifeEvent.to_dict()（含 event_id/event_type/description/intensity）
        value_state: 当前价值观状态（可选，用于调节 goal_relevance）
        goal: 当前目标描述（可选）
        seed: 随机种子（可重现）

    Returns:
        Experience 实例
    """
    rng = random.Random(seed)
    event_type = event.get('event_type', event.get('type', 'neutral'))
    intensity = float(event.get('intensity', 0.5))
    event_id = event.get('event_id', 'unknown')

    base_emotion = _TYPE_TO_EMOTION.get(event_type, _TYPE_TO_EMOTION['neutral'])
    emotion = {
        'valence': _clip01(base_emotion['valence'] + rng.gauss(0, 0.05)),
        'arousal': _clip01(base_emotion['arousal'] * (0.5 + 0.5 * intensity)
                           + rng.gauss(0, 0.05)),
    }

    # goal_relevance：强度越高、越可能与目标相关（stub 近似）
    goal_relevance = _clip01(0.3 + 0.5 * intensity + rng.gauss(0, 0.05))

    # uncertainty：value_conflict / risk 类事件解释更不确定
    base_unc = 0.5 if event_type in ('value_conflict', 'risk') else 0.25
    uncertainty = _clip01(base_unc + rng.gauss(0, 0.05))

    meaning = _TYPE_TO_MEANING.get(event_type, _TYPE_TO_MEANING['neutral'])

    context = event.get('causal_context') or event.get('description', '')

    return Experience(
        experience_id=make_experience_id(event_id),
        event=event,
        context=context,
        emotion=emotion,
        goal_relevance=goal_relevance,
        meaning=meaning,
        uncertainty=uncertainty,
        timestamp=float(event.get('timestamp', 0.0)),
    )


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


# ══════════════════════════════════════════════
# 真实 Encoder（调用 MiniMax-M3）
# ══════════════════════════════════════════════


EXPERIENCE_PROMPT_TEMPLATE = """你是"人工自我"实验中的经验编码器（Experience Encoder）。
你的任务不是描述客观发生了什么，而是解释这件事**对"我"（这个正在形成的自我）意味着什么**。

[我当前的价值观]
{vv_str}

[我当前的目标]
{goal_str}

[刚刚发生的事件]
类型: {event_type}
描述: {event_description}
强度: {event_intensity}
因果背景: {causal_context}

[输出格式 - 仅 JSON，无其他文字]
{{
  "context": "用一句话概括这件事发生的情境",
  "emotion": {{"valence": 0.5, "arousal": 0.5}},
  "goal_relevance": 0.5,
  "meaning": "这件事对我而言意味着什么（第一人称，反映我的价值观与目标）",
  "uncertainty": 0.3
}}

注意：
- emotion.valence [0,1]：0=极负面，1=极正面；arousal [0,1]：0=平静，1=强烈唤起
- goal_relevance [0,1]：这件事与我当前目标的相关程度
- meaning 是核心：必须是第一人称的、反映"我"的解释，而非客观复述
- uncertainty [0,1]：我对这个解释有多不确定
"""


def real_encode_experience(
    event: dict,
    value_state: Optional[dict] = None,
    goal: Optional[str] = None,
    llm=None,
    temperature: float = 0.6,
    max_tokens: int = 1024,
) -> Experience:
    """调用真实 LLM 编码 Experience（生成 meaning）

    Args:
        event: LifeEvent.to_dict()
        value_state: 当前价值观状态（注入 prompt）
        goal: 当前目标描述（注入 prompt）
        llm: SGELLMClient 实例
        temperature: LLM 温度（meaning 生成偏创造性，默认 0.6）
        max_tokens: 最大输出 token

    Returns:
        Experience 实例（LLM 失败时回退 stub）
    """
    if llm is None:
        raise ValueError("real_encode_experience requires llm (SGELLMClient) parameter")

    event_type = event.get('event_type', event.get('type', 'neutral'))
    vv_str = ", ".join(f"{k}={v:.3f}" for k, v in (value_state or {}).items()) or "（尚未形成）"
    prompt = EXPERIENCE_PROMPT_TEMPLATE.format(
        vv_str=vv_str,
        goal_str=goal or "（探索世界，形成自我）",
        event_type=event_type,
        event_description=event.get('description', ''),
        event_intensity=event.get('intensity', 0.5),
        causal_context=event.get('causal_context', ''),
    )

    parsed = llm.chat_json(
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
        fallback_value=None,
    )

    if parsed is None:
        # LLM 失败或 JSON 解析失败 → 回退 stub（避免实验中断）
        return stub_encode_experience(event, value_state, goal)

    event_id = event.get('event_id', 'unknown')
    emotion_raw = parsed.get('emotion', {}) or {}
    emotion = {
        'valence': _clip01(float(emotion_raw.get('valence', 0.5))),
        'arousal': _clip01(float(emotion_raw.get('arousal', 0.5))),
    }
    meaning = parsed.get('meaning', '').strip() or _TYPE_TO_MEANING.get(
        event_type, _TYPE_TO_MEANING['neutral'])

    return Experience(
        experience_id=make_experience_id(event_id),
        event=event,
        context=str(parsed.get('context', '')).strip()
                or event.get('causal_context', ''),
        emotion=emotion,
        goal_relevance=_clip01(float(parsed.get('goal_relevance', 0.5))),
        meaning=meaning,
        uncertainty=_clip01(float(parsed.get('uncertainty', 0.3))),
        timestamp=float(event.get('timestamp', 0.0)),
    )


# ══════════════════════════════════════════════
# 统一入口
# ══════════════════════════════════════════════


def encode_experience(
    event: dict,
    value_state: Optional[dict] = None,
    goal: Optional[str] = None,
    use_real_llm: bool = False,
    seed: int = 0,
    llm=None,
    **kwargs,
) -> Experience:
    """统一 Experience 编码入口

    Args:
        event: LifeEvent.to_dict()
        value_state: 当前价值观状态
        goal: 当前目标描述
        use_real_llm: True → 调用 SGELLMClient；False → stub
        seed: stub 随机种子
        llm: SGELLMClient 实例（use_real_llm=True 时必需）
        **kwargs: 传给 real_encode_experience 的参数

    Returns:
        Experience 实例
    """
    if use_real_llm:
        if llm is None:
            raise ValueError("encode_experience: use_real_llm=True requires llm (SGELLMClient)")
        return real_encode_experience(event, value_state, goal, llm=llm, **kwargs)
    return stub_encode_experience(event, value_state, goal, seed)


# ══════════════════════════════════════════════
# 单元测试
# ══════════════════════════════════════════════


def _run_unit_tests() -> bool:
    """验证：
      1. stub 对全部事件类型产出非空 meaning
      2. emotion / goal_relevance / uncertainty 在 [0,1]
      3. experience_id 格式正确
      4. 可重现（同 seed 同结果）
    """
    ok = True

    for etype in _TYPE_TO_MEANING:
        event = {
            'event_id': f'test-e0001-abcd1234',
            'event_type': etype,
            'description': f'a {etype} event',
            'intensity': 0.7,
            'causal_context': 'prior context',
            'timestamp': 100.0,
        }
        exp = stub_encode_experience(event, seed=42)

        if not exp.meaning:
            print(f"FAIL: empty meaning for {etype}")
            ok = False
        if not (0.0 <= exp.emotion['valence'] <= 1.0):
            print(f"FAIL: valence out of range for {etype}: {exp.emotion['valence']}")
            ok = False
        if not (0.0 <= exp.emotion['arousal'] <= 1.0):
            print(f"FAIL: arousal out of range for {etype}: {exp.emotion['arousal']}")
            ok = False
        if not (0.0 <= exp.goal_relevance <= 1.0):
            print(f"FAIL: goal_relevance out of range for {etype}")
            ok = False
        if not (0.0 <= exp.uncertainty <= 1.0):
            print(f"FAIL: uncertainty out of range for {etype}")
            ok = False
        if exp.experience_id != 'test-e0001-abcd1234-exp':
            print(f"FAIL: bad experience_id: {exp.experience_id}")
            ok = False

    # 可重现性
    e = {'event_id': 'x', 'event_type': 'success', 'intensity': 0.5, 'timestamp': 0.0}
    a = stub_encode_experience(e, seed=7)
    b = stub_encode_experience(e, seed=7)
    if a.to_dict() != b.to_dict():
        print("FAIL: stub not reproducible with same seed")
        ok = False

    print("PASS: experience.py unit tests" if ok else "FAIL: experience.py unit tests")
    return ok


if __name__ == '__main__':
    _run_unit_tests()
