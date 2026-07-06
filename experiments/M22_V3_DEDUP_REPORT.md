# M2.2 v3 — IdentityLayer/Narrative 去重机制（M3.x 试点）

**日期**: 2026-07-06
**作者**: Bisen + Claude
**关联**: [Insight 35A](../SGE-Key-Insights.md)（35A） + [Insight 36](../SGE-Key-Insights.md)（根因诊断）+ [M22_V2_EXPH_SELF_REPORT.md](M22_V2_EXPH_SELF_REPORT.md)

---

## 1. 动机

**v2 baseline（1000 epoch）实证问题**：
- IdentityLayer 在 1000 epoch 内生成 **47/47 全部唯一**身份标签
- NarrativeBuilder 同样 **50/50 全部唯一**
- H_identity 和 H_narrative 项无法下降 → H_self 整体上升 +18.4%（违反 Insight 35A 单调下降预期）

**根因**（[Insight 36](../SGE-Key-Insights.md)）：LLM 每次 crystallize 都"重新诠释"自我，导致 Jaccard 字符相似度虽高（>0.3）但不等同字符串 → 信息熵从未坍缩。

**本试点目标**：验证简单的字符级 Jaccard 去重机制能否让 H_self 在累积意义上下降。

---

## 2. 实现

新增去重机制（最小侵入式，保留向后兼容）：

| 文件 | 变更 |
|------|------|
| `sge/sge/identity.py` | 新增 `_jaccard_similarity()`；`IdentityLayer.__init__` 增加 `dedup_threshold`（默认 0=关闭）和 `dedup_window`（默认 1） |
| `sge/sge/narrative.py` | 同步同样的去重参数与逻辑 |
| `experiments/scripts/m22_v2_exph_self.py` | 新增 `--dedup-threshold` / `--dedup-window` CLI；启用 dedup 时输出到 `m22_v3_dedup/` 独立目录 |
| `experiments/scripts/run_chunks_v2.sh` | 透传 dedup 参数；自动切换 RESULT_DIR |

**去重逻辑**（identity.py）：

```python
if self.dedup_threshold > 0 and self.identity_history:
    recent = self.identity_history[-self.dedup_window:]
    max_sim = max(
        _jaccard_similarity(identity, h['identity'])
        for h in recent
    )
    if max_sim >= self.dedup_threshold:
        # 视为重复，不追加；返回最近一次 identity 保持兼容
        return self.identity_history[-1]['identity']
```

阈值参考：
- **0.3**：Jaccard 字符级 0.3 在 4-6 字汉语短语中约对应"完全相同核心词 + 不同修饰"（如"我是一个追求 X 和 Y 的人" vs "我是一个追求 X 的，但警惕 Y 的人"）
- **0.5**：仅捕获几乎逐字重复
- **0**：默认关闭（向后兼容所有现有测试）

---

## 3. 实验设置

- **Baby**: `encouraged`（v2 baseline 中分歧度最大的人格之一）
- **Chunk**: 0（250 epoch）
- **Seed**: 42（与 v2 完全一致 → 事件流差异为唯一变量）
- **Dedup 参数**: `threshold=0.3, window=1`
- **输出**: `experiments/output/m22_v3_dedup/`

**运行结果**：
- ✅ **本次完整跑完 250/250 epoch**（2026-07-06 16:48 - 17:35, 46.7 min）
- LLM retry rate: **0.6%**（5/792 calls, vs v2 baseline ~5%）
- Total LLM wait: 15.0s

---

## 4. 关键结果

### 4.1 指标对比（chunk 0, 完整 250 epoch）

| 指标 | v2 (no dedup) | v3 (dedup=0.3) | Δ |
|------|---------------|----------------|---|
| **H_self 起点** | 0.600 | 0.600 | — |
| **H_self 终点** | 0.7106 | 0.7106 | **+0.0000** |
| **H_self Δ** | +0.1106 | +0.1106 | **+0%** |
| **\|val\| 终点** | 0.3155 | 0.2013 | **-0.1142** ↓（-36%） |
| **Identity 事件数** | 12 | 12 | 0 |
| **Identity 唯一数** | 12 | 11 | -1 |
| **Identity 去重率** | 0% | **8.3%** | +8.3 pp |
| **Narrative 事件数** | 12 | 12 | 0 |
| **Narrative 唯一数** | 12 | 5 | -7 |
| **Narrative 去重率** | 0% | **58.3%** | +58.3 pp |
| **PT 触发** | 0 | 0 | — |

