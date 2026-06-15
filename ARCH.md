# SGE（Self Genesis Engine）架构文档

版本：v0.1

日期：2026-06-15

状态：草案

---

# 一、架构总览

## 1.1 设计哲学

SGE 的核心设计哲学是：**LLM 只是认知引擎，真正的"自我"存在于引擎内部的动态系统中。**

这与 AiBeing 的 Genome v10 引擎一致——LLM 是表达工具，不是智能来源。SGE 在此基础上增加了三层 AiBeing 没有的模块：Value Layer、Identity Layer、Narrative Layer。

## 1.2 架构全景

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SGE 单轮认知循环                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                        符号层（Symbolic）                          │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐   │  │
│  │  │ Value Layer  │  │ Identity     │  │ Narrative Layer       │   │  │
│  │  │ 价值观向量    │  │ Layer        │  │ 人生叙事              │   │  │
│  │  └──────┬──────┘  │ 身份标签      │  │ 过去→现在→未来        │   │  │
│  │         │         └──────┬───────┘  └───────────┬───────────┘   │  │
│  │         │                │                      │               │  │
│  │         └────────────────┼──────────────────────┘               │  │
│  │                          │                                      │  │
│  │                    ┌─────▼─────┐                                │  │
│  │                    │ Reflection │  ← 拱桥：经验→符号            │  │
│  │                    │ Layer      │                                │  │
│  │                    └─────┬─────┘                                │  │
│  └──────────────────────────┼──────────────────────────────────────┘  │
│                             │                                         │
│  ┌──────────────────────────┼──────────────────────────────────────┐  │
│  │                    经验层（Experiential）                        │  │
│  │                          │                                      │  │
│  │  ┌─────────────┐  ┌─────▼─────┐  ┌─────────────────────────┐  │  │
│  │  │ Time        │  │ Memory    │  │ KNN Style Retrieval     │  │  │
│  │  │ Metabolism  │  │ Layer     │  │ 经历检索                 │  │  │
│  │  │ 时间动力学   │  │ 记忆层    │  └────────────┬────────────┘  │  │
│  │  └──────┬──────┘  └─────┬─────┘               │               │  │
│  │         │               │                      │               │  │
│  │         └───────────────┼──────────────────────┘               │  │
│  │                         │                                      │  │
│  │                   ┌─────▼─────┐                                │  │
│  │                   │ Crystall-  │  ← 记忆筛选                   │  │
│  │                   │ ization    │                                │  │
│  │                   └─────┬─────┘                                │  │
│  └─────────────────────────┼───────────────────────────────────────┘  │
│                            │                                          │
│  ┌─────────────────────────┼───────────────────────────────────────┐  │
│  │                    感知层（Perception）                          │  │
│  │                          │                                      │  │
│  │  ┌─────────────┐  ┌─────▼─────┐  ┌─────────────────────────┐  │  │
│  │  │ Event       │  │ Critic    │  │ Thermodynamic Noise     │  │  │
│  │  │ Generator   │  │ 事件感知   │  │ 热力学噪声               │  │  │
│  │  │ 事件生成器   │  └─────┬─────┘  └────────────┬────────────┘  │  │
│  │  └──────┬──────┘        │                      │               │  │
│  │         │               │                      │               │  │
│  │         └───────────────┼──────────────────────┘               │  │
│  │                         │                                      │  │
│  │                   ┌─────▼─────┐                                │  │
│  │                   │ Reward    │  ← 情绪翻译器                   │  │
│  │                   │ Calculator│                                │  │
│  │                   └─────┬─────┘                                │  │
│  └─────────────────────────┼───────────────────────────────────────┘  │
│                            │                                          │
│  ┌─────────────────────────┼───────────────────────────────────────┐  │
│  │                    表达层（Expression）                          │  │
│  │                          │                                      │  │
│  │  ┌─────────────┐  ┌─────▼─────┐  ┌─────────────────────────┐  │  │
│  │  │ Hebbian     │  │ Actor     │  │ Async Memory            │  │  │
│  │  │ Learning    │  │ LLM 表达   │  │ 异步记忆存储/检索        │  │  │
│  │  │ 行为学习     │  └───────────┘  └─────────────────────────┘  │  │
│  │  └─────────────┘                                               │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 二、模块架构

