# SGE 认知工具的具体应用

> **本文档系统化 SGE 设计中 7 个认知科学工具的具体应用**。当前 SGE 明确用了 3 个（双系统、预测加工、记忆分层），其他 4 个（贝叶斯、BDI、元认知、经典架构）如何应用是开放问题。
>
> 相关文档：[SGE-Key-Insights 洞察 9](../sge-learning/SGE-Learning-from-AiBeing.md)（7 个工具列表）、[Cognitive-Architectures-Overview.md](./Cognitive-Architectures-Overview.md)（8 个经典架构）、[Shared-Cognitive-Science-Toolbox.md](./Shared-Cognitive-Science-Toolbox.md)（工具箱详细说明）。

---

# 一、7 个认知科学工具清单

依据 [SGE-Key-Insights 洞察 9](../sge-learning/SGE-Learning-from-AiBeing.md) 和 [Shared-Cognitive-Science-Toolbox.md](./Shared-Cognitive-Science-Toolbox.md)：

| # | 工具 | SGE 当前应用 | 应用程度 |
|---|------|------------|---------|
| 1 | 经典认知架构 | 模块划分借鉴 | **部分** |
| 2 | 贝叶斯状态更新 | 价值向量的不确定性？ | **未用** |
| 3 | 预测加工理论 | Identity Layer 预测行为 | **已用** |
| 4 | 双系统理论 | 认知失调触发反思 | **已用** |
| 5 | 记忆系统分层 | Memory Layer 三层 | **已用** |
| 6 | BDI 模型 | 信念/欲望/意图？ | **未用** |
| 7 | 元认知 | 反思的反思？ | **未用** |

**当前应用率**：3/7 = 43%

---

# 二、已用工具的强化

## 2.1 预测加工（Predictive Processing）

### 2.1.1 当前应用

[ARCH §1.1](../../ARCH.md) 中提到：
> Identity Layer 基于 Narrative 预测自身行为，实际经历与预测的"预测误差"是人格修正和情绪涌现的根本源泉。

### 2.1.2 强化方向

**当前不足**：预测只有"Identity → 行为"一条路径。完整预测加工应是**多层级**的：

```
最高层：Narrative → 预测整个生命故事
        ↓
中高层：Identity → 预测行为模式
        ↓
中层：Value → 预测具体选择
        ↓
低层：Hebbian → 预测行为信号
        ↓
最低层：Drive → 预测情绪反应
```

### 2.1.3 实施建议

**Phase 2 M2.1 完整架构时**：
- 在 Value Layer 上加一个"预测机制"——根据 ValueVector 预测 Actor 应该选什么
- 用预测误差驱动 Value Layer 更新（类似反向传播）

## 2.2 双系统理论（Dual-System）

### 2.2.1 当前应用

[ARCH §1.1](../../ARCH.md) 和 [SGE-Key-Insights 洞察 6](../../SGE-Key-Insights.md)：
> 90% 的日常事件只沉淀到 Memory Layer，不触发重度反思。只有遭遇认知失调才激活系统 2。

### 2.2.2 强化方向

**当前不足**：双系统的切换是**硬阈值**（认知失调 > 阈值才切换）。完整双系统应是**软切换**：

```
硬切换（当前）：
  if 认知失调 > 0.5:
      启用系统 2（反思）

软切换（建议）：
  系统 2 强度 = sigmoid(认知失调 - 0.3)  # 渐进式
  # 认知失调 0.3 → 50% 启用系统 2
  # 认知失调 0.5 → 88% 启用系统 2
  # 认知失调 0.7 → 95% 启用系统 2
```

### 2.2.3 实施建议

**M1.1 阶段**：
- 保留硬切换（降低复杂度）
- 记录"接近阈值但未达"的 Epoch，为后续软切换优化提供数据

## 2.3 记忆系统分层（Memory Layer）

### 2.3.1 当前应用

[PRD §4.1 FR-2](../../PRD.md) 明确三层：
- 工作记忆：当前事件
- 情节记忆：带时间戳的关键事件
- 语义记忆：抽象化的自我认知图谱

### 2.3.2 强化方向

**当前不足**：记忆之间的"转换机制"不清晰。Atkinson-Shiffrin 模型的"复述（rehearsal）"和"巩固（consolidation）"在 SGE 中如何实现？

