# SGE 现状地图（Status Map）

> **项目战略仪表盘** — 1-2 页总结 SGE 当前状态、关键不确定性、下一步动作。
>
> **使用场景**：当你（或未来协作者）想快速了解"SGE 到底在哪个位置"时，先读这份文档。
>
> **更新机制**：每次大版本变更后更新（如 CHANGELOG 新增 minor version）。
>
> **最后更新**：2026-08-12（CHANGELOG [1.35.0]）

---

## 0. 一句话总结

M2.x 全部完成（M2.2 v6 长程验证 6 实验 5/6 通过，PRD §6 双维度首次同时达成）。SGE 已从"研究纲领"转型为 **Self Evolution Runtime**（[洞察 33](./SGE-Key-Insights.md)），sge/ Python 包就绪。**Phase 3.1 已完成 persistence.py + session.py**，剩 context_injection.py。

---

## 1. 项目当前阶段

| 阶段 | 状态 | 关键节点 |
|------|------|---------|
| **Phase 0** 理论奠基 | ✅ 完成 | 36 条洞察 + 17 篇研究文档 + 7 篇 ECA 调研 |
| **Phase 1** 最小验证 | ✅ 完成 | M1.1/M1.2/M1.3/M1.4 + 跨 LLM 验证 ([CHANGELOG 1.5-1.8](./CHANGELOG.md)) |
| **Phase 2** 完整实验 | ✅ 完成 | M2.1 阶段 A-D + M2.2 v6 长程 + M2.3 个人真实测试 ([CHANGELOG 1.20-1.31](./CHANGELOG.md)) |
| **Phase 3** 系统完善 | 🚧 **实施中** | 规划完成（[research/phase3/](./research/phase3/) 18 文件）+ sge/ 包就绪 + Phase 3.1 启动 |
| **M4+ 延后** | ⏸ 暂缓 | Emotion / Meta-Cognition / Multi-AI（按 [research/phase3/03-roadmap.md §1](./research/phase3/00-overview/03-roadmap.md) 重新定位） |

**关键验证**（CHANGELOG 1.30-1.31）：

- **PRD §6 双维度首次同时通过** — A 维度（|val| 增长 ≥ 20%）6/6 + B 维度（H_self reduction > 30%）5/6 + PT ≥ 1 6/6
- 跨流通用性（challenged / uncertain / encouraged 各自 ≥ 42% reduction）
- 跨长程确认（4 chunks × 250 epoch，mean +36.5%）
- **核心假设**（"AI 能否形成自己的价值判断能力"）得到**稳健验证**

---

## 2. 已稳固的基础（✓ 不需要返工）

### 2.1 哲学立场（已稳定）

- **立场**：涌现主义/功能主义 + 拒绝金观涛"AI 不可能" + 接受其工具（[洞察 25](./SGE-Key-Insights.md)）
- **核心赌注**：成功 → 部分证伪金观涛；失败 → 部分支持；无论结果都是有价值的科学贡献
- **诚实地**：SGE 验证的是"功能性自我"——不声称解决意识硬问题

### 2.2 架构设计（CHANGELOG 1.25-1.26 落地）

- **Self Evolution Runtime 定位**（[洞察 33](./SGE-Key-Insights.md)）— LLM 是认知引擎，SGE 是 Self Runtime
- **5 层架构 + 6 条 Transformation 协议**（ARCH §1.5-1.8）— Event → Experience → Memory → Reflection → Value → Identity → Narrative
- **19 步认知循环**（vs 原 17 步）— 新增 Step 2.5 Experience Encoding + Step 16 Compute Self Entropy
- **H_self 统一目标函数**（[洞察 35](./SGE-Key-Insights.md)）— `H_self = w_v·H_value + w_i·H_identity + w_n·H_narrative`，公式 A3 修复 P0-4 非单调

### 2.3 工程实现（CHANGELOG 1.26 落地）

- **sge/ Python 包** 10 个模块 + Runtime 审计 + 公开 API（pip install sge）
- **2 个加法模块**（[sge/RUNTIME_AUDIT.md](./sge/RUNTIME_AUDIT.md)）：Experience Encoder + H_self 度量
- **H_self 公式 A3** 单元测试 11 项全绿
- **真实 LLM 工程**稳健（60s timeout + 8 retry，v6 4808 calls retry rate 0.27%）

### 2.4 实验验证（不可回退）

- **M1.x**：value vector 涌现（涌现幅度 0.642-0.848，方向一致性 0.954-0.969）
- **M2.1**：完整 12 步编排器 + D6 真实 LLM 验证 5/5 PASS
- **M2.2 v6**：6 个独立实验 mean +37.7%（5/6 > 30%），跨流通用
- **M2.3**：challenged baby 一致性 6.00/7，L4 identity 9.0/10
- **M1.3 跨 LLM**（Moonshot kimi-k2.6）：5/6 维度方向一致，LLM-agnostic

### 2.5 项目治理（已建立）

- 5 个核心文档版本号体系（PRD/ARCH/DESIGN/ROADMAP/DEVELOP）已对齐 [1.31.0]
- 36 条洞察的编号连续（1-36），主题可追溯到来源讨论
- CHANGELOG 单调递增的版本号（1.5 → 1.31）+ commit hash 引用
- CLAUDE.md 工作流闭环（讨论 → 洞察 → 修正 → 同步）

---

## 3. 关键不确定性（△/? 需要决策或核查）

### 3.1 △ Phase 3.1 实施细节

- **TwinStateDB schema**：[research/phase3/10-engineering/01-persistence.md](./research/phase3/10-engineering/01-persistence.md) 是 v1.5 设计，**实施时可能需要细化**（特别是 value_state/identity_state 的序列化策略）
- **GDPR delete**：设计存在但**未验证**（v6 长程实验中未触发）
- **M2.2 跨 chunk 状态连续性**（12 chunks × 250 epoch）— Phase 3.1 实施时需重跑验证