## 2.1 模块依赖图

```
Event Generator
    │
    ▼
Critic (LLM) ──────────────────────┐
    │                               │
    ├─→ context (8D+4D=12D) ───────┼─→ compute_signals → Noise → KNN → Prompt → Actor
    │                               │
    ├─→ frustration_delta (5D) ────┼─→ Reward Calculator → Hebbian Learning
    │                               │
    ├─→ relationship_delta (3D) ───┼─→ Relationship EMA
    │                               │
    └─→ drive_satisfaction (5D) ───┘
                                        │
    Time Metabolism ────────────────────┤
    (冷却 + 饥饿)                        │
                                        │
    Crystallization Gate ───────────────┤
    (记忆筛选)                           │
                                        │
    Value Layer (EMA) ←─────────────────┘
        │
        ▼
    Identity Layer (凝聚)
        │
        ▼
    Narrative Layer (串联)
```

## 2.2 核心数据流

### 单轮认知循环

```
1. Event Generator → 生成模拟人生事件
2. Time Metabolism → 更新 frustration（冷却+饥饿）
3. Critic (LLM) → 感知事件 → context(12D) + delta(5D) + rel(3D) + sat(5D)
4. Relationship EMA → 融合关系变化 → 更新 relationship_4d
5. Reward Calculator → frustration 变化 → reward(float)
6. Drive Baseline Evolution → 长期性格漂移
7. Crystallization Gate → 判断是否结晶为长期记忆
8. Compute Signals → 神经网络：context+drives+recurrent → 8D signals
9. Thermodynamic Noise → 高挫败感 → 高温度 → 高噪声
10. KNN Style Retrieval → 检索相似经历 → few-shot
11. Build Actor Prompt → 组装完整 prompt
12. Actor (LLM) → 生成内心独白 + 行为选择
13. Value Layer (EMA) → 根据行为选择更新价值观向量
14. Identity Layer → 从价值观凝聚身份标签
15. Narrative Layer → 将事件串联到人生叙事
16. Hebbian Learning → 根据 reward 更新神经网络权重
17. Async Memory → 异步存储到长期记忆
```

---

# 三、核心模块设计

## 3.1 Event Generator（事件生成器）

**职责**：生成模拟人生事件

**事件类型**：

| 类型 | 描述 | 价值观影响 |
|------|------|----------|
| 成功 | 目标达成、获得认可 | 强化当前价值观 |
| 失败 | 目标未达、遭遇挫折 | 质疑当前价值观 |
| 关系 | 建立/深化/破裂关系 | 考验联结 vs 自主 |
| 探索 | 新领域、新体验 | 考验安全 vs 探索 |
| 风险 | 需要做艰难选择 | 考验安全 vs 自由 |
| 价值冲突 | 两个价值观不可兼得 | 迫使价值观排序 |

**动态生成**：根据当前 Value Layer 的权重，生成针对性的价值困境事件。例如，如果 AI 的"安全"权重很高，生成更多需要冒险的事件来考验它。

## 3.2 Critic（事件感知）

**职责**：将事件文本转换为结构化数值

**输出维度**：

| 输出 | 维度 | 来源 |
|------|------|------|
| context | 12D | 8D 事件情境 + 4D 关系状态 |
| frustration_delta | 5D | 事件对 5 个驱动的影响 |
| relationship_delta | 3D | 事件对关系的影响 |
| drive_satisfaction | 5D | 事件直接满足了多少需求 |

**LLM 配置**：temperature=0.2（稳定结构化输出）

## 3.3 Value Layer（价值观层）

**职责**：从经历中涌现价值观

**数据结构**：

