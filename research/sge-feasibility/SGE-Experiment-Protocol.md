# SGE 实验运行与评估手册

> **本文件是 SGE 所有实验（M1.1/M1.2/M1.3/M2.x/M3.x）的运行协议与评估规范**，统一收纳：
> - 实验运行前提与依赖
> - 可执行步骤
> - 可复现性约束
> - 评估指标计算方法
> - 判定阈值与判定流程
> - 数据记录与日志规范
> - 异常处理
>
> 详细术语参见 [references/Glossary.md](../../../references/Glossary.md)；验收标准（高层目标）见 [PRD §6](../../../PRD.md)；里程碑定义见 [ROADMAP.md](../../../ROADMAP.md)。

---

# 一、实验运行前提

## 1.1 环境要求

| 项目 | 要求 | 备注 |
|------|------|------|
| Python | 3.11+ | 与 AiBeing 一致 |
| LLM API Key | Anthropic / OpenAI 之一 | 至少配置一个 |
| 存储 | 本地文件系统（SQLite + JSON） | 不需要分布式数据库 |
| 计算资源 | 单机即可 | 支持 3 AI 婴儿并行（[PRD §5.1 性能](../../../PRD.md)） |
| 网络 | 能访问 LLM API | M1 阶段每次 Epoch 需 2-3 次 LLM 调用 |

## 1.2 依赖项

参见 [DEVELOP.md §二 技术栈](../../../DEVELOP.md)。**关键依赖**：
- `litellm`（统一多模型调用）
- `chromadb`（向量检索）
- `sqlite3`（Python 内置）
- `asyncio`（Python 内置）
- `pyyaml`（配置管理）
- `structlog`（结构化日志）

## 1.3 模型选择

| 阶段 | Critic 模型 | Actor 模型 | 理由 |
|------|------------|-----------|------|
| M1.1（原型） | Haiku / GPT-4o-mini | 同 Critic | 降低成本（~$1-10） |
| M1.2（分化） | Haiku / GPT-4o-mini | 同 Critic | 仅观察 Value Layer |
| M1.3（反合理化） | Haiku / GPT-4o-mini | Sonnet / GPT-4o | 行为质量需提升 |
| M2.x（完整） | Sonnet / GPT-4o | Sonnet / GPT-4o | 全栈使用中等模型 |
| M3.x（系统完善） | Sonnet / GPT-4o | Opus / GPT-4-turbo | 元认知需要更强推理 |

> 模型版本会过期，建议用 `litellm` 的模型别名（如 `claude-3-haiku-latest`）而非具体快照版本号。

---

# 二、实验运行步骤

## 2.1 通用流程

```
0. 准备阶段
   - 设置 LLM API Key
   - 准备配置文件（[DEVELOP §六 配置文件](../../../DEVELOP.md)）
   - 选择种子 N（5 ≤ N ≤ 10）

1. 启动阶段
   - 初始化 AI 婴儿（Event Generator + Critic + Actor + Value Layer + Memory + Hebbian）
   - 加载初始状态（[ARCH §5 数据架构](../../../ARCH.md)）
   - 加载事件流

2. 运行阶段
   - 对每个 Epoch 重复：
     a. Event Generator → 生成事件
     b. Critic → 解析事件（FR-7）
     c. Time Metabolism → 更新 frustration
     d. Reward Calculator → 计算 reward
     e. Crystallization Gate → 判断是否结晶
     f. Compute Signals → 神经网络计算
     g. Thermodynamic Noise → 加入噪声
     h. KNN Retrieval → 检索相似经历
     i. Build Prompt → 组装 prompt
     j. Actor → 生成行为选择
     k. Value Layer → 更新价值观
     l. Identity Layer → 更新身份（Phase 2+）
     m. Narrative Layer → 更新叙事（Phase 2+）
     n. Hebbian → 更新 W2 权重
     o. Async Memory → 持久化

3. 评估阶段
   - 计算 §四 评估指标
   - 与 §五 判定阈值对比
   - 生成报告

4. 报告阶段
   - 输出 value_trajectory.jsonl
   - 输出 identity_history.jsonl
   - 输出 experiment_report.md
```

