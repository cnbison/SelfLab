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

**H_identity / H_narrative 公式演进**：
  - 2026-07-08 公式 A2：基于 unique 数线性映射（1 unique → 0.0, N_MAX → 1.0）
  - 2026-07-10 发现 P0-4：H_self 非单调（identity 增长 → H_identity 必然上升）
  - 2026-07-10 公式 A3（语义聚类版）：基于 char-bigram Jaccard 聚类，N_clusters 套用公式 A2
    → "探索者" 和 "创造探索者" 被识别为同一类 → identity 增长不必然导致 H 上升
  - 详见 [M22_V5_REPORT.md 2026-07-10 重写版 §5.3](../../experiments/M22_V5_REPORT.md)
    + [discussions/2026-07-10-v5-full-rerun-correction.md](../../discussions/2026-07-10-v5-full-rerun-correction.md)

关联文档：
- [DESIGN.md §9.5 Self Entropy](../../DESIGN.md)
- [SGE-Key-Insights.md 洞察 35](../../SGE-Key-Insights.md)
- [ARCH.md §1.8 Cognitive Entropy 目标函数](../../ARCH.md)
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Optional, Union


# 默认权重（DESIGN §9.5，待 M2.2 校准）
DEFAULT_WEIGHTS = (0.4, 0.3, 0.3)  # (w_value, w_identity, w_narrative)

# H_value 直方图分箱
_VALUE_BINS = 10
_VALUE_LO = -1.0
_VALUE_HI = 1.0

# H_identity / H_narrative 公式 A2/A3 的发散阈值（unique/cluster 数 > N_MAX 视为完全发散）
# 选择依据：chunk_size=250 时 ~8% 唯一性 = "发散"，适合绝大多数训练场景
N_MAX_DIVERGENT = 20

