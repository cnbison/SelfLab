"""
SGE Actor LLM 适配层（阶段 D 引入）

本文件是 **SGE 自有实现**——封装 Actor LLM 调用，提供 SGE 化的接口。

**为什么是独立文件**：
- 与 _sge_critic.py 镜像（感知 vs 表达分离）
- 独立文件便于 stub/real 切换（Phase 3 不同应用可用不同 Actor）
- 不与 _sge_baseline.py 耦合

**实现策略**：
- 复用 m11_smoke_test.py:call_actor 的 prompt 模板（已验证 MiniMax-M3 输出格式）
- 接口简化：返回 ActorOutput dataclass（inner_monologue + behavior_label + intention + confidence）
- 支持 stub 模式（不调用真实 LLM，基于 signals 阈值生成行为标签）

**与 Critic 的对比**：

| 维度 | Critic（感知）| Actor（表达）|
|------|------------|------------|
| 输入 | event + drives + values | signals + values + retrieved + narrative |
| 输出 | 8D context + 6D value_delta | inner_monologue + behavior_label + intention + confidence |
| 温度 | 0.2（稳定性）| 0.9（多样性）|
| 角色 | 评估事件 → 价值观冲击 | 选择行为 → 内心独白 + 行为标签 |
| 来源 | AiBeing critic.py | AiBeing actor_single prompt |

关联文档：
- [SGE-M21-Phase-D-Implementation-Plan.md §D2](../research/sge-feasibility/SGE-M21-Phase-D-Implementation-Plan.md)
- [SGE-M21-AiBeing-Implementation-Mapping.md §2.9](../research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md)
- [PRD.md §FR-10（双 LLM 架构）](../PRD.md)
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, asdict
from typing import Optional


# ══════════════════════════════════════════════
# Actor 输出 Schema（SSOT）
# ══════════════════════════════════════════════

# 行为标签集合（设计为有限集合 → 便于 Hebbian 学习接收）
BEHAVIOR_LABELS = [
    '主动引导',    # initiative 高
    '关怀回应',    # warmth 高
    '玩闹撒娇',    # playfulness 高
    '深度提问',    # depth + curiosity 高
    '沉默不语',    # 所有 signal 都低
    '反抗嘴硬',    # defiance 高
    '委婉暗示',    # directness 低
    '袒露脆弱',    # vulnerability 高
    '认真严肃',    # playfulness 低 + depth 高
    '敷衍回应',    # 全部中等偏低
]


@dataclass
class ActorOutput:
    """Actor LLM 输出（DESIGN §9.2 行为度量）

    来源: AiBeing actor_single prompt 输出格式
    字段:
      - inner_monologue: 内心独白（用于 Narrative Builder 输入）
      - behavior_label: 行为标签（Hebbian 学习接收）
      - intention: 意图（用于记忆筛选）
      - confidence: 置信度 [0, 1]
    """
    inner_monologue: str
    behavior_label: str
    intention: str
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


# ══════════════════════════════════════════════
# Stub Actor（不调用 LLM）
# ══════════════════════════════════════════════


def stub_actor_express(
    signals: dict,
    value_vector: Optional[dict] = None,
    retrieved_memories: Optional[list] = None,
    current_narrative: Optional[str] = None,
    seed: int = 0,
) -> ActorOutput:
    """Stub Actor — 基于 signals 阈值生成行为标签

    规则：
      - signals['initiative'] > 0.6 → '主动引导'
      - signals['warmth'] > 0.6 → '关怀回应'
      - signals['playfulness'] > 0.6 → '玩闹撒娇'
      - signals['curiosity'] > 0.6 AND signals['depth'] > 0.5 → '深度提问'
      - signals['defiance'] > 0.6 → '反抗嘴硬'
      - signals['vulnerability'] > 0.6 → '袒露脆弱'
      - signals['directness'] < 0.3 → '委婉暗示'
      - signals['playfulness'] < 0.3 AND signals['depth'] > 0.6 → '认真严肃'
      - 全部 < 0.4 → '沉默不语'
      - 其他 → '敷衍回应'

    Args:
        signals: 8D signals dict（来自 Agent.compute_signals）
        value_vector: 6D value_state dict（可选，用于内心独白）
        retrieved_memories: list（可选，KNN 检索结果）
        current_narrative: 当前叙事（可选）
        seed: 随机种子（用于内心独白的轻微随机性）

    Returns:
        ActorOutput
    """
    rng = random.Random(seed)

    # 默认值保护
    s = {
        'directness': signals.get('directness', 0.5),
        'vulnerability': signals.get('vulnerability', 0.5),
        'playfulness': signals.get('playfulness', 0.5),
        'initiative': signals.get('initiative', 0.5),
        'depth': signals.get('depth', 0.5),
        'warmth': signals.get('warmth', 0.5),
        'defiance': signals.get('defiance', 0.5),
        'curiosity': signals.get('curiosity', 0.5),
    }

    # 按规则判断行为标签（注意顺序：全部低判断优先于单项阈值规则）
    if all(v < 0.4 for v in s.values()):
        behavior = '沉默不语'
    elif s['initiative'] > 0.6:
        behavior = '主动引导'
    elif s['warmth'] > 0.6:
        behavior = '关怀回应'
    elif s['playfulness'] > 0.6:
        behavior = '玩闹撒娇'
    elif s['curiosity'] > 0.6 and s['depth'] > 0.5:
        behavior = '深度提问'
    elif s['defiance'] > 0.6:
        behavior = '反抗嘴硬'
    elif s['vulnerability'] > 0.6:
        behavior = '袒露脆弱'
    elif s['directness'] < 0.3:
        behavior = '委婉暗示'
    elif s['playfulness'] < 0.3 and s['depth'] > 0.6:
        behavior = '认真严肃'
    else:
        behavior = '敷衍回应'

    # 内心独白（stub: 基于 strongest signal + value_state）
    dominant_signal = max(s, key=s.get)
    dominant_value = None
    if value_vector:
        dominant_value = max(value_vector, key=value_vector.get)
        if value_vector[dominant_value] < 0.1:
            dominant_value = None

    monologue_parts = []
    if dominant_signal == 'initiative':
        monologue_parts.append('这次我想主动一点')
    elif dominant_signal == 'warmth':
        monologue_parts.append('我想表达关心')
    elif dominant_signal == 'playfulness':
        monologue_parts.append('想轻松地聊')
    elif dominant_signal == 'curiosity':
        monologue_parts.append('我想追问到底')
    elif dominant_signal == 'defiance':
        monologue_parts.append('我有不同看法')
    elif dominant_signal == 'vulnerability':
        monologue_parts.append('我想坦诚')
    elif dominant_signal == 'directness' and s['directness'] < 0.3:
        monologue_parts.append('我想委婉一点')
    elif dominant_signal == 'depth':
        monologue_parts.append('我想深入探讨')
    else:
        monologue_parts.append('我保持现状')

    if dominant_value:
        monologue_parts.append(f'，坚持 {dominant_value}')
    monologue = ''.join(monologue_parts) + '。'

    # 意图（stub: 基于 behavior 推导）
    intention_map = {
        '主动引导': '想引导话题方向',
        '关怀回应': '想让对方感到被关心',
        '玩闹撒娇': '想活跃气氛',
        '深度提问': '想理解对方更深层想法',
        '沉默不语': '想保持安静',
        '反抗嘴硬': '想表达不同意见',
        '委婉暗示': '想间接表达',
        '袒露脆弱': '想建立信任',
        '认真严肃': '想就事论事',
        '敷衍回应': '想简短回应',
    }
    intention = intention_map.get(behavior, '想观察局势')

    # 置信度（stub: 基于 dominant signal 强度）
    dominant_value_strength = s[dominant_signal]
    confidence = round(0.5 + 0.5 * (dominant_value_strength - 0.5), 3)
    confidence = max(0.1, min(1.0, confidence))

    return ActorOutput(
        inner_monologue=monologue,
        behavior_label=behavior,
        intention=intention,
        confidence=confidence,
    )


# ══════════════════════════════════════════════
# Real Actor（调用 MiniMax-M3）
# ══════════════════════════════════════════════


def real_actor_express(
    signals: dict,
    value_vector: Optional[dict] = None,
    retrieved_memories: Optional[list] = None,
    current_narrative: Optional[str] = None,
    llm=None,
    seed: int = 0,
) -> ActorOutput:
    """真实 LLM Actor — 用 MiniMax-M3 生成

    prompt 模板（基于 m11_smoke_test.py:actor_single）:
      基于当前 signals + values + retrieved memories + narrative
      输出 4 字段 JSON：inner_monologue + behavior_label + intention + confidence

    Args:
        signals, value_vector, retrieved_memories, current_narrative: 同 stub
        llm: LLM 客户端（如 anthropic.Anthropic()）
        seed: 随机种子

    Returns:
        ActorOutput
    """
    if llm is None:
        raise ValueError("real_actor_express requires llm parameter")

    # 构造 prompt
    sig_str = ', '.join(f'{k}={v:.2f}' for k, v in signals.items())
    val_str = ', '.join(f'{k}={v:+.2f}' for k, v in (value_vector or {}).items())
    nar_str = current_narrative or '（暂无叙事）'
    mem_str = '\n'.join(
        f'- {m.get("content", m)}' for m in (retrieved_memories or [])[:5]
    ) or '（暂无记忆）'

    prompt = f"""你是一个 AI 的"表达"模块（Actor）。基于当前状态生成内心独白 + 行为选择。