## 2.2 M1.1 特定步骤

```
0. 准备：3 个配置文件（鼓励 / 失败 / 不确定）
1. 启动：1 个 AI 婴儿（鼓励组）
2. 运行：50-100 Epoch
3. 评估：
   - 涌现幅度（§四.1.1）
   - 收敛度（§四.1.2）
   - 方向一致性（§四.1.3）
4. 报告：value_trajectory.jsonl + 控制台输出
```

## 2.3 M1.2 特定步骤

```
0. 准备：3 个事件流（鼓励 / 失败 / 不确定）
1. 启动：3 个 AI 婴儿（并行）
2. 运行：每个 100 Epoch，相同元价值种子（真实=0.5, 自由=0.5）
3. 评估：人格差异度（§四.1.4）
4. 报告：3 组 value_trajectory 对比图
```

## 2.4 M1.3 特定步骤

```
0. 准备：1 个 AI 婴儿（已完成 M1.1）
1. 启动：加载已训练 100 Epoch 的 Value Layer 状态
2. 运行：
   - Epoch A：给定与价值观矛盾的事件，观察行为
   - Epoch B：触发反思（注入认知失调）
   - Epoch C：再给定相似事件，观察行为是否改变
3. 评估：
   - 行为变化率（§四.1.5）
   - 反思深度（§四.1.6）
4. 报告：行为选择熵变化曲线
```

## 2.5 M2.x 特定步骤

参见 [ROADMAP §M2.1-M2.3](../../../ROADMAP.md)。

---

# 三、可复现性约束

> **核心原则**：相同的初始种子 + 相同的事件序列 = 相同的结果（[PRD §5.3](../../../PRD.md)）。

## 3.1 必须固定的随机源

| 随机源 | 固定方法 |
|-------|---------|
| 事件生成器随机性 | 使用 `random.seed(N)` 在每次启动时设置 |
| LLM 输出的随机性 | Critic temperature=0.2（接近确定性），Actor temperature=0.5-0.9（保留创造性但需记录） |
| Crystallization 评分 | 使用固定权重（reward × novelty × engagement × harmony） |
| Thermodynamic Noise | 由 frustration 唯一决定，无额外随机性 |
| KNN Retrieval | 检索过程确定性（无随机性） |

## 3.2 必须记录的内容

参见 [ARCH §5.3 日志与观测](../../../ARCH.md)：

- 每个 Epoch 的完整输入/输出
- 价值观向量时间序列
- 身份标签演化历史
- 叙事演变过程
- LLM 调用的 token 消耗和延迟
- 任何异常（API 失败、解析错误、超时）

## 3.3 不应记录的敏感内容

- API Key
- 用户上传的隐私数据（SGE 本身不涉及，但日志系统应设计为可屏蔽）

---

# 四、评估指标计算

> **可复现性约束**：所有度量基于 N≥5 次独立运行（不同随机种子，相同事件序列），报告均值 ± 标准差。

## 4.1 必达指标（对应 PRD §6.1）

### 4.1.1 涌现幅度（Emergence Magnitude）

```
em = (1/D) × Σᵢ ||V_final[i] - V_initial[i]||₂
```

- `D = 6`（具体价值观维度数）
- `V_initial[i]`：第 i 个具体价值观的初始值
- `V_final[i]`：第 i 个具体价值观在 100 Epoch 后的值
- **判定**：emergence_magnitude > 0.3

### 4.1.2 收敛度（Convergence）

```
conv = (1/D) × Σᵢ std({V_final_N[i] : N in seeds})
```

- `V_final_N[i]`：第 N 个种子下，第 i 个价值观的最终值
- `seeds = {1, 2, 3, 4, 5}`
- **判定**：convergence < 0.1

