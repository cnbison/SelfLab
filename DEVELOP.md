# SGE（Self Genesis Engine）开发规范

文档版本：v0.1
项目版本：[0.3.0]（权威版本见 [CHANGELOG.md](./CHANGELOG.md)）

日期：2026-06-15

状态：草案

> **版本约定**：项目级文档的"项目版本"以 [CHANGELOG.md](./CHANGELOG.md) 为权威源；"文档版本"为该文档自身的迭代号，两者独立管理。

---

# 一、项目性质

**本项目是研究规划与技术探讨项目，不是代码实现项目。**

本文档定义的是 SGE 的开发规范框架——当未来进入代码实现阶段时应遵循的规范。当前阶段以文档和原型设计为主，不产出可运行的应用代码。

---

# 二、技术栈

## 2.1 核心技术栈

| 组件 | 选型 | 版本 | 说明 |
|------|------|------|------|
| 语言 | Python | 3.11+ | 与 AiBeing 一致 |
| LLM SDK | litellm / openai | latest | 统一多模型调用 |
| 结构化存储 | SQLite | 3.40+ | 轻量级，单机部署 |
| 向量存储 | ChromaDB | latest | 语义检索 |
| 异步框架 | asyncio | 内置 | 与 AiBeing 一致 |
| 配置管理 | YAML | - | 角色参数、引擎参数 |
| 日志 | structlog | latest | 结构化日志 |

## 2.2 LLM 模型选型

| 角色 | 模型 | 用途 | 温度 |
|------|------|------|------|
| Critic | Haiku / Qwen-2.5-7B | 事件感知，稳定结构化输出 | 0.2 |
| Actor | Sonnet / GPT-4o | 行为表达，创造性生成 | 0.9 |
| Identity | Sonnet / GPT-4o | 身份凝聚 | 0.3 |
| Narrative | Sonnet / GPT-4o | 叙事构建 | 0.5 |

## 2.3 模型降级策略

```
前沿模型不可用时：
  Sonnet → Haiku（牺牲表达质量，降低成本）
  GPT-4o → GPT-4o-mini（同上）

API 不可用时：
  返回默认值，不阻塞认知循环
```

---

# 三、代码规范

## 3.1 命名规范

```python
# 模块名：snake_case
drive_metabolism.py
value_layer.py

# 类名：PascalCase
class ValueVector:
class LifeEvent:

# 函数名：snake_case
def calculate_reward():
def ema_update():

# 常量：UPPER_SNAKE_CASE
FRUSTRATION_DECAY_LAMBDA = 0.08
HIDDEN_SIZE = 24

# 私有方法：前缀下划线
def _apply_relationship_ema():
def _should_crystallize():
```

## 3.2 类型注解

```python
from typing import Optional, Dict, List, Tuple

def calculate_reward(
    old_frustration: Dict[str, float],
    frustration_delta: Dict[str, float],
    decay_rate: float = 0.1
) -> float:
    ...

def compute_signals(self, context: Dict[str, float]) -> Dict[str, float]:
    ...
```

## 3.3 文档字符串

```python
def ema_update(self, value_delta: dict, event_intensity: float):
    """
    根据事件的价值观冲击更新价值观向量。

    使用指数移动平均（EMA）融合历史价值观和新冲击。
    alpha 与 event_intensity 正相关：重大事件影响更大。

    Args:
        value_delta: 事件对各价值观的冲击量
        event_intensity: 事件强度 [0, 1]
    """
```

---

# 四、目录结构

> **前瞻性章节**：本节描述的是 SGE **未来实现阶段**（Phase 1 之后）的代码组织。当前 Phase 0 阶段不产生可运行代码，本节仅作为实现前的设计参考。
>
> 当项目进入 Phase 1（实现 M1.1）时，本节将作为代码组织的基础。

```
sge/
├── __init__.py
├── main.py                     # 入口
├── config.py                   # 配置管理
│
├── engine/                     # 核心引擎
│   ├── __init__.py
│   ├── genome_engine.py        # 神经网络（W1, W2, b1, b2）
│   ├── drive_metabolism.py     # 时间代谢 + 热力学噪声 + 奖励计算
│   ├── critic.py               # 事件感知（LLM）
│   ├── style_memory.py         # 风格记忆 + KNN 检索 + 结晶
│   └── value_layer.py          # 价值观 EMA（SGE 新增）
│
├── agent/                      # Agent 层
│   ├── __init__.py
│   ├── chat_agent.py           # 主 Agent（12 步认知循环）
│   ├── parser.py               # LLM 输出解析
│   ├── prompt_builder.py       # Prompt 构建
│   └── identity_layer.py       # 身份凝聚（SGE 新增）
│   └── narrative_layer.py      # 叙事构建（SGE 新增）
│
├── event/                      # 事件生成（SGE 新增）
│   ├── __init__.py
│   ├── event_generator.py      # 事件生成器
│   └── value_conflict.py       # 价值困境生成器
│
├── prompts/                    # Prompt 模板
│   ├── critic.md               # Critic prompt
│   ├── actor_single.md         # Actor prompt
│   ├── identity.md             # 身份凝聚 prompt
│   └── narrative.md            # 叙事构建 prompt
│
├── providers/                  # 外部服务
│   ├── llm_provider.py         # LLM 统一调用
│   └── memory_provider.py      # 记忆存储
│
└── utils/                      # 工具
    ├── math_utils.py           # 数学工具
    ├── json_utils.py           # JSON 解析
    └── logger.py               # 日志
```

---

# 五、测试策略

## 5.1 测试层次

