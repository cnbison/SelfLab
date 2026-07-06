"""
SGE Narrative Layer（C4 实施）

本文件实现 PRD §FR-6 Narrative Layer：
- NarrativeBuilder 类（build + check_consistency + handle_phase_transition）
- build_narrative() — 串联结晶记忆为人生故事
- check_narrative_consistency() — 检查叙事与行为历史的一致性
- handle_phase_transition() — Phase Transition 时叙事断裂与重建

**实现来源标注规范**（每个函数/类 docstring 包含三项）：
  1. "来源: DESIGN §六" — 设计依据
  2. "公式: ..." — 核心逻辑
  3. "参考: SGE-M21-Phase-C-Implementation-Plan.md §C4" — 实施计划

**FR-6 验收**：
- 将零散记忆串联为因果链
- 支持叙事断裂与重建（Phase Transition）
- 定期一致性扫描和修复
"""

from __future__ import annotations

import json
import random
from typing import Optional


# ══════════════════════════════════════════════
# 提示模板（DESIGN §六/§6.1-§6.3）
# ══════════════════════════════════════════════


SGE_NARRATIVE_PROMPT = """基于以下关键经历，构建一个连贯的人生叙事。

我的身份：{current_identity}

关键经历（按时间顺序）：
{events_timeline}

要求：
- 过去 → 现在 → 未来 的结构
- 每个经历之间有因果连接
- 总结"我从这些经历中学到了什么"
- 展望"我将走向何方"
- 不超过 500 字

输出仅 JSON 格式：
{{"narrative": "..."}}
"""

SGE_CONSISTENCY_PROMPT = """叙事：{narrative}

实际经历：
{events_timeline}

这个叙事与实际经历的一致性如何？
评分：0.0（完全不一致）~ 1.0（完全一致）
只输出数字。
"""


# ══════════════════════════════════════════════
# Stub Narrative（不调用 LLM）
# ══════════════════════════════════════════════


