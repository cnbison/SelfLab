"""sge.metrics pytest 单元测试 — Self Entropy 公式 A2 + A3 + compute_self_entropy。

Phase 3.2 conversion 第二批 4/4。
覆盖:
  公式 A2（_sequence_entropy_normalized）:
    1. 全部 [0, 1] 范围
    2. 1 unique → H=0.0（稳定）
    3. N=0 → H=1.0（未形成）
    4. 2 ≤ N ≤ N_MAX → (N-1)/(N_MAX-1)
    5. N > N_MAX → H=1.0（发散）
    6. n_max < 2 抛 ValueError
  公式 A3（_semantic_diversity）:
    7. 完全相同 → H=0
    8. 语义相似 → 聚为 1 类 → H=0
    9. 完全不同 → H>0
    10. 阈值过低/过高边界
    11. 25 个 2-char 不相关 → 各自成 cluster → clamp to 1.0
  工具:
    12. _shannon_entropy 正确性
    13. _histogram_entropy_normalized 均匀分布最大 + 单值最小
    14. _char_ngrams bigram + 短字符串 fallback
    15. _jaccard / _overlap_coefficient 边界
    16. entropy_reduction_rate 公式
  compute_self_entropy:
    17. 4 个 H_* 字段齐全 + weights + method
    18. weights 参数生效
    19. 无 identity/narrative → H=1.0
    20. value_layer duck typing（to_vec / value_state / dict）
    21. v5 真实 identities 数据集 H < 0.5（公式 A3 聚类效果）
"""

from __future__ import annotations

import pytest

from sge.metrics import (
    _shannon_entropy,
    _histogram_entropy_normalized,
    _sequence_entropy_normalized,
    _semantic_diversity,
    _char_ngrams,
    _jaccard,
    _overlap_coefficient,
    compute_self_entropy,
    entropy_reduction_rate,
    DEFAULT_WEIGHTS,
    N_MAX_DIVERGENT,
)


# ════════════════════════════════════════════════
# _shannon_entropy
# ════════════════════════════════════════════════


def test_shannon_entropy_uniform_distribution_max():
    """均匀分布 → log2(N) bits。"""
    h = _shannon_entropy([0.25, 0.25, 0.25, 0.25])
    assert abs(h - 2.0) < 1e-9  # log2(4) = 2.0


def test_shannon_entropy_deterministic_distribution_zero():
    """确定性分布 → 0 bits。"""
    h = _shannon_entropy([1.0, 0.0, 0.0])
    assert abs(h) < 1e-9


def test_shannon_entropy_ignores_zero_probabilities():
    """零概率项不参与计算（0 * log(0) 视为 0）。"""
    h = _shannon_entropy([0.5, 0.5, 0.0, 0.0])
    assert abs(h - 1.0) < 1e-9  # log2(2) = 1.0


# ════════════════════════════════════════════════
# _histogram_entropy_normalized
# ════════════════════════════════════════════════


def test_histogram_entropy_uniform_max():
    """均匀分布直方图 → H=1.0（最大值）。"""
    # 9 个 values 均匀分到 3 个 bins
    h = _histogram_entropy_normalized([-0.9, -0.5, -0.1, 0.1, 0.5, 0.9], bins=3, lo=-1.0, hi=1.0)
    # [-1, -0.33), [-0.33, 0.33), [0.33, 1] → 各 2 个 → 均匀
    assert abs(h - 1.0) < 1e-9


def test_histogram_entropy_all_same_zero():
    """所有值相同 → H=0.0（最小值）。"""
    h = _histogram_entropy_normalized([0.5] * 10, bins=10, lo=0.0, hi=1.0)
    assert abs(h) < 1e-9


def test_histogram_entropy_empty_returns_zero():
    """空 values → H=0.0（防御性 fallback）。"""
    h = _histogram_entropy_normalized([], bins=10, lo=0.0, hi=1.0)
    assert h == 0.0


# ════════════════════════════════════════════════
# _sequence_entropy_normalized（公式 A2）
# ════════════════════════════════════════════════


def test_sequence_entropy_zero_items_returns_one():
    """空序列 → H=1.0（未形成）。"""
    assert _sequence_entropy_normalized([]) == 1.0


