"""
SGE Identity Layer（C3 实施）

本文件实现 PRD §FR-5 Identity Layer：
- IdentityLayer 类（crystallize + validate）
- crystallize_identity() — 凝聚价值观向量和关键记忆为身份标签
- validate_identity() — 交叉验证身份描述是否与行为历史一致

**实现来源标注规范**（每个函数/类 docstring 包含三项）：
  1. "来源: DESIGN §五" — 设计依据
  2. "公式: ..." — 核心逻辑
  3. "参考: SGE-M21-Phase-C-Implementation-Plan.md §C3" — 实施计划

**FR-5 验收**：
- 自动生成"我是谁"的回答
- 身份标签与行为历史交叉验证
- 身份随时间演化但保持稳定性
"""

from __future__ import annotations

import json
import random
from typing import Optional


# ══════════════════════════════════════════════
# 提示模板（DESIGN §五/§5.1-§5.2）
# ══════════════════════════════════════════════


SGE_IDENTITY_PROMPT = """基于以下价值观和人生经历，用一句话描述"我是谁"。

价值观：
{vv_desc}

关键经历：
{memories_desc}

要求：
- 用第一人称
- 不超过 50 字
- 必须能从上述经历中推导出来

输出仅 JSON 格式：
{{"identity": "..."}}
"""

SGE_VALIDATE_PROMPT = """身份描述：{identity}

价值观：{vv_desc}
关键经历：{memories_desc}

这个身份描述与价值观和经历是否一致？回答 YES 或 NO。
"""


# ══════════════════════════════════════════════
# Stub Identity（不调用 LLM）
# ══════════════════════════════════════════════


