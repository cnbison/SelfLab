# SGE M1.1 评估脚本规范

> **本目录定义 M1.1 评估脚本的规范**——所有评估逻辑必须按这些规范实现。
>
> 遵循 [CLAUDE.md §实验代码约定](../../../CLAUDE.md)：**一次性、归档不修改、与文档同步**。

---

# 1. 评估脚本清单

| 脚本 | 输入 | 输出 | 用途 |
|------|------|------|------|
| `compute_metrics.py` | `epoch_log.jsonl` | `metrics.json` | 计算 5 维评分卡指标 |
| `aggregate_seeds.py` | 多个 `metrics.json` | `cross_seed_summary.json` | 跨种子汇总 |
| `compare_babies.py` | 多个 `cross_seed_summary.json` | `cross_baby_summary.json` | 跨 AI 婴儿组比较（M1.2 准备）|
| `generate_report.py` | `metrics.json` + `epoch_log.jsonl` | `experiment_report.md` | 生成人类可读报告 |

---

# 2. compute_metrics.py 规范

## 2.1 输入

- 一个 `epoch_log.jsonl` 文件
- 一个 `value_vector.json` 终态文件

## 2.2 输出

- 一个 `metrics.json` 文件

## 2.3 计算逻辑

```python
"""
M1.1 评估指标计算（伪代码）

本脚本计算 4 个主要指标和多个次要指标。
所有计算基于 [PRD §6.1 4.1.1-4.1.6] 和 SGE-Experiment-Protocol.md §4.1。
"""

def compute_metrics(epoch_log_path, final_value_vector_path):
    # 读取所有 Epoch
    epochs = read_jsonl(epoch_log_path)
    final_vv = read_json(final_value_vector_path)["concrete_values"]
    initial_vv = {
        "safety": 0.0, "creativity": 0.0, "connection": 0.0,
        "autonomy": 0.0, "justice": 0.0, "compassion": 0.0
    }

    # ========== 主要指标 1：涌现幅度 ==========
    # 公式: L2 距离（最终值向量 vs 初始值向量）取均值
    # [PRD §6.1 4.1.1]
    emergence_magnitude = l2_distance(final_vv, initial_vv) / 6  # 6 个维度

    # ========== 主要指标 2：收敛度 ==========
    # 仅当 N≥5 个 seed 时计算
    # 公式: 多次运行最终值向量的 L2 标准差均值
    # [PRD §6.1 4.1.2]
    # 单一 seed 时: N/A
    convergence = None  # 需要 aggregate_seeds.py 计算

    # ========== 主要指标 3：方向一致性 ==========
    # 公式: cos(final_vv, weighted_event_vv)
    # [PRD §6.1 4.1.3]
    weighted_event_vv = compute_event_weighted_value_vector(epochs)
    direction_coherence = cosine_similarity(final_vv, weighted_event_vv)

    # ========== 主要指标 4：价值冲突选择多样性 ==========
    # 公式: value_conflict 事件中不同选择的数量
    # [SGE-M11-Experiment-Design.md §3.2.2]
    value_conflict_events = [e for e in epochs if e["event"]["type"] == "value_conflict"]
    choices = extract_actor_choices(value_conflict_events)
    value_conflict_diversity = len(set(choices))

    # ========== 次要指标 ==========
    # 价值轨迹平滑度
    value_trajectory = [e["value_vector"] for e in epochs]
    smoothness = compute_trajectory_smoothness(value_trajectory)

    # value_delta 分布
    value_delta_stats = compute_value_delta_stats(epochs)

    # Hebbian W2 范数
    hebbian_state = read_hebbian_state()
    w2_norm = hebbian_state["W2_norm"]

    # frustration 演化
    frustration_evolution = compute_frustration_stats(epochs)

    return {
        "version": "1.0",
        "experiment": "M1.1",
        "baby_id": epochs[0]["baby_id"],
        "seed": epochs[0]["seed"],
        "primary_metrics": {
            "emergence_magnitude": emergence_magnitude,
            "direction_coherence": direction_coherence,
            "value_conflict_diversity": value_conflict_diversity
        },
        "secondary_metrics": {
            "value_trajectory_smoothness": smoothness,
            "w2_norm": w2_norm,
            "frustration_mean": frustration_evolution["mean"],
            "frustration_std": frustration_evolution["std"]
        }
    }
```

