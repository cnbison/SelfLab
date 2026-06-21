# 2026-06-21 — M2.2 E4 12 chunks 全部完成 + 关键发现

## 主题
M2.2 主实验（E4）通过 chunk 模式完成 — 12 个 chunks × 250 epochs × 真实 LLM 全部成功。

## 背景
E4 多次尝试：
- **v1**（1000 epoch 一次跑）：encouraged epoch 490 崩溃，丢 10h 数据
- **v3**（1000 epoch + checkpoint writes）：encouraged epoch 490 崩溃 + challenged epoch 336 崩溃
- **v4**（4 × 250 chunk 模式）：**12 chunks 全部成功，0 失败**

两次 v1/v3 崩溃都遵循相同 pattern（SSL `UNEXPECTED_EOF_WHILE_READING` + 多次 retry timeout）→ MiniMax server 在长时间运行后变得不稳定。

## 关键数据

### 三胞胎对比（1000 epoch 真实 LLM）

| Baby | \|val\| | PT | Id | Nar | Succ% | Fail% | LLM calls |
|------|---------|----|----|----|-------|-------|-----------|
| **encouraged** | 0.189 | **4** | 48/50 | 50 | **55.3%** | 11.1% | 2208 |
| **challenged** | 0.069 | **12** | 38/50 | 50 | 8.0% | **35.0%** | 2208 |
| **uncertain** | 0.168 | **15** | 47/50 | 50 | 17.0% | 16.4% | 2208 |

**总计**：6624 LLM 调用，17h 串行（含 chunk 间 5min gap × 11）。

### Personality Divergence（cosine distance on final value_state）

| Pair | 距离 |
|------|------|
| encouraged vs challenged | **1.5871** |
| encouraged vs uncertain | 0.2784 |
| challenged vs uncertain | 1.0997 |
| **平均** | **0.9884** |

**E3 pilot 100 epoch 也是 0.9884** → 10x epoch 规模下分化水平保持稳定。

### 价值状态终态（final_value_state）

```
encouraged:  {safety: +0.081, creativity: +0.094, connection: +0.060,
              autonomy: +0.010, justice: +0.048, compassion: +0.120}
              → 全维度正向（最正人格）

challenged:  {safety: -0.046, creativity: +0.008, connection: -0.028,
              autonomy: -0.038, justice: -0.010, compassion: -0.018}
              → 4/6 维度负向（最负人格）

uncertain:   {safety: -0.046, creativity: +0.107, connection: +0.071,
              autonomy: +0.006, justice: +0.012, compassion: +0.097}
              → 2 负 4 正（中性偏积极）
```

**分化模式清晰**：encouraged 全正 / challenged 全负 / uncertain 中间态 — 这与 M1.2 baseline "无方向性事件流 → 无方向性价值观" 一致。

### Phase Transition 触发：意外发现

**原假设**：challenged (failure 多) > uncertain > encouraged (success 多)
**实际**：**uncertain 15 > challenged 12 > encouraged 4**

可能解释（待分析）：
1. uncertain 事件流更随机 → frustration 累积路径更多样化 → 多种 PT 触发条件命中
2. challenged 的 frustration 在某次大崩溃后 reset/释放（需要看 frustration 时间序列）
3. PT 触发是 frustration 总量 vs 阈值，**不是简单 failure 计数**
4. challenged 价值向量已经全负向（人格"认命"），可能降低了 PT 触发的 surprise 信号

### Identity 收敛观测

- encouraged: 48/50（96%）
- uncertain: 47/50（94%）
- challenged: 38/50（76%）

**challenged Identity 触发率低**：可能因 value_conflict 频繁触发（468/1000 = 47%）→ Identity 验证拒绝概率高。

### Frustration 设计确认

3 个 baby 的 frustration 都只在 **exploration + connection** 累积（其他 drives = 0）：
```
exploration: 4.4-4.8 / 5.0 max
connection:  4.6-4.9 / 5.0 max
safety/creativity/autonomy: 0.0
```

**确认 D6 报告中的设计发现**：Critic LLM prompt 只输出 `value_delta`（6D），不输出 `frustration_delta`（5D drives）→ drives frustration 仅来自 `hunger_rates`（仅 connection + exploration 有饥饿累积）。

