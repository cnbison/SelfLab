# SGE M2.1 阶段 D — 实施计划

文档版本：v0.1
日期：2026-06-19
整理者：Bisen & Claude
状态：📋 待 Bisen 评审

> **本文件性质**：**M2.1 阶段 D 的实施计划**——把阶段 B/C 的所有模块组装为完整 12 步双 LLM 编排 + 100 epoch 长 epoch 验证。

> **本文件承接阶段 C**：C1-C4 已在 [1.19.0] 完成，提供了 EventGenerator / Value Conflict / IdentityLayer / NarrativeBuilder。阶段 D 把这些模块 + 阶段 B 的 Hawking/Crystallize 接入主循环，并跑 100 epoch 验证。

**关联文档**：
- [SGE-M21-Phase-C-Implementation-Plan.md](./SGE-M21-Phase-C-Implementation-Plan.md) — 阶段 C 实施计划（已通过，commit `84d1f12`）
- [SGE-M21-Phase-B-Implementation-Plan.md](./SGE-M21-Phase-B-Implementation-Plan.md) — 阶段 B 实施计划（已通过，commit `bc42a47`）
- [SGE-M21-AiBeing-Implementation-Mapping.md §2.9](./SGE-M21-AiBeing-Implementation-Mapping.md#29-双-llm-架构--sge-critic--actor-编排) — 双 LLM 编排的 12 步循环参考
- [experiments/M21_PHASE_C_REPORT.md](../../experiments/M21_PHASE_C_REPORT.md) — 阶段 C 报告
- [experiments/M21_PHASE_B_REPORT.md](../../experiments/M21_PHASE_B_REPORT.md) — 阶段 B 报告
- [PRD.md §FR-1, FR-3, FR-4, FR-5, FR-6, FR-7, FR-8, FR-9, FR-10](../../PRD.md) — 全功能需求
- [DESIGN.md §二, §三, §四, §五, §六, §七, §九](../../DESIGN.md) — 全详细设计

---

# 0. 目的与边界

## 0.1 阶段 D 的目标

把 M2.1 阶段 B/C 实现的全部 SGE 模块（drives / values / EMA / Critic / Hawking / Crystallize / Identity / Narrative / Event）组装为**完整 12 步双 LLM 编排**，并通过 100 epoch 长 epoch 验证全链路可运行。

阶段 D 完成后，SGE 完整 6 层架构 + 双 LLM 编排可端到端跑通，为 M2.2 的 1000 epoch 三胞胎实验提供工程基线。

## 0.2 阶段 D **不**包含（明确边界）

- ❌ **1000 epoch 三胞胎实验**（M2.2 才做）
- ❌ **Identity Profile 化**（Phase 3 才做）
- ❌ **情绪对叙事的影响**（M3.1 才做）
- ❌ **Phase/Hawking/Crystallize 阈值的参数扫描**（M2.2 扫 [1.0, 3.0] 等范围，阶段 D 只验证默认参数跑通）
- ❌ **真实 LLM 模式的成本优化**（阶段 D 默认 stub，M2.2/M2.3 才用真实 LLM）

## 0.3 阶段 D 的输入与输出

| 输入 | 来源 |
|------|------|
| 阶段 B 自有实现 `_sge_baseline.py` | B1-B7（drives/values/EMA/Hawking/Crystallize/Phase）|
| 阶段 B Critic LLM `_sge_critic.py` | B4 Critic LLM 适配层 |
| 阶段 C `_sge_event.py` | C1 Event Generator + C2 Value Conflict Generator |
| 阶段 C `_sge_identity.py` | C3 Identity Layer |
| 阶段 C `_sge_narrative.py` | C4 Narrative Builder MVP |
| DESGIN.md §二/§三/§五/§六 | 12 步编排设计 |
| AiBeing 12 步循环 §2.9 | 编排逻辑参考（Step 顺序、温度参数）|

| 输出 | 用途 |
|------|------|
| 新增 `_sge_actor.py` | Actor LLM 模块（行为表达）|
| 新增 `_sge_orchestrator.py` | 12 步编排器 |
| 修改 `_sge_baseline.py` Agent | 集成 Hawking/Crystallize 到主循环 |
| 新增 `m21_phase_d.py` | 阶段 D 集成测试（100 epoch 冒烟 + 3 seed × 100 epoch）|
| 新增 `m21_phase_d.yaml` | 配置（Phase/Hawking/Crystallize 阈值 + 触发频率）|
| `experiments/M21_PHASE_D_REPORT.md` | 阶段 D 报告 |

---

# 1. 阶段 D 范围：5 个子任务

## D1：HawkingDecay + MemoryCrystallizer 集成

**目标**：把 `_sge_baseline.py` 中已就绪的 `HawkingDecay`（B6）和 `MemoryCrystallizer`（B7）接入主循环。

**为何需要集成**：
- 阶段 B 已实现两个类并通过单元测试，但**未接入 Agent.step**
- 阶段 D 必须把它们放进 12 步循环，否则 Hawking 衰减 + Crystallize 合并无法生效
- 阶段 C 的 m21_phase_c.py 用 `key_memories` 和 `crystallized_events` 两个临时列表，**未走 Hawking/Crystallize**

**改造契约**：

```python
# 在 _sge_baseline.py Agent.__init__ 新增：
self.hawking: Optional[HawkingDecay] = None      # 每 step tick
self.crystallizer: Optional[MemoryCrystallizer] = None  # 每 step insert_or_merge

# 新增方法 Agent.integrate_memory_layer(hawking, crystallizer)：
#   - 注入 Hawking + Crystallizer 实例
#   - 触发条件可由外部配置

# Agent.step 增加步骤（在 Phase Transition 检查之前）：
#   self.hawking.tick()          # 记忆衰减
#   self.crystallizer.insert_or_merge(...)  # 记忆合并
```

**Hawking 触发条件**：
- 每 step 都 tick（Hawking 衰减是连续过程）

**Crystallize 触发条件**：
- 每 N step（默认 N=10，与 Identity/Narrative 同周期）
- 触发时把"当前 value_vector + recent signals"打包为 14D 向量（6D values + 8D signals），存入 Crystallizer
- 距离 < `0.25/sqrt(14)` 阈值则合并，否则新建

**DESIGN 关联**：[DESIGN §三 Memory Layer]（参考 + 整合）——DESIGN 中 Memory Layer 是抽象定义，本子任务给出工程实现路径。

---

## D2：Actor LLM 模块

**目标**：实现 Actor LLM（"行为表达"侧，与 Critic 的"感知"侧配对）。

**为何需要 Actor**：
- 阶段 B/C 只实现了 Critic（感知事件 → value_delta + context），但**没有 Actor**（signals → 行为/语言）
- AiBeing 12 步循环的 Step 9 是 Actor，temperature=0.9（高随机性 → 多样性表达）
- 阶段 D 必须实现 Actor 才能构成"双 LLM 编排"

**功能需求**：[PRD §FR-10（双 LLM 架构）]

**模块契约**（新建 `_sge_actor.py`）：

```python
# Actor 输出结构（DESIGN §9.2 行为度量）
@dataclass
class ActorOutput:
    inner_monologue: str    # 内心独白（如"这次我想主动一点"）
    behavior_label: str     # 行为标签（如"主动回应" / "沉默不语" / "反问"）
    intention: str          # 意图（如"想了解对方感受" / "想结束话题"）
    confidence: float       # 置信度 [0, 1]


def stub_actor_express(
    signals: dict, value_vector: dict, retrieved_memories: list,
    current_narrative: Optional[str], seed: int = 0,
) -> ActorOutput:
    """stub Actor — 基于 signals 强度生成行为标签
    
    规则：
      - signals['initiative'] > 0.6 → behavior='主动引导'
      - signals['playfulness'] > 0.6 → behavior='玩闹撒娇'
      - signals['defiance'] > 0.6 → behavior='反抗/嘴硬'
      - signals['warmth'] > 0.6 → behavior='关怀'
      ...
    """


def real_actor_express(
    signals: dict, value_vector: dict, retrieved_memories: list,
    current_narrative: Optional[str], llm, seed: int = 0,
) -> ActorOutput:
    """真实 LLM Actor — 用 MiniMax-M3 生成
    
    prompt 模板：基于 signals + values + retrieved + narrative
    温度 = 0.9（高随机性）
    """


def actor_express(...): ...  # 适配层（stub / real 选择）
```

**关键设计决策**：
- Actor 输出是**结构化**（inner_monologue + behavior_label + intention），便于下游 Hebbian 学习接收
- temperature=0.9（与 AiBeing 一致）
- stub 模式基于 signals 阈值（确定性），real 模式基于 LLM（多样性）

**DESIGN 关联**：[DESIGN §9.2]（Actor 行为度量）

---

## D3：完整 12 步双 LLM 编排器

**目标**：实现完整 12 步双 LLM 编排器 `_sge_orchestrator.py`。

**为何需要独立编排器**：
- 阶段 C 的 m21_phase_c.py 在一个函数 `run_phase_c_loop` 里手动组装了 6 步
- 阶段 D 需要把 Step 0-12 全部串通，且 Step 之间的数据流（signals → prompt → actor output → hebbian）需要严格管理
- 独立编排器便于：
  - **单步调用**：阶段 D 测试可验证每步都执行
  - **可替换组件**：Hawking/Crystallize 等可独立替换为 stub
  - **可观测**：每步返回 trace 数据

**模块契约**（新建 `_sge_orchestrator.py`）：

```python
@dataclass
class OrchestratorStep:
    """每步的完整 trace — 用于阶段 D 测试和调试"""
    epoch: int
    # 步骤 1-2 (感知侧)
    event: dict                      # Step 2: EventGenerator 输出
    critic_context: dict             # Step 3: Critic 输出的 12D context
    critic_value_delta: dict         # Step 3: Critic 输出的 6D value_delta
    # 步骤 4-6 (记忆侧)
    value_state_before: dict         # Step 4: Value EMA 更新前
    value_state_after: dict          # Step 4: Value EMA 更新后
    hawking_removed: int             # Step 5: Hawking 衰减移除数
    crystallize_result: str          # Step 6: 'merged' or 'created'
    # 步骤 7-11 (表达侧)
    signals: dict                    # Step 7: 神经网络前向
    noisy_signals: dict              # Step 8: 热力学噪声
    retrieved_memories: list         # Step 9: KNN 检索
    actor_output: ActorOutput        # Step 11: Actor 输出
    # 步骤 12 (学习侧)
    phase_xition: bool               # Step 12: 是否触发 Phase Transition
    # 步骤 13-14 (身份/叙事侧)
    identity: Optional[str]          # Step 13: Identity Crystallize
    narrative: Optional[str]         # Step 14: Narrative Build


class SGEOrchestrator:
    """完整 12 步双 LLM 编排器
    
    架构来源: AiBeing engine/genome/chat_agent.py:_chat_inner() (12 步循环)
    SGE 化: 参考 SGE-M21-AiBeing-Implementation-Mapping.md §2.9
    """
    
    def __init__(self, agent, value_layer, drive_metabolism,
                 event_generator, critic_fn, actor_fn,
                 identity_layer, narrative_builder,
                 hawking: Optional[HawkingDecay] = None,
                 crystallizer: Optional[MemoryCrystallizer] = None,
                 crystallize_every: int = 10):
        ...
    
    def step(self, epoch: int) -> OrchestratorStep:
        """执行一个 epoch 的完整 12 步"""
        # Step 1: Time Metabolism
        # Step 2: Event Generation
        # Step 3: Critic (temperature=0.2)
        # Step 4: Value EMA Update
        # Step 5: Hawking Tick
        # Step 6: Crystallize Gate
        # Step 7: Compute Signals
        # Step 8: Thermodynamic Noise
        # Step 9: KNN Retrieve (Hawking.retrieve)
        # Step 10: Build Prompt
        # Step 11: Actor (temperature=0.9)
        # Step 12: Hebbian Learn + Phase Transition
        # Step 13: Identity Crystallize (if epoch trigger)
        # Step 14: Narrative Build (if epoch trigger)
        return OrchestratorStep(...)
    
    def run(self, n_epochs: int) -> list[OrchestratorStep]:
        """跑 n_epochs，返回全部 trace"""
        ...
```

**关键设计决策**：
- **Step 编号与 AiBeing 一致**（0-12），便于后续 reference 回溯
- **数据流严格**：每步只读上一步输出，不跨步修改
- **可观测**：OrchestratorStep 暴露所有中间状态，便于测试和调试
- **可配置**：Hawking/Crystallize 可选（向后兼容阶段 B/C 的 stub 模式）

---

## D4：100 epoch 冒烟测试

**目标**：单 seed × 100 epoch 长跑，验证完整 12 步编排可运行。

**实验设计**：
- 1 个 AI 婴儿（baby_id='smoke'）
- 100 epoch（长 epoch 验证 Hawking/Crystallize/Identity/Narrative）
- seed=42（确定性）
- 默认 Phase/Hawking/Crystallize 阈值

**验收标准**：

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | 100 epoch 全部跑通 | m21_phase_d.py 不报错，输出 trace 长度=100 |
| 2 | Hawking 衰减生效 | `len(hawking)` 在 epoch 100 < epoch 50（部分记忆衰减掉）|
| 3 | Crystallize 合并触发 | `crystallize_result='merged'` 出现 ≥ 1 次 |
| 4 | Identity 至少结晶 1 次 | `identity_layer.identity_history` 非空 |
| 5 | Narrative 至少构建 1 次 | `narrative_builder.narrative_history` 非空 |
| 6 | Phase Transition 触发 ≥ 1 次 | `phase_xition=True` 出现 ≥ 1 次（100 epoch 应该累积足够 frustration）|
| 7 | Value state 在 [-1, 1] | 所有 value 都在合法范围 |
| 8 | Actor 输出结构有效 | 所有 actor_output 都有 inner_monologue/behavior_label/intention |

---

## D5：3 seed × 100 epoch 多 seed 长 epoch 验证

**目标**：3 seed × 100 epoch，验证多 seed 一致性 + 量化指标。

**实验设计**：
- 3 个 seed：42 / 7 / 123
- 每个 seed 跑 100 epoch
- 收集：value_magnitude / identity_stability / narrative_coherence / phase_xition_count / hawking_survivors

**验收标准**：

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | 3 seed 全部跑通 | 3 个 result 都生成 |
| 2 | value_magnitude > 0.1 | 价值观非平凡演化 |
| 3 | identity_stability < 0.9（持续演化）| 100 epoch 还在变化 |
| 4 | narrative_coherence 至少 > 0 | 叙事构建成功 |
| 5 | personality divergence ≥ 阈值 | 3 seed 间 value vector 有差异（不一定像 M1.2 三胞胎那样大，因为这里都是默认事件流）|
| 6 | phase_xition_count 跨 seed 一致 | 都在 [0, 5] 区间（100 epoch 应触发 0-3 次）|

---

# 2. 子任务依赖图

```
D1 (Hawking/Crystallize 集成) ──┐
                                  │
D2 (Actor LLM) ──────────────────┤
                                  │
D3 (12 步编排器) ←────────────────┘ (D1 + D2 + 阶段 B + 阶段 C 全部模块)
                                  │
                                  ▼
                            D4 (100 epoch 冒烟)
                                  │
                                  ▼
                            D5 (3 seed × 100 epoch)
```

**关键路径**：D2 → D3 → D4 → D5（4-5 天）
**可并行**：D1 与 D2 完全独立（无依赖），可并行 0.5 天

**总时长**：4-5 天

---

# 3. 验收标准（阶段 D 完成时）

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | HawkingDecay 接入 Agent.step | Agent.step() 每步调用 hawking.tick() |
| 2 | MemoryCrystallizer 接入 Agent.step | Agent.step() 每 N 步调用 insert_or_merge() |
| 3 | Actor LLM 模块 | `_sge_actor.py` 实现 stub + real 模式 |
| 4 | Actor 结构化输出 | ActorOutput dataclass（inner_monologue + behavior_label + intention + confidence）|
| 5 | 12 步编排器 | `SGEOrchestrator.step()` 完整执行 14 步（含 Identity/Narrative 触发）|
| 6 | 100 epoch 冒烟 | m21_phase_d.py 跑 100 epoch 不报错 |
| 7 | 3 seed × 100 epoch 多 seed | 3 seed 全部跑通且量化指标在合理范围 |
| 8 | Identity Stability 量化 | DESIGN §9.1 entropy-based score |
| 9 | Narrative Coherence 量化 | DESIGN §9.3 stub coherence avg |
| 10 | Phase Transition 触发统计 | 100 epoch 内至少触发 ≥ 1 次（验证 frustration 累积路径生效）|
| 11 | 阶段 A/B/C 回归 | m21_setup.py / m21_phase_b.py / m21_phase_c.py 仍 PASS |
| 12 | 实验报告 | M21_PHASE_D_REPORT.md |

---

# 4. 关键参数（阶段 D 默认值）

| 参数 | 默认值 | 来源 |
|------|--------|------|
| Phase Transition 阈值 | 2.0 | 阶段 B 默认值 |
| Hawking γ | 0.01/h | 阶段 B 默认值（半衰期 ~3 天）|
| Crystallize base | 0.25/sqrt(N) | 阶段 B 默认值 |
| Crystallize 触发频率 | 每 10 epoch | 与 Identity/Narrative 同周期 |
| Identity 触发频率 | 每 20 epoch | 阶段 C 默认值 |
| Narrative 触发频率 | 每 50 epoch | 阶段 C 默认值 |
| Critic temperature | 0.2 | AiBeing 默认（稳定性）|
| Actor temperature | 0.9 | AiBeing 默认（多样性）|
| Hawking remove threshold | 1e-4 | 阶段 B 默认值 |
| 100 epoch 时间模拟 | 100 小时（1 epoch ≈ 1 小时）| 受控实验假设 |

---

# 5. 风险与开放问题

| 风险 | 影响 | 缓解 |
|------|------|------|
| 100 epoch 仍不够触发 Phase Transition | frustration 累积不到 2.0 | 阶段 D 验证：若不触发，记录"需 M2.2 1000 epoch" |
| Identity 在 100 epoch 仍在快速演化 | stability 指标不收敛 | 阶段 D 记录演化趋势，M2.2 长 epoch 看收敛 |
| Actor stub 行为过于简单 | 行为标签多样性不足 | 阶段 D 默认 stub，M2.2 才用 real LLM |
| 12 步编排顺序错误 | Hawking/Crystallize 在 Critic 之前触发导致逻辑混乱 | 阶段 D 单元测试：每步独立验证（trace 数据）|
| Memory Layer 抽象不全 | D1 集成后仍有未走通的路径 | 阶段 D 在 D4 验证覆盖 |

---

# 6. 与现有文档的关联

| 文档 | 影响 |
|------|------|
| [PRD §FR-1, FR-3, FR-4, FR-5, FR-6, FR-7, FR-8, FR-9, FR-10](../../PRD.md) | 阶段 D 需求依据（全部 FR）|
| [DESIGN §二, §三, §四, §五, §六, §九](../../DESIGN.md) | 阶段 D 设计依据 |
| [ARCH §3.4, §3.5](../../ARCH.md) | Identity + Narrative 架构 |
| [SGE-M21-AiBeing-Implementation-Mapping.md §2.9](./SGE-M21-AiBeing-Implementation-Mapping.md#29-双-llm-架构--sge-critic--actor-编排) | 12 步编排逻辑参考 |
| [SGE-Phase0-Closeout.md](../sge-core/SGE-Phase0-Closeout.md) | 阶段 D 不触发新的决策点（全部参数已 Closeout §5 决策）|
| [experiments/M21_PHASE_C_REPORT.md](../../experiments/M21_PHASE_C_REPORT.md) | 阶段 C 报告（基础）|
| [experiments/M21_PHASE_B_REPORT.md](../../experiments/M21_PHASE_B_REPORT.md) | 阶段 B 报告（基础）|

---

# 7. 时间估算

| 子任务 | 工作量 | 依赖 |
|--------|-------|------|
| D1: Hawking/Crystallize 集成 | 0.5 天 | 阶段 B 类已就绪 |
| D2: Actor LLM 模块 | 1 天 | — |
| D3: 12 步编排器 | 1.5 天 | D1 + D2 |
| D4: 100 epoch 冒烟 | 0.5 天 | D3 |
| D5: 3 seed × 100 epoch | 0.5 天 | D3 |
| 报告写作 | 0.5 天 | 全部 |
| **总计** | **4-5 天** | |

**关键路径**：D2 → D3 → D4 → D5（4 天）+ 报告 0.5 天

**可并行**：D1 与 D2 完全独立，可并行 0.5 天（但 D1 仅 0.5 天，节省有限）

---

# 8. 一句话总结

> **阶段 D = "12 步组装 + 100 epoch 验证"**——把 B/C 的 9 个模块串成端到端可跑的 SGE 完整架构，为 M2.2 三胞胎实验提供工程基线。

---

**创建日期**：2026-06-19
**维护者**：Bisen & Claude
**状态**：📋 待 Bisen 评审 → 评审通过后启动实施