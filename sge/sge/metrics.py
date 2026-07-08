"""
SGE Self Entropy 度量（Phase 3 架构落地 · 洞察 35）

本文件是 **SGE 自有实现**——计算自我认知熵 H_self，作为"自我形成"的统一目标函数。
纯 Python `math` 实现，**不依赖 numpy/scipy**（保持 sge/ Runtime 零重量依赖）。

**核心命题**（洞察 35 / DESIGN §9.5）：
    自我形成 = 自我认知熵的下降
    H_self = w_v · H_value + w_i · H_identity + w_n · H_narrative

    - H_value：价值观分布熵——价值观越分化/稳定，熵越低
    - H_identity：身份稳定熵——身份反复摇摆，熵越高；固化为一，熵→0
    - H_narrative：叙事一致熵——叙事版本越多/越不连贯，熵越高

**验收指标**（PRD §6）：一段成长后 H_self 下降率 > 30%。

**权重校准**：默认 (0.4, 0.3, 0.3)，应在 M2.2 1000 Epoch 实验中校准。

**H_identity / H_narrative 公式演进**（2026-07-08 修订）：
    原公式：归一化 Shannon 熵 / log2(N_total) → 全 unique → 永远 = 1.0 → 结构性地板 0.6
    新公式（公式 A2）：基于 unique 数线性映射 → 1 unique → 0.0，N_MAX → 1.0 → 数学下界 0
    详见 [research/sge-feasibility/M22_H_SELF_DIAGNOSIS.md](../../research/sge-feasibility/M22_H_SELF_DIAGNOSIS.md)
    与 [experiments/M22_V3_DEDUP_REPORT.md](../../experiments/M22_V3_DEDUP_REPORT.md)

关联文档：
- [DESIGN.md §9.5 Self Entropy](../../DESIGN.md)
- [SGE-Key-Insights.md 洞察 35](../../SGE-Key-Insights.md)
- [ARCH.md §1.8 Cognitive Entropy 目标函数](../../ARCH.md)
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Optional


# 默认权重（DESIGN §9.5，待 M2.2 校准）
DEFAULT_WEIGHTS = (0.4, 0.3, 0.3)  # (w_value, w_identity, w_narrative)

# H_value 直方图分箱
_VALUE_BINS = 10
_VALUE_LO = -1.0
_VALUE_HI = 1.0

# H_identity / H_narrative 公式 A2 的发散阈值（unique 数 > N_MAX 视为完全发散）
# 选择依据：chunk_size=250 时 ~8% 唯一性 = "发散"，适合绝大多数训练场景
N_MAX_DIVERGENT = 20


def _shannon_entropy(probs: list[float], base: float = 2.0) -> float:
    """Shannon 熵（默认 bits）"""
    return -sum(p * math.log(p, base) for p in probs if p > 0)


def _histogram_entropy_normalized(
    values: list[float], bins: int, lo: float, hi: float
) -> float:
    """把 values 装入等宽直方图，返回归一化熵 [0, 1]

    归一化基准 = log2(bins)（均匀分布时熵最大）
    """
    if not values or bins < 2:
        return 0.0
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in values:
        idx = int((v - lo) / width) if width > 0 else 0
        idx = min(max(idx, 0), bins - 1)
        counts[idx] += 1
    total = sum(counts)
    probs = [c / total for c in counts]
    h = _shannon_entropy(probs)
    return h / math.log(bins, 2)


def _sequence_entropy_normalized(items: list, n_max: int = N_MAX_DIVERGENT) -> float:
    """离散序列（身份串/叙事串）的归一化熵 [0, 1]

    公式 A2（2026-07-08 修订，替代原 Shannon 归一化）：
        H = 1.0                        if N_unique == 0  (未形成)
        H = 0.0                        if N_unique == 1  (完全稳定)
        H = (N_unique - 1) / (N_MAX - 1)   if 2 <= N_unique <= N_MAX
        H = 1.0                        if N_unique > N_MAX  (完全发散)

    优点（相对原公式）：
      1. 数学下界为 0（H_self → 0 当所有身份/叙事收敛到唯一表征）
      2. 1 unique identity → H=0（真正反映"稳定"）
      3. dedup 效果可观测：减少 unique 数 → 直接降低 H

    原公式缺陷：归一化基准 = log2(N_total)，全 unique → 永远 = 1.0
      → H_self 结构性地板 0.6 → Insight 35A "下降率 >30%" 不可达

    Args:
        items: 序列条目列表（identity 串 / narrative 串）
        n_max: 发散阈值（默认 N_MAX_DIVERGENT=20）

    Returns:
        [0, 1] 范围的归一化熵
    """
    if n_max < 2:
        raise ValueError(f"n_max must be >= 2, got {n_max}")
    n_unique = len(set(items)) if items else 0
    if n_unique == 0:
        return 1.0  # 未形成 = 最大不确定性
    if n_unique == 1:
        return 0.0  # 完全稳定
    return min(1.0, (n_unique - 1) / (n_max - 1))


def compute_self_entropy(
    value_layer,
    identity_layer=None,
    narrative_builder=None,
    weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
) -> dict:
    """计算自我认知熵 H_self（洞察 35 / DESIGN §9.5）

    Args:
        value_layer: ValueLayer 实例（须有 .value_state 或 .to_vec()）
        identity_layer: IdentityLayer 实例（可选，须有 .identity_history）
        narrative_builder: NarrativeBuilder 实例（可选，须有 .narrative_history）
        weights: (w_value, w_identity, w_narrative)，默认 (0.4, 0.3, 0.3)

    Returns:
        {
          'H_self': float,        # 加权总熵 [0, 1]
          'H_value': float,       # 价值观分布熵 [0, 1]
          'H_identity': float,    # 身份稳定熵 [0, 1]
          'H_narrative': float,   # 叙事一致熵 [0, 1]
          'weights': (w_v, w_i, w_n),
        }
    """
    w_v, w_i, w_n = weights

    # ── H_value：6 维价值观分布熵 ──
    if hasattr(value_layer, 'to_vec'):
        value_vec = value_layer.to_vec()
    elif hasattr(value_layer, 'value_state'):
        value_vec = list(value_layer.value_state.values())
    else:
        value_vec = list(value_layer.values()) if isinstance(value_layer, dict) else []
    H_value = _histogram_entropy_normalized(value_vec, _VALUE_BINS, _VALUE_LO, _VALUE_HI)

    # ── H_identity：身份序列熵 ──
    if identity_layer is not None and hasattr(identity_layer, 'identity_history'):
        identities = [h['identity'] for h in identity_layer.identity_history]
        H_identity = _sequence_entropy_normalized(identities)
    else:
        H_identity = 1.0  # 无身份层 → 未形成

    # ── H_narrative：叙事序列熵 ──
    if narrative_builder is not None and hasattr(narrative_builder, 'narrative_history'):
        narratives = [h['narrative'] for h in narrative_builder.narrative_history]
        H_narrative = _sequence_entropy_normalized(narratives)
    else:
        H_narrative = 1.0  # 无叙事层 → 未形成

    H_self = w_v * H_value + w_i * H_identity + w_n * H_narrative

    return {
        'H_self': H_self,
        'H_value': H_value,
        'H_identity': H_identity,
        'H_narrative': H_narrative,
        'weights': weights,
    }


def entropy_reduction_rate(h_start: float, h_end: float) -> float:
    """H_self 下降率（PRD §6 验收：> 0.30）

    = (H_start - H_end) / H_start，H_start=0 时返回 0.0
    """
    if h_start <= 0:
        return 0.0
    return (h_start - h_end) / h_start


# ══════════════════════════════════════════════
# 单元测试
# ══════════════════════════════════════════════


def _run_unit_tests() -> bool:
    """验证（公式 A2）：
      1. 全部熵值 ∈ [0, 1]
      2. 固化身份（全同，N=1）H_identity → 0.0；摇摆身份（N>1）H_identity > 0
      3. 空身份/叙事 → H = 1.0（未形成）
      4. 发散身份（N>N_MAX）H_identity → 1.0（clamped）
      5. 下降率计算正确
      6. wobbly[4 unique] = (4-1)/(20-1) = 3/19 ≈ 0.1579
    """
    ok = True

    class _VL:
        def __init__(self, vs):
            self.value_state = vs
        def to_vec(self):
            return list(self.value_state.values())

    class _IL:
        def __init__(self, ids):
            self.identity_history = [{'identity': i} for i in ids]

    class _NB:
        def __init__(self, ns):
            self.narrative_history = [{'narrative': n} for n in ns]

    vl = _VL({'safety': 0.8, 'creativity': -0.5, 'connection': 0.3,
              'autonomy': 0.0, 'justice': 0.6, 'compassion': -0.2})

    # 固化身份（全同 N=1）vs 摇摆身份（N=5）vs 发散身份（N=25>N_MAX=20）
    stable = compute_self_entropy(vl, _IL(['探索者'] * 5), _NB(['叙事A'] * 5))
    wobbly = compute_self_entropy(vl, _IL(['A', 'B', 'C', 'D', 'E']),
                                  _NB(['n1', 'n2', 'n3', 'n4', 'n5']))
    divergent = compute_self_entropy(
        vl,
        _IL([f'id_{i}' for i in range(25)]),
        _NB([f'n_{i}' for i in range(25)]),
    )
    unformed = compute_self_entropy(vl, None, None)

    for res, name in [(stable, 'stable'), (wobbly, 'wobbly'),
                      (divergent, 'divergent'), (unformed, 'unformed')]:
        for key in ('H_self', 'H_value', 'H_identity', 'H_narrative'):
            if not (0.0 <= res[key] <= 1.0):
                print(f"FAIL: {name}.{key} out of [0,1]: {res[key]}")
                ok = False

    # 公式 A2: 5 unique → (5-1)/(20-1) = 4/19 ≈ 0.2105
    expected_wobbly_id = 4 / 19
    expected_wobbly_na = 4 / 19
    if abs(wobbly['H_identity'] - expected_wobbly_id) > 1e-9:
        print(f"FAIL: wobbly H_identity ({wobbly['H_identity']}) "
              f"!= 4/19 ({expected_wobbly_id})")
        ok = False
    if abs(wobbly['H_narrative'] - expected_wobbly_na) > 1e-9:
        print(f"FAIL: wobbly H_narrative ({wobbly['H_narrative']}) "
              f"!= 4/19 ({expected_wobbly_na})")
        ok = False
    if stable['H_identity'] >= wobbly['H_identity']:
        print(f"FAIL: stable H_identity ({stable['H_identity']}) "
              f"should be < wobbly ({wobbly['H_identity']})")
        ok = False
    if stable['H_identity'] != 0.0:
        print(f"FAIL: all-same identity should give H_identity=0, got {stable['H_identity']}")
        ok = False
    # 发散场景: 25 unique > N_MAX=20 → H_identity clamped to 1.0
    if divergent['H_identity'] != 1.0:
        print(f"FAIL: divergent (>N_MAX) H_identity should be 1.0, "
              f"got {divergent['H_identity']}")
        ok = False
    if unformed['H_identity'] != 1.0 or unformed['H_narrative'] != 1.0:
        print("FAIL: unformed self should give H_identity=H_narrative=1.0")
        ok = False

    # 下降率
    if abs(entropy_reduction_rate(1.0, 0.6) - 0.4) > 1e-9:
        print("FAIL: entropy_reduction_rate(1.0, 0.6) != 0.4")
        ok = False
    if entropy_reduction_rate(0.0, 0.0) != 0.0:
        print("FAIL: entropy_reduction_rate(0,0) != 0.0")
        ok = False

    print("PASS: metrics.py unit tests" if ok else "FAIL: metrics.py unit tests")
    return ok


if __name__ == '__main__':
    _run_unit_tests()
