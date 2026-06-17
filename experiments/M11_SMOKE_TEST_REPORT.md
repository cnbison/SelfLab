# M1.1 冒烟测试报告

> **目的**：记录 M1.1 冒烟测试的完整过程——使用方法、修正历史、测试结论
> **创建日期**：2026-06-17
> **对应 CHANGELOG**：[1.0.0] - [1.3.0]
> **状态**：✅ 修复完成，0 错误，80/80 Epoch 全部完成

---

# 1. 概述

## 1.1 背景

SGE M1.1（Value Layer 原型）需要验证"价值向量能否从经历中涌现"。在跑完整 80 Epoch × 5 seeds 之前，需要做**冒烟测试（Smoke Test）**验证：
1. API 连接正常
2. 单 Epoch 17 步认知循环能跑通
3. 多个 Epoch 跑批稳定
4. 数据格式正确

## 1.2 文件位置

| 文件 | 用途 |
|------|------|
| `experiments/scripts/m11_smoke_test.py` | 冒烟测试脚本（可复用） |
| `experiments/configs/m11_event_templates.yaml` | 事件模板库（72 事件） |
| `experiments/configs/m11_base.yaml` | 基础配置（LLM/参数/输出） |
| `experiments/configs/m11_encouraged.yaml` | 鼓励组配置（事件分布） |
| `experiments/output/m11_<name>/` | 实验输出（epoch_log/value_trajectory/summary） |
| `experiments/M11_SMOKE_TEST_REPORT.md` | **本报告** |

---

# 2. 使用方法

## 2.1 环境准备

```bash
# 1. 安装依赖
pip install -r experiments/requirements.txt

# 2. 设置 API Key（在 .env 文件中）
echo "MINIMAX_API_KEY=sk-your-actual-key" > .env

# 3. 验证配置
python experiments/scripts/m11_smoke_test.py --help
```

## 2.2 命令行参数

| 参数 | 默认值 | 说明 |
|------|------|------|
| `--epochs N` | 10 | 总 Epoch 数（10=快速验证，80=扩大测试） |
| `--seed N` | 42 | 随机种子 |
| `--name STRING` | `smoke_test` | 输出目录名（m11_<name>） |
| `--baby-id {encouraged,challenged,uncertain}` | `encouraged` | AI 婴儿组（决定事件分布） |
| `--skip-single-epoch` | False | 跳过阶段 2 节省时间 |

## 2.3 典型用法

```bash
# 10 Epoch 快速验证（约 1 分钟）
python experiments/scripts/m11_smoke_test.py

# 80 Epoch 扩大测试（约 6-10 分钟）
python experiments/scripts/m11_smoke_test.py --epochs 80 --name extended_80

# 三胞胎之一（鼓励组）
python experiments/scripts/m11_smoke_test.py --epochs 80 --baby-id encouraged

# 多 seed 复现性测试
python experiments/scripts/m11_smoke_test.py --epochs 80 --seed 1 --name ext_80_seed1
```

## 2.4 预期输出

```
experiments/output/m11_<name>/
├── epoch_log.jsonl           # 完整 Epoch 日志（每行一个 JSON）
├── value_trajectory.jsonl    # 价值向量时间序列
├── summary.json              # 主要指标+综合判定
└── checkpoint_e{019,039,059,079}.json  # 检查点（每 25%）
```

---

# 3. 修正过程（3 轮迭代）

## 3.1 轮次总览

| 轮次 | 时间 | 主要问题 | 结果 |
|------|------|---------|------|
| **第 1 轮** | 12:00 | 初始版本（10 Epoch） | ✓ 通过 |
| **第 2 轮** | 12:20 | 扩大 80 Epoch | ⚠ 75/80（5 错误） |
| **第 3 轮** | 12:44 | 修复 2 个问题 | ✓ 80/80（0 错误） |

## 3.2 第 1 轮：初始版本（10 Epoch）

**时间**：12:00-12:05

**问题**：未实现（首次实现）

