# M2.1 阶段 A — 基线冒烟测试报告

> **目的**：记录 M2.1 阶段 A 的基线冒烟测试——验证从 AiBeing 借鉴的 4 个核心机制在 SGE 实验环境中可独立运行
> **创建日期**：2026-06-18
> **对应 CHANGELOG**：[1.10.0]
> **状态**：✅ PASS — 4/5 借鉴机制 import OK，5 步最小循环跑通

---

# 1. 概述

## 1.1 背景

M2.1（完整 SGE 架构）需要"基于 AiBeing 的 Genome v10 引擎改造"（[ROADMAP §M2.1](../ROADMAP.md)）。在开始 SGE 化改造之前，**阶段 A** 需要建立**可比基线**——把 AiBeing 的 4 个核心机制原样跑通，验证：

1. 借鉴模块可 import 且无意外错误
2. 5 步最小循环（sense → compute_signals → learn → tick_drives → metabolism）可执行
3. drive_state 和 temperature 都有预期变化

**目的**：建立基线后，阶段 B 的 SGE 化改造才有"对照"——能区分"借鉴机制本身的问题"和"SGE 改造引入的问题"。

## 1.2 文件位置

| 文件 | 用途 |
|------|------|
| `experiments/scripts/m21_setup.py` | 基线冒烟测试脚本（一次性，验证后归档） |
| `experiments/configs/m21_baseline.yaml` | 基线配置（AiBeing 原生参数，5D drives） |
| `experiments/output/m21_baseline/m21_setup_snapshot.json` | 5 步状态快照（6393 bytes） |
| `experiments/M21_BASELINE_SETUP_REPORT.md` | **本报告** |
| `research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md` | 实施映射文档（§五 阶段 A 的依据） |

## 1.3 借鉴来源（不复制到 SelfLab 仓库）

| 机制 | AiBeing 源码 | SGE 用途（阶段 A） | 验证方式 |
|------|-------------|------------------|---------|
| Time Metabolism | `engine/genome/drive_metabolism.py:57-87` | 直接复用（不调参） | 5 步后 temperature > 0 ✅ |
| Thermodynamic Noise | `engine/genome/drive_metabolism.py:113-136` | 直接复用（不调参） | 5 步后温度随 frustration 变化 ✅ |
| Hebbian Learning | `engine/genome/genome_engine.py:289-354` | 直接复用（核心） | 5 步后 drive_state 变化 0.6715 ✅ |
| KNN + Hawking | `engine/genome/style_memory.py:29, 209-255` | 阶段 A 仅 import 验证 | import OK ✅ |
| Critic LLM | `engine/genome/critic.py:76-190` | 阶段 A 仅 import 验证（stub） | import OK ✅ |
| Relationship EMA | `agent/evermemos_mixin.py:_apply_relationship_ema` | 阶段 A 仅 import 验证 | import 失败（缺 frontmatter 依赖，阶段 A 可忽略）⊘ |

**不复制代码到 SelfLab 仓库**——`m21_setup.py` 通过 `sys.path` 把 `/Users/loubicheng/project/AiBeing` 加入，运行时直接 `from engine.genome.X import Y`。这与 `experiments/README.md` 约定一致（"❌ 跨 notebook 的可复用模块"）。

---

# 2. 实验设计

## 2.1 最小循环

```
[Step 0] 构造 stub context（12D，含 8D Critic + 4D EverMemOS）
[Step 1] Agent.compute_signals(context) → 8D signals
[Step 2] Agent.learn(signals, reward) → Hebbian + frustration accumulation
[Step 3] Agent.tick_drives() → drive_state 累积
[Step 4] DriveMetabolism.apply_llm_delta() → frustration 更新
[Step 5] 记录 snapshot，重复 5 次
```

## 2.2 stub 设计

- **LLM**：不调用。用 `make_stub_context()` 返回固定 12D context。
- **Reward**：`make_stub_reward()` 返回交替正负值（+0.3, -0.15, +0.3, -0.15, +0.3）—— 偶数步正、奇数步负，用于观察 Hebbian 学习的方向性。
- **Seed**：单 seed=42（阶段 A 不需要多 seed，验证机制可运行即可）。

## 2.3 关键参数（直接复用 AiBeing 默认值）

| 参数 | 值 | 来源 |
|------|---|------|
| frustration_decay_lambda | 0.08/h | drive_metabolism.py:24 |
| connection_hunger_k | 0.15/h | drive_metabolism.py:25 |
| novelty_hunger_k | 0.05/h | drive_metabolism.py:26 |
| temp_coeff | 0.12 | drive_metabolism.py:27 |
| temp_floor | 0.03 | drive_metabolism.py:28 |
| hebbian_lr | 0.02 | genome_engine.py:203 |
| phase_threshold | 2.0 (阶段 A 禁用) | genome_engine.py:204 |
| weight_decay | 0.995 | genome_engine.py:87 |
| hidden_size | 24 | genome_engine.py:86 |
| hawking_gamma | 0.001/h | style_memory.py:29 |

完整参数见 `experiments/configs/m21_baseline.yaml`。

---

# 3. 实验结果

## 3.1 借鉴模块验证

```
✓ drive_metabolism.DriveMetabolism — import OK
✓ genome_engine.Agent / DRIVES / SIGNALS — import OK
✓ style_memory.ContinuousStyleMemory / HAWKING_GAMMA=0.001/h — import OK
✓ critic.critic_sense / 8D context keys — import OK
⊘ agent.evermemos_mixin (EMA) — missing dep: frontmatter (阶段 A 可忽略)
```

**4/5 模块 import 成功**。EverMemOSMixin 失败原因是 AiBeing 项目依赖 `frontmatter`（用于解析 SOUL.md）未安装。**阶段 A 不影响**——EMA 验证留到阶段 B。