```python
class ValueVector:
    # 元价值（固定，不参与 EMA 更新）
    truth_seeking: float = 0.5
    freedom: float = 0.5

    # 具体价值观（从经历中涌现）
    safety: float = 0.0
    creativity: float = 0.0
    connection: float = 0.0
    autonomy: float = 0.0
    justice: float = 0.0
    compassion: float = 0.0

    def ema_update(self, event_delta: dict, event_intensity: float):
        alpha = clip(0.15 + 0.5 * event_intensity, 0.15, 0.65)
        for key, delta in event_delta.items():
            posterior = clip(self.__dict__[key] + delta, -1, 1)
            self.__dict__[key] = alpha * posterior + (1 - alpha) * self.__dict__[key]
```

## 3.4 Identity Layer（身份层）

**职责**：从价值观凝聚身份标签

**机制**：
- 定期（每 N 个 Epoch）将价值观向量 + 关键记忆输入 LLM
- LLM 生成身份描述（"我是谁"）
- 身份描述与行为历史交叉验证

## 3.5 Narrative Layer（叙事层）

**职责**：构建连贯的人生故事

**机制**：
- 将结晶记忆串联为因果链
- LLM 定期生成"人生叙事"（过去 → 现来 → 未来）
- 支持叙事断裂与重建（Phase Transition）
- 定期一致性扫描和修复

---

# 四、技术选型

## 4.1 核心技术栈

| 组件 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | 与 AiBeing 一致，生态丰富 |
| LLM（Critic） | Haiku / Qwen | 低成本，稳定结构化输出 |
| LLM（Actor） | Sonnet / GPT-4o | 高质量表达 |
| 结构化存储 | SQLite | 轻量级，单机部署 |
| 向量存储 | ChromaDB / FAISS | 语义检索 |
| 异步框架 | asyncio | 与 AiBeing 一致 |
| 状态持久化 | JSON 文件 | 简单可靠 |

## 4.2 AiBeing 组件复用

| AiBeing 组件 | SGE 用途 | 改造程度 |
|-------------|---------|---------|
| Critic prompt + 解析 | 事件感知 | 低 |
| Time Metabolism | 时间动力学 | 直接复用 |
| Relationship EMA | 价值观 EMA | 低（扩展维度） |
| Hebbian Learning | 行为模式学习 | 直接复用 |
| Phase Transition | 叙事断裂 | 直接复用 |
| Crystallization | 记忆筛选 | 低 |
| KNN + Hawking 辐射 | 经历检索 | 直接复用 |
| Thermodynamic Noise | 行为不确定性 | 直接复用 |

---

# 五、数据架构

## 5.1 状态持久化

```
state/
├── agent_state.json          # drive_state, drive_baseline, W1, W2, b1, b2, recurrent
├── value_vector.json         # 价值观向量
├── identity.json             # 身份标签 + 最后更新时间
├── narrative.json            # 人生叙事文本
├── relationship_ema.json     # 关系 EMA 状态
├── frustration.json          # 当前 frustration 值
└── metadata.json             # age, interaction_count, total_reward, epoch
```

## 5.2 记忆存储

```
memory/
├── style_memory.json         # 风格记忆池（Genesis + Personal）
├── crystallized_events.json  # 结晶事件（带 context 向量）
└── evermemos.db              # 长期记忆（SQLite）
```

## 5.3 日志与观测

```
logs/
├── epoch_log.jsonl           # 每个 Epoch 的完整输入/输出
├── value_trajectory.jsonl    # 价值观向量时间序列
├── identity_history.jsonl    # 身份标签演化历史
└── reward_history.jsonl      # reward 时间序列
```

---

# 六、并发与容错

## 6.1 并发模型

```python
async with self._turn_lock:
    await self._cognitive_cycle(event)
```

单轮认知循环由 `asyncio.Lock` 串行化，确保内部状态一致性。

## 6.2 容错设计

| 故障场景 | 处理方式 |
|---------|---------|
| LLM API 超时 | 重试一次，失败则使用默认值 |
| LLM JSON 解析失败 | 多层容错解析，最终使用默认值 |
| SQLite 写入失败 | 打印错误，不阻塞认知循环 |
| 向量数据库不可用 | 降级为随机检索 |

## 6.3 中断与恢复

状态持久化支持中断和恢复：
- 每个 Epoch 结束后自动保存状态
- 重启后从最后保存的状态恢复
- 记忆和权重不丢失