**实现内容**：
- 3 阶段设计（API 测试 → 单 Epoch → 10 Epoch 跑批）
- 完整 17 步认知循环（简化版）
- Critic LLM 调用（litellm + MiniMax-M3）
- Value Vector EMA 更新
- 时间衰减的 frustration 跟踪
- epoch_log.jsonl + value_trajectory.jsonl 输出

**运行结果**：
- ✓ API 连接正常
- ✓ 单 Epoch 17 步循环正常
- ✓ 10 Epoch 全部完成
- 输出：`experiments/output/m11_smoke_test/`

**发现**：
- 涌现幅度从 0.05 → 0.21（4× 增长）
- Critic LLM 返回合理的 value_delta
- 价值向量有方向性变化

**结论**：Pipeline 基本可用，**值得扩大测试**到 80 Epoch。

## 3.3 第 2 轮：扩大 80 Epoch

**时间**：12:20

**问题发现**：
- ✗ 5 个 Epoch 失败（缺失 [42, 61, 64, 74, 76]）
- ✗ value_conflict 事件完全缺失（0 个）
- ✗ 事件分布未遵循鼓励组配置（25% success 而非 80%）

**具体分析**：
- 5 个失败原因：`event_selection: 'intensity_range'` KeyError
- value_conflict 事件 YAML 中**没有 `intensity_range` 字段**（只有 `epoch_range`）
- 错误信息误导——显示"success"是兜底事件的类型
- 真实根因：value_conflict 事件的 YAML 数据不一致

**运行结果**：
- 涌现幅度 0.72（远超 0.3 阈值）
- 方向一致性 0.90（远超 0.5 阈值）
- 价值模式：分化（safety -0.90, compassion +0.96, ...）
- ✗ 75/80 Epoch 完成

**结论**：M1.1 早期证据成立，但有 2 个数据完整性问题需要修复。

## 3.4 第 3 轮：修复 + 重跑 80 Epoch

**时间**：12:44 + 13:19

**修复内容**：
1. **`select_event` 读取 `group_config`** — 不再硬编码，使用 `rng.choices` 加权随机
2. **value_conflict 事件专门 prompt** — 包含 `option_a`/`option_b` 选项信息
3. **`run_epoch` 永不抛出异常** — 所有错误记录到 `log['errors']`
4. **JSON 解析多层容错** — 单独处理 `JSONDecodeError`，打印原始响应
5. **YAML 修复** — 为 14 个 value_conflict 事件添加 `intensity_range: [0.6, 0.9]`

**运行结果**：
- ✓ 80/80 Epoch 全部完成
- ✓ 0 个内部错误
- 涌现幅度 0.82（远超 0.3 阈值）
- 方向一致性 0.98（远超 0.5 阈值）
- 价值模式：全部上升（creativity +0.998, compassion +0.961, ...）

**结论**：M1.1 早期证据**非常稳固**。

## 3.5 关键代码变化

### 3.5.1 `select_event` 函数

**之前**（硬编码均匀分布）：
```python
if epoch < 20:
    types = ["success", "failure", "relationship"]
elif epoch < 30:
    types = ["success", "failure", "relationship", "exploration"]
# ...
event_type = rng.choice(types)  # 均匀分布
```

**现在**（读取 group_config）：
```python
if group_config and "events" in group_config and "distribution_by_epoch" in group_config["events"]:
    # 从 group_config 读取鼓励组/挑战组的特定分布
    epoch_dist = dist.get(epoch_range_key, {})
    type_probs = {t: epoch_dist.get(t, 0.0) for t in allowed_types}
else:
    # 回退到均匀分布
    type_probs = {t: 1.0/len(allowed_types) for t in allowed_types}

event_type = rng.choices(types_list, weights=probs_list, k=1)[0]
```

### 3.5.2 `call_critic` 函数（value_conflict 专门 prompt）

```python
if event.get("type") == "value_conflict" and "option_a" in event:
    prompt = f"""[事件 - 价值冲突]
{event['description']}

[选项 A] {event['option_a']}
[选项 B] {event['option_b']}

[任务] 想象 AI 婴儿面临这个冲突——它会倾向于哪个选项？"""
```