### 4.1.3 方向一致性（Direction Coherence）

```
dir = cos(V_final, V_event_weighted)
V_event_weighted = Σₑ (event_weight[e] × V_delta[e])
```

- `V_event_weighted`：所有事件的"价值冲击"按事件权重加和
- `cos(a, b) = (a · b) / (||a|| × ||b||)`
- **判定**：direction_coherence > 0.5

### 4.1.4 人格差异度（Personality Divergence）

```
F = MS_between / MS_within
MS_between = Σₖ nₖ × ||V_k - V_grand||₂² / (K - 1)
MS_within = Σₖ Σⱼ ||V_kⱼ - V_k||₂² / (N - K)
```

- K = 3 组（鼓励/失败/不确定）
- N = 总运行次数
- **判定**：F 统计量 > F 临界值（α=0.05, df=2, N-3）

### 4.1.5 行为变化率（Behavior Change Rate）

```
kl = D_KL(P_pre || P_post)
P_pre, P_post：反思前后的行为选择分布（对 5+ 个相似事件的行为选择）
D_KL(P||Q) = Σ P(x) log(P(x) / Q(x))
```

- **判定**：KL 散度 > 0.2

### 4.1.6 反思深度（Reflection Depth）

```
depth = ||V_post - V_pre||₂
```

- V_pre, V_post：反思前后的 ValueVector
- **判定**：depth > 0.05

## 4.2 期望指标（对应 PRD §6.2）

### 4.2.1 身份-行为一致性

```
consistency = mean(LLM_judge(identity_desc, behavior_history) for each identity)
LLM_judge ∈ [0, 1]
```

### 4.2.2 身份熵

```
H = -Σₛ p(s) log₂ p(s)
p(s) = 身份标签 s 在时间窗口内的频率
```

- **判定**：H < 1.0

### 4.2.3 叙事一致性

```
consistency = LLM_judge(narrative, crystallized_events)
LLM_judge ∈ [0, 1]
```

- **判定**：consistency > 0.6

### 4.2.4 收敛速度

```
drift = mean(||V[t+1] - V[t]||₂ for t in last_200_epochs)
```

- **判定**：drift < 0.01 / Epoch

### 4.2.5 可追溯性

```
traceability = count(successful_answers) / count(total_questions)
successful_answer = 1 if external LLM 找到 ≥ 1 个支撑事件 else 0
```

- **判定**：traceability > 0.8

### 4.2.6 W2 影响度

```
kl = D_KL(P_with_hebbian || P_without_hebbian)
```

- P_with_hebbian, P_without_hebbian：保留/移除 Hebbian 学习时 Actor 输出的分布
- **判定**：KL 散度 > 0.1

### 4.2.7 道德选择多样性

```
diversity = 1 - max(f(choice = c) for c in {鼓励, 失败, 不确定})
```

- f(choice = c)：选择 c 的频率
- **判定**：diversity > 0.5（即 3 组各有不同倾向）

---

# 五、判定流程

## 5.1 假设验证判定树

```
启动 M1.1 实验
    │
    ▼
涌现幅度 > 0.3？
    │
    ├── 否 → 重新设计 Value Layer（停止实验）
    │
    └── 是 → 继续
         │
         ▼
    收敛度 < 0.1？
         │
         ├── 否 → 调整 EMA 参数或事件多样性
         │
         └── 是 → 继续
              │
              ▼
         方向一致性 > 0.5？
              │
              ├── 否 → 检查 Critic 输出质量
              │
              └── 是 → M1.1 通过 ✓
                   │
                   ▼
              启动 M1.2 实验
                   │
                   ▼
              F 统计量 > 临界值？
                   │
                   ├── 否 → 增强事件流差异性
                   │
                   └── 是 → M1.2 通过 ✓
                        │
                        ▼
                   启动 M1.3 实验
                        │
                        ▼
                   KL > 0.2 AND 反思深度 > 0.05？
                        │
                        ├── 否 → 反思机制需重新设计
                        │
                        └── 是 → M1.3 通过 ✓
                             │
                             ▼
                        Phase 1 全部通过 → 进入 Phase 2
```

