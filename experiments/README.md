# SGE 实验代码目录

> **本目录是 SGE Phase 1+ 实验代码的存放地**。完整约定见 [CLAUDE.md §实验代码约定](../../CLAUDE.md)，本文件给出操作细节。

## 环境变量设置（必读）

M1.1 需要 LLM API Key。设置方法：

```bash
# 1. 复制环境变量示例文件
cp .env.example .env

# 2. 编辑 .env 填入实际 API Key
# MINIMAX_API_KEY=your-actual-key

# 3. 验证（代码中会读取 .env）
```

**.env 已被 .gitignore 排除**——不会泄露到 git。

**使用的提供商**：MiniMax（`https://api.minimax.io`）
**模型**：MiniMax-M3
**协议**：默认 Anthropic 兼容（`https://api.minimax.io/anthropic`）

详见 [.env.example](../../.env.example) 和 `experiments/configs/m11_base.yaml`。

---

## 当前状态

- **Phase 0（已完成，2026-06-15 之前）**：本目录建立（README、子目录结构、命名约定、约束规则）
- **Phase 1（已完成，2026-06-17）**：M1.1~M1.4 实验代码 + 报告已归档
- **Phase 2（当前，2026-06-18+）**：M2.1 启动中（[SGE-M21-AiBeing-Implementation-Mapping.md](../../research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md)）

权威阶段状态：[ROADMAP.md §Phase 进度](../../ROADMAP.md)。本 README 不维护"当前阶段"标注——以 ROADMAP 为准。

---

## 子目录结构

```
experiments/
├── notebooks/        # Jupyter notebooks（单次实验运行、参数探索）
├── scripts/          # ad-hoc Python 脚本（一次性运行）
├── analysis/         # 数据处理脚本（统计、可视化、报告生成）
└── configs/          # 实验配置文件（YAML）
```

---

## 命名约定

### Jupyter Notebook

格式：`YYYY-MM-DD-{phase}-m{milestone}-{description}.ipynb`

- `YYYY-MM-DD`：实验启动日期
- `{phase}`：phase1 / phase2 / phase3
- `m{milestone}`：M11 / M12 / M13 / M21 / M22 / M23 / M31 / M32 / M33
- `{description}`：简短描述

**示例**：
- `2026-06-20-phase1-m11-value-ema-prototype.ipynb` —— Phase 1 M1.1 的 Value EMA 原型实验
- `2026-07-01-phase1-m12-three-babies-divergence.ipynb` —— Phase 1 M1.2 三胞胎分化实验

### Python 脚本

格式：`m{milestone}_{action}.py`

- `m{milestone}`：同上
- `{action}`：run / analyze / visualize / report 等

**示例**：
- `m11_run_epochs.py` —— 跑 M1.1 的 Epoch
- `m11_analyze_trajectory.py` —— 分析价值轨迹
- `m12_compare_babies.py` —— 对比 3 个 AI 婴儿的价值观

### 配置文件

格式：`m{milestone}_{variant}.yaml`

- `m{milestone}`：同上
- `{variant}`：encouraged / challenged / uncertain / base

**示例**：
- `m11_encouraged.yaml` —— M1.1 鼓励组配置
- `m11_challenged.yaml` —— M1.1 失败组配置
- `m12_base.yaml` —— M1.2 基础配置（3 组共用）

---

## 实验代码的"头文件"模板

每个 notebook 和脚本**必须**在头部说明：

```python
"""
实验说明

对应 ROADMAP 里程碑：M1.1（Value Layer 原型）
对应 PRD 需求：FR-1, FR-4
对应 ARCH 模块：§1.3 Hebbian-Value 双轨, §3.1 Event Generator, §3.3 Value Layer

实验目的：验证价值观向量是否随经历变化
实验设计：单个 AI 婴儿，100 Epoch，包含价值困境事件
运行方法：python m11_run_epochs.py --config configs/m11_base.yaml
预期产出：value_trajectory.jsonl, experiment_report.md
归档策略：实验完成后归档到 experiments/archive/YYYY-MM-M1.1/
"""
```

---

## 与项目级文档的同步规则

### 实验开始前

1. 在 `discussions/YYYY-MM-DD-{phase}-m{milestone}.md` 创建会话记录
2. 引用对应 ROADMAP / PRD / ARCH 章节
3. 在 CHANGELOG 添加 `[0.X.0]` 实验启动条目

### 实验完成后

1. 在 `discussions/` 续写结果
2. 实验报告（如 `research/sge-feasibility/SGE-Experiment-Result-Phase1-M1.1.md`）
3. 修订 PRD §6 验收标准的实际结果
4. CHANGELOG 添加完成条目

### 归档策略

实验完成后，notebook 和脚本**保留在原位置**（便于查阅），不删除。如果有重要更新版本，使用 `archive/` 子目录：

```
experiments/
├── notebooks/
│   ├── 2026-06-20-phase1-m11-...ipynb
│   └── archive/
│       └── 2026-06-25-phase1-m11-v2.ipynb
```

---

## 当前已准备（Phase 0 末期）

- `configs/m11_event_templates.yaml` — M1.1 事件模板库（72 个模板）
- `configs/m11_base.yaml` — M1.1 基础配置
- `configs/m11_encouraged.yaml` — 鼓励组配置
- `configs/m11_challenged.yaml` — 挑战组配置
- `configs/m11_uncertain.yaml` — 不确定组配置
- `formats/README.md` — 数据格式标准（epoch_log/value_trajectory/identity/reward）
- `evaluation/README.md` — 评估脚本规范（compute_metrics/aggregate_seeds/compare_babies/generate_report）

## 工具与依赖

实验代码使用以下技术栈（与 [DEVELOP.md §二 技术栈](../../DEVELOP.md) 一致）：

- Python 3.11+
- litellm（统一 LLM 调用）
- SQLite + ChromaDB（状态与向量存储）
- structlog（日志）
- matplotlib / seaborn（可视化）

**安装**：

```bash
pip install litellm chromadb structlog matplotlib seaborn pyyaml
```

---

## 不允许的代码形态（提醒）

| 形态 | 原因 |
|------|------|
| ❌ 可复用的 `sge/` Python 包 | Phase 3+ 才考虑，不在本目录 |
| ❌ 生产级代码（CI/CD、测试套件） | 不在研究项目范围 |
| ❌ 完整的 CLI/Web UI | 不是当前研究目标 |
| ❌ 跨 notebook 的可复用模块 | 实验代码应一次性 |

如果发现需要"可复用模块"——这是 Phase 3+ 的范围，应在**新仓库**（如 SGE-Prototype）中实施，而不是在 SelfLab 内重构。

---

## 相关文档

- [CLAUDE.md §实验代码约定](../../CLAUDE.md) — 实验代码的边界与原则
- [DEVELOP.md §二 技术栈](../../DEVELOP.md) — 实验代码使用技术栈
- [DEVELOP.md §四 目录结构](../../DEVELOP.md) — 未来 sge/ 包的目录（标注"前瞻性"）
- [PRD.md §6 验收标准](../../PRD.md) — 实验结果的判定标准
- [SGE-Experiment-Protocol.md](../../research/sge-feasibility/SGE-Experiment-Protocol.md) — 实验运行与评估手册
- [ROADMAP.md §里程碑](../../ROADMAP.md) — 实验对应的里程碑定义

---

**创建日期**：2026-06-15
**维护者**：Bisen & Claude
