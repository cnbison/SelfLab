# 04 - Phase 3 风险矩阵

> **目的**：识别 Phase 3 实施风险 + 缓解方案
> **基础**：基于 M2.2 chunk reset 痛点 + MiniMax API 不稳 + AiBeing 应用经验

---

## 1. 风险矩阵

| # | 风险 | 概率 | 影响 | 等级 | 缓解方案 |
|---|------|------|------|------|---------|
| R1 | **MiniMax API 长跑不稳定** | 高 | 高 | 🔴 P0 | chunk + retry + warmup（M2.2 已用）；Phase 3.1 用 LLM cache 减少调用 |
| R2 | **chunk 边界状态丢失** | 中 | 高 | 🔴 P0 | persistence 解决（M2.2 v4 痛点 → Phase 3.1 修复） |
| R3 | **持久化数据库锁竞争** | 低 | 中 | 🟡 P1 | SQLite WAL mode；Phase 4 迁 PostgreSQL |
| R4 | **学生数据隐私 / GDPR** | 中 | 高 | 🔴 P0 | 加密 + 删除权 + 保留期限；详见 §5 |
| R5 | **学生成绩误用风险** | 中 | 高 | 🔴 P0 | 知情同意 + 数据最小化 + 教师审阅 |
| R6 | **AI 教练"个性化幻觉"** | 中 | 中 | 🟡 P1 | Identity 可审计；人工 spot check |
| R7 | **SubjectMasteryState schema 频繁变更** | 中 | 中 | 🟡 P1 | schema_version 字段；migration 工具 |
| R8 | **测试覆盖率不足** | 中 | 中 | 🟡 P1 | Phase 3.2 强制 ≥ 80% |
| R9 | **跨会话状态恢复失败** | 低 | 高 | 🟡 P1 | e2e 测试覆盖 save → close → load 循环 |
| R10 | **多用户数据隔离漏洞** | 低 | 极高 | 🔴 P0 | DB row-level 隔离 + student_id 验证 |
| R11 | **Hawking 衰减导致重要事件被忘** | 中 | 中 | 🟡 P1 | 重要性评分（Phase 3.1 考虑） |
| R12 | **跨 LLM provider 兼容性** | 低 | 低 | 🟢 P2 | SGELLMClient 已抽象，Phase 4 加 Moonshot |

---

## 2. 风险详情 + 缓解

### R1: MiniMax API 长跑不稳定 🔴 P0

**观察**：
- M2.2 v1 单次跑 1000 epoch → epoch 490 崩溃（SSL EOF）
- M2.2 v3 1000 epoch → encouraged epoch 490 + challenged epoch 336 都崩
- 失败模式：Server disconnected, [SSL: UNEXPECTED_EOF_WHILE_READING], Timeout
- retry 后成功率高，但偶尔 5 次全失败导致脚本崩溃

**缓解**（M2.2 已实施）：
- chunk 隔离（每 chunk 独立 SGELLMClient + fresh server session）
- Retry 5x + base_delay 3s（指数退避 3/6/12/24s）
- timeout=30s 显式 socket 超时

**Phase 3.1 增强**：
- LLM cache（相同 prompt 不重复调用，节省 ~30% 调用）
- Circuit breaker（连续失败 N 次后暂停 N 分钟）
- 多 provider fallback（MiniMax 失败时切换到 Moonshot）— Phase 4

### R2: chunk 边界状态丢失 🔴 P0

**观察**：M2.2 chunk 模式下，每个 chunk 是独立进程 → Hawking memory、Crystallizer clusters、value state 全部丢失

**缓解**：Phase 3.1 persistence 层
- 每个 chunk 结束 → save_full_state 到 DB
- 每个 chunk 开始 → load_full_state 从 DB
- 详见 [10-engineering/01-persistence.md](../10-engineering/01-persistence.md)

### R4: 学生数据隐私 / GDPR 🔴 P0

**风险**：
- 学生是未成年人，数据保护要求更高
- 家长有权删除孩子的所有数据
- 数据保留期限（毕业后保留 N 年）