## 3.2 5 步循环追踪

| Step | Reward | Frustration | Temperature | Dominant Signal | Phase Xition |
|------|--------|-------------|-------------|-----------------|--------------|
| 0 | +0.300 | 0.270 | 0.062 | defiance=0.588 | False |
| 1 | -0.150 | 0.108 | 0.043 | curiosity=0.625 | False |
| 2 | +0.300 | 0.367 | 0.074 | defiance=0.662 | False |
| 3 | -0.150 | 0.195 | 0.053 | defiance=0.565 | False |
| 4 | +0.300 | 0.446 | 0.083 | curiosity=0.625 | False |

**观察**：

- Frustration 累积模式：每步按 reward 调整（apply_llm_delta 中含 `decay_rate=0.1` 的衰减），5 步后从 0 → 0.446
- Temperature 单调跟随 frustration（tanh 饱和曲线）：0.030 → 0.062 → 0.074 → 0.083（floor+调整）
- Phase transition 未触发（5 步 frustration 累积未达阈值 2.0，符合预期）
- Dominant signal 在 `defiance` 和 `curiosity` 之间切换（正负 reward 引起的 Hebbian 学习方向性变化）

## 3.3 验证结果

```
[verify] drive_state 变化总量 (vs baseline) = 0.6715
[verify] final temperature = 0.0830

drives_settled=PASS | metabolism=PASS
总体: ✅ PASS — 基线可运行
```

| 验证项 | 阈值 | 实际 | 状态 |
|--------|------|------|------|
| drives_settled | > 0.0 | 0.6715 | ✅ PASS |
| metabolism_works | > 0.0 | 0.0830 | ✅ PASS |
| no_exceptions | 无异常 | 无异常 | ✅ PASS |

---

# 4. 关键发现

1. **AiBeing 路径引用策略可行**——`sys.path` + `from engine.genome.X import Y` 在没有复制代码到 SelfLab 仓库的情况下能正常运行。这与 `experiments/README.md` "❌ 跨 notebook 的可复用模块" 约定一致。

2. **Hebbian + Time Metabolism + Thermodynamic Noise 三者联动正常**——5 步内 drive_state 累积 0.6715，temperature 跟踪 frustration 累积（0.030 → 0.083），tanh 饱和曲线保护高温下信号不随机化。

3. **Phase Transition 未触发是预期的**——5 步 frustration 累积 < 2.0 阈值。要触发相变需要更长的负面事件流（与 M1.4 REVISIT 测试的观察一致——需要"连续负面事件"才会触发）。

4. **Critic stub 简化有效**——5 步循环的 stub context（12D 固定值）足以让 Agent 学习产生方向性变化。阶段 B 接入真实 LLM 时，只需把 `make_stub_context()` 替换为 `critic_sense()` 调用。

---

# 5. 已知问题与风险

| 风险 | 状态 | 缓解 |
|------|------|------|
| `frontmatter` 依赖未装 | ⚠️ 阶段 A 可忽略；阶段 B 需要时再装 | `pip install python-frontmatter` |
| 阶段 A 仅 1 seed × 5 steps | ⚠️ 统计功效不足 | 阶段 B/D 扩展到多 seed × 长 epoch |
| 阶段 A 用 AiBeing 5D drives | ⚠️ 不是 SGE 化 drives | **Phase 0 终稿需先统一 SGE drives 清单**（洞察 24 vs 6 个价值观的冲突） |
| Phase Transition 阈值 2.0 在 SGE 中是否合适 | ⚠️ 未验证 | 阶段 B 实验中扫描 [1.0, 3.0] 找最优 |
| Hawking gamma 0.001/h（29 天半衰期） | ⚠️ 对 1000 epoch 实验可能过长 | 阶段 B/D 调参验证 |

---

# 6. 下一步

**M2.1 阶段 B — SGE 化改造**（1-2 周 + 实验）

必须先做：

1. **Phase 0 收尾决策**（沉淀到 `research/sge-core/SGE-Phase0-Closeout.md`）：
   - SGE drives 清单（5 个 vs 6 个冲突）
   - Value scale（[-1, 1] vs [0, 1]）
   - Phase Transition 阈值、Hawking gamma 调参依据
2. **Critic LLM 接入**（`make_stub_context()` → `critic_sense()` 真实调用）
3. **Relationship EMA 改造**（`evermemos_mixin._apply_relationship_ema` → Value EMA，relationship → value）
4. **多 seed × 长 epoch 验证**（3 seeds × 100 epochs）

**M2.1 阶段 C — 新增组件**（1-2 周）

5. Value EMA Tracker（多维价值观 EMA 状态管理）
6. Value Conflict Generator（基于 Value state 生成针对性事件）
7. Event Generator（外部事件源）
8. Narrative Builder MVP

**M2.1 阶段 D — 集成 + 验证**（1-2 周）

9. 完整 12 步循环组装
10. 100 epoch 冒烟测试
11. 1000 epoch 三胞胎实验（M2.2 的预备）

**总时长估算**：6-9 周（与 [SGE-M21-AiBeing-Implementation-Mapping.md §五](../research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md#五m21-实施步骤建议) 一致）

---

# 7. 归档策略

- **本脚本保留在 `experiments/scripts/`**（不删除，便于查阅和复用）
- **snapshot 数据保留在 `experiments/output/m21_baseline/`**
- **本报告保留在 `experiments/`**（与 M1x 报告并列）
- **不进入主分支的 develop/main 演进路径**——M2.1 完成后归档到 `experiments/archive/2026-06-m21/`

---

**创建日期**：2026-06-18
**维护者**：Bisen & Claude