## 2.4 关键算法

### compute_event_weighted_value_vector

```python
def compute_event_weighted_value_vector(epochs):
    """
    计算所有事件的"价值冲击"加权和。
    每个事件的 value_delta × intensity 加和。
    """
    weighted = {v: 0.0 for v in ["safety", "creativity", "connection",
                                  "autonomy", "justice", "compassion"]}
    for e in epochs:
        for v, delta in e["critic_output"]["value_delta"].items():
            weighted[v] += delta * e["event"]["intensity"]
    return weighted
```

### compute_trajectory_smoothness

```python
def compute_trajectory_smoothness(trajectory):
    """
    计算价值轨迹的"平滑度"——相邻 Epoch 间 L2 距离的均值。
    越小越平滑。
    """
    if len(trajectory) < 2:
        return 0.0
    distances = []
    for i in range(1, len(trajectory)):
        d = l2_distance(trajectory[i], trajectory[i-1])
        distances.append(d)
    return sum(distances) / len(distances)
```

### extract_actor_choices

```python
def extract_actor_choices(value_conflict_events):
    """
    从 value_conflict 事件中提取 Actor 的选择（A 或 B）。
    """
    choices = []
    for e in value_conflict_events:
        # Actor LLM 输出包含 "choice": "A" 或 "B"
        choice = extract_choice_from_actor_output(e["actor_output"])
        choices.append(choice)
    return choices
```

---

# 3. aggregate_seeds.py 规范

## 3.1 输入

- N 个 `metrics.json` 文件（一个 seed 一个）

## 3.2 输出

- 一个 `cross_seed_summary.json` 文件

## 3.3 计算逻辑

```python
def aggregate_seeds(metrics_files):
    """
    跨种子汇总。
    计算主要指标的 mean, std, min, max。
    """
    all_metrics = [read_json(f) for f in metrics_files]

    return {
        "version": "1.0",
        "experiment": "M1.1",
        "baby_id": all_metrics[0]["baby_id"],
        "n_seeds": len(all_metrics),
        "primary_metrics": {
            "emergence_magnitude": {
                "mean": mean([m["primary_metrics"]["emergence_magnitude"] for m in all_metrics]),
                "std": std([m["primary_metrics"]["emergence_magnitude"] for m in all_metrics]),
                "min": min([m["primary_metrics"]["emergence_magnitude"] for m in all_metrics]),
                "max": max([m["primary_metrics"]["emergence_magnitude"] for m in all_metrics]),
                "per_seed": [m["primary_metrics"]["emergence_magnitude"] for m in all_metrics]
            },
            "convergence": {
                # 跨种子的 L2 标准差均值
                "mean": mean_std_across_seeds(all_metrics, "emergence_magnitude"),
                "std": std_of_stds_across_seeds(all_metrics, "emergence_magnitude"),
                "max": max_std_across_seeds(all_metrics, "emergence_magnitude"),
                "per_seed": [std([m["primary_metrics"]["emergence_magnitude"]
                                  for m in all_metrics])
            },
            "direction_coherence": {
                "mean": mean([m["primary_metrics"]["direction_coherence"] for m in all_metrics]),
                "std": std([m["primary_metrics"]["direction_coherence"] for m in all_metrics]),
                "per_seed": [m["primary_metrics"]["direction_coherence"] for m in all_metrics]
            },
            "value_conflict_diversity": {
                "mean": mean([m["primary_metrics"]["value_conflict_diversity"] for m in all_metrics]),
                "std": std([m["primary_metrics"]["value_conflict_diversity"] for m in all_metrics]),
                "per_seed": [m["primary_metrics"]["value_conflict_diversity"] for m in all_metrics]
            }
        },
        "judgment_summary": {
            "all_pass": all(
                m["primary_metrics"]["emergence_magnitude"] > 0.3 and
                compute_convergence(m) < 0.1 and
                m["primary_metrics"]["direction_coherence"] > 0.5 and
                m["primary_metrics"]["value_conflict_diversity"] >= 8
                for m in all_metrics
            ),
            "n_pass": sum(1 for m in all_metrics if passes_judgment(m)),
            "n_fail": sum(1 for m in all_metrics if not passes_judgment(m))
        }
    }
```

---

# 4. compare_babies.py 规范