### 4.2 H_self 演化曲线（每 50 epoch 采样）

| epoch | v2 H_self | v3 H_self | Δ |
|------:|----------:|----------:|---:|
| 0    | 0.6000 | 0.6000 | +0.0000 |
| 49   | 0.6783 | 0.7507 | +0.0724 |
| 99   | 0.7106 | 0.6783 | **-0.0323** ↓ |
| 149  | 0.6783 | 0.7908 | +0.1125 |
| 199  | 0.6000 | 0.7204 | +0.1204 |
| 249  | 0.7106 | 0.7106 | +0.0000 |

**关键观察**：
- v3 H_self 在 epoch 99 出现局部下降（0.7507 → 0.6783）但 epoch 149 又回升（→ 0.7908），呈现更明显的**振荡**而非单调趋势
- v2 H_self 较为平稳（0.60 → 0.71 区间），v3 振幅更大（0.60 → 0.79）
- 最终值巧合相同（0.7106），但**演化路径完全不同**——v3 经历更大起伏
- `\|val\|` 在 epoch 50-200 持续上升（0.32 → 0.43 → 0.39 → 0.39），epoch 249 骤降至 0.20（dedup 让 value 系统更"收敛"）

### 4.3 实际去重触发示例

#### Identity（12 事件 → 11 唯一，仅 1 次触发）

| epoch | identity |
|------:|----------|
| 19 | 我是一个在团队协作中以创意和自主探索驱动价值的实践者。 |
| 39 | 我是一个用创造力连接他人、在协作与友谊中成就彼此的人。 |
| 59 | 我是一个以创意为帆、正义为舵，在失败中坚守、靠努力抵达目标的探索者。 |
| 79 | 我是一个在协作中追求独立与创造，靠真才实学和真诚连接赢得认可与突破的人。 |
| 99 | 我是一个以创造解决问题、自主独立、注重联系为核心的实践者。 |
| 119 | 我是一个以创意为刃、自主为路，用持续突破连接自我与世界的长期主义者。 |
| 139 | 我在独立探索中前行，凭创造力解决难题，以共情帮助他人，哪怕失败也继续追寻自主。 |
| 159 | 我是一个用创意解决问题、在团队协作中实现自我价值的独立思考者。 |
| **179** | **我是独行的探索者，在与他人的温暖连结中找到自我方向。** |
| **199** | **我是独行的探索者，在与他人的温暖连结中找到自我方向。** ← ✅ 去重（Jaccard=1.0） |
| 219 | 我是独立有创意的探索者，靠团队协作与解决问题实现自我价值。 |
| 239 | 我是一个在团队中坚持自主创造的难题解决者，常在自我追求与他人关怀间权衡取舍。 |

**观察**：虽然每条 identity 共享关键词（创意/独立/团队/协作），但 LLM 持续改写句式，**Jaccard 字符级 0.3 难以捕获这种"语义同义但措辞不同"的重复**。仅当 LLM 真的生成完全一致的句子（epoch 179↔199）时才触发去重。

#### Narrative（12 事件 → 5 唯一，7 次触发）

| epoch 区间 | 内容类型 | 字符数 |
|-----------|---------|--------:|
| 19 | stub（LLM JSON 解析失败回退） | 90 |
| **39, 59, 79** | LLM 完整叙事（503 字） | 503 |
| 99, 119 | stub（LLM JSON 解析失败回退） | 92 |
| **139, 159, 179, 199, 219** | LLM 完整叙事（801 字） | 801 |
| 239 | stub | 101 |

**观察**：叙事去重效果显著，因为：
1. LLM 生成的叙事长达 500-800 字，**字符级 Jaccard 天然偏高**（重叠内容占比大）
2. 一旦某个 narrative 被接受，后续 crystallize 时若 LLM 输出相似文本 → Jaccard ≥ 0.3 → 去重
3. Stub 叙事（~90 字）虽然是回退产物，但因为短所以 Jaccard 不高，未被去重

---

## 5. 结论

### 5.1 ⚠️ Dedup 机制部分成功