### 3.2 ✅ Runtime 状态托管缺口（已关闭）

[sge/RUNTIME_AUDIT.md §2](./sge/RUNTIME_AUDIT.md) 曾指出：State 分散在 `agent` / `value_layer` / `hawking` / `identity_layer` / `narrative_builder`，**无统一 `snapshot()`**。已于 CHANGELOG 1.32.0 落地统一 `snapshot()/restore()` 接口 + `SGEOrchestrator.snapshot_all()/restore_all()` 聚合层，persistence.py 与 session.py 均已在其上构建。

### 3.3 △ H_narrative 长程偏高

[M22_V6_LONG_REPORT.md §3.4](./experiments/M22_V6_LONG_REPORT.md)：1000 epoch 长程中 chunk 1 H_narrative 0.50（vs chunk 0 0.21）→ H_self 终值 0.441 偏高。**已知偏差，决策不修复**（统计误差范围内），但**未来可考虑** `n_max` 20 → 30 缓解。

### 3.4 △ SGE vs ECOS 边界

[洞察 31](./SGE-Key-Insights.md) 已明确：SGE 适合"AI 自身需要状态"，不适合"建模他人认知"（ECOS 战场）。**兄弟项目 ECOS**（`/Users/loubicheng/project/ecos/`）已独立。SGE Phase 3 应用方向应**严格守住**"AI 是'我'"的边界（数字孪生/AI 陪伴/Personal AI/创作者分身/历史人物）。

### 3.5 △ M4+ 何时重启

Emotion Layer / Meta-Cognition / Multi-AI Interaction 已重新定位为 M4+ 延后。**触发重启条件**未明确：是否需要 (a) Phase 3 全部完成，(b) 至少 1 个 PoC 跑通并验证，(c) 兄弟项目 ECOS 有新需求？

---

## 4. 下一步 3-5 个具体动作

> **按推荐顺序排列**。每项标明：工作量、依赖、风险、退出标准。

### 动作 1：Phase 3.1 context_injection.py — **最优先**

- **工作量**：1.5 天（参考 [research/phase3/10-engineering/03-context-injection.md](./research/phase3/10-engineering/03-context-injection.md)）
- **依赖**：persistence.py（1.33.0/1.34.0 已完成）+ session.py（1.35.0 已完成）
- **风险**：中（prompt 组装策略 + token 预算需实测）
- **退出标准**：history / identity / narrative / hawking 检索结果可注入 Actor prompt + 单测全绿

### 动作 2：Phase 3.1 已完成部分 — **✅ 收口**

- ✅ **snapshot/restore 统一接口**（1.32.0）— 5 个分散 state + 编排器聚合层
- ✅ **persistence.py / TwinStateDB**（1.33.0 + 1.34.0）— 20 测试，含 GDPR + schema 迁移 + 编排器自动 checkpoint
- ✅ **session.py / TwinSession**（1.35.0）— 8 测试，构造即恢复 + 进程内 SessionLock
- **遗留**：跨进程 SessionLock（DB 级 `session_locks` 表）未做，当前仅依赖 SQLite WAL 串行化

### 动作 3：Phase 3.2 单元测试覆盖（≥80%）— **Phase 3.1 完成后**

- **工作量**：3.5 天
- **依赖**：Phase 3.1 持久化层（已就绪）
- **风险**：中（各模块目前用 `python -m sge.X` 自测，需迁移到 pytest 框架并统计覆盖率）
- **退出标准**：9 个核心模块覆盖率 ≥ 80%

### 动作 4：A→B / ECOS 边界维护 — **持续（轻量）**

- **工作量**：每月 0.5 天（同步 ECOS 进展，识别 SGE 可借鉴的工程经验）
- **依赖**：无
- **退出标准**：兄弟项目有边界冲突时主动同步

### 动作 5：M2.2 跨 LLM 验证（暂缓）— **非阻塞**

- **状态**：CHANGELOG 1.30.0 标记"非阻塞后续工作"，未在 Phase 3 时间线内
- **退出标准**：当 Phase 3 完成后或 SGE 应用层需求出现时再启动

---

## 5. 长期路径（12-24 个月）

```
2026 Q3 (现在)         Q4                     2027 Q1               Q2
─────────             ──────                 ──────               ──────
Phase 3.1 (W1-W3)  →  Phase 3.2 (W4-W6)  →  Phase 3.3 PoCs   →  M4+ 评估
persistence         →  llm_cache + 单测   →  2 个 PoC 跑通    →  Emotion?
session             →  prompt 管理        →  评估报告         →  Meta-Cog?
context_injection   →  (可选) async       →  Phase 3 总结     →  Multi-AI?
```

**Phase 3 总结报告**（W12 末）会决定 M4+ 重启条件。**PoC 验证**决定 SGE 应用的"产品化"路径（学生数字孪生 vs Personal AI vs 创作者分身）。

---

## 6. 相关文档索引

- [ROADMAP.md §Phase 3](./ROADMAP.md) — 顶层里程碑
- [research/phase3/](./research/phase3/) — Phase 3 规划 SSOT
- [sge/RUNTIME_AUDIT.md](./sge/RUNTIME_AUDIT.md) — Runtime 定位审计
- [SGE-Key-Insights.md](./SGE-Key-Insights.md) — 36 条核心洞察
- [CHANGELOG.md](./CHANGELOG.md) — 完整版本历史（权威源）
- [CLAUDE.md](./CLAUDE.md) — 项目工作流与协作规范

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-15
**最后重写**：2026-08-12（基于 CHANGELOG 1.35.0）