def test_sequence_entropy_one_unique_returns_zero():
    """1 unique → H=0.0（完全稳定）。"""
    assert _sequence_entropy_normalized(['探索者', '探索者', '探索者']) == 0.0


def test_sequence_entropy_two_unique_returns_one_over_n_max_minus_one():
    """2 unique → (2-1)/(20-1) = 1/19 ≈ 0.0526。"""
    h = _sequence_entropy_normalized(['A', 'B'])
    assert abs(h - 1 / 19) < 1e-9


def test_sequence_entropy_four_unique_returns_three_over_nineteen():
    """4 unique → (4-1)/(20-1) = 3/19 ≈ 0.1579。"""
    h = _sequence_entropy_normalized(['A', 'B', 'C', 'D'])
    assert abs(h - 3 / 19) < 1e-9


def test_sequence_entropy_above_n_max_clamps_to_one():
    """> N_MAX unique → H=1.0（完全发散）。"""
    items = [f'id_{i}' for i in range(25)]
    assert _sequence_entropy_normalized(items) == 1.0


def test_sequence_entropy_at_n_max_uses_linear():
    """N=N_MAX → (N_MAX-1)/(N_MAX-1) = 1.0。"""
    items = [f'id_{i}' for i in range(N_MAX_DIVERGENT)]
    assert abs(_sequence_entropy_normalized(items) - 1.0) < 1e-9


def test_sequence_entropy_n_max_less_than_two_raises():
    """n_max < 2 → ValueError。"""
    with pytest.raises(ValueError, match='n_max must be >= 2'):
        _sequence_entropy_normalized(['A', 'B'], n_max=1)


# ════════════════════════════════════════════════
# _char_ngrams / _jaccard / _overlap_coefficient
# ════════════════════════════════════════════════


def test_char_ngrams_bigrams():
    """默认 bigram 提取。"""
    grams = _char_ngrams('探索者')
    # "探索者" 是 3 字 → 2 个 bigram
    assert len(grams) == 2


def test_char_ngrams_short_string_fallback():
    """短字符串（< n）→ fallback 为 {text}。"""
    assert _char_ngrams('A') == {'A'}
    assert _char_ngrams('') == set()


def test_jaccard_identical_sets_returns_one():
    """相同集合 → 1.0。"""
    assert _jaccard({'a', 'b'}, {'a', 'b'}) == 1.0


def test_jaccard_disjoint_sets_returns_zero():
    """无交集 → 0.0。"""
    assert _jaccard({'a'}, {'b'}) == 0.0


def test_jaccard_empty_sets_returns_one():
    """两个空集 → 1.0（约定）。"""
    assert _jaccard(set(), set()) == 1.0


def test_jaccard_one_empty_returns_zero():
    """一个空一个非空 → 0.0。"""
    assert _jaccard(set(), {'a'}) == 0.0
    assert _jaccard({'a'}, set()) == 0.0


def test_overlap_coefficient_subset_returns_one():
    """子集关系 → overlap = 1.0（比 Jaccard 更宽容）。"""
    assert _overlap_coefficient({'a', 'b'}, {'a', 'b', 'c'}) == 1.0


def test_overlap_coefficient_empty_sets_returns_one():
    """两个空集 → 1.0。"""
    assert _overlap_coefficient(set(), set()) == 1.0


def test_overlap_coefficient_one_empty_returns_zero():
    """一个空 → 0.0。"""
    assert _overlap_coefficient(set(), {'a'}) == 0.0
    assert _overlap_coefficient({'a'}, set()) == 0.0


# ════════════════════════════════════════════════
# _semantic_diversity（公式 A3）
# ════════════════════════════════════════════════


def test_semantic_diversity_empty_returns_one():
    """空 items → H=1.0。"""
    assert _semantic_diversity([]) == 1.0


def test_semantic_diversity_same_strings_returns_zero():
    """完全相同字符串 → H=0（聚为 1 类）。"""
    h = _semantic_diversity(['探索者', '探索者', '探索者'])
    assert h == 0.0


@pytest.mark.parametrize("items", [
    (['我是探索者', '我是创造探索者']),
    (['我是一个创新者', '我是一个自主创新的创造者']),
    (['探索新世界的科学家', '探索未知世界的科学工作者']),
])
def test_semantic_diversity_similar_strings_cluster(items):
    """语义相似字符串应聚为 1 类 → H=0。"""
    h = _semantic_diversity(items)
    assert h == 0.0, f"items {items} should cluster to 1, got H={h}"