**缓解**：
- 加密敏感字段（student_id 用 hash，name 用 AES）
- `delete_student(student_id)` 级联删除 7 张表
- 数据保留期限：毕业后 3 年自动删除（cron job）
- 审计日志：每次访问记录 student_id + timestamp + 操作
- 详见 [10-engineering/01-persistence.md §隐私](../10-engineering/01-persistence.md)

### R5: 学生成绩误用风险 🔴 P0

**风险场景**：AI 教练根据 SubjectMasteryState 给学生"贴标签"（"你是数学差生"），影响学生心理健康

**缓解**：
- AI 教练输出需经过"建设性表达"过滤（不说"你差"，说"你最近代数有挑战"）
- 教师审阅 hook（AI 输出先到教师，教师决定是否给学生看）
- SubjectMasteryState 不直接暴露给学生（只暴露给 AI）
- 学生数据访问权限分级（学生/家长/教师/管理员 看不同字段）

### R6: AI 教练"个性化幻觉" 🟡 P1

**风险**：M2.3 验证 challenged AI 自我认知清晰（9.0/10），但也可能"过度个性化"——认为"我了解这个学生"，但实际只是基于部分事件推断

**缓解**：
- Identity 可审计（每次结晶的 ~50 字可人工读）
- Phase 3.2 加"人工 spot check"机制（每月随机抽 10 个 AI 回答人工评分）
- 不让 AI 教练做"高风险决策"（如推荐留级/转班）

### R10: 多用户数据隔离漏洞 🔴 P0

**风险**：学生 A 的事件意外写入学生 B 的 DB row

**缓解**：
- 所有 DB 操作强制带 student_id 参数
- 单元测试覆盖：尝试跨用户访问必须抛异常
- 集成测试：100 用户并发测试数据隔离

---

## 3. 风险等级分布

| 等级 | 数量 | 占比 |
|------|------|------|
| 🔴 P0（必修） | 5 | 42% |
| 🟡 P1（应修） | 6 | 50% |
| 🟢 P2（可选）| 1 | 8% |

**结论**：Phase 3 主要工作是 P0 + P1 风险的缓解，共 11 项。

---

## 4. 风险 vs 阶段对应

| 风险 | Phase 3.1 | Phase 3.2 | Phase 3.3 |
|------|-----------|-----------|-----------|
| R1 MiniMax API | ✅ LLM cache | ✅ retry 已实施 | |
| R2 chunk reset | ✅ persistence | | |
| R4 GDPR | ✅ persistence 含 delete | | |
| R5 数据误用 | | ✅ AI 输出过滤 | |
| R6 AI 幻觉 | | ✅ 单元测试覆盖 | ✅ PoC 人工评估 |
| R8 测试覆盖 | | ✅ ≥80% | |
| R10 多用户隔离 | ✅ persistence + tests | ✅ 集成测试 | |

---

## 5. GDPR / 隐私详细方案

```sql
-- 学生数据访问审计
CREATE TABLE access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    accessor_id TEXT NOT NULL,  -- 教师/家长/学生本人
    operation TEXT,  -- 'read_state' / 'modify_state' / 'delete'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT
);

-- 数据保留期限管理
CREATE TABLE retention_policy (
    student_id TEXT PRIMARY KEY,
    graduation_date DATE,
    deletion_date DATE,  -- graduation_date + 3 years
    status TEXT  -- 'active' / 'pending_deletion' / 'deleted'
);

-- 加密敏感字段（应用层处理）
-- 例：student_id = hash(school_id + salt)
-- 例：name = AES_Encrypt(real_name, key_from_env)
```

**合规检查清单**：
- [ ] 加密 student_id（不能用明文 email）
- [ ] 加密 student name（FERPA compliance）
- [ ] 审计日志记录所有访问
- [ ] 删除权：24 小时内响应家长请求
- [ ] 数据最小化：只存必要的 SubjectMastery 数据
- [ ] 知情同意：使用前家长 + 学生签字
- [ ] 数据可携带：家长可导出孩子数据

---

## 6. 关联文档

- [README.md](../README.md) — Phase 3 SSOT
- [02-architecture.md](./02-architecture.md) — 架构边界
- [03-roadmap.md](./03-roadmap.md) — 时间线
- [10-engineering/](../10-engineering/) — 各工程文件

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-22
