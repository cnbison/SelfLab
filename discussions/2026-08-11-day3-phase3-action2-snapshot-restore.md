# 会话记录：Day 3 Phase 3.1 动作 2 — Runtime 状态托管统一

> **会话定位**：续接 `2026-08-11-project-review-and-cleanup.md`（Day 1+2 文档清理），执行 Day 3 第一个任务（Status-Map §4 动作 2 — Runtime 状态托管统一前置，0.5 天工作量）。下一会话启动动作 1（persistence.py 实施）。

日期：2026-08-11

参与者：Bisen & Claude

---

## 讨论主题

Status-Map §3.2 指出 sge/ 包的 7 个 state 类分散在不同模块（Agent / ValueLayer / DriveMetabolism / HawkingDecay / MemoryCrystallizer / IdentityLayer / NarrativeBuilder），**无统一 snapshot() 接口**——这是 `01-persistence.md §5/§6` `_save_checkpoint()` 的 7 套硬编码读取逻辑的根因。Status-Map §4 动作 2 是动作 1（persistence.py）的前置。

## 背景与动机

- Day 1+2 完成 5 个🔴 严重漂移 + 2 个🟡 中度漂移（M2.x 已完成但文档未对齐 + PRD §6.3 5 层修订注堆叠）
- Day 3 启动 Phase 3.1 实施：先做 0.5 天前置（Runtime 状态托管统一），再做 1.5 天主体（persistence.py）
- persistence.py 涉及 TwinStateDB schema 决策（value_state / identity_state 序列化、GDPR delete 语义），需要 Bisen 在场配合——分批做是合理节奏

## 核心决策

### 1. 序列化策略（AskUserQuestion 之前）

Plan agent 评估 3 种选项：
- **A：纯 JSON**（神经网络 W1/W2 nested list，调试友好）
- **B：JSON + base64 pickle 子块**（高效但复杂）
- **C：每 state 自由决定**（混合）

**Bisen 选定 → 推荐 A**：纯 JSON + list-of-list 嵌套（与现有 `to_vec` 风格一致）。理由：神经网络权重总量 ~1000 floats ≈ 8KB，base64 编码徒增复杂度。

### 2. snapshot_all 范围（Plan agent 倾向完整保真）

**推荐 → Bisen 采纳 → 完整保真（含 EventGenerator）**

理由：
- M2.2 chunk reset 痛点的根本修复就是跨 chunk 保真 state——没有 event_history 无法验证"是否能继续正确演化"
- persistence.md §1 明确把 event_history 列在 12 项持久化 state 之一
- 200KB 体积对一个 1000-epoch 实验 < 1MB，可接受
- EventGenerator 用 `rng.getstate()/setstate()` 保真（不是仅存 seed），避免跨 chunk 重放时事件序列偏移

### 3. Commit 拆分粒度（Plan agent 推荐 4 commit）

**推荐 → Bisen 采纳 → 2 commit**

理由：
- commit 1（baseline 原子单元）独立可验证，**立刻解锁 persistence.py 写 storage 部分**
- commit 2（编排器集成）紧接 persistence.py checkpoint hook
- 经验法则：单 commit ≤ 400 行净改动 / ≤ 3 个文件——2 commit 各满足
- 避免 4 commit 过度琐碎（Day 3 是 0.5+1.5 天连续工作）

### 4. 关键反对意见（Plan agent 评估）

- **白名单 vs 黑名单**：白名单更安全（黑名单在字段扩张时静默泄露不可序列化引用）
- **Agent.hawking / Agent.crystallizer 单点快照**：`__init__` 把 hawking/crystallizer 注入到 agent 作为 alias——snapshot 只走 `self.hawking/self.crystallizer`，避免 JSON 重复 + restore 时序竞争
- **mid-step 暂态 llm**：orchestrator.py:347-360 在 step() 中临时翻转 `identity_layer.use_real_llm/llm`——snapshot **只在 epoch 边界调用**（用户代码负责）
- **Agent INPUT_SIZE 兼容性**：restore 时校验 `snap['input_size'] == self.INPUT_SIZE`，否则 SnapshotError

## 实施清单

| Commit | 文件 | 改动 |
|--------|------|------|
| **commit 1 (`81d7706`)** | sge/sge/baseline.py | +398 行：SnapshotError 异常类 + 5 个 state 类 snapshot/restore + 9 个单元测试 |
| **commit 2 (`1c74afd`)** | sge/sge/event.py | +82 行：EventGenerator.snapshot/restore + rng_state 序列化辅助方法 |
| | sge/sge/identity.py | +37 行：IdentityLayer.snapshot/restore（不含 llm） |
| | sge/sge/narrative.py | +39 行：NarrativeBuilder.snapshot/restore（不含 llm） |
| | sge/sge/orchestrator.py | +216 行：snapshot_all/restore_all + current_epoch + 5 个新测试 |

**总计**：5 个文件，+772 行（baseline 5 state + 编排器聚合 + 14 个单元测试）