def _value_vector_to_description(value_layer) -> str:
    """ValueLayer → 自然语言描述（用于 prompt 注入）"""
    if hasattr(value_layer, 'value_state'):
        values = value_layer.value_state
    elif isinstance(value_layer, dict):
        values = value_layer
    else:
        return "无价值向量数据"

    # 排序：绝对值最大的 3 个 value
    sorted_values = sorted(values.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
    parts = [f"{k}={v:+.2f}" for k, v in sorted_values]
    return ", ".join(parts)


def _memories_to_description(memories: list, max_n: int = 5) -> str:
    """关键记忆列表 → 自然语言描述"""
    if not memories:
        return "暂无关键经历"

    recent = memories[-max_n:]
    parts = []
    for m in recent:
        if isinstance(m, dict):
            desc = m.get('description', str(m))[:30]
            ev_type = m.get('event_type', 'event')
            parts.append(f"[{ev_type}] {desc}")
        else:
            parts.append(str(m)[:30])
    return "; ".join(parts)


def stub_crystallize_identity(
    value_layer,
    key_memories: list,
    seed: int = 0,
) -> str:
    """Stub 身份凝聚（不调用 LLM）

    逻辑: 基于 value_state 最强的 2 个 value 生成模板化身份
    """
    rng = random.Random(seed)
    values = value_layer.value_state if hasattr(value_layer, 'value_state') else value_layer

    # 按绝对值排序
    sorted_values = sorted(values.items(), key=lambda x: abs(x[1]), reverse=True)
    top1, top2 = sorted_values[0], sorted_values[1]

    # 模板：基于 top1 正负极性
    if top1[1] > 0:
        if top2[1] > 0:
            identity = f"我是一个重视 '{top1[0]}' 和 '{top2[0]}' 的人。"
        else:
            identity = f"我追求 '{top1[0]}' 但对 '{top2[0]}' 持谨慎态度。"
    else:
        if top2[1] > 0:
            identity = f"我对 '{top1[0]}' 感到矛盾，但仍然相信 '{top2[0]}'。"
        else:
            identity = f"我是一个对 '{top1[0]}' 和 '{top2[0]}' 都保持距离的人。"

    return identity


def stub_validate_identity(
    identity: str,
    value_layer,
    key_memories: list,
) -> bool:
    """Stub 身份验证（DESIGN §5.2）

    简化验证：
    1. identity 包含至少一个 value 名字 → 通过（否则不通过）
    2. key_memories 非空 → 通过
    """
    values = value_layer.value_state if hasattr(value_layer, 'value_state') else value_layer
    # 至少有一个 value 名字出现在 identity 中
    for v_name in values:
        if v_name in identity:
            return True
    return False


# ══════════════════════════════════════════════
# 真实 LLM Identity（DESIGN §五）
# ══════════════════════════════════════════════


def real_crystallize_identity(
    value_layer,
    key_memories: list,
    api_key: Optional[str] = None,
    base_url: str = "https://api.minimax.io/anthropic",
    model: str = "anthropic/MiniMax-M3",
    temperature: float = 0.3,
    max_tokens: int = 256,
) -> str:
    """DESIGN §5.1 调用真实 LLM 生成 identity"""
    try:
        from litellm import completion
    except ImportError:
        raise ImportError("litellm 未安装")

    import os
    api_key = api_key or os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise ValueError("MINIMAX_API_KEY 环境变量未设置")

    vv_desc = _value_vector_to_description(value_layer)
    memories_desc = _memories_to_description(key_memories)
    prompt = SGE_IDENTITY_PROMPT.format(vv_desc=vv_desc, memories_desc=memories_desc)

    response = completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content.strip()

    # 解析 JSON
    if content.startswith('```'):
        lines = content.split('\n')
        content = '\n'.join(lines[1:-1]) if lines[-1].strip() == '```' else content
        if content.startswith('json'):
            content = content[4:].lstrip()

    try:
        parsed = json.loads(content)
        return parsed.get('identity', content[:50])
    except json.JSONDecodeError:
        return content[:50]


def real_validate_identity(
    identity: str,
    value_layer,
    key_memories: list,
    api_key: Optional[str] = None,
    base_url: str = "https://api.minimax.io/anthropic",
    model: str = "anthropic/MiniMax-M3",
    temperature: float = 0.0,
    max_tokens: int = 16,
) -> bool:
    """DESIGN §5.2 调用真实 LLM 验证 identity"""
    try:
        from litellm import completion
    except ImportError:
        raise ImportError("litellm 未安装")

    import os
    api_key = api_key or os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise ValueError("MINIMAX_API_KEY 环境变量未设置")

    vv_desc = _value_vector_to_description(value_layer)
    memories_desc = _memories_to_description(key_memories)
    prompt = SGE_VALIDATE_PROMPT.format(
        identity=identity, vv_desc=vv_desc, memories_desc=memories_desc,
    )

    response = completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content.strip().upper()
    return "YES" in content


# ══════════════════════════════════════════════
# IdentityLayer 类（DESIGN §五）
# ══════════════════════════════════════════════


class IdentityLayer:
    """SGE Identity Layer

    来源: DESIGN §五（Identity Layer）
    公式:
      - 触发: 每 N 个 Epoch 或 Phase Transition 后
      - crystallize: LLM 生成 identity → validate → 写入 history
      - validate: identity 与 value_vector/key_memories 一致性检查
    参考: SGE-M21-Phase-C-Implementation-Plan.md §C3
    """

    def __init__(
        self,
        identity_history: Optional[list] = None,
        crystallize_every_n_epochs: int = 20,  # DESIGN §5.1 触发条件
        use_real_llm: bool = False,
        llm=None,
    ):
        """
        Args:
            identity_history: 初始化历史（None 则空）
            crystallize_every_n_epochs: 每 N 个 Epoch 触发一次
            use_real_llm: True 调用真实 LLM，False 用 stub
            llm: SGELLMClient 实例（阶段 D 统一接口）
        """
        self.identity_history = identity_history or []
        self.crystallize_every_n_epochs = crystallize_every_n_epochs
        self.use_real_llm = use_real_llm
        self.llm = llm

    def should_crystallize(self, epoch: int) -> bool:
        """DESIGN §5.1 触发条件：每 N 个 Epoch（跑完第 N 个 epoch 后触发）

        epoch 从 0 开始（orchestrator.run 用 range(n_epochs)），所以
        "跑完 20 个 epoch"对应 epoch=19，应触发一次。
        公式：(epoch + 1) % N == 0  → epoch ∈ {N-1, 2N-1, ...}
        """
        return (epoch + 1) % self.crystallize_every_n_epochs == 0

    def crystallize(
        self,
        value_layer,
        key_memories: list,
        epoch: int = 0,
        seed: int = 0,
        force_validate: bool = False,
        **kwargs,
    ) -> Optional[str]:
        """DESIGN §5.1 凝聚身份

        Args:
            value_layer: ValueLayer 实例
            key_memories: 关键记忆列表
            epoch: 当前 Epoch（用于记录）
            seed: stub 随机种子
            force_validate: True 即使 stub 也调用 validate
            **kwargs: 传给 real_crystallize_identity

        Returns:
            identity 字符串，验证失败则 None
        """
        # 1. 生成 identity
        if self.use_real_llm:
            if self.llm is not None:
                # 阶段 D：使用统一 SGELLMClient
                vv_desc = _value_vector_to_description(value_layer)
                memories_desc = _memories_to_description(key_memories)
                prompt = SGE_IDENTITY_PROMPT.format(vv_desc=vv_desc, memories_desc=memories_desc)
                parsed = self.llm.chat_json(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=256,
                    fallback_value=None,
                )
                if parsed is None:
                    identity = None
                elif isinstance(parsed, dict):
                    identity = parsed.get('identity', str(parsed)[:50])
                elif isinstance(parsed, str):
                    identity = parsed  # LLM 直接返回字符串（真实 LLM 常见）
                else:
                    identity = str(parsed)[:50]  # 兜底
            else:
                # 向后兼容：旧接口（kwargs 里有 api_key / base_url）
                identity = real_crystallize_identity(value_layer, key_memories, **kwargs)
        else:
            identity = stub_crystallize_identity(value_layer, key_memories, seed=seed)

        if identity is None:
            return None

        # 2. 验证
        if self.use_real_llm or force_validate:
            if self.use_real_llm and self.llm is not None:
                # 阶段 D：使用统一 SGELLMClient
                vv_desc = _value_vector_to_description(value_layer)
                memories_desc = _memories_to_description(key_memories)
                prompt = SGE_VALIDATE_PROMPT.format(
                    identity=identity, vv_desc=vv_desc, memories_desc=memories_desc,
                )
                content = self.llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=16,
                )
                valid = "YES" in content.upper()
            elif self.use_real_llm:
                valid = real_validate_identity(identity, value_layer, key_memories, **kwargs)
            else:
                valid = stub_validate_identity(identity, value_layer, key_memories)
            if not valid:
                return None

        # 3. 记录到 history
        self.identity_history.append({
            'epoch': epoch,
            'identity': identity,
            'value_snapshot': dict(value_layer.value_state if hasattr(value_layer, 'value_state') else value_layer),
        })
        return identity

    def get_current(self) -> Optional[str]:
        """获取当前身份（最近一次 crystallize 成功的 identity）"""
        if self.identity_history:
            return self.identity_history[-1]['identity']
        return None

    def stability_score(self) -> float:
        """DESIGN §9.1 身份稳定度（信息熵倒数）"""
        if len(self.identity_history) < 2:
            return 1.0  # 默认稳定
        from collections import Counter
        import math
        identities = [h['identity'] for h in self.identity_history]
        counts = Counter(identities)
        total = len(identities)
        entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
        return 1.0 / (1.0 + entropy)