def test_semantic_diversity_different_strings_nonzero():
    """语义无关字符串 → H > 0（多个 cluster）。"""
    h = _semantic_diversity([
        '探索宇宙的科学家', '烹饪美食的厨师', '演奏音乐的艺术家',
    ])
    assert h > 0


def test_semantic_diversity_25_unique_two_chars_clamps_to_one():
    """25 个完全不同 2-char 字符串 → clamp to 1.0。"""
    h = _semantic_diversity([
        'ab', 'cd', 'ef', 'gh', 'ij', 'kl', 'mn', 'op', 'qr', 'st',
        'uv', 'wx', 'yz', 'AB', 'CD', 'EF', 'GH', 'IJ', 'KL', 'MN',
        'OP', 'QR', 'ST', 'UV', 'WX',
    ])
    assert h == 1.0


def test_semantic_diversity_threshold_zero_clusters_all():
    """threshold=0 → 所有 item 聚为 1 类 → H=0（第一个 item 必被采纳）。"""
    h = _semantic_diversity(['A', 'B', 'C', 'D', 'E'], threshold=0.0)
    # 注：第一个 item 永远新建 cluster；后续 item 与 cluster center 比较 overlap。
    # threshold=0 时 max_sim >= 0 永远成立 → 全部并入第一个 cluster → H=0
    assert h == 0.0


def test_semantic_diversity_threshold_one_separates_all_unique():
    """threshold=1 → 各自成 cluster（除非完全相同）。"""
    h = _semantic_diversity(['A', 'A', 'B'], threshold=1.0)
    # 'A','A' → 1 cluster；'B' → 与 'A' 的 overlap=0 < 1.0 → 新 cluster → 2 clusters
    # (2-1)/(20-1) ≈ 0.0526
    assert h > 0.0


def test_semantic_diversity_n_max_less_than_two_raises():
    """n_max < 2 → ValueError。"""
    with pytest.raises(ValueError, match='n_max must be >= 2'):
        _semantic_diversity(['A', 'B'], n_max=1)


def test_semantic_diversity_threshold_out_of_range_raises():
    """threshold ∉ [0, 1] → ValueError。"""
    with pytest.raises(ValueError, match='threshold must be in'):
        _semantic_diversity(['A', 'B'], threshold=1.5)


# ════════════════════════════════════════════════
# entropy_reduction_rate
# ════════════════════════════════════════════════


def test_entropy_reduction_rate_basic():
    """(1.0, 0.6) → 0.4。"""
    assert abs(entropy_reduction_rate(1.0, 0.6) - 0.4) < 1e-9


def test_entropy_reduction_rate_zero_to_zero():
    """(0, 0) → 0.0。"""
    assert entropy_reduction_rate(0.0, 0.0) == 0.0


def test_entropy_reduction_rate_negative_drop():
    """entropy 上升 → 负值（公式 (h_start - h_end) / h_start）。"""
    # (0.3 - 0.5) / 0.3 = -2/3 ≈ -0.6667
    assert abs(entropy_reduction_rate(0.3, 0.5) - (-2/3)) < 1e-9


def test_entropy_reduction_rate_full_drop():
    """(1.0, 0.0) → 1.0。"""
    assert entropy_reduction_rate(1.0, 0.0) == 1.0


# ════════════════════════════════════════════════
# compute_self_entropy
# ════════════════════════════════════════════════


class _FakeVL:
    def __init__(self, vs):
        self.value_state = vs

    def to_vec(self):
        return list(self.value_state.values())


class _FakeIdentity:
    def __init__(self, identities):
        self.identity_history = [{'identity': i} for i in identities]


class _FakeNarrative:
    def __init__(self, narratives):
        self.narrative_history = [{'narrative': n} for n in narratives]


def _make_vl() -> _FakeVL:
    return _FakeVL({
        'safety': 0.8, 'creativity': -0.5, 'connection': 0.3,
        'autonomy': 0.0, 'justice': 0.6, 'compassion': -0.2,
    })