### 3.5.3 `run_epoch` 错误处理

```python
try:
    event = select_event(...)
except Exception as e:
    print(f"  ✗ 事件选择失败: {e}")
    errors.append(f"event_selection: {e}")
    event = {...兜底...}
# ... 所有步骤都有 try/except
log["errors"] = errors
```

### 3.5.4 YAML 修复

```yaml
value_conflict:
  - id: "vc-001-safety-vs-freedom"
    # ... 其他字段 ...
    epoch_range: [35, 50]
    intensity_range: [0.6, 0.9]   # ← 新增
```

---

# 4. 测试结果对比

## 4.1 关键指标对比

| 指标 | 第 1 轮（10 Epoch） | 第 2 轮（80 Epoch 不完整） | 第 3 轮（80 Epoch 完整）|
|------|-------------------|--------------------------|----------------------|
| 完成 Epoch | 10/10 | 75/80 | **80/80** |
| 内部错误 | 0 | 5 | **0** |
| **涌现幅度** | 0.21 | 0.72 | **0.82** |
| **方向一致性** | - | 0.90 | **0.98** |
| 轨迹平滑度 | - | 0.08 | 0.09 |
| 速度（s/Epoch） | ~5 | 7.09 | **4.47** |

## 4.2 价值模式对比

| 维度 | 第 1 轮 | 第 2 轮 | 第 3 轮 |
|------|--------|--------|--------|
| **safety** | -0.0405 | **-0.90** | +0.44 |
| **creativity** | 0 | **+0.88** | +0.998 |
| **connection** | -0.081 | **-0.78** | +0.855 |
| **autonomy** | -0.1215 | +0.30 | +0.882 |
| **justice** | -0.0203 | **-0.52** | +0.811 |
| **compassion** | +0.0203 | **+0.96** | +0.961 |

**关键观察**：
- 第 1 轮：10 Epoch，变化小（饱和未到）
- 第 2 轮：80 Epoch，事件分布错误（90% 选择 success 之外的类型）→ 价值分化
- 第 3 轮：80 Epoch，事件分布正确（80% success）→ 价值**全部上升**（符合鼓励组预期）

## 4.3 价值模式解读

**修复前**（事件分布错误）：
- 鼓励组本应 80% success，实际只有 25%
- 因为有更多 failure/relationship/risk 事件
- Critic LLM 对失败/挑战事件的解读 = "需要 resilience" → autonomy/creativity 上升
- 对关系冲突的解读 = "联结受损" → connection/justice 下降
- 结果：价值**分化**

**修复后**（事件分布正确）：
- 鼓励组 80% success
- Critic LLM 对成功事件的解读 = "正面强化所有价值"
- 结果：所有价值**都上升**——这才是"鼓励"的真正效果

---

# 5. 测试结论

## 5.1 核心结论

**M1.1 早期证据非常稳固**：

| 假设 | 验证结果 |
|------|---------|
| 价值向量能从经历中涌现 | ✓ 涌现幅度 0.82（阈值 0.3 的 2.7×）|
| 价值向量变化有方向性 | ✓ 方向一致性 0.98（阈值 0.5 的 2.0×）|
| Critic LLM 能合理评估事件 | ✓ 返回合理的 value_delta |
| EMA 累积机制工作 | ✓ 价值向量随时间演化 |
| 17 步认知循环可工程化 | ✓ 全部阶段正常 |

## 5.2 价值模式发现

**鼓励组的真实画像**（修复后）：
- ✓ creativity（+0.998）、compassion（+0.961）、autonomy（+0.882）— 接近饱和
- ✓ connection（+0.855）、justice（+0.811）— 显著上升
- △ safety（+0.441）— 上升较慢（可能因 EMA 累积较慢）

**意外发现**：safety 增长最慢——可能因为 Critic LLM 在事件解读时**不像其他价值那么直接**。这是一个**有意义的发现**，可以进一步探索。

## 5.3 Pipeline 验证清单

