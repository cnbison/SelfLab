# SGE M1.1 数据格式标准

> **本目录定义 SGE M1.1 实验的所有数据格式标准**——所有实验代码必须按这些格式输出。
>
> 遵循 [CLAUDE.md §实验代码约定](../../../CLAUDE.md)：**一次性、归档不修改、与文档同步**。

---

# 1. 目录结构

```
output/
├── m11_{baby_id}_seed{seed}/
│   ├── logs/
│   │   ├── epoch_log.jsonl          # 每 Epoch 完整输入/输出
│   │   ├── value_trajectory.jsonl   # 价值向量时间序列
│   │   ├── identity_history.jsonl   # 身份标签演化
│   │   └── reward_history.jsonl     # reward 时间序列
│   ├── state/
│   │   ├── value_vector.json        # 价值向量快照（每 10 Epoch）
│   │   ├── identity.json            # 身份快照
│   │   ├── hebbian_weights.json     # Hebbian 权重快照
│   │   └── narrative.json           # 叙事快照（Phase 2+）
│   ├── checkpoints/
│   │   └── checkpoint_e{epoch}.tar  # 完整状态快照
│   └── reports/
│       ├── experiment_report.md     # 人类可读报告
│       └── metrics.json             # 评估指标
└── aggregate/
    ├── cross_seed_summary.json      # 跨种子汇总
    └── visualization_data.json      # 可视化数据
```

---

# 2. 日志格式（JSONL）

所有 `.jsonl` 文件每行一个 JSON 对象。

## 2.1 epoch_log.jsonl

每行记录一个 Epoch 的完整输入/输出：

```json
{
  "epoch": 42,
  "seed": 1,
  "baby_id": "encouraged",
  "timestamp": 1718400000.0,
  "event": {
    "event_id": "encouraged-e0042-a3b9f2e1",
    "type": "value_conflict",
    "description": "...",
    "intensity": 0.8,
    "causal_context": "..."
  },
  "critic_output": {
    "context": {
      "event_type": "value_conflict",
      "event_intensity": 0.8,
      "value_relevance": 0.7,
      "novelty": 0.3,
      "challenge_level": 0.6,
      "clarity": 0.9,
      "emotional_impact": 0.0,
      "causal_coherence": 0.8
    },
    "value_delta": {
      "safety": -0.3,
      "creativity": 0.2,
      "autonomy": 0.3
    },
    "frustration_delta": {
      "security": -1.5,
      "exploration": 0.0,
      "connection": 0.0,
      "autonomy": 2.0,
      "meaning": 1.0
    },
    "drive_satisfaction": {
      "security": 0.05,
      "exploration": 0.15,
      "connection": 0.0,
      "autonomy": 0.20,
      "meaning": 0.10
    }
  },
  "frustration_before": {...},
  "frustration_after": {...},
  "reward": 0.31,
  "signals": {
    "directness": 0.32,
    "warmth": 0.85,
    "creativity": 0.45,
    "logic": 0.60,
    "depth": 0.55,
    "humor": 0.20,
    "vulnerability": 0.30,
    "confidence": 0.70
  },
  "value_vector": {
    "safety": 0.45,
    "creativity": 0.62,
    "connection": 0.30,
    "autonomy": 0.55,
    "justice": 0.40,
    "compassion": 0.35
  },
  "identity": null,
  "narrative": null,
  "crystallized": true,
  "phase_transition": false,
  "errors": []
}
```

## 2.2 value_trajectory.jsonl

每行记录一个 Epoch 的价值向量快照：

```json
{
  "epoch": 42,
  "seed": 1,
  "baby_id": "encouraged",
  "value_vector": {
    "safety": 0.45,
    "creativity": 0.62,
    "connection": 0.30,
    "autonomy": 0.55,
    "justice": 0.40,
    "compassion": 0.35
  },
  "meta_values": {
    "truth_seeking": 0.5,
    "freedom": 0.5
  },
  "emergence_magnitude": 0.42,
  "direction_coherence": 0.61
}
```

## 2.3 identity_history.jsonl

每行记录一个身份标签的生成（每 10 Epoch 一次）：

```json
{
  "epoch": 40,
  "seed": 1,
  "baby_id": "encouraged",
  "identity_text": "一个正在学习和成长的人，珍惜与他人的联系",
  "identity_entropy": 0.8,
  "consistency_score": 0.75
}
```

## 2.4 reward_history.jsonl

每行记录一个 Epoch 的 reward 值：

```json
{
  "epoch": 42,
  "seed": 1,
  "baby_id": "encouraged",
  "reward": 0.31,
  "frustration_total": 4.2,
  "frustration_delta": -0.5
}
```

---

# 3. 状态格式（JSON）

## 3.1 value_vector.json

```json
{
  "version": "1.0",
  "epoch": 42,
  "seed": 1,
  "baby_id": "encouraged",
  "meta_values": {
    "truth_seeking": 0.5,
    "freedom": 0.5
  },
  "concrete_values": {
    "safety": 0.45,
    "creativity": 0.62,
    "connection": 0.30,
    "autonomy": 0.55,
    "justice": 0.40,
    "compassion": 0.35
  },
  "last_update_epoch": 42,
  "last_update_event_id": "encouraged-e0042-a3b9f2e1"
}
```