def stub_build_narrative(
    crystallized_events: list,
    current_identity: Optional[str],
    seed: int = 0,
) -> str:
    """Stub 叙事构建（DESIGN §6.1）

    逻辑: 串联 crystallized_events + 套用模板
    """
    rng = random.Random(seed)

    if not crystallized_events:
        return "我还在寻找自己的故事。"

    # 过去部分
    n = len(crystallized_events)
    past_count = max(1, n // 3)
    past_events = crystallized_events[:past_count]
    present_events = crystallized_events[past_count:-max(1, n // 3)] if n > 3 else []
    future_events = crystallized_events[-max(1, n // 3):]

    parts = []
    if current_identity:
        parts.append(f"我是{current_identity}")
    parts.append(f"回顾过去，我经历了 {past_count} 次重要事件")
    if present_events:
        parts.append(f"，这些经历塑造了现在的我")
    if future_events:
        future_type = future_events[-1].get('event_type', '未知') if isinstance(future_events[-1], dict) else '未知'
        parts.append(f"。展望未来，我将继续探索 '{future_type}' 类型的经历")

    return "。".join(parts) + "。"


def stub_check_narrative_consistency(
    narrative: str,
    crystallized_events: list,
    seed: int = 0,
) -> float:
    """Stub 一致性检查（DESIGN §6.2）

    简化: 返回基于事件数量的伪分数（[0.5, 1.0]）
    """
    rng = random.Random(seed)
    if not crystallized_events:
        return 0.5
    # 简单启发式: 事件越多 → 一致性越高（上限 1.0）
    n = len(crystallized_events)
    base = min(1.0, 0.5 + 0.1 * n)
    return round(base + rng.uniform(-0.05, 0.05), 3)


# ══════════════════════════════════════════════
# 真实 LLM Narrative（DESIGN §六）
# ══════════════════════════════════════════════


def real_build_narrative(
    crystallized_events: list,
    current_identity: Optional[str],
    api_key: Optional[str] = None,
    base_url: str = "https://api.minimax.io/anthropic",
    model: str = "anthropic/MiniMax-M3",
    temperature: float = 0.5,
    max_tokens: int = 1024,
) -> str:
    """DESIGN §6.1 调用真实 LLM 构建叙事"""
    try:
        from litellm import completion
    except ImportError:
        raise ImportError("litellm 未安装")

    import os
    api_key = api_key or os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise ValueError("MINIMAX_API_KEY 环境变量未设置")

    events_timeline = _format_events_timeline(crystallized_events)
    prompt = SGE_NARRATIVE_PROMPT.format(
        current_identity=current_identity or "（无身份记录）",
        events_timeline=events_timeline,
    )

    response = completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content.strip()

    if content.startswith('```'):
        lines = content.split('\n')
        content = '\n'.join(lines[1:-1]) if lines[-1].strip() == '```' else content
        if content.startswith('json'):
            content = content[4:].lstrip()

    try:
        parsed = json.loads(content)
        return parsed.get('narrative', content[:200])
    except json.JSONDecodeError:
        return content[:200]


def real_check_narrative_consistency(
    narrative: str,
    crystallized_events: list,
    api_key: Optional[str] = None,
    base_url: str = "https://api.minimax.io/anthropic",
    model: str = "anthropic/MiniMax-M3",
    temperature: float = 0.0,
    max_tokens: int = 16,
) -> float:
    """DESIGN §6.2 调用真实 LLM 检查一致性"""
    try:
        from litellm import completion
    except ImportError:
        raise ImportError("litellm 未安装")

    import os
    api_key = api_key or os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise ValueError("MINIMAX_API_KEY 环境变量未设置")

    events_timeline = _format_events_timeline(crystallized_events)
    prompt = SGE_CONSISTENCY_PROMPT.format(
        narrative=narrative, events_timeline=events_timeline,
    )

    response = completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content.strip()
    # 提取数字
    import re
    match = re.search(r'([0-9]*\.?[0-9]+)', content)
    if match:
        try:
            score = float(match.group(1))
            return max(0.0, min(1.0, score))
        except ValueError:
            pass
    return 0.5  # 解析失败默认值


def _format_events_timeline(events: list) -> str:
    """事件列表 → 时间线描述"""
    if not events:
        return "（无经历）"
    parts = []
    for i, ev in enumerate(events):
        if isinstance(ev, dict):
            desc = ev.get('description', str(ev))[:50]
            ev_type = ev.get('event_type', 'event')
            parts.append(f"[E{i}] {ev_type}: {desc}")
        else:
            parts.append(f"[E{i}] {str(ev)[:50]}")
    return "\n".join(parts)


# ══════════════════════════════════════════════
# NarrativeBuilder 类（DESIGN §六）
# ══════════════════════════════════════════════


class NarrativeBuilder:
    """SGE Narrative Layer

    来源: DESIGN §六（Narrative Layer）
    公式:
      - 触发: 每 N 个 Epoch 或 Phase Transition 后
      - build: LLM 串联 crystallized_events 为连贯叙事
      - check_consistency: 叙事与经历的一致性 [0, 1]
      - handle_phase_transition: 重建叙事（保留旧叙事 backup）
    参考: SGE-M21-Phase-C-Implementation-Plan.md §C4
    """

    def __init__(
        self,
        current_narrative: Optional[str] = None,
        build_every_n_epochs: int = 50,
        use_real_llm: bool = False,
        consistency_threshold: float = 0.5,
        llm=None,
        dedup_threshold: float = 0.0,  # M3.x 试点
        dedup_window: int = 1,
        dedup_method: str = 'jaccard',  # 'jaccard' | 'ngram'（v4 试点）
    ):
        """
        Args:
            current_narrative: 初始叙事
            build_every_n_epochs: 每 N 个 Epoch 触发 build
            use_real_llm: True 调用真实 LLM
            consistency_threshold: 重建叙事的一致性阈值（DESIGN §6.3 规定 0.5）
            llm: SGELLMClient 实例（阶段 D 统一接口）
            dedup_threshold: 相似度阈值（>0 启用去重）
            dedup_window: 比对窗口
            dedup_method: 去重算法（'jaccard' or 'ngram'）
        """
        self.current_narrative = current_narrative
        self.build_every_n_epochs = build_every_n_epochs
        self.use_real_llm = use_real_llm
        self.consistency_threshold = consistency_threshold
        self.llm = llm
        self.dedup_threshold = dedup_threshold
        self.dedup_window = max(1, dedup_window)
        self.dedup_method = dedup_method
        self.narrative_history = []  # [(epoch, narrative, coherence_score), ...]

    def should_build(self, epoch: int) -> bool:
        """DESIGN §六 触发条件：每 N 个 Epoch（跑完第 N 个 epoch 后触发）

        epoch 从 0 开始（orchestrator.run 用 range(n_epochs)），所以
        "跑完 50 个 epoch"对应 epoch=49，应触发一次。
        公式：(epoch + 1) % N == 0  → epoch ∈ {N-1, 2N-1, ...}
        """
        return (epoch + 1) % self.build_every_n_epochs == 0

    def build(
        self,
        crystallized_events: list,
        current_identity: Optional[str],
        epoch: int = 0,
        seed: int = 0,
        **kwargs,
    ) -> str:
        """DESIGN §6.1 构建叙事

        Args:
            crystallized_events: 结晶后的事件列表
            current_identity: 当前身份
            epoch: 当前 Epoch
            seed: stub 随机种子

        Returns:
            叙事字符串
        """
        if self.use_real_llm:
            if self.llm is not None:
                # 阶段 D：使用统一 SGELLMClient
                events_timeline = _format_events_timeline(crystallized_events)
                prompt = SGE_NARRATIVE_PROMPT.format(
                    current_identity=current_identity or '（暂无身份）',
                    events_timeline=events_timeline,
                )
                parsed = self.llm.chat_json(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=800,
                    fallback_value=None,
                )
                if parsed is None:
                    narrative = stub_build_narrative(
                        crystallized_events, current_identity, seed=seed,
                    )
                else:
                    narrative = parsed.get('narrative', str(parsed)[:500])
            else:
                # 向后兼容
                narrative = real_build_narrative(
                    crystallized_events, current_identity, **kwargs,
                )
        else:
            narrative = stub_build_narrative(
                crystallized_events, current_identity, seed=seed,
            )

        # M3.x 试点：narrative 去重（同 IdentityLayer 逻辑）
        if (getattr(self, 'dedup_threshold', 0) > 0
                and self.narrative_history):
            # 根据 dedup_method 选择相似度算法
            from .identity import _jaccard_similarity, _ngram_similarity
            if getattr(self, 'dedup_method', 'jaccard') == 'ngram':
                sim_fn = _ngram_similarity
            else:  # 'jaccard'
                sim_fn = _jaccard_similarity
            recent = self.narrative_history[-getattr(self, 'dedup_window', 1):]
            max_sim = max(
                sim_fn(narrative, h['narrative'])
                for h in recent
            )
            if max_sim >= self.dedup_threshold:
                self.current_narrative = self.narrative_history[-1]['narrative']
                return self.narrative_history[-1]['narrative']

        self.current_narrative = narrative
        # 记录到 history（含 coherence 分数）
        coherence = self.check_consistency(
            narrative, crystallized_events, seed=seed,
        )
        self.narrative_history.append({
            'epoch': epoch,
            'narrative': narrative,
            'coherence': coherence,
            'phase_transition': False,
        })
        return narrative

    def check_consistency(
        self,
        narrative: str,
        crystallized_events: list,
        seed: int = 0,
        **kwargs,
    ) -> float:
        """DESIGN §6.2 一致性检查

        Returns:
            [0, 1] 范围的分数
        """
        if self.use_real_llm:
            if self.llm is not None:
                # 阶段 D：使用统一 SGELLMClient
                events_timeline = _format_events_timeline(crystallized_events)
                prompt = SGE_CONSISTENCY_PROMPT.format(
                    narrative=narrative, events_timeline=events_timeline,
                )
                parsed = self.llm.chat_json(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=16,
                    fallback_value=None,
                )
                if parsed is None:
                    score = 0.5  # 默认中等一致性
                elif isinstance(parsed, (int, float)):
                    score = float(parsed)  # LLM 直接返回数字（真实 LLM 常见）
                elif isinstance(parsed, dict):
                    score = float(parsed.get('score', parsed.get('coherence', 0.5)))
                else:
                    score = 0.5  # 未知类型 → 中性
            else:
                # 向后兼容
                score = real_check_narrative_consistency(
                    narrative, crystallized_events, **kwargs,
                )
        else:
            score = stub_check_narrative_consistency(
                narrative, crystallized_events, seed=seed,
            )
        return max(0.0, min(1.0, score))

    def handle_phase_transition(
        self,
        value_layer,
        crystallized_events: list,
        current_identity: Optional[str],
        epoch: int = 0,
        seed: int = 0,
        **kwargs,
    ) -> dict:
        """DESIGN §6.3 叙事断裂与重建

        触发: Phase Transition（frustration > threshold）
        逻辑:
          1. 记录旧叙事（作为 backup）
          2. 重建叙事（build）
          3. 检查一致性 → > 0.5 接受新叙事；否则保留旧叙事

        Args:
            value_layer: 当前 ValueLayer
            crystallized_events: 结晶后的事件列表
            current_identity: 当前身份
            epoch: 当前 Epoch
            seed: stub 随机种子

        Returns:
            {'old_narrative': str, 'new_narrative': str, 'accepted': bool, 'coherence': float}
        """
        # 1. 记录旧叙事
        old_narrative = self.current_narrative or "（无旧叙事）"

        # 2. 重建叙事
        new_narrative = self.build(
            crystallized_events, current_identity, epoch=epoch, seed=seed,
        )

        # 3. 一致性检查
        coherence = self.check_consistency(
            new_narrative, crystallized_events, seed=seed,
        )
        accepted = coherence >= self.consistency_threshold

        if accepted:
            # 接受新叙事
            self.narrative_history.append({
                'epoch': epoch,
                'narrative': new_narrative,
                'coherence': coherence,
                'phase_transition': True,
                'replaced': old_narrative,
            })
        else:
            # 拒绝新叙事，保留旧叙事
            self.narrative_history.append({
                'epoch': epoch,
                'narrative': old_narrative,
                'coherence': self.check_consistency(old_narrative, crystallized_events, seed=seed),
                'phase_transition': True,
                'rejected_new': new_narrative,
            })

        return {
            'old_narrative': old_narrative,
            'new_narrative': new_narrative,
            'accepted': accepted,
            'coherence': coherence,
        }

    def get_current(self) -> Optional[str]:
        """获取当前叙事"""
        return self.current_narrative