## 单元测试结果

### baseline.py（commit 1）
- ✓ 测试 1: Agent round-trip（compute_signals ≤1e-9）
- ✓ 测试 2: Agent NN weights（W1/W2/b1/b2 逐元素）
- ✓ 测试 3: Agent recurrent_state 独立
- ✓ 测试 4: ValueLayer round-trip（6D 全等）
- ✓ 测试 5: DriveMetabolism round-trip（frustration + _last_tick）
- ✓ 测试 6: HawkingDecay round-trip（含 content dict 嵌套）
- ✓ 测试 7: MemoryCrystallizer round-trip（vec/weight/count）
- ✓ 测试 8: strict 校验（缺 recurrent_state → SnapshotError）
- ✓ 测试 9: 无 LLM 泄露（5 类 snapshot 均不含 llm）

### orchestrator.py（commit 2 新增 5 个 + 原 12 个）
- ✓ 测试 13: orchestrator round-trip（epoch 56 上 value/signal/identity/narrative 全等 ≤1e-9）
- ✓ 测试 14: 缺 _schema_version → SnapshotError
- ✓ 测试 15: identity/narrative 不含 llm
- ✓ 测试 16: EventGenerator rng_state 保真
- ✓ 测试 17: snapshot_all 无外部 ref 泄露

**最终状态**：编排器 17/17 + baseline 9/9 全绿，无回归

## 实施过程的关键修复

1. **compute_signals 用 module-level random**（baseline.py:403）→ 测试 1 需 `random.seed(42)` 重置两侧随机序列
2. **`random.Random` 公开 API 是 `getstate()/setstate()`**（无下划线）→ 第一次实现错用 `_getstate()` 报错
3. **Python 3.13 getstate 内部结构是 `(3, tuple[625 ints], None)`**：
   - tuple → JSON 时转 list，restore 需转回 tuple
   - `gauss_next` 可能是 `None`（未调用过 gauss 时）→ 需默认 0.0
   - `state[1]` 必须是 tuple（Python 3.13 `random.setstate` 严格要求）→ `_serialize_rng_state` / `_deserialize_rng_state` 双向转换

## 产出文件

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `sge/sge/baseline.py` | commit 1 | 5 state 类 snapshot/restore + SnapshotError + 9 测试 |
| `sge/sge/event.py` | commit 2 | EventGenerator.snapshot/restore + rng_state 序列化辅助 |
| `sge/sge/identity.py` | commit 2 | IdentityLayer.snapshot/restore |
| `sge/sge/narrative.py` | commit 2 | NarrativeBuilder.snapshot/restore |
| `sge/sge/orchestrator.py` | commit 2 | snapshot_all/restore_all + current_epoch + 5 新测试 |
| `CHANGELOG.md` | 1.32.0 索引行 | Day 3 动作 2 完成记录 |

## Git 状态

```
81d7706 feat(sge): baseline 5 类 state snapshot/restore 协议（Phase 3.1 动作 2 前置）
1c74afd feat(sge): 编排器聚合层 snapshot_all/restore_all + Identity/Narrative/Event 集成（Phase 3.1 动作 2 完成）
（即将提交）docs: CHANGELOG 1.32.0 + Day 3 动作 2 会话简记
```

净行数：+772 行（5 文件）

## 是否产生关键洞察

**否**。本次会话是**纯工程实施**——落实已有设计决策（Status-Map §4 动作 2 已规划 + Plan agent 评估），未引入新概念或框架修订。

## 下次会话建议起点

1. **Day 3 动作 1：persistence.py 实施**（TwinStateDB v1.5）—— 1.5 天工作量
2. 读 `research/phase3/10-engineering/01-persistence.md §5/§6`（TwinStateDB API + schema 设计）
3. **决策点**（需要 Bisen 在场）：
   - value_state / identity_state 序列化策略（JSON 全文 vs 拆分细粒度表）
   - GDPR delete 语义（物理删除 vs 软删除 + 审计日志保留）
   - checkpoint 触发策略（每 100 epoch vs session end vs phase transition）
   - WAL mode + 跨 chunk 一致性保证
4. 实施后单元测试 ≥ 80% save/load 4 层（Phase 3.2 范围）

## 关联文档

- [SGE-Status-Map §3.2/§4 动作 2](../../SGE-Status-Map.md) — 本次任务的状态来源
- [research/phase3/10-engineering/01-persistence.md](../../research/phase3/10-engineering/01-persistence.md) — 下一步 persistence.py 设计 SSOT
- [sge/RUNTIME_AUDIT.md §四 方案 4.4](../../sge/RUNTIME_AUDIT.md) — "统一 State 托管留待 Phase 3.1"的判断
- [discussions/2026-08-11-project-review-and-cleanup.md](./2026-08-11-project-review-and-cleanup.md) — Day 1+2 上下文

---

**记录者**：Bisen & Claude
**最后更新**：2026-08-11