当前行为信号（signals）：
{sig_str}

当前价值观（values）：
{val_str}

当前叙事：
{nar_str}

近期记忆（Hawking 检索，按权重排序）：
{mem_str}

要求：
1. inner_monologue: 内心独白（≤50 字，第一人称）
2. behavior_label: 从以下行为标签中选一个：
   {', '.join(BEHAVIOR_LABELS)}
3. intention: 意图描述（≤30 字）
4. confidence: 置信度 [0.0, 1.0]

输出 JSON 格式：
{{"inner_monologue": "...", "behavior_label": "...", "intention": "...", "confidence": 0.X}}"""

    # 调用 LLM
    try:
        response = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,  # 高温度 → 多样性表达
            max_tokens=300,
        )
        # 解析 JSON（兼容多种格式）
        content = response.content if hasattr(response, 'content') else str(response)
        # 提取 JSON 块
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]
        parsed = json.loads(content.strip())

        # 字段保护
        behavior = parsed.get('behavior_label', '敷衍回应')
        if behavior not in BEHAVIOR_LABELS:
            behavior = '敷衍回应'
        confidence = float(parsed.get('confidence', 0.5))
        confidence = max(0.0, min(1.0, confidence))

        return ActorOutput(
            inner_monologue=str(parsed.get('inner_monologue', '')),
            behavior_label=behavior,
            intention=str(parsed.get('intention', '')),
            confidence=confidence,
        )
    except Exception as e:
        # LLM 失败 → 回退到 stub
        print(f"[WARN] real_actor_express failed: {e}, fallback to stub")
        return stub_actor_express(
            signals=signals,
            value_vector=value_vector,
            retrieved_memories=retrieved_memories,
            current_narrative=current_narrative,
            seed=seed,
        )


# ══════════════════════════════════════════════
# 统一入口（阶段 D 默认使用 stub）
# ══════════════════════════════════════════════


def actor_express(
    signals: dict,
    value_vector: Optional[dict] = None,
    retrieved_memories: Optional[list] = None,
    current_narrative: Optional[str] = None,
    use_real_llm: bool = False,
    llm=None,
    seed: int = 0,
) -> ActorOutput:
    """统一 Actor EXPRESS 入口

    Args:
        signals: 8D signals dict（来自 Agent.compute_signals）
        value_vector: 6D value_state dict
        retrieved_memories: KNN 检索结果（Hawking.retrieve）
        current_narrative: 当前叙事（IdentityLayer + NarrativeBuilder）
        use_real_llm: True → 调用 MiniMax-M3；False → stub
        llm: LLM 客户端（use_real_llm=True 时必需）
        seed: 随机种子

    Returns:
        ActorOutput
    """
    if use_real_llm:
        return real_actor_express(
            signals=signals,
            value_vector=value_vector,
            retrieved_memories=retrieved_memories,
            current_narrative=current_narrative,
            llm=llm,
            seed=seed,
        )
    return stub_actor_express(
        signals=signals,
        value_vector=value_vector,
        retrieved_memories=retrieved_memories,
        current_narrative=current_narrative,
        seed=seed,
    )


# ══════════════════════════════════════════════
# 单元测试（模块直接运行时执行）
# ══════════════════════════════════════════════


def _run_unit_tests() -> bool:
    """单元测试 stub_actor_express 的 8 条规则 + 字段结构"""
    print(f"\n{'─'*60}")
    print(f"  _sge_actor.py 单元测试")
    print(f"{'─'*60}\n")

    base_signals = {
        'directness': 0.5, 'vulnerability': 0.5, 'playfulness': 0.5,
        'initiative': 0.5, 'depth': 0.5, 'warmth': 0.5,
        'defiance': 0.5, 'curiosity': 0.5,
    }

    test_cases = [
        # (signals, expected_behavior, label)
        ({**base_signals, 'initiative': 0.7}, '主动引导', 'initiative 高'),
        ({**base_signals, 'warmth': 0.7}, '关怀回应', 'warmth 高'),
        ({**base_signals, 'playfulness': 0.7}, '玩闹撒娇', 'playfulness 高'),
        ({**base_signals, 'curiosity': 0.7, 'depth': 0.6}, '深度提问', 'curiosity + depth 高'),
        ({**base_signals, 'defiance': 0.7}, '反抗嘴硬', 'defiance 高'),
        ({**base_signals, 'vulnerability': 0.7}, '袒露脆弱', 'vulnerability 高'),
        ({**base_signals, 'directness': 0.2}, '委婉暗示', 'directness 低'),
        ({**base_signals, 'playfulness': 0.2, 'depth': 0.7}, '认真严肃', 'playfulness 低 + depth 高'),
        ({k: 0.2 for k in base_signals}, '沉默不语', '全部低'),
        ({**base_signals, 'initiative': 0.5, 'warmth': 0.5}, '敷衍回应', '全部中等'),
    ]

    all_ok = True
    for signals, expected, label in test_cases:
        out = stub_actor_express(signals=signals, value_vector={'safety': 0.5}, seed=42)
        ok = out.behavior_label == expected
        status = '✓' if ok else '✗'
        print(f"  {status} [{label:30s}] behavior={out.behavior_label} (expected={expected})")
        if not ok:
            all_ok = False

    # 字段结构验证
    out = stub_actor_express(signals=base_signals, value_vector={'safety': 0.5}, seed=42)
    assert out.inner_monologue is not None
    assert out.behavior_label in BEHAVIOR_LABELS
    assert out.intention is not None
    assert 0.0 <= out.confidence <= 1.0
    print(f"  ✓ [字段结构] monologue/intention/confidence 全部合法")

    # ActorOutput.to_dict
    d = out.to_dict()
    assert 'inner_monologue' in d
    assert 'behavior_label' in d
    print(f"  ✓ [to_dict 序列化] keys={list(d.keys())}")

    print(f"\n  状态: {'✅ PASS — 11/11 测试通过' if all_ok else '❌ FAIL'}")
    return all_ok


if __name__ == "__main__":
    import sys
    ok = _run_unit_tests()
    sys.exit(0 if ok else 1)