# SGE 技术栈全景

整理者：Bisen & Claude

日期：2026-06-15

> **本文件性质**：**技术栈调研全景**（survey），不是技术栈定义的权威源。
>
> **SSOT（单一信息源）**：[DEVELOP.md §二 技术栈](../../../DEVELOP.md) 是 SGE 实际选型的权威定义。本文件提供**更广的调研视角**——包含备选框架、借鉴技术、参考实现。
>
> 本文件结构：
> - §一~五：现有框架和技术的调研（备选、参考、对比）
> - §六：核心技术栈选型（**与 DEVELOP.md 保持一致**）
> - §七：自研部分（与 ARCH §1.3、DESIGN §4 对应）
> - §八：一句话总结

---

# 一、来自 AiBeing（Genome v10）的 8 个可复用机制

AiBeing 的 Genome v10 引擎是目前最接近"有持续内在状态的 AI agent"的工程实现。SGE 直接复用其 8 个核心机制：

| 机制 | 来源模块 | SGE 用途 | 复用程度 |
|------|---------|---------|---------|
| Critic（事件感知） | `engine/genome/critic.py` | 将模拟事件转为结构化数值（8D context + 5D delta + 3D rel + 5D sat） | 直接复用 |
| Time Metabolism | `engine/genome/drive_metabolism.py` | 冷却方程（指数衰减）+ 饥饿方程（线性累积），模拟时间对内心状态的影响 | 直接复用 |
| Relationship EMA | `agent/chat_agent.py` | 指数移动平均融合历史状态与新冲击，SGE 用于价值观渐进演化 | 低改造（扩展维度） |
| Hebbian Learning | `engine/genome/genome_engine.py` | "一起激发的神经元连在一起"，SGE 用作暗知识的载体 | 直接复用 |
| Phase Transition | `engine/genome/genome_engine.py` | 挫败累积超过阈值时行为剧烈扰动，SGE 用于叙事断裂与价值观重构 | 直接复用 |
| Crystallization | `engine/genome/style_memory.py` | 复合评分（reward × novelty × engagement × harmony）筛选值得记忆的事件 | 低改造 |
| KNN + Hawking 辐射 | `engine/genome/style_memory.py` | 在记忆池中检索最相似经历；质量高的记忆更容易被回忆，不常用的记忆逐渐淡化 | 直接复用 |
| Thermodynamic Noise | `engine/genome/drive_metabolism.py` | 挫败感→温度→高斯噪声，模拟高压下的情绪化和不可预测行为 | 直接复用 |

**额外借鉴**：AiBeing 的双 LLM 架构（Critic 感知 + Actor 表达分离）也直接用于 SGE。

---

# 二、LLM 模型选型

| 角色 | 模型 | 用途 | 温度 |
|------|------|------|------|
| Critic（事件感知） | Haiku / Qwen-2.5-7B | 稳定结构化 JSON 输出 | 0.2 |
| Actor（行为表达） | Sonnet / GPT-4o | 创造性生成内心独白 + 行为选择 | 0.9 |
| Identity（身份凝聚） | Sonnet / GPT-4o | 从价值观生成身份描述 | 0.3 |
| Narrative（叙事构建） | Sonnet / GPT-4o | 将记忆串联为人生故事 | 0.5 |

**降级策略**：Sonnet → Haiku（牺牲质量降成本），GPT-4o → GPT-4o-mini（同上）。API 不可用时返回默认值，不阻塞认知循环。

---

# 三、记忆框架

| 框架 | 架构特点 | 成熟度 | SGE 用途 |
|------|---------|--------|---------|
| MemGPT / Letta | 受 OS 虚拟内存启发，分层管理 working / archival / recall memory；agent 可自主编辑记忆 | 最成熟，已有公司化运营和 API | 三层记忆架构的参考 |
| Mem0 | 轻量级个性化记忆 API，基于向量数据库 | 成熟，2024 年广泛采用 | 个性化记忆存储 |
| Zep | 时序知识图谱 + 向量混合检索 | 成熟，强在结构化事实记忆 | 结构化事实检索 |

---

# 四、反思/自改进技术

| 技术 | 来源 | 核心思想 | SGE 用途 |
|------|------|---------|---------|
| Reflexion | Shinn et al., 2023 | 通过 verbal reinforcement 学习，反思文本存入 episodic memory | 反思机制的参考 |
| Self-Refine | Madaan et al., 2023 | 单 LLM 完成生成-自我批评-精炼循环 | 自我修正的参考 |
| STaR / Quiet-STaR | Zelikman et al., 2022/2024 | 模型用自身生成的正确推理链进行 fine-tune | 自我教学的参考 |
| LATS | Language Agent Tree Search | 结合树搜索与自我反思 | 决策优化的参考 |

---

# 五、事件生成参考

| 技术 | 来源 | 核心思想 | SGE 用途 |
|------|------|---------|---------|
| Generative Agents / Smallville | Stanford, 2023 | 25 个 LLM agent 在沙盒世界中自主生活，产生涌现社会行为 | 事件生成的架构参考 |
| Sotopia | 社交模拟平台 | 评估 LLM 社交智能的 benchmark | 社交场景生成参考 |

---

# 六、核心技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 语言 | Python 3.11+ | 与 AiBeing 一致 |
| LLM SDK | litellm / openai | 统一多模型调用 |
| 结构化存储 | SQLite | 轻量级，单机部署 |
| 向量存储 | ChromaDB | 语义检索 |
| 异步框架 | asyncio | 与 AiBeing 一致 |
| 配置管理 | YAML | 角色参数、引擎参数 |
| 日志 | structlog | 结构化日志 |

---

# 七、需要自研的部分（无现成框架）

SGE 区别于所有现有系统的核心创新点，需要从零构建：

| 组件 | 功能 | 难度 | 说明 |
|------|------|------|------|
| Value EMA Tracker | 多维价值观的 EMA 演化 | 低 | 基于 Relationship EMA 扩展维度 |
| Value Conflict Generator | 动态生成针对性价值困境事件 | 中 | 根据当前 Value Layer 生成考验性事件 |
| Identity Crystallizer | 从价值观凝聚身份标签 | 中 | LLM + 行为历史交叉验证 |
| Narrative Builder | 将记忆串联为人生故事 | 高 | 长程一致性是最大挑战 |
| Meta-Value Initialization | 元价值（真实、自由）的初始化 | 低 | 固定先验，不参与 EMA 更新 |
| Narrative Consistency Checker | 检测和修复叙事矛盾 | 高 | 定期一致性扫描 |

---

# 八、一句话总结

SGE 的底层机制（记忆、代谢、学习、噪声、检索）大量复用 AiBeing 的 Genome v10 引擎，LLM 调用层用 litellm 统一多模型，记忆层参考 MemGPT/Letta。真正需要从零构建的是 Value Layer（价值观涌现）、Identity Layer（身份结晶）和 Narrative Layer（叙事构建）——这三层是 SGE 区别于所有现有系统的核心创新点。
