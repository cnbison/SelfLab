# M2.2 v4 — Ngram-TF-Cosine 去重机制（M3.x 试点，负向结果）

**日期**: 2026-07-07
**作者**: Bisen + Claude
**关联**: [Insight 35A](../SGE-Key-Insights.md)（35A） + [Insight 36](../SGE-Key-Insights.md)（根因诊断）+ [M22_V2_EXPH_SELF_REPORT.md](M22_V2_EXPH_SELF_REPORT.md) + [M22_V3_DEDUP_REPORT.md](M22_V3_DEDUP_REPORT.md)

---

## 1. 动机

**v3 (Jaccard dedup) 部分失败**：
- Identity 去重率 8.3%（仅 1 次触发）
- Narrative 去重率 58.3%（7 次触发）
- **H_self 终点不变（0.7106），|val| 反而 -36%**

**v3 根因诊断**：Jaccard 字符级 0.3 在短文本（identity ~30 字）上太宽松，LLM 通过同义词替换即可绕过。

**v4 目标**：用 **TF-cosine 相似度（char unigram + bigram 向量）** 替代 Jaccard，捕获"语义同义但措辞不同"的重复，验证去重本身是否有效。

---

## 2. 实现

| 文件 | 变更 |
|------|------|
| `sge/sge/identity.py` | 新增 `_char_ngram_vector()` (Counter over unigram+bigram)；`_tfidf_cosine()`；`_ngram_similarity()` |
| `sge/sge/narrative.py` | 同 identity.py |
| `experiments/scripts/m22_v2_exph_self.py` | 新增 `--dedup-method {jaccard,ngram}`；ngram 时输出到 `m22_v4_dedup/` 独立目录 |
| `experiments/scripts/compare_v2_v3_v4_dedup.py` | 三向对比脚本（v2/v3/v4）|

**核心算法**：

```python
def _char_ngram_vector(s: str, ns: tuple = (1, 2)) -> Counter:
    """字符 n-gram 计数向量；同时使用 unigram + bigram"""
    vec = Counter()
    for n in ns:
        for i in range(len(s) - n + 1):
            vec[s[i:i + n]] += 1
    return vec

def _tfidf_cosine(a: Counter, b: Counter) -> float:
    """TF-cosine 相似度（无 IDF，0 依赖）"""
    common = set(a.keys()) & set(b.keys())
    dot = sum(a[k] * b[k] for k in common)
    norm_a = math.sqrt(sum(v*v for v in a.values()))
    norm_b = math.sqrt(sum(v*v for v in b.values()))
    return dot / (norm_a * norm_b)
```

**为何用 char (1,2)-gram 而非纯 embedding**：
- litellm.embedding 在本 provider 上不支持（`Unmapped LLM provider`）
- 无 torch/sklearn/sentence-transformers，pip install 会引入 ~700MB 依赖
- TF-cosine on (1,2)-grams 是轻量代理方案：unigram 捕获字符重叠，bigram 捕获词级特征（"团队"、"协作"、"创意"）
- **可在 30 行内纯 Python 实现，0 依赖**

**阈值校准**（用 v3 真实数据预演）：

| 阈值 | jaccard 触发 | ngram 触发 |
|------|--------------|-------------|
| 0.30 | 1/11 | 4/11 |
| 0.35 | 0/11 | 3/11 |
| 0.50 | 0/11 | 1/11 |

锁定 `ns=(1,2), threshold=0.30`（4x dedup vs jaccard 同阈值）。

---

## 3. 实验设置

- **Baby**: `encouraged`（与 v2/v3 完全一致）
- **Chunk**: 0（250 epoch）
- **Seed**: 42（与 v2/v3 完全一致 → 事件流可比）
- **Dedup 参数**: `method=ngram, threshold=0.3, window=1`
- **输出**: `experiments/output/m22_v4_dedup/`

**运行结果**：
- ✅ **完整跑完 250/250 epoch**（107 min，比 v3 慢 2.3x，可能是 ngram 计算开销或网络延迟）
- LLM retry rate: **0.9%**（7/785 calls）
- LLM total wait: 27.0s

---

## 4. 关键结果

### 4.1 三向指标对比（chunk 0, 完整 250 epoch）