```
工作记忆（短期） → 复述 → 情节记忆（中期） → 巩固 → 语义记忆（长期）
```

### 2.3.3 实施建议

**Phase 2 M2.1**：
- 复述：当一个事件被 K 次检索（KNN）时，自动提升为情节记忆
- 巩固：当一个情节记忆被 N 次引用时，提取抽象模式到语义记忆
- 这类似"睡眠巩固记忆"——可在非活跃时段运行

---

# 三、未用工具的应用方案

## 3.1 贝叶斯状态更新（Bayesian State Update）

### 3.1.1 当前缺失

SGE 的 Value Layer 是**确定性数值**（V = [safety: 0.7, ...]）。但现实中"AI 重视安全"应该有**不确定性**（AI 自己也可能不确定）。

### 3.1.2 应用方案

**新设计**：ValueVector 升级为**概率分布**。

```python
class BayesianValueVector:
    def __init__(self):
        # 原来是确定性值
        # self.safety = 0.5
        # 改为 (mean, variance) 对
        self.safety = (0.5, 0.1)  # (均值, 方差)
        # ...

    def update(self, evidence: Dict[str, float]):
        """贝叶斯更新"""
        for v in self.values:
            prior_mean, prior_var = self.__dict__[v]
            # 假设 evidence 是 noisy observation
            evidence_var = 0.05  # 观测噪声
            # 贝叶斯更新公式
            posterior_var = 1.0 / (1.0/prior_var + 1.0/evidence_var)
            posterior_mean = posterior_var * (prior_mean/prior_var + evidence[v]/evidence_var)
            self.__dict__[v] = (posterior_mean, posterior_var)

    def confidence(self) -> float:
        """返回整体不确定性（值越小越自信）"""
        return sum(var for _, var in self.__dict__.values() if isinstance(_, float)) / 6
```

### 3.1.3 应用场景

- **维度 1：反思深度**（[SGE-Authenticity-vs-Simulation-Operationalization.md](../sge-core/SGE-Authenticity-vs-Simulation-Operationalization.md)）—— 高 confidence + 高反思 = 真正的"我"
- **失败 4（方向性差）**—— 如果 confidence 持续上升（从 0.1 到 0.01），说明 AI 在"确信"
- **元认知**—— confidence 反映 AI 对自身价值观的把握

### 3.1.4 实施建议

**M1.1 阶段**：
- 不实施（增加复杂度）
- 仅在日志中记录 value_delta 的数值（已实施）

**Phase 2 M2.1**：
- 实施贝叶斯 Value Layer
- 增加 confidence 指标

## 3.2 BDI 模型（Belief-Desire-Intention）

### 3.2.1 当前缺失

SGE 没有明确的"意图"概念。AI 婴儿有"价值观"（类似 desire）和"行为"（类似 intention），但**没有 belief 的显式表示**。

### 3.2.2 应用方案

**新设计**：增加 **Belief Layer**（信念层）

```python
class BeliefDesireIntention:
    def __init__(self):
        # 信念（Belief）：关于世界的认知
        self.beliefs = {
            "世界是危险的": 0.3,  # 0.0-1.0
            "我是有能力的": 0.7,
            "他人是可信的": 0.5,
            # ...
        }

        # 欲望（Desire）：想要的状态
        # = Value Layer
        self.desires = ValueVector()

        # 意图（Intention）：计划的行为
        self.intentions = []  # 当前活跃的计划
```

### 3.2.3 应用场景

- **身份描述**：[FR-5 Identity Layer](../../PRD.md) 可融合 Belief + Value → "我是一个[X]的人，因为我认为[Y]"
- **反思**：[FR-3 Reflection Layer](../../PRD.md) 可反思"我的信念是否合理"
- **叙事**：[FR-6 Narrative Layer](../../PRD.md) 可串联 "我相信 X，所以想要 Y，所以做了 Z"

### 3.2.4 实施建议

**Phase 2 M2.1**：
- 增加 Belief Layer
- Identity Layer 同时使用 Belief + Value

**Phase 3+**：
- Belief 可作为"暗知识"的一部分（被 Hebbian 调节）
- 反思可显式更新 Belief

## 3.3 元认知（Meta-Cognition）