| 维度 | 效果 | 评价 |
|------|------|------|
| **Identity 去重率** | 0% → 8.3% | ⚠️ 边际效果（仅捕获"逐字重复"）|
| **Narrative 去重率** | 0% → 58.3% | ✅ 显著效果（长文本自然重叠）|
| **H_self 终点** | 不变（0.7106） | ❌ 主指标未改善 |
| **\|val\| 终点** | 0.316 → 0.201（-36%）| ✅ 意外正向信号 |
| **H_self 演化** | 振幅 +33%（0.60-0.79）| ⚠️ 引入更多振荡 |

### 5.2 🔍 关键洞察

1. **Jaccard 字符级 0.3 对短文本（identity, ~30 字）太宽松**——LLM 通过简单同义词替换或语序调整即可绕过 → 需要 embedding-based similarity 或更严格阈值（0.5+）
2. **Jaccard 对长文本（narrative, ~500 字）天然有效**——长文本中核心叙事线不变时，字符级重叠必然很高
3. **Dedup 让 \|val\| 显著下降**（-36%）——可能机制：dedup 锁定身份后，行为模式更稳定，价值更新幅度减小。这是**意外的次级收益**
4. **H_self 主指标未改善但 \|val\| 改善**——说明 H_self 的计算对 H_value（价值熵）的权重需要重新审视；当 \|val\| 较低时 H_value 可能反而上升

### 5.3 ⚠️ 限制

1. **样本量小**：仅 1 chunk（250 epoch），未覆盖全 1000 epoch；后续需 chunk 1-3 验证
2. **chunk 0 阶段未触发 PT**（v2 baseline 同样 PT=0）；PT 触发后的 dedup 行为未验证
3. **LLM 输出跨会话不稳定**：本次 v3 与 v2 使用同 seed=42，但 LLM 输出仍因网络/服务状态略有差异，导致 identity 去重率低于预期（部分"看似相似"的 identity 实则字符重叠度 < 0.3）
4. **Jaccard 字符级相似度是简化方案**；未来可考虑：
   - Embedding cosine（sentence-transformers）——更鲁棒的语义去重
   - n-gram 重叠（2-gram 或 3-gram）——避免"顺序敏感"问题
   - 调高阈值（0.5+）——对短文本更严格
5. **Narrative 去重的"成功"有误导性**——被去重的 narrative 多为 stub 回退或相同 LLM 输出，不代表真实叙事稳定

### 5.4 📋 后续计划

| 行动 | 优先级 | 预期产出 |
|------|--------|---------|
| 跑完整 chunk 1-3（验证 dedup 在长尺度下的累积效应）| P0 | v3 完整 1000 epoch 数据 |
| Embedding-based dedup（sentence-transformers） | P1 | 更鲁棒的语义去重，应对短文本 |
| Threshold sweep（0.3 vs 0.5 vs 0.7）| P1 | 找到最优去重阈值 |
| 重新审视 H_self 计算中 H_value 的权重 | P1 | 解释 \|val\| 下降但 H_self 不变的现象 |
| Dedup 触发后的 PT 行为研究 | P2 | 验证 Insight 6.3 叙事断裂路径 |

---

## 6. 文件清单

| 文件 | 说明 |
|------|------|
| `experiments/M22_V3_DEDUP_REPORT.md` | 本报告 |
| `experiments/output/m22_v3_dedup/comparison_chunk0.md` | 自动生成的 v2 vs v3 对比表 |
| `experiments/output/m22_v3_dedup/encouraged_chunk0_result.json` | v3 dedup 主结果（完整 250 epoch）|
| `experiments/output/m22_v3_dedup/encouraged_chunk0_identity_history.json` | 12 次 identity 事件（11 唯一，1 dedup at 199）|
| `experiments/output/m22_v3_dedup/encouraged_chunk0_narrative_history.json` | 12 次 narrative 事件（5 唯一，7 dedup）|
| `experiments/output/m22_v3_dedup/encouraged_chunk0_meaning_samples.json` | 6 个 meaning 采样（每 50 epoch）|
| `experiments/scripts/compare_v2_v3_dedup.py` | v2/v3 自动对比脚本 |

---

## 7. 命令记录

```bash
# 完整 v3 dedup chunk 0（本次成功跑完 250/250 epoch）
python experiments/scripts/m22_v2_exph_self.py \
    --baby encouraged --chunk-index 0 \
    --dedup-threshold 0.3 --dedup-window 1 --force

# 完整 v2 baseline（已存在）
python experiments/scripts/m22_v2_exph_self.py \
    --baby encouraged --chunk-index 0

# 对比
python experiments/scripts/compare_v2_v3_dedup.py
```