| 层次 | 范围 | 工具 |
|------|------|------|
| 单元测试 | 单个函数/方法 | pytest |
| 集成测试 | 模块间交互 | pytest + mock |
| 端到端测试 | 完整认知循环 | pytest + 真实 LLM |

## 5.2 关键测试用例

### Value Layer 测试

```python
def test_value_ema_convergence():
    """相同事件序列重复 100 次，价值观应收敛到稳定值。"""

def test_value_ema_differentiation():
    """不同事件序列应产生不同的价值观分布。"""

def test_value_ema_not_random_walk():
    """价值观变化应有方向性，不是随机漂移。"""

def test_meta_values_stable():
    """元价值（真实、自由）不应随事件变化。"""
```

### Identity Layer 测试

```python
def test_identity_consistency():
    """身份描述应与行为历史一致。"""

def test_identity_not_contradiction():
    """身份不应与价值观矛盾。"""
```

### Narrative Layer 测试

```python
def test_narrative_coherence():
    """叙事应与行为历史一致。"""

def test_narrative_after_phase_transition():
    """Phase Transition 后叙事应能重建。"""
```

### End-to-End 测试

```python
def test_100_epoch_value_emergence():
    """100 个 Epoch 后价值观应显著不同于初始状态。"""

def test_three_babies_divergence():
    """3 个 AI 婴儿应形成不同的人格。"""
```

---

# 六、配置管理

> **SSOT**：[DESIGN.md §八 参数配置](../DESIGN.md) 是 SGE 所有参数的**算法权威源**（包含数学定义、默认值、推荐范围）。本节描述**配置文件**（YAML 格式）如何将这些参数序列化，配置文件是参数**部署**层面的载体。
>
> **同步约束**：修改 DESIGN.md 中的默认值必须同步更新本节的 YAML 示例；反之亦然。建议修改时同时更新两处并标注 commit。

## 6.1 配置文件结构

```yaml
# config.yaml
engine:
  frustration_decay_lambda: 0.08
  connection_hunger_k: 0.15
  novelty_hunger_k: 0.05
  hebbian_lr: 0.02
  weight_decay: 0.995
  hidden_size: 24
  n_signals: 8
  temp_coeff: 0.12
  temp_floor: 0.03
  crystal_threshold: 0.50
  hawking_gamma: 0.001
  phase_threshold: 3.0

value_layer:
  base_alpha: 0.15
  max_alpha: 0.65
  meta_values:
    truth_seeking: 0.5
    freedom: 0.5
  concrete_values:
    safety: 0.0
    creativity: 0.0
    connection: 0.0
    autonomy: 0.0
    justice: 0.0
    compassion: 0.0

llm:
  critic_model: "claude-3-haiku-latest"  # 使用 litellm 模型别名，避免版本号过期
  actor_model: "claude-sonnet-latest"    # 使用 litellm 模型别名，避免版本号过期
  critic_temperature: 0.2
  actor_temperature: 0.9

experiment:
  total_epochs: 1000
  babies:
    - name: "encouraged"
      event_bias: "positive"
    - name: "challenged"
      event_bias: "negative"
    - name: "uncertain"
      event_bias: "random"
```

---

# 七、日志与观测

## 7.1 日志格式

```python
# 每个 Epoch 的日志
{
    "epoch": 42,
    "baby": "encouraged",
    "timestamp": 1718400000.0,
    "event": {
        "type": "value_conflict",
        "description": "你发现了一个可以改变一切的机会...",
        "intensity": 0.8
    },
    "critic_output": {
        "context": {...},
        "value_delta": {...},
        "frustration_delta": {...}
    },
    "reward": 0.31,
    "signals": {
        "directness": 0.32,
        "warmth": 0.85,
        ...
    },
    "value_vector": {
        "safety": 0.45,
        "creativity": 0.62,
        ...
    },
    "identity": "一个在挫折中坚持探索的人",
    "crystallized": true
}
```

## 7.2 可观测性指标

| 指标 | 说明 | 告警条件 |
|------|------|---------|
| reward 均值 | 近 100 Epoch 的平均 reward | < -0.5 |
| 价值观熵 | 价值观向量的信息熵 | 熵过高（随机漂移） |
| 身份变化频率 | 身份标签的变化次数 | 变化过频（不稳定） |
| 叙事一致性 | 叙事与行为历史的一致性分数 | < 0.5 |
| Phase Transition 频率 | 相变触发次数 | 过于频繁 |

---

# 八、部署与运行

## 8.1 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 LLM API
export ANTHROPIC_API_KEY=sk-...
export OPENAI_API_KEY=sk-...

# 运行实验
python -m sge.main --config config.yaml --epochs 100
```

## 8.2 实验输出

```
output/
├── encouraged/
│   ├── state/              # 最终状态
│   ├── logs/               # 完整日志
│   ├── value_trajectory.png  # 价值观演化图
│   └── identity_history.txt  # 身份演化历史
├── challenged/
│   └── ...
├── uncertain/
│   └── ...
└── report.md               # 实验报告
```

---

# 九、协作规范

## 9.1 文档优先

- 所有设计决策必须先写文档，再考虑实现
- 文档使用中文，技术术语保留英文
- 文档版本号与代码版本号同步

## 9.2 Git 规范

```
feat: 新功能
fix: 修复
docs: 文档
refactor: 重构
test: 测试
chore: 构建/工具
```

## 9.3 代码审查

- 所有代码变更必须经过审查
- 审查重点：与 SGE 研究纲领的一致性
- 不追求代码完美，追求假设验证