### 3.3.1 当前缺失

SGE 的反思是"对经历反思"，但**没有"对反思的反思"**（元认知）。这正是 [Phase 3 M3.2 元认知层](../../ROADMAP.md) 的目标。

### 3.3.2 应用方案

**当前**：[PRD §4.1 FR-3](../../PRD.md) 反思是对事件的反思
**M3.2 增加**：元认知是对**反思过程的反思**

```
L0：行为（action）
L1：事件反思（"为什么我做了这个？"）  ← 当前 FR-3
L2：反思过程的反思（"我的反思方式合理吗？"）  ← M3.2
L3：元-元认知（"我为什么会这样反思？"）  ← 未来
```

### 3.3.3 应用场景

- **维度 1：反思深度**（[SGE-Authenticity-vs-Simulation-Operationalization.md](../sge-core/SGE-Authenticity-vs-Simulation-Operationalization.md)）—— L2/L3 反思的具体实施
- **失败 6（反思无效）**—— 如果 L1 反思无效，可尝试 L2 元认知
- **AI 的"成长"**—— 元认知让 AI 婴儿能"自我教育"

### 3.3.4 实施建议

**Phase 3 M3.2 专门实施**：
- 增加 Meta-Cognition Layer
- 反思的反思（meta-reflection）触发条件：连续 N 次反思无新信息

## 3.4 经典认知架构（Classical Cognitive Architectures）

### 3.4.1 当前应用

[Cognitive-Architectures-Overview.md](./Cognitive-Architectures-Overview.md) 已分析 8 个经典架构（SOAR/ACT-R/GWT-LIDA/CLARION/包容架构/心智社会/OpenCog/Sigma），SGE 模块划分参考了这些。

### 3.4.2 当前不足

只借鉴了"模块划分"，**没有借鉴具体算法**。

| 经典架构 | 核心算法 | SGE 是否借鉴 |
|---------|---------|------------|
| SOAR | 决策周期 + 块（chunking） | 否 |
| ACT-R | 声明性记忆 + 产生式 | 部分（Hebbian 类似） |
| GWT/LIDA | 全局工作空间 + 意识广播 | 否 |
| CLARION | 显隐分离 + 自下而上 | 部分 |
| 包容架构 | 层次反应 | 否 |
| 心智社会 | 多 agent 协作 | 否 |
| OpenCog | 节点+关系 | 否 |
| Sigma | 图形化记忆 | 否 |

### 3.4.3 应用方案：SOAR 的"块（chunking）"机制

**SOAR chunking**：当 AI 解决了一个问题，将解决过程"压缩"为一个块，存储在记忆中。下次遇到类似问题，直接调用块。

**SGE 应用**：
- 在 Memory Layer 中增加 "chunk" 类型
- 当反思产生新的价值判断时，创建一个 chunk（value_delta + 触发条件）
- 下次遇到类似事件，直接使用 chunk

```python
class ChunksMemory:
    def store_chunk(self, value_delta: dict, trigger: str, outcome: str):
        chunk = Chunk(
            trigger=trigger,
            value_delta=value_delta,
            outcome=outcome,
            created_at=epoch
        )
        self.chunks.append(chunk)

    def retrieve_chunk(self, event: Event) -> Optional[Chunk]:
        for chunk in self.chunks:
            if chunk.matches(event):
                return chunk
        return None
```

### 3.4.4 应用方案：CLARION 的"显隐分离"

**CLARION**：显式知识 + 隐式知识双轨，与 SGE 的 Value Layer + Hebbian 类似。

**SGE 强化**：
- Value Layer（显式）+ Hebbian（隐式）已经存在
- 但缺乏"显隐转化"机制——什么时候从显式变隐式，反之亦然
- CLARION 提供了"提取"和"内化"的具体算法

```python
def extract_to_explicit(hebbian_state: np.ndarray) -> ValueVector:
    """Hebbian 状态 → Value Layer（提取）"""
    # 通过 LLM 把 W2 矩阵翻译为可读价值观描述
    return llm_translate_hebbian(hebbian_state)

def internalize_to_implicit(value_vector: ValueVector, signal: np.ndarray) -> np.ndarray:
    """Value Layer → Hebbian（内化）"""
    # 把价值观"压缩"为 W2 权重
    return llm_compress_to_hebbian(value_vector, signal)
```

