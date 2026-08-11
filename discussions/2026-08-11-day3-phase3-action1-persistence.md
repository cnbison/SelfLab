# 会话记录：Day 3 Phase 3.1 动作 1 — persistence.py（TwinStateDB v1.5）实施

> **会话定位**：续接 `2026-08-11-day3-phase3-action2-snapshot-restore.md`（动作 2 完成），执行 Day 3 第二个任务（Status-Map §4 动作 1 — TwinStateDB 实施，1.5 天工作量）。下一会话启动 Day 4（集成 hook + migration + 文档）。

日期：2026-08-11

参与者：Bisen & Claude

---

## 讨论主题

Status-Map §4 动作 1 是动作 2（snapshot/restore 接口）解锁后的下一个里程碑。`research/phase3/10-engineering/01-persistence.md` §10 实施清单第一项：**M2.2 chunk reset 痛点（R2 P0）的根本修复**。直接消费昨天落地的 `SGEOrchestrator.snapshot_all()` 接口，把 SGE 状态写入 SQLite + JSON。

## 背景与动机

- Day 1+2 完成文档清理（5 个🔴 + 2 个� 漂移）
- Day 3 动作 2 完成（snapshot/restore 接口 + 17/17 测试）
- Day 3 动作 1 启动：persistence.py（TwinStateDB）+ 6 个 Bisen schema 决策已采纳
- Day 4 延后（2 天）：SGEOrchestrator 集成 hook + migration 框架 + 文档示例

## 4 个 Bisen schema 决策（已采纳）

| # | 决策点 | 选择 | 理由 |
|---|--------|------|------|
| 1 | value_state/identity_state 序列化 | **拆分 4 层细粒度表 + sge_state_json 总览** | 细粒度表支持 SQL 查询 + 单层恢复 + 历史审计 |
| 2 | GDPR delete 语义 | **软删除**（retention_policy + 审计保留） | K12 学生数据有法律保留义务，需软删除 + 宽限期 |
| 3 | checkpoint 触发策略 | **多触发点**：100 epoch/session end/phase transition/手动 | 满足不同应用层需求 |
| 4 | 跨 chunk 一致性 | **混合**：主表 WAL + 100 epoch 全量；细粒度表增量 INSERT | 主表全量保证跨进程恢复；细粒度表追加保留事件历史 |

## Plan agent 反对意见（采纳）

- **save_full_state 不应同步写 4 层细粒度表**：避免重复 + 避免覆盖历史。细粒度表是事件追加（save_incremental 单独），与全量快照语义分离
- **主表 UPDATE + checkpoints INSERT 必须同事务**：`rowcount == 1` 校验；任一失败 → 全部回滚
- **access_log 硬删除时脱敏**：`student_id` 替换为 `deleted:<sha256>` 不可逆 hash + `ip_address=NULL`
- **`create_student` 显式**：避免 save_full_state 静默 INSERT student（违反 R10 多用户隔离）
- **`load_*` 默认拒绝软删除学生**：避免删除后静默恢复（持久化层防线，不依赖调用方记得过滤）

## 实施清单

| Commit | 文件 | 改动 |
|--------|------|------|
| **commit 1 (`16c4d36`)** | sge/sge/persistence.py | +781 行：6 异常类 + TwinStateDB 9 方法 + 11 表 DDL + 9 索引 + WAL 配置 + 7 测试 |
| **commit 2 (`ecf8cf3`)** | sge/sge/persistence.py | +794 行：6 方法 + 4 层 schema 配置 + Hawking ISO 序列化 + GDPR 全套 + monkey-patch deleted 校验 + 8 测试 |

**总计**：1 个文件，+1570 行（含 DDL + 15 个单元测试）

## 单元测试结果（15/15 全绿）

### commit 1（7 个）
- ✓ 测试 1: create + full round-trip（JSON 深层结构 + epoch 全等）
- ✓ 测试 2: 跨连接持久化（关闭 → 重开 → load 恢复）
- ✓ 测试 3: checkpoint history（4 次 save → 完整历史 + trigger + limit）
- ✓ 测试 8: schema_version（写入 + 不兼容拒绝）
- ✓ 测试 9: student_not_found（load 返回空 + save 抛异常 + create 重复）
- ✓ 测试 10: empty_state（空 dict round-trip）
- ✓ 测试 14: WAL + foreign_keys + context manager

### commit 2（8 个）
- ✓ 测试 4: 4 层增量 save/load（identity/narrative/hawking/crystallizer + 未知 layer 拒绝）
- ✓ 测试 5: 多用户隔离（stu_A/B 完全隔离 + 删除 B 不影响 A）
- ✓ 测试 6: 软删除（status=deleted + 后续读写拒绝 + audit 事件）
- ✓ 测试 7: 硬删除 + 审计脱敏（9 业务表无数据 + access_log 脱敏 deleted:<hash>）
- ✓ 测试 11: 大 state round-trip（>1 MB JSON 无截断）
- ✓ 测试 12: 事务回滚保护（非法 JSON → checkpoints + last_epoch 不变）
- ✓ 测试 13: retention_policy + purge（过期 purge + 非法 status 拒绝）
- ✓ 测试 15: SQL 注入抵抗（特殊字符 student_id + 注入字符串不破坏 schema）

## 实施过程的关键修复