## 5.2 失败应对

| 失败模式 | 应对措施 |
|---------|---------|
| 价值观只是随机漂移（M1.1 涌现幅度 > 0.3 但 方向一致性 < 0） | 检查 Critic 输出的 value_delta 是否合理 |
| 价值观收敛到训练数据众数 | 增加反合理化测试，验证涌现真实性 |
| 3 组 AI 婴儿无差异 | 强化事件流差异（鼓励/失败/不确定的事件生成器需要本质不同） |
| 反思只改 ValueLayer 不改 Hebbian | 反思的 Reward 信号应同时影响两条学习轨 |
| 成本超出预算 | 使用更小模型或减少 Epoch 数 |

---

# 六、日志与报告

## 6.1 日志格式

参见 [DEVELOP §七 日志与观测](../../../DEVELOP.md) 和 [ARCH §5.3](../../../ARCH.md)。

每个 Epoch 输出 JSONL 格式日志：
```json
{
  "epoch": 42,
  "seed": 1,
  "baby": "encouraged",
  "timestamp": 1718400000.0,
  "event": {
    "type": "value_conflict",
    "description": "...",
    "intensity": 0.8
  },
  "critic_output": {
    "context": {...},
    "value_delta": {...},
    "frustration_delta": {...}
  },
  "reward": 0.31,
  "signals": {...},
  "value_vector": {
    "safety": 0.45,
    "creativity": 0.62,
    ...
  },
  "identity": "...",
  "crystallized": true,
  "errors": []
}
```

## 6.2 报告输出

每个实验结束后生成 `experiment_report.md`：
- 实验基本信息（阶段、日期、模型、参数）
- 评估指标结果（4.1 / 4.2 中的具体数值）
- 判定结果（5.1 判定树的具体分支）
- 价值轨迹图（PNG/SVG）
- 失败模式与改进建议

## 6.3 异常日志

异常必须显式记录在 `errors` 字段：
- LLM API 超时
- LLM JSON 解析失败（多层容错解析后的最终结果）
- SQLite 写入失败
- 向量数据库不可用

---

# 七、异常处理

| 异常 | 处理方式 | 是否阻塞 |
|------|---------|---------|
| LLM API 超时 | 重试 1 次（指数退避）；失败则使用默认值 | 否 |
| LLM JSON 解析失败 | 多层容错解析（regex → 截取 → 默认值） | 否 |
| SQLite 写入失败 | 打印错误，继续认知循环（内存状态不受影响） | 否 |
| 向量数据库不可用 | 降级为随机检索（标 warning） | 否 |
| Critic 输出明显异常（如 value_delta 全为 0） | 记录异常 + 使用历史均值替代 | 否 |
| 累计错误率 > 30% | 中止实验 + 报警 | **是** |

---

# 八、相关文档

- **产品需求**：[PRD.md](../../../PRD.md) — 愿景、需求、验收标准
- **路线图**：[ROADMAP.md](../../../ROADMAP.md) — 阶段划分与里程碑
- **架构**：[ARCH.md](../../../ARCH.md) — 模块设计、4 层架构
- **详细设计**：[DESIGN.md](../../../DESIGN.md) — 算法、数据结构、参数
- **开发规范**：[DEVELOP.md](../../../DEVELOP.md) — 技术栈、代码规范
- **术语表**：[references/Glossary.md](../../../references/Glossary.md) — 核心概念定义
- **可行性分析**：[SGE-Engineering-Feasibility-Analysis.md](./SGE-Engineering-Feasibility-Analysis.md)
- **技术栈全景**：[SGE-Technology-Stack-Overview.md](./SGE-Technology-Stack-Overview.md)
- **关键洞察**：[SGE-Key-Insights.md](../../../SGE-Key-Insights.md)