### 3.4.5 实施建议

**Phase 2 M2.1**：
- 实施 SOAR 的 chunking 机制
- 强化 Memory Layer

**Phase 2 M2.2**：
- 实施 CLARION 的显隐转化
- 强化"反思-内化"循环

---

# 四、综合应用方案

## 4.1 短期（M1.1-M1.3）：维持当前 + 记录数据

- 维持 Value Layer（确定性）
- 强化双系统软切换（数据驱动优化）
- 强化记忆巩固机制
- 不实施贝叶斯/BDI/元认知

## 4.2 中期（M2.1-M2.2）：增加 3 个新工具

- **贝叶斯 Value Layer**：value + uncertainty
- **Belief Layer**：BDI 的 B（信念）
- **SOAR chunking**：记忆压缩

## 4.3 长期（M3.x）：元认知成熟

- **Meta-Cognition Layer**：M3.2 实施
- **CLARION 显隐转化**：强化反思-内化循环
- **8 个经典架构的核心思想**：在 SGE 中找到对应

---

# 五、5 个工具的协同效应

5 个工具有**相互加强**的关系：

```
贝叶斯（不确定性）+ 双系统（软切换）
  → 软切换阈值 = sigmoid(认知失调 - confidence)
  → confidence 高的 AI 更少触发反思（因为自信）

BDI（Belief-Desire-Intention）+ 元认知
  → 元认知反思 Belief 的合理性
  → Identity Layer 用 Belief + Desire 描述

SOAR chunking + 记忆分层
  → chunk 是情节记忆的"压缩版"
  → 巩固机制把 chunk 提升为语义记忆

预测加工 + 贝叶斯
  → 预测的不确定性 = 贝叶斯 confidence
  → 自由能 = 预测误差 + 不确定性惩罚
```

**最终架构 = 当前 EMA+Hebbian + 4 个新工具** = 8 维认知工具的完整应用。

---

# 六、应用成熟度评估

| 工具 | M1.1 | M2.1 | M2.2 | M3.2 |
|------|------|------|------|------|
| 1. 经典架构 | 借鉴 SOAR chunking | 强化 | 完整 | 完整 |
| 2. 贝叶斯 | 仅记录 | 实施 | 强化 | 强化 |
| 3. 预测加工 | 基础 | 多层级 | 完整 | 完整 |
| 4. 双系统 | 硬切换 | 软切换 | 强化 | 强化 |
| 5. 记忆分层 | 3 层 | +chunk | 巩固机制 | 完整 |
| 6. BDI | 无 | Belief Layer | 强化 | 完整 |
| 7. 元认知 | 无 | 雏形 | 强化 | 完整 |

**最终工具应用率**：3/7 → 7/7 = 100%

---

# 七、与失败模式的关系

| 工具 | 应对的失败模式 |
|------|------------|
| 贝叶斯 | 失败 4（方向性差）、失败 11（维度相关） |
| BDI | 失败 6（反思无效）、失败 7（身份不结晶） |
| 元认知 | 失败 6（反思无效）、失败 13（真我失败） |
| SOAR chunking | 失败 8（叙事崩溃） |
| CLARION 显隐转化 | 失败 12（Hebbian 不变） |

**5 个新工具可以应对 5 种失败模式**——是 SGE 演进的"安全网"。

---

# 八、相关文档

- **认知架构综述**：[Cognitive-Architectures-Overview.md](./Cognitive-Architectures-Overview.md)
- **认知工具箱**：[Shared-Cognitive-Science-Toolbox.md](./Shared-Cognitive-Science-Toolbox.md)
- **A→B 工具共享**：[SGE-Key-Insights 洞察 9](../sge-learning/SGE-Learning-from-AiBeing.md)
- **当前架构**：[ARCH.md](../../ARCH.md)
- **失败模式**：[SGE-Failure-Mode-Deep-Analysis.md](../sge-feasibility/SGE-Failure-Mode-Deep-Analysis.md)
- **替代架构**：[SGE-Alternative-Architectures.md](../sge-feasibility/SGE-Alternative-Architectures.md)

---

**创建日期**：2026-06-15
**维护者**：Bisen & Claude
**下次更新**：M2.1 实施时，根据实际需要调整