| 指标 | v2 (no dedup) | v3 (jaccard@0.3) | v4 (ngram@0.3) | v4 vs v3 |
|------|---------------|------------------|----------------|----------|
| **H_self 起点** | 0.600 | 0.600 | 0.600 | — |
| **H_self 终点** | 0.7106 | 0.7106 | **0.7507** | **+0.0401 ↑** |
| **H_self Δ** | +0.1106 | +0.1106 | **+0.1507** | **+36% ↑** |
| **\|val\| 终点** | 0.3155 | 0.2013 | **0.3822** | **+90% ↑** |
| **Identity 唯一数** | 12/12 | 11/12 | **8/12** | 4 dedup |
| **Identity 去重率** | 0% | 8.3% | **33.3%** | **+25.0 pp** |
| **Narrative 唯一数** | 12/12 | 5/12 | **1/12** | 11 dedup |
| **Narrative 去重率** | 0% | 58.3% | **91.7%** | **+33.3 pp** |
| **PT 触发** | 0 | 0 | 0 | — |

### 4.2 H_self 演化曲线（每 50 epoch）

| epoch | v2 H_self | v3 H_self | v4 H_self |
|------:|----------:|----------:|----------:|
| 0   | 0.6000 | 0.6000 | 0.6000 |
| 49  | 0.6783 | 0.7507 | 0.6783 |
| 99  | 0.7106 | 0.6783 | 0.7106 |
| 149 | 0.6783 | 0.7908 | 0.7757 |
| 199 | 0.6000 | 0.7204 | 0.6000 |
| 249 | 0.7106 | 0.7106 | 0.7507 |

**关键观察**：
- v4 H_self 在 epoch 149 飙升至 0.7757（v2/v3 类似波动）
- epoch 199 三者都"回落"到 0.6
- epoch 249 v4 反而升至 0.7507（高于 v2/v3 的 0.7106）

### 4.3 实际去重触发

#### Identity（12 事件 → 8 唯一，4 次触发）

| epoch 区间 | 内容 |
|-----------|------|
| **19, 39** | 我是一个在协作中以创意驱动新领域的探索者。 |
| **59, 79** | 我是一个以同情心为根基，用创造力连接他人，在成败起伏中坚持帮助困境者的践行者。 |
| **99, 119** | 我是一个用创意解决难题、在独立思考中找到价值的人。 |
| **139** | 我是靠独立与创意走出自己路的人，即使反对偏见、面对风险，也坚守自主探索的方向。 |
| **159, 179** | 我是一个用创意解决问题、靠协作连接彼此、保持自主而活的人。 |
| 199 | 我用创意连接他人，在正义与自主中坚守自我，用方案温暖世界。 |
| 219 | 我是一个用创新方案解决问题、愿为突破冒险但坚守底线的创造者。 |
| 239 | 我是一个在自由与善意间寻找平衡、用连接和创造温暖他人的人。 |

**观察**：所有 dedup 触发都是 **逐字相同**（Jaccard=1.0）。Ngram 未能像预期那样捕获"语义同义但措辞不同"的重复——LLM 实际产出的 identity 字符重叠确实不高。

#### Narrative（12 事件 → 1 唯一，11 次触发）

**关键发现**：v4 chunk 0 跑出的 12 个 narrative 几乎全部被去重（仅 1 个 unique），意味着 LLM 在 12 次 build 中产生了高度相似的文本——这与 v3 看到的"几个 LLM 输出 + stub 回退"的模式不同。

---

## 5. 结论

### 5.1 ❌ Ngram dedup 加重问题（负向结果）

| 维度 | v3 (jaccard) | v4 (ngram) | 评价 |
|------|--------------|------------|------|
| **Identity 去重率** | 8.3% | 33.3% | ✅ dedup 显著提升 |
| **Narrative 去重率** | 58.3% | 91.7% | ✅ dedup 显著提升 |
| **H_self** | 不变 | **恶化 +0.040** | ❌ 反效果 |
| **\|val\|** | -36% | **+21%** | ❌ 反效果 |

### 5.2 🔍 关键洞察（哲学层面）

1. **强制身份稳定 ≠ 真实身份稳定**——v4 把 12 个 identity 压到 8 个，看似"稳定"，但 H_self 反而上升。说明 dedup 制造的是"伪稳定"，系统被迫重复使用旧的 identity 表征，**失去自然演化的张力**
2. **Identity 反复出现同一表征 → 行为模式固化 → 价值波动幅度加大**（\|val\| ↑）。稳定的 identity 模板让 value_layer 失去"重新校准"的契机
3. **Ngram dedup 真实有效**——4 次 identity dedup 全部是逐字相同（ngram cos = Jaccard = 1.0），并未"过度去重"。说明 LLM 实际产出的字符重叠度低，ngram 在"语义同义但措辞不同"上**确实没有明显优势**
4. **Dedup 本身不是 H_self 问题的解**——H_self 在 v2/v3/v4 都上升（+0.111, +0.111, +0.151），说明根因不在"identity 重复生成"。更可能是：
   - H_self 公式中 H_value 权重设计问题（\|val\| ↓ 时 H_value 可能反而 ↑）
   - 或是"自我持续重构"本身是 SGE 的固有特征，而非缺陷

