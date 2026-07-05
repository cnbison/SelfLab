# sge/ Runtime 定位审计

> **日期**：2026-07-05
> **触发**：洞察 33（SGE 是 Self Evolution Runtime，不是 Memory Framework）落地前的代码审视
> **目标**：评估当前 `sge/` 包的 API 与编排结构是否符合"Self Evolution Runtime"定位，判断是否需要重构，并给出 1.25.0 架构修订的落地方案。
> **结论摘要**：**不需要推倒重构**——当前 12+3 步编排器已具备 Runtime 骨架（受控时钟、单步可调用、组件可插拔、逐步 trace）。缺的是 **Experience 层**（洞察 34）与 **H_self 度量**（洞察 35）两个"加法"模块，以及 Transformation 视角的命名对齐。按 §四 方案增量落地即可。

---

## 一、审计范围

| 文件 | 行数 | 审计维度 |
|------|------|---------|
| `sge/__init__.py` | 88 | 公开 API 是否体现 Runtime 定位 |
| `sge/orchestrator.py` | 550 | 编排结构是否是 Runtime（vs 单向 Pipeline）|
| `sge/event.py` | ~430 | Event → Experience 缺口 |
| `sge/baseline.py` | ~900 | State 管理是否集中、可快照 |
| `sge/llm_client.py` | ~380 | LLM 适配层是否稳定 |

---

## 二、Runtime 定位符合度评估

洞察 33 主张 SGE 是"自我的运行时"（类比 JVM / Python Runtime）。一个 Runtime 的关键特征及当前符合度：

| Runtime 特征 | 说明 | 当前 sge/ 是否具备 | 证据 |
|-------------|------|:---:|------|
| **受控时钟** | 时间由 Runtime 驱动，非墙钟 | ✅ | `orchestrator.step(epoch)`，`timestamp = epoch * hours_per_epoch` |
| **单步可执行** | 可 step-by-step 推进并观测 | ✅ | `step()` / `run()` 分离；`OrchestratorStep` 逐步 trace |
| **状态集中托管** | Self 状态由 Runtime 持有、可快照 | ⚠️ 部分 | State 分散在 `agent` / `value_layer` / `hawking` / `identity_layer` / `narrative_builder`，无统一 `snapshot()` |
| **组件可插拔** | 机制可替换（stub/real、可选模块）| ✅ | `use_real_llm` 开关；`hawking` / `crystallizer` 可选；critic/actor 有 stub/real 双实现 |
| **反向重写能力** | 上层可 rewrite 下层（Evolution Loop）| ⚠️ 部分 | 仅 Step 15：Phase Transition → Narrative 重建。无普遍 Reverse Rewrite |
| **统一目标函数** | Runtime 可度量"自我形成"进度 | ❌ | 无 H_self / Cognitive Entropy 度量 |
| **Experience 编码** | Event 经解释成为 Experience | ❌ | Step 2 直接 `event_generator.generate()` → critic，无 Meaning 字段 |

**符合度小结**：7 项中 4 项 ✅、2 项 ⚠️、2 项 ❌（含 1 项重叠）。骨架是 Runtime，缺的是"自我"语义层（Experience + Meaning + H_self）。

---

## 三、缺口清单（与 1.25.0 架构修订对照）

### 缺口 1：无 Experience 层（洞察 34）

`orchestrator.py:221` Step 2 当前直接把 `LifeEvent` 交给 Critic：

```python
# ── Step 2: Event Generation ──
event = self.event_generator.generate(epoch=epoch, value_vector=self.value_layer)
# ── Step 3: Critic Sense ──
critic_context, critic_value_delta = critic_sense(event=event.to_dict(), ...)
```

**问题**：同一个 Event，不同 Self 应产生不同的 Meaning → 不同 value_delta。当前 Critic 直接从裸 Event 推导 value_delta，跳过了"这件事对我意味着什么"的解释步骤。ARCH §3.6 要求在 Event 与 Critic 之间插入 Experience Encoder，产出含 `meaning` 字段的 `Experience`。