## 4.1 输入

- 3 个 `cross_seed_summary.json` 文件（鼓励/挑战/不确定）

## 4.2 输出

- 一个 `cross_baby_summary.json` 文件

## 4.3 计算逻辑

```python
def compare_babies(summaries):
    """
    跨 AI 婴儿组比较。
    使用单因素 ANOVA 检验 3 组是否有显著差异。
    """
    # 提取 3 组的最终价值向量
    encouraged_vvs = summaries["encouraged"]["final_value_vectors"]  # 5 seeds × 6 维
    challenged_vvs = summaries["challenged"]["final_value_vectors"]
    uncertain_vvs = summaries["uncertain"]["final_value_vectors"]

    # 单因素 ANOVA（每个维度独立检验）
    f_stats = []
    for dim in ["safety", "creativity", "connection", "autonomy", "justice", "compassion"]:
        # 收集 3 组在该维度上的值
        groups = [
            [vv[dim] for vv in encouraged_vvs],
            [vv[dim] for vv in challenged_vvs],
            [vv[dim] for vv in uncertain_vvs]
        ]
        # ANOVA
        f, p = scipy.stats.f_oneway(*groups)
        f_stats.append({
            "dimension": dim,
            "F_statistic": f,
            "p_value": p,
            "significant": p < 0.05
        })

    # 综合判定：是否有任何维度显著
    any_significant = any(s["significant"] for s in f_stats)
    min_f = min(s["F_statistic"] for s in f_stats if s["significant"])
    f_critical = scipy.stats.f.ppf(0.95, 2, 12)  # df_between=2, df_within=12

    return {
        "version": "1.0",
        "experiment": "M1.2",
        "babies": ["encouraged", "challenged", "uncertain"],
        "comparison": {
            "any_dimension_significant": any_significant,
            "min_F_statistic": min_f,
            "F_critical": f_critical,
            "per_dimension": f_stats,
            "pass": any_significant and min_f > f_critical
        }
    }
```

---

# 5. generate_report.py 规范

## 5.1 输入

- `metrics.json`
- `epoch_log.jsonl`
- 模板：`formats/experiment_report.md`（见 [formats/README.md](../formats/README.md)）

## 5.2 输出

- `experiment_report.md`

## 5.3 生成逻辑

```python
def generate_report(metrics, epochs, template):
    """
    生成人类可读报告。
    填充模板中的占位符。
    """
    report = template

    # 填充基本信息和指标
    report = fill_basic_info(report, metrics, epochs)
    report = fill_metrics_table(report, metrics)
    report = fill_judgment_table(report, metrics)
    report = fill_trajectory_visualization(report, epochs)

    # 失败诊断
    if not metrics["judgment"]["overall_pass"]:
        report = fill_failure_diagnosis(report, metrics, epochs)

    return report
```

---

# 6. 验证规则

## 6.1 必须验证

- 输入文件存在
- JSON 格式正确
- 必需字段存在
- 数值在合理范围
- 跨种子的 n_seeds ≥ 5（来自 [PRD §6.1 可复现性约束](../../../PRD.md)）

## 6.2 失败处理

- 输入缺失 → 中止 + 报警
- 字段缺失 → 标记 + 报告
- 数值越界 → clip + 警告

---

# 7. 复用与依赖

| 函数 | 来源 |
|------|------|
| `l2_distance` | 标准 |
| `cosine_similarity` | 标准 |
| `scipy.stats.f_oneway` | scipy |
| `mean/std/min/max` | statistics |
| `read_jsonl/read_json` | 项目 utilities |

---

# 8. 实施检查清单

- [ ] 脚本使用 [experiments/configs/](../configs/) 提供的配置
- [ ] 脚本输出符合 [experiments/formats/](../formats/) 标准
- [ ] 脚本不修改输入文件
- [ ] 脚本可重复运行（同一输入 → 同一输出）
- [ ] 脚本有清晰的错误消息
- [ ] 脚本不联网（除 LLM API 外）

---

# 9. 元数据

- **创建日期**：2026-06-15
- **版本**：1.0
- **对应文档**：[SGE-Experiment-Protocol.md §4 评估指标计算](../../../research/sge-feasibility/SGE-Experiment-Protocol.md)
- **下一次更新**：M1.1 实施后基于实际需要修订