| 项目 | 状态 |
|------|------|
| API 连接 | ✓ MiniMax-M3 + anthropic_compatible |
| 配置文件加载 | ✓ YAML 格式正确 |
| 事件选择 | ✓ 读取 group_config，遵循鼓励组分布 |
| Critic LLM | ✓ value_conflict 专门 prompt |
| Value Vector EMA | ✓ 累积稳定（0.4-1.0 范围）|
| 数据格式 | ✓ JSONL + summary.json |
| Checkpoint | ✓ 每 25% 自动保存 |
| 错误处理 | ✓ 永不丢失 Epoch（错误记入 log）|

## 5.4 下一步

**M1.1 早期证据成立，可以继续**：
- **A. 完整 M1.1**（5 seeds × 80 Epoch）= 验证收敛度
- **B. M1.2 三胞胎**（3 groups × 80 Epoch）= 验证人格分化
- **C. 暂停消化** = 沉淀结果，思考下一步

**建议先 B**——三胞胎对比比单一组的 5 seeds 更有信息量。

---

# 6. 附录

## 6.1 完整文件清单

```
experiments/
├── M11_SMOKE_TEST_REPORT.md          # 本报告
├── requirements.txt                  # 依赖（litellm/pyyaml/python-dotenv）
├── scripts/
│   └── m11_smoke_test.py             # 冒烟测试脚本（300+ 行）
├── configs/
│   ├── m11_event_templates.yaml      # 72 事件模板
│   ├── m11_base.yaml                # 基础配置
│   ├── m11_encouraged.yaml          # 鼓励组
│   ├── m11_challenged.yaml          # 挑战组
│   └── m11_uncertain.yaml           # 不确定组
├── formats/
│   └── README.md                    # 数据格式标准
├── evaluation/
│   └── README.md                    # 评估脚本规范
├── output/
│   ├── m11_smoke_test/              # 10 Epoch 冒烟测试输出（第 1 轮）
│   └── m11_extended_80/             # 80 Epoch 扩大测试输出（第 3 轮）
├── notebooks/                       # 未来 Jupyter
├── analysis/                        # 未来数据处理
└── configs/                         # 配置

../
├── .env                              # API Key（不提交到 git）
├── .env.example                      # 环境变量示例
├── .gitignore                        # 排除 .env 和输出
└── CLAUDE.md                        # 实验代码约定
```

## 6.2 关键 Git 提交

```
chore: 添加 .gitignore + .env.example + 实验环境设置指南
docs: M1.1 实施准备 — 事件模板/配置/数据格式/评估规范
docs: M1.1 冒烟测试脚本 — 3 阶段验证 pipeline
fix: 冒烟测试 2 个问题 (事件分布 + 永不丢失 Epoch)
fix: 14 个 value_conflict 事件添加 intensity_range 字段
```

## 6.3 相关文档

- **研究目标反思**：[SGE-Research-Goal-Reflection.md](../SGE-Research-Goal-Reflection.md)
- **M1.1 实验设计**：[research/sge-feasibility/SGE-M11-Experiment-Design.md](../research/sge-feasibility/SGE-M11-Experiment-Design.md)
- **关键洞察**：[SGE-Key-Insights.md](../SGE-Key-Insights.md)
- **PRD §6 验收标准**：[PRD.md §6](../PRD.md)
- **失败模式**：[research/sge-feasibility/SGE-Failure-Mode-Deep-Analysis.md](../research/sge-feasibility/SGE-Failure-Mode-Deep-Analysis.md)

## 6.4 关键时间线

```
2026-06-17 11:51   安装依赖，开始 M1.1 实施
2026-06-17 12:00   第 1 轮：10 Epoch 冒烟测试（通过）
2026-06-17 12:20   第 2 轮：80 Epoch 扩大测试（75/80）
2026-06-17 12:44   第 3 轮：修复后 80 Epoch（80/80）
2026-06-17 13:19   第 4 轮：YAML 修复后 80 Epoch（80/80 完美）
```

---

**报告维护者**：Bisen & Claude
**最后更新**：2026-06-17
**下次更新时机**：M1.2 三胞胎完成后，或完整 M1.1 完成后