1. **SQLite `PARSE_DECLTYPES` 与 ISO timestamp 冲突**：sqlite3 默认尝试把 TIMESTAMP 字段解析为 datetime，但我们存的是 ISO 字符串（与 SQLite CURRENT_TIMESTAMP 的 "YYYY-MM-DD HH:MM:SS" 格式不同）→ 禁用 PARSE_DECLTYPES
2. **Hawking timestamp 序列化**：Hawking timestamp 是 epoch-hours（受控时钟），需要 ISO 字符串存储 → `_float_to_iso` / `_iso_to_float` 辅助函数（基准时间 2026-01-01）
3. **retention_policy 外键约束失败**：硬删除 students 时，retention_policy 的 FOREIGN KEY 引用 → 移除 retention_policy 的外键约束，保留为审计孤儿行
4. **monkey-patch deleted 校验**：原 `save_full_state` / `load_full_state` 不检查 deletion status → wrap 原始方法，commit 2 启用持久化层防线

## TwinStateDB 完整 API（15 个方法）

```python
class TwinStateDB:
    # 连接管理
    def __init__(db_path, schema_version='1.0', wal=True)
    def __enter__ / __exit__ / close

    # CRUD（commit 1）
    def create_student(student_id, name=None, app_state=None)
    def save_full_state(student_id, sge_state, app_state, epoch, trigger)
    def load_full_state(student_id) -> Tuple[dict, dict, int]
    def get_checkpoint_history(student_id, limit=None)

    # 审计
    def log_access(student_id, accessor_id, operation, ip_address=None)

    # 版本管理
    def migrate_schema(target_version=None)  # commit 1 占位

    # 增量层（commit 2）
    def save_incremental(student_id, layer, data, epoch)
    def load_layer(student_id, layer) -> list

    # GDPR（commit 2）
    def set_retention_policy(student_id, graduation_date, deletion_date, status)
    def delete_student(student_id, hard=False, accessor_id='system')
    def purge_expired_students(now=None) -> int
    def list_students(include_deleted=False) -> list[dict]
```

## 11 张 SQLite 表（完整 DDL）

```sql
students (主表) + checkpoints (历史) + 4 细粒度层表
  + subject_mastery (app_state)
  + access_log (审计，硬删除脱敏)
  + retention_policy (保留策略，不加 FK 保留孤儿审计)
  + schema_meta (版本元数据)
```

**索引**：9 个覆盖常见查询模式（checkpoint by epoch DESC, layer by epoch/inserted_at, audit by student+timestamp, retention by status+deletion_date）

## 产出文件

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `sge/sge/persistence.py` | commit 1 + 2 | **新建**（TwinStateDB + 异常类 + 11 表 DDL + 15 个测试） |
| `CHANGELOG.md` | 1.33.0 索引行 | Day 3 动作 1 完成记录 |

## Git 状态

```
16c4d36 feat(sge): TwinStateDB schema + 全量 save/load API（Phase 3.1 动作 1 commit 1）
ecf8cf3 feat(sge): TwinStateDB 增量层 + GDPR 全套（Phase 3.1 动作 1 commit 2）
（即将提交）docs: CHANGELOG 1.33.0 + Day 3 动作 1 会话简记
```

净行数：+1570 行（1 文件）+ CHANGELOG +1 行

## 风险解决状态

| 风险 | 等级 | 状态 |
|------|------|------|
| **R2** chunk reset | 🔴 P0 | ✅ 已修复（save_full_state/load_full_state round-trip + 跨连接持久化） |
| **R4** GDPR 隐私 | 🔴 P0 | ✅ 已修复（软删除 + 硬删除脱敏 + access_log 审计 + purge_expired_students） |
| **R10** 多用户隔离 | 🔴 P0 | ✅ 已修复（create_student 显式 + 所有 SQL 参数化 + 测试 5/15 强制覆盖） |

## 是否产生关键洞察

**否**。本次会话是**纯工程实施**——按已采纳的 schema 决策落地 persistence 层，未引入新概念。但 Phase 3.1 整体（动作 1 + 2）形成的洞察：

- **洞察候选 37**："Self 的可序列化性"——Runtime 状态托管统一（snapshot_all）是 Self Evolution Runtime 的**必要前提**（洞察 33 的工程落地）；没有快照接口，persistence / 跨进程恢复 / A/B 测试都无从谈起

**建议下次会话讨论**是否升格为正式洞察并写入 SGE-Key-Insights.md。

## 下次会话建议起点

**Day 4 范围**（2 天）：
1. **SGEOrchestrator 集成 hook**（0.5 天）
   - `__init__` 新增 `db + student_id + checkpoint_every` 参数
   - `step()` 末尾添加 `_maybe_checkpoint()` 钩子（每 N epoch 自动 save_full_state）
   - Phase Transition / Session End 触发手动 checkpoint
2. **Migration 框架真实实现**（0.5 天）
   - `migrate_schema()` 支持 v1.0 → v1.1 真实迁移（如 rename 字段）
   - migration 注册表 + 幂等执行
3. **文档 + 示例**（0.5 天）
   - `sge/__init__.py` 导出 `TwinStateDB`
   - `sge/README.md` 更新公开 API + Phase 3.1 持久化示例
   - `examples/persistence_demo.py`
4. **Phase 3.2 单元测试覆盖 ≥ 80%**（3.5 天）— 后续 Phase 3.2 范围

## 关联文档

- [SGE-Status-Map §3.1/§4 动作 1](../../SGE-Status-Map.md) — 本次任务的状态来源
- [research/phase3/10-engineering/01-persistence.md](../../research/phase3/10-engineering/01-persistence.md) — 设计 SSOT
- [research/phase3/00-overview/04-risks.md](../../research/phase3/00-overview/04-risks.md) — R2/R4/R10 风险矩阵
- [research/phase3/10-engineering/02-session.md](../../research/phase3/10-engineering/02-session.md) — Day 5+ 范围（依赖 persistence）
- [discussions/2026-08-11-day3-phase3-action2-snapshot-restore.md](./2026-08-11-day3-phase3-action2-snapshot-restore.md) — 动作 2 前置

---

**记录者**：Bisen & Claude
**最后更新**：2026-08-11