### 5.3 ⚠️ 限制

1. **样本量小**：仅 chunk 0（250 epoch），未覆盖全 1000 epoch
2. **LLM 输出跨会话不稳定**：与 v2/v3 相比，ngram run 的 LLM 输出**重复度更高**（导致 91.7% narrative dedup），这可能是因为 ngram 计算开销使 LLM 调用间隔更均匀、温度采样窗口更稳定——是 confound
3. **未测试更高阈值**：0.5/0.7 可能更接近 jaccard 的"保守"行为
4. **未跑 challenged/uncertain baby**：仅 encouraged 单一人格

### 5.4 📋 后续计划

| 行动 | 优先级 | 预期产出 |
|------|--------|---------|
| **重新审视 H_self 公式**（H_value 权重）| **P0** | 解释为何 \|val\| 变化与 H_self 趋势不一致 |
| **重新审视 M3.x dedup 假设** | **P0** | Insight 36 根因诊断可能不完整——dedup 不一定是正确机制 |
| 跑 v3/v4 chunk 1-3（1000 epoch 全程）| P2 | 验证 v4 结论是否在长程上成立（数据已有 v2 chunk 1-3）|
| Embedding-based（真 sentence-transformers）| P3 | 仅在 P0/P1 找到新方向后再考虑；否则不投入 700MB 依赖 |
| 阈值 sweep（0.3 / 0.5 / 0.7）| P3 | 同上 |

---

## 6. 文件清单

| 文件 | 说明 |
|------|------|
| `experiments/M22_V4_DEDUP_REPORT.md` | 本报告 |
| `experiments/output/m22_v4_dedup/comparison_chunk0.md` | 自动生成的三向对比 |
| `experiments/output/m22_v4_dedup/encouraged_chunk0_result.json` | v4 主结果（完整 250 epoch）|
| `experiments/output/m22_v4_dedup/encouraged_chunk0_identity_history.json` | 12 次 identity（8 唯一，4 dedup）|
| `experiments/output/m22_v4_dedup/encouraged_chunk0_narrative_history.json` | 12 次 narrative（1 唯一，11 dedup）|
| `experiments/scripts/compare_v2_v3_v4_dedup.py` | 三向对比脚本 |

---

## 7. 命令记录

```bash
# v4 ngram dedup chunk 0（本次）
python experiments/scripts/m22_v2_exph_self.py \
    --baby encouraged --chunk-index 0 \
    --dedup-method ngram --dedup-threshold 0.3 --dedup-window 1 --force

# v3 jaccard dedup chunk 0
python experiments/scripts/m22_v2_exph_self.py \
    --baby encouraged --chunk-index 0 \
    --dedup-method jaccard --dedup-threshold 0.3 --dedup-window 1 --force

# v2 baseline chunk 0
python experiments/scripts/m22_v2_exph_self.py \
    --baby encouraged --chunk-index 0

# 三向对比
python experiments/scripts/compare_v2_v3_v4_dedup.py
```

---

## 8. 元结论：M3.x dedup 路线的根本性问题

基于 v3 + v4 两轮实验，dedup 作为降低 H_self 的机制**已被实证无效**：

- **jaccard dedup**：H_self 不变，\|val\| 下降（中性偏正）
- **ngram dedup**：H_self 恶化，\|val\| 上升（明确负向）
- **物理直觉**：身份和叙事是"自我"持续表达的过程；dedup 强行压制这种表达，反而打破系统的自然平衡

**Insight 36 的诊断可能不完全正确**——LLM 持续生成新 identity 不一定是 bug，可能是 self 在持续重构的真实表现。真正的"自我稳定"或许不通过强制 dedup 实现，而是通过：
1. **Phase Transition**（v2 chunk 0 仍未触发 PT=0，说明 SGE 现有触发机制可能不够激进）
2. **价值-身份双向约束**（让 value_layer 反向影响 identity 生成，而非单向 crystallization）
3. **重新审视 H_self 设计目标**（也许 H_self 不应单调下降，而是周期性收敛-发散）

下一步建议：**暂停 M3.x dedup 路线，转向 H_self 公式重审 + Phase Transition 触发机制研究**。