### 缺口 2：无 H_self 度量（洞察 35）

`OrchestratorStep` 没有任何自我熵字段。DESIGN §9.5 要求每 epoch（或每 N epoch）计算 `H_self = w_v·H_value + w_i·H_identity + w_n·H_narrative`，作为自我形成的统一目标函数与验收指标（PRD §6：H_self 下降率 > 30%）。

### 缺口 3：命名仍是 Pipeline 语义

`orchestrator.py` docstring 通篇"12 步双 LLM 编排器"，OrchestratorStep 字段注释按"感知侧/记忆侧/表达侧/学习侧"分组——这是单向流水线的心智模型。洞察 33 主张 Transformation > Module。**但这是低优先级**：命名对齐可在文档层完成，不必改代码结构（改动大、收益小、有回归风险）。

### 缺口 4：Reverse Rewrite 仅 Phase Transition（M3.x 范围）

仅 Step 15 实现了一处反向重写。完整 Evolution Loop（每层可 rewrite 上层）是 M3.x 方向，**不在本次落地范围**，已在 discussions/2026-07-05 §五诚实声明。

---

## 四、落地方案（增量，不重构）

按"最小改动 + 可验证"原则，本次架构落地分 2 个加法模块 + 编排器 2 处插入：

### 4.1 Experience Encoder（新增 `sge/experience.py`）

- `Experience` dataclass（ARCH §3.6）：`event / context / emotion / goal_relevance / action_taken / outcome / reflection / meaning / uncertainty`
- `encode_experience(event, value_state, ...) -> Experience`：LLM 解释生成 meaning（stub + real 双实现，与 critic/actor 一致）
- **编排器插入点**：Step 2 与 Step 3 之间新增 **Step 2.5 Experience Encoding**；Step 3 Critic 改为接收 `experience`（含 meaning）而非裸 `event`
- **向后兼容**：`OrchestratorStep` 新增 `experience: Optional[dict]` 字段

### 4.2 H_self 度量（新增 `sge/metrics.py`）

- `compute_self_entropy(value_layer, identity_layer, narrative_builder, weights=(0.4,0.3,0.3)) -> dict`（DESIGN §9.5）
- 返回 `{H_self, H_value, H_identity, H_narrative}`
- **编排器插入点**：Step 14 之后新增 **Step 16 Compute Self Entropy**；`OrchestratorStep` 新增 `self_entropy: Optional[dict]` 字段

### 4.3 公开 API 扩展（`sge/__init__.py`）

```python
from .experience import Experience, encode_experience
from .metrics import compute_self_entropy
```

### 4.4 不做的事（明确边界）

- ❌ 不重命名 orchestrator / 不改"12步"为"Transformation 链" — 文档层对齐即可
- ❌ 不引入统一 `SelfState.snapshot()` — 缺口小，留待 Phase 3.1 State 托管时统一
- ❌ 不实现完整 Reverse Rewrite — M3.x 方向

---

## 五、验证标准

落地后须满足：

1. `encode_experience()` stub 与 real 均产出非空 `meaning` 字段
2. `compute_self_entropy()` 返回 4 个熵值且 `H_self ∈ [0, log(bins)]` 合理区间
3. `orchestrator.step()` 单元测试通过：Step 2.5 与 Step 16 均执行，trace 含 `experience` / `self_entropy`
4. 短程冒烟（stub，10 epoch）：H_self 序列可计算、无 NaN
5. 既有 12+3 步测试不回归

---

## 六、结论

当前 `sge/` 已是一个合格的 Runtime **骨架**：受控时钟、单步执行、组件可插拔、逐步可观测。与"Self Evolution Runtime"定位的差距集中在**语义层**——缺 Experience/Meaning（自我如何解释世界）与 H_self（自我形成的度量）。二者均为**加法**，通过新增两个模块 + 编排器两处插入即可落地，无需触动既有机制。命名 Pipeline→Transformation 与统一 State 托管是低优先级/后续阶段事项，本次不做。