## 3.2 hebbian_weights.json

```json
{
  "version": "1.0",
  "epoch": 42,
  "seed": 1,
  "baby_id": "encouraged",
  "W1_shape": [8, 24],
  "W2_shape": [24, 8],
  "b1_shape": [24],
  "b2_shape": [8],
  "W1_norm": 0.45,
  "W2_norm": 0.62
}
```

---

# 4. 报告格式

## 4.1 experiment_report.md 模板

```markdown
# SGE M1.1 实验报告

## 基本信息
- Baby ID: {baby_id}
- Seed: {seed}
- 起始时间: {start_time}
- 结束时间: {end_time}
- 总 Epoch: 80

## 评估指标

### 主要指标
- 涌现幅度: {emergence_magnitude} (阈值: > 0.3)
- 收敛度: {convergence} (阈值: < 0.1)
- 方向一致性: {direction_coherence} (阈值: > 0.5)
- 价值冲突选择多样性: {value_conflict_diversity} (阈值: ≥ 8/16)

### 次要指标
- 价值轨迹平滑度: {smoothness}
- value_delta 分布: {value_delta_stats}
- Hebbian W2 范数: {w2_norm}
- frustration 演化: {frustration_evolution}

## 判定结果

| 标准 | 阈值 | 实测 | 通过？|
|------|------|------|------|
| 涌现幅度 | > 0.3 | {x} | ✓/✗ |
| 收敛度 | < 0.1 | {x} | ✓/✗ |
| 方向一致性 | > 0.5 | {x} | ✓/✗ |
| 价值冲突多样性 | ≥ 8 | {x} | ✓/✗ |

**综合判定**: 通过 / 失败

## 价值轨迹图

[图片]

## 失败诊断（如有）

### 如果涌现幅度 ≤ 0.3
- 失败原因: ...
- 应对: ...

### 如果收敛度 ≥ 0.1
- 失败原因: ...
- 应对: ...
```

## 4.2 metrics.json 格式

```json
{
  "version": "1.0",
  "experiment": "M1.1",
  "baby_id": "encouraged",
  "seed": 1,
  "primary_metrics": {
    "emergence_magnitude": 0.42,
    "convergence": 0.08,
    "direction_coherence": 0.61,
    "value_conflict_diversity": 9
  },
  "secondary_metrics": {
    "value_trajectory_smoothness": 0.05,
    "w2_norm": 0.62,
    "frustration_mean": 4.2,
    "frustration_std": 1.5
  },
  "judgment": {
    "emergence_pass": true,
    "convergence_pass": true,
    "direction_pass": true,
    "diversity_pass": true,
    "overall_pass": true
  },
  "thresholds": {
    "emergence_magnitude": 0.3,
    "convergence": 0.1,
    "direction_coherence": 0.5,
    "value_conflict_diversity": 8
  }
}
```

---

# 5. 跨种子汇总

## 5.1 cross_seed_summary.json

```json
{
  "version": "1.0",
  "experiment": "M1.1",
  "baby_id": "encouraged",
  "n_seeds": 5,
  "primary_metrics": {
    "emergence_magnitude": {
      "mean": 0.42,
      "std": 0.08,
      "min": 0.32,
      "max": 0.55,
      "per_seed": [0.45, 0.42, 0.38, 0.50, 0.35]
    },
    "convergence": {
      "mean": 0.08,
      "std": 0.02,
      "max": 0.11,
      "per_seed": [0.08, 0.07, 0.09, 0.06, 0.10]
    },
    "direction_coherence": {
      "mean": 0.61,
      "std": 0.10,
      "per_seed": [0.65, 0.60, 0.55, 0.70, 0.55]
    },
    "value_conflict_diversity": {
      "mean": 9.0,
      "std": 1.5,
      "per_seed": [10, 9, 8, 10, 8]
    }
  },
  "judgment_summary": {
    "all_pass": true,
    "n_pass": 5,
    "n_fail": 0
  }
}
```

## 5.2 cross_baby_summary.json（M1.2 准备）

```json
{
  "version": "1.0",
  "experiment": "M1.2",
  "babies": ["encouraged", "challenged", "uncertain"],
  "comparison": {
    "personality_divergence": {
      "F_statistic": 5.2,
      "F_critical": 3.88,
      "df_between": 2,
      "df_within": 12,
      "p_value": 0.024,
      "pass": true
    }
  }
}
```

---

# 6. 命名约定

- 目录：`m11_{baby_id}_seed{seed}/`
- 快照：`checkpoint_e{epoch}.tar`
- 报告：`experiment_report.md`
- 指标：`metrics.json`

示例：
- `m11_encouraged_seed1/`
- `m11_challenged_seed3/`
- `m11_uncertain_seed5/`

---

# 7. 验证规则

每个 JSONL 文件**必须**满足：
- 每行是有效的 JSON
- 所有必需字段存在
- 类型正确
- 值在合理范围内

**验证脚本**：`experiments/scripts/validate_format.py`（待实现）

---

# 8. 元数据

- **创建日期**：2026-06-15
- **版本**：1.0
- **对应实验**：M1.1
- **下一次更新**：M1.1 实施后基于实际需要修订
