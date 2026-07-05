# 2026-07-05 架构落地：Experience Encoder + H_self（方向 B）

## 元信息

- **日期**：2026-07-05
- **主题**：把 1.25.0 的 ECA 架构修订（洞察 33/34/35）从文档落到 `sge/` 可验证代码
- **参与者**：Bisen + Claude
- **触发**：Bisen 问"sge 下一步任务" → 通过 AskUserQuestion 选择**方向 B（架构落地）**——先实现 Experience Encoder + H_self + sge/ Runtime 审视，再启动 Phase 3.1
- **工作流阶段**：Runtime 审计 → 代码实现 → 单测 → 文档同步 → 推送

---

## 一、背景

1.25.0 完成了 ARCH/DESIGN/PRD/Glossary 的架构修订（新增 Experience 层与 H_self 目标函数），但都停留在**文档层**。当前 `sge/` 编排器 Step 2 仍是 Event Generator 直接产出 Event → Critic，跳过了"这件事对我意味着什么"的 Meaning 解释，也没有任何自我熵度量。本次把二者落为代码。

---

## 二、Runtime 定位审计结论（sge/RUNTIME_AUDIT.md）

评估 7 项 Runtime 特征：受控时钟 ✅、单步执行 ✅、状态托管 ⚠️、组件可插拔 ✅、反向重写 ⚠️、统一目标函数 ❌、Experience 编码 ❌。

**判定**：当前 sge/ 已是合格的 Runtime **骨架**，差距集中在**语义层**（Experience/Meaning + H_self）。二者均为**加法**——新增两个模块 + 编排器两处插入即可，**不需要推倒重构**。命名 Pipeline→Transformation 与统一 State 托管列为低优先级/后续。

---

## 三、核心产出

### 3.1 新增代码模块

| 文件 | 内容 |
|------|------|
| `sge/RUNTIME_AUDIT.md` | Runtime 定位审计（判定增量落地） |
| `sge/sge/experience.py` | `Experience` dataclass + `encode_experience`（stub/real 双实现，生成 meaning，纯 math 无 numpy 依赖） |
| `sge/sge/metrics.py` | `compute_self_entropy`（H_self = w_v·H_value + w_i·H_identity + w_n·H_narrative，归一化 [0,1]）+ `entropy_reduction_rate` |

### 3.2 编排器集成（orchestrator.py）

- **Step 2.5 Experience Encoding**：Event → Experience，meaning 注入 Critic 的事件描述，使"我的解读"真正影响下游 value_delta
- **Step 16 Compute Self Entropy**：每 epoch 计算 H_self
- `OrchestratorStep` 新增 `experience` / `self_entropy` 字段（放在尾部默认字段，避免 dataclass 排序错误）
- verbose 输出增加 `H_self=x.xxx`

### 3.3 API 导出（__init__.py）

新增 `Experience` / `encode_experience` / `real_encode_experience` / `stub_encode_experience` / `make_experience_id` / `compute_self_entropy` / `entropy_reduction_rate` / `DEFAULT_WEIGHTS`

### 3.4 文档同步

- `sge/README.md`：公开 API + 架构树 + Runtime 定位说明
- `ARCH.md §3.6.5`：实施状态 → ✅ 已实施
- `CHANGELOG.md`：1.26.0

---

## 四、验证

- `python -m sge.experience` → PASS（8 事件类型 meaning 非空 + 范围 + 可重现）
- `python -m sge.metrics` → PASS（熵 ∈ [0,1] + 固化身份 H_identity=0 + 未形成=1.0 + 下降率）
- `python -m sge.orchestrator` → **12/12 PASS**（新增测试 11 Experience + 测试 12 H_self；既有 10 项无回归）
- `import sge` → OK，新符号可见

**观察**：stub 模式 55 epoch H_self 略升（0.678→0.720）——因 stub 身份/叙事多样、value 近零。真实 LLM + 身份结晶下应转为下降趋势。指标已接通、可观测；权重待 M2.2 校准。

---

## 五、边界（本次不做）

- ❌ orchestrator 不改名"12步→Transformation 链"（文档层对齐即可）
- ❌ 不引入统一 `SelfState.snapshot()`（留待 Phase 3.1）
- ❌ 不实现完整 Reverse Rewrite（M3.x）

---

## 六、后续

1. M2.2 1000 epoch 补跑，校准 H_self 权重、验证真实 LLM 下 H_self 下降 > 30%
2. 完成后可启动 **Phase 3.1 Reflection Layer**

---

## 七、产出文件清单

- `sge/RUNTIME_AUDIT.md`（新增）
- `sge/sge/experience.py`（新增）
- `sge/sge/metrics.py`（新增）
- `sge/sge/orchestrator.py`（修改：Step 2.5 + Step 16 + trace 字段）
- `sge/sge/__init__.py`（修改：导出）
- `sge/README.md`（修改）
- `ARCH.md`（修改：§3.6.5）
- `CHANGELOG.md`（修改：1.26.0）
- `discussions/2026-07-05-architecture-landing.md`（本文件）