# 公式 A3（语义聚类）参数
DEFAULT_SIMILARITY_THRESHOLD = 0.5   # overlap coefficient ≥ 0.5 视为同类
DEFAULT_NGRAM_SIZE = 2               # char bigram


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
    """离散序列（身份串/叙事串）的**字符串 unique**归一化熵 [0, 1]

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

    **局限**（P0-4, 2026-07-10）：identity 增长 → N_unique 必然上升 → H 必然上升
      → 公式 A2 反映"多样性"而非"形成度" → 建议改用 `_semantic_diversity`（公式 A3）

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


# ══════════════════════════════════════════════
# 公式 A3：基于 char-bigram Jaccard 的语义聚类多样性（2026-07-10）
# ══════════════════════════════════════════════


def _char_ngrams(text: str, n: int = DEFAULT_NGRAM_SIZE) -> set:
    """提取字符串的 char n-gram 集合（pure Python 零依赖）"""
    if not text or len(text) < n:
        return {text} if text else set()
    return {text[i:i + n] for i in range(len(text) - n + 1)}


def _jaccard(set_a: set, set_b: set) -> float:
    """集合 Jaccard 相似度 [0, 1]"""
    if not set_a and not set_b:
        return 1.0  # 两个空集视为完全相同
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def _overlap_coefficient(set_a: set, set_b: set) -> float:
    """Overlap Coefficient [0, 1]：|A ∩ B| / min(|A|, |B|)

    相对 Jaccard 的优势：
      - 对子集关系更宽容（A ⊂ B → overlap = 1.0）
      - 适合"长字符串包含短字符串关键词"的语义匹配
      - 不会因 cluster 累积增长而失真（只要 cluster center 不变）

    Examples:
      >>> _overlap_coefficient({'a', 'b'}, {'a', 'b', 'c', 'd'})  # = 2/2 = 1.0
      >>> _overlap_coefficient({'a', 'b', 'c'}, {'a', 'b', 'd'})  # = 2/3 ≈ 0.667
    """
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    return intersection / min(len(set_a), len(set_b))


def _semantic_diversity(
    items: list,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    n_max: int = N_MAX_DIVERGENT,
    ngram_size: int = DEFAULT_NGRAM_SIZE,
) -> float:
    """基于语义聚类的多样性度量 [0, 1]（公式 A3, 2026-07-10）

    算法：
      1. 每个 item → char n-gram 集合
      2. 贪心聚类：依次遍历 items，每个 item 找最相似的已有 cluster
         - cluster center = 首个 item 的 n-gram 集合（**不增长**，避免后续 item 相似度衰减）
         - 相似度 = overlap_coefficient(ngrams, center) ≥ threshold → 加入该 cluster
         - 相似度 < threshold → 新建 cluster
      3. N_clusters 套用公式 A2：
         H = 1.0                        if N_clusters == 0  (未形成)
         H = 0.0                        if N_clusters == 1  (完全稳定)
         H = (N_clusters - 1) / (N_MAX - 1)   if 2 <= N_clusters <= N_MAX
         H = 1.0                        if N_clusters > N_MAX  (完全发散)

    相对公式 A2 的优势：
      - "探索者" 和 "创造探索者" 被识别为同一类 → identity 增长不必然导致 H 上升
      - 真正反映"语义重复度"而非"字符串 unique 度"

    相对 sentence-transformers 的优势：
      - 零依赖（pure Python）
      - 确定性（无模型加载/调用）
      - 快速（< 1ms for 12 items）
      - 适合作为 baseline，semantic embedding 可后续替换

    Args:
        items: 字符串列表（identity 串 / narrative 串）
        threshold: overlap coefficient 阈值 [0, 1]，默认 0.5
        n_max: 发散阈值（cluster 数 > N_MAX 视为完全发散），默认 20
        ngram_size: char n-gram 长度，默认 2（bigram）

    Returns:
        [0, 1] 范围的归一化多样性度量
    """
    if not items:
        return 1.0  # 未形成

    if n_max < 2:
        raise ValueError(f"n_max must be >= 2, got {n_max}")

    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"threshold must be in [0, 1], got {threshold}")

    # 1. 计算每个 item 的 n-gram 集合
    item_ngrams = [_char_ngrams(s, ngram_size) for s in items]

    # 2. 贪心聚类：clusters 是 list of sets（cluster center = 首个 item 的 n-gram）
    #    关键设计：cluster center 不增长！这样后续 item 永远与"原始 cluster 中心"比较
    clusters: list[set] = []

    for ngrams in item_ngrams:
        if not clusters:
            clusters.append(ngrams)
            continue

        # 找最相似的 cluster（用 overlap coefficient，更宽容子集关系）
        sims = [_overlap_coefficient(ngrams, c) for c in clusters]
        max_sim = max(sims)
        if max_sim >= threshold:
            # 加入最相似的 cluster（center 不变）
            pass  # cluster center 已经是首个 item 的 ngrams，无需更新
        else:
            # 新建 cluster
            clusters.append(ngrams)

    n_clusters = len(clusters)

    # 3. 套用公式 A2 框架
    if n_clusters == 0:
        return 1.0
    if n_clusters == 1:
        return 0.0
    return min(1.0, (n_clusters - 1) / (n_max - 1))


def compute_self_entropy(
    value_layer,
    identity_layer=None,
    narrative_builder=None,
    weights: tuple[float, float, float] = DEFAULT_WEIGHTS,
    semantic_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> dict:
    """计算自我认知熵 H_self（洞察 35 / DESIGN §9.5）

    Args:
        value_layer: ValueLayer 实例（须有 .value_state 或 .to_vec()）
        identity_layer: IdentityLayer 实例（可选，须有 .identity_history）
        narrative_builder: NarrativeBuilder 实例（可选，须有 .narrative_history）
        weights: (w_value, w_identity, w_narrative)，默认 (0.4, 0.3, 0.3)
        semantic_threshold: 公式 A3 的 Jaccard 相似度阈值（仅 H_identity/H_narrative 使用）

    Returns:
        {
          'H_self': float,        # 加权总熵 [0, 1]
          'H_value': float,       # 价值观分布熵 [0, 1]
          'H_identity': float,    # 身份稳定熵 [0, 1]（公式 A3 语义聚类）
          'H_narrative': float,   # 叙事一致熵 [0, 1]（公式 A3 语义聚类）
          'weights': (w_v, w_i, w_n),
          'method': 'A3-semantic-clustering',  # 标识当前使用的方法
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

    # ── H_identity：身份序列熵（公式 A3 语义聚类版, 2026-07-10）──
    if identity_layer is not None and hasattr(identity_layer, 'identity_history'):
        identities = [h['identity'] for h in identity_layer.identity_history]
        H_identity = _semantic_diversity(identities, threshold=semantic_threshold)
    else:
        H_identity = 1.0  # 无身份层 → 未形成

    # ── H_narrative：叙事序列熵（公式 A3 语义聚类版, 2026-07-10）──
    if narrative_builder is not None and hasattr(narrative_builder, 'narrative_history'):
        narratives = [h['narrative'] for h in narrative_builder.narrative_history]
        H_narrative = _semantic_diversity(narratives, threshold=semantic_threshold)
    else:
        H_narrative = 1.0  # 无叙事层 → 未形成

    H_self = w_v * H_value + w_i * H_identity + w_n * H_narrative

    return {
        'H_self': H_self,
        'H_value': H_value,
        'H_identity': H_identity,
        'H_narrative': H_narrative,
        'weights': weights,
        'method': 'A3-semantic-clustering',
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
    """兼容层：转调 pytest（Phase 3.2 起的测试已在 sge/tests/unit/test_metrics.py）。"""
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, '-m', 'pytest',
         'tests/unit/test_metrics.py', '-v', '--tb=short'],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_unit_tests() else 1)