def test_compute_self_entropy_returns_all_keys():
    """返回 dict 含 H_self / H_value / H_identity / H_narrative / weights / method。"""
    result = compute_self_entropy(
        _make_vl(),
        _FakeIdentity(['探索者'] * 5),
        _FakeNarrative(['叙事A'] * 5),
    )
    assert 'H_self' in result
    assert 'H_value' in result
    assert 'H_identity' in result
    assert 'H_narrative' in result
    assert 'weights' in result
    assert 'method' in result


def test_compute_self_entropy_all_h_in_unit_interval():
    """所有 H_* 字段都在 [0, 1]。"""
    cases = [
        (_make_vl(), _FakeIdentity(['探索者'] * 5), _FakeNarrative(['叙事A'] * 5)),  # stable
        (_make_vl(), _FakeIdentity(['A', 'B', 'C', 'D', 'E']), _FakeNarrative(['n1', 'n2', 'n3', 'n4', 'n5'])),  # wobbly
        (_make_vl(), _FakeIdentity([f'id_{i}' for i in range(25)]), _FakeNarrative([f'n_{i}' for i in range(25)])),  # divergent
        (_make_vl(), None, None),  # unformed
    ]
    for vl, il, nb in cases:
        r = compute_self_entropy(vl, il, nb)
        for key in ('H_self', 'H_value', 'H_identity', 'H_narrative'):
            assert 0.0 <= r[key] <= 1.0, f"{key} out of range: {r[key]}"


def test_compute_self_entropy_stable_identity_low_entropy():
    """固化身份（5 个相同字符串） → H_identity = 0.0。"""
    result = compute_self_entropy(
        _make_vl(),
        _FakeIdentity(['探索者'] * 5),
        _FakeNarrative(['叙事A'] * 5),
    )
    assert result['H_identity'] == 0.0


def test_compute_self_entropy_unformed_returns_one():
    """无 identity / narrative → H_identity = H_narrative = 1.0。"""
    result = compute_self_entropy(_make_vl(), None, None)
    assert result['H_identity'] == 1.0
    assert result['H_narrative'] == 1.0


def test_compute_self_entropy_wobbly_uses_semantic_clustering():
    """A/B/C/D/E 5 unique bigram 不同 → 各自成 cluster → (5-1)/19 ≈ 0.2105。"""
    result = compute_self_entropy(
        _make_vl(),
        _FakeIdentity(['A', 'B', 'C', 'D', 'E']),
        _FakeNarrative(['n1', 'n2', 'n3', 'n4', 'n5']),
    )
    # 'A','B','C','D','E' 都是 1 char → 各自的 bigram = {char} → overlap = 1.0 → 聚为 5 类
    assert abs(result['H_identity'] - 4 / 19) < 1e-9


def test_compute_self_entropy_divergent_bigram_overlap_clamps():
    """25 个 id_X 因 '_X' 后缀重复 → 聚为 1 类 → H=0。"""
    result = compute_self_entropy(
        _make_vl(),
        _FakeIdentity([f'id_{i}' for i in range(25)]),
        _FakeNarrative([f'n_{i}' for i in range(25)]),
    )
    # 'id_0' 和 'id_1' 的 bigram 有重叠 {'d_', '_0' vs '_1'}
    # 但 overlap coefficient 是 |intersection| / min(len_a, len_b)
    # 'id_0' bigrams = {'id', 'd_', '_0'} (3 个)；'id_1' = {'id', 'd_', '_1'} (3 个)
    # overlap = |{'id', 'd_'}| / min(3,3) = 2/3 = 0.667 ≥ 0.5 → 聚为同 cluster
    assert result['H_identity'] == 0.0


def test_compute_self_entropy_weights_parameter():
    """weights 参数生效（设置 w_i=1 → H_self 应主要受 H_identity 影响）。"""
    r_equal = compute_self_entropy(
        _make_vl(),
        _FakeIdentity(['A', 'B', 'C', 'D', 'E']),
        _FakeNarrative(['X', 'Y', 'Z']),
        weights=(0.4, 0.3, 0.3),
    )
    r_identity_only = compute_self_entropy(
        _make_vl(),
        _FakeIdentity(['A', 'B', 'C', 'D', 'E']),
        _FakeNarrative(['X', 'Y', 'Z']),
        weights=(0.0, 1.0, 0.0),
    )
    # identity-only 权重下 H_self 应等于 H_identity
    assert abs(r_identity_only['H_self'] - r_equal['H_identity']) < 1e-9