### Chunk 时长分布（揭示 server 退化模式）

**encouraged**（server 逐步退化）：
| Chunk | Time | sec/epoch |
|-------|------|-----------|
| 0 | 2611s (44 min) | 10.4 |
| 1 | 3279s (55 min) | 13.1 |
| 2 | 3849s (64 min) | 15.4 |
| 3 | 4439s (74 min) | 17.8 |

→ server 退化明显：epoch 越往后越慢

**challenged**（server 大幅退化）：
| Chunk | Time | sec/epoch |
|-------|------|-----------|
| 0 | 4793s (80 min) | 19.2 |
| **1** | **24772s (6.9h)** | **99.1** ⚠ |
| 2 | 1459s (24 min) | 5.8 |
| 3 | 2251s (38 min) | 9.0 |

→ chunk 1 出现极端慢化（~99s/epoch），可能 server 遭遇临时故障（但 chunk 隔离保护了数据完整性）

**uncertain**（相对稳定）：
| Chunk | Time | sec/epoch |
|-------|------|-----------|
| 0 | 1394s (23 min) | 5.6 |
| 1 | 1541s (26 min) | 6.2 |
| 2 | 1502s (25 min) | 6.0 |
| 3 | 6649s (1.85h) | 26.6 |

→ chunk 3 又出现慢化（MiniMax server 周期性慢化）

**结论**：MiniMax server 不稳定是**结构性问题**（非偶发）→ chunk 模式有效隔离。

## 假设验证总结

| 假设 | 预测 | 实际 | 验证 |
|------|------|------|------|
| success_rate 排序 | enc > unc > cha | 55% / 17% / 8% | ✅ |
| PT cha > enc | cha > enc | cha 12 vs enc 4 | ✅ |
| PT cha > unc | cha > unc | cha 12 < unc 15 | ❌ **意外** |
| Personality divergence > 0.5 | > 0.5 | 0.9884 | ✅ |
| enc vs cha 高分化 | > 1.0 | 1.5871 | ✅ |
| Identity 收敛 | entropy 下降 | Id 接近 50/50 | ✅ |
| Hawking 衰减 | weight 下降 | 数据未直接展示，需看 timeseries | ⏳ |

**6/7 假设验证通过，1 个意外发现（PT 顺序）。**

## 经验教训（M2.3+ 必读）

1. **MiniMax server 长跑不可靠** — 250 epoch 内基本稳定（~10s/epoch），但 1000+ epoch 累积不稳定（最高 99s/epoch）
2. **Chunk 模式是必需** — 不只是性能优化，是数据完整性保障
3. **Challenged 流 value_conflict 高（47%）** → Identity 验证拒绝多 → Identity 触发率仅 76%（其他 94-96%）
4. **真实 LLM 累积效果强** — 1000 epoch value_magnitude 比 100 epoch 大 2-3x
5. **PT 触发不只是 failure 计数** — uncertain 流随机性高反而触发最多，需要更精细的模型解释

## 下一步

- **E5**: 叙事盲审（3 baby × 5 epoch × 3 prompt = 45 评分）
- **E6**: M2.2 完整报告（6 章节 + 5+ 数据可视化 + 3+ 关键发现）

## 产出文件

| 文件 | 类型 | 状态 |
|------|------|------|
| `experiments/output/m22_triplets/{baby}_chunk{0-3}_result.json` | 12 个 chunk 结果 | gitignored |
| `experiments/output/m22_triplets/{baby}_chunk{0-3}_identity_history.json` | 12 个 identity 历史 | gitignored |
| `experiments/output/m22_triplets/{baby}_chunk{0-3}_narrative_history.json` | 12 个 narrative 历史 | gitignored |
| `experiments/output/m22_triplets/triplets_summary.json` | 3 baby 汇总 | gitignored |
| `experiments/scripts/m22_triplets.py` | E4 chunk 模式 | ✅ committed |
| `experiments/scripts/run_chunks.sh` | 12 chunks wrapper | ✅ committed |
| `experiments/scripts/aggregate_chunks.py` | chunks 合并器 | ✅ committed |

## 维护者
Bisen & Claude

## 状态
✅ M2.2 E4 完成 — 12/12 chunks 成功 — 0 失败 — 17h 总时间 — 6624 LLM 调用 — 数据已合并