def test_compute_self_entropy_value_layer_with_to_vec():
    """value_layer 有 to_vec() → 使用 to_vec。"""
    vl = _FakeVL({'a': 0.5, 'b': -0.5, 'c': 0.3, 'd': -0.3, 'e': 0.1, 'f': -0.1})
    result = compute_self_entropy(vl)
    assert 'H_value' in result


def test_compute_self_entropy_value_layer_dict_input():
    """value_layer 为 dict → 使用 .values()。"""
    result = compute_self_entropy({'a': 0.5, 'b': -0.5, 'c': 0.3, 'd': -0.3, 'e': 0.1, 'f': -0.1})
    assert 'H_value' in result


def test_compute_self_entropy_v5_real_identities_clusters_low_h():
    """v5 真实 identity 数据集（含"创造""连接""自主""探索者"等共同词）→ 公式 A3 聚类 H < 0.5。"""
    v5_identities = [
        '我是一个以创意为驱动、自主探索新方向、并在团队中实现价值的创新者。',
        '我是一个以创意为核心、以连接为使命、以自主为态度的存在。',
        '我是一个在意义与连接中寻找位置、靠创造力与共情开拓道路的人。',
        '我是一个以创造与连接为核心、在世界中留下独特印记的探索者。',
        '我是一个以创造、连接与自主为支柱、不断在世界中寻找意义的探索者。',
        '我是一个以创意为引擎、以连接为意义、以自主为底色的存在。',
        '我是一个以创造和连接为骨、以自主为翼、在世界中不断寻找意义的存在。',
        '我是一个以创造、连接与自主为锚、在世界中不断寻找意义坐标的探索者。',
        '我是一个以创造、连接与自主为底层动力、在世界中寻找独特意义的存在。',
        '我是一个以创造、连接与自主为底层结构、同时在正义与慈悲之间寻找平衡点的探索者。',
        '我是一个以创造、连接与自主为底层结构、不断在世界中寻找意义与位置的探索者。',
        '我是一个以创造、连接与自主为底层结构、在世界中寻找意义与独特印记的探索者。',
    ]
    h = _semantic_diversity(v5_identities)
    # 12 个 v5 identity 因包含共同关键词 → 公式 A3 聚类后 cluster 数少 → H < 0.5
    assert h < 0.5, f"v5 H={h} 偏高（聚类效果不佳）"


def test_compute_self_entropy_method_field_a3():
    """method 字段标识使用公式 A3。"""
    result = compute_self_entropy(_make_vl())
    assert result['method'] == 'A3-semantic-clustering'


def test_compute_self_entropy_weights_field_matches_input():
    """weights 字段返回传入的权重元组。"""
    custom_weights = (0.5, 0.3, 0.2)
    result = compute_self_entropy(_make_vl(), weights=custom_weights)
    assert result['weights'] == custom_weights


def test_compute_self_entropy_default_weights():
    """默认 weights = (0.4, 0.3, 0.3)。"""
    result = compute_self_entropy(_make_vl())
    assert result['weights'] == DEFAULT_WEIGHTS


def test_compute_self_entropy_semantic_threshold_parameter():
    """semantic_threshold 参数影响 H_identity 聚类。"""
    # 高阈值 → 倾向分多个 cluster
    r_high = compute_self_entropy(
        _make_vl(),
        _FakeIdentity(['我是探索者', '我是创造探索者']),
        semantic_threshold=0.99,
    )
    # 低阈值 → 倾向聚为 1 个 cluster
    r_low = compute_self_entropy(
        _make_vl(),
        _FakeIdentity(['我是探索者', '我是创造探索者']),
        semantic_threshold=0.01,
    )
    assert r_low['H_identity'] <= r_high['H_identity']


def test_compute_self_entropy_h_self_is_weighted_sum():
    """H_self = w_v*H_value + w_i*H_identity + w_n*H_narrative。"""
    weights = (0.4, 0.3, 0.3)
    result = compute_self_entropy(
        _make_vl(),
        _FakeIdentity(['A', 'B', 'C']),
        _FakeNarrative(['X', 'Y', 'Z']),
        weights=weights,
    )
    expected = (weights[0] * result['H_value']
                + weights[1] * result['H_identity']
                + weights[2] * result['H_narrative'])
    assert abs(result['H_self'] - expected) < 1e-9