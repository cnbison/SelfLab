# 10-01 - 持久化层（SQLite + TwinStateDB）

> **目的**：把 SGE 4 层状态 + App 状态持久化到 SQLite，解决 M2.2 chunk reset 痛点
> **关联**：[README.md §P0 任务](../README.md)、[discussions/2026-06-21-...-strategic-significance.md §9](../../../discussions/2026-06-21-sge-strategic-significance.md)

---

## 1. 状态清点（12 项需要持久化）

```
┌─ SGE 内部状态（必须持久化）─────────────────────┐
│ 1. HawkingDecay.memory (~921 条 after 1000h)        │
│ 2. MemoryCrystallizer.clusters (~9 clusters)        │
│ 3. ValueLayer.value_state (6D)                       │
│ 4. DriveMetabolism.drive_state + frustration (5D)   │
│ 5. IdentityLayer.identity_history (~50 条)           │
│ 6. NarrativeBuilder.narrative_history (~50 条)        │
│ 7. EventGenerator.event_history (~1000 条)            │
│ 8. Agent 内部状态（step counter 等）                │
├─ App 层状态（领域相关，App 自管）──────────────────┤
│ 9. SubjectMasteryState（学生领域）                 │
│ 10. 原始事件流（数据审计/重放）                     │
│ 11. 用户对话历史                                    │
│ 12. 学生元数据                                       │
└─────────────────────────────────────────────────────┘
```

---

## 2. 设计原则

| 原则 | 说明 |
|------|------|
| 轻依赖 | 不引入 SQLAlchemy / Django ORM |
| 可读优先 | JSON > Pickle > Protobuf（v1 期调试友好）|
| schema 版本化 | 字段必须可演进，schema_version 嵌入 JSON |
| chunk reset 修复 | M2.2 痛点：跨 chunk 状态丢失 → 持久化解决 |
| 细粒度恢复 | 可只恢复 Identity / Narrative / Hawking |
| 延迟写入 | 不阻塞 SGE 主循环 |

---

## 3. 格式 + 存储选择（v1 决策）

| 决策 | 选择 | 理由 |
|------|------|------|
| **格式** | JSON | M2.2/M2.3 已用 JSON，延续工具链一致 |
| **存储** | SQLite | 单文件、SQL 查询、事务、Phase 4 可迁 PostgreSQL |
| 拒绝 Pickle | — | 版本敏感 + 安全风险 |
| 拒绝 Protobuf | — | v1 期过度设计 |

---

## 4. Schema 设计

```sql
-- 主表：每学生一行
CREATE TABLE students (
    student_id        TEXT PRIMARY KEY,
    name              TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at    TIMESTAMP,
    sge_state_json    TEXT NOT NULL,
    app_state_json    TEXT NOT NULL,
    schema_version    TEXT DEFAULT '1.0',
    last_epoch        INTEGER DEFAULT 0
);

-- 增量 checkpoint（回溯用）
CREATE TABLE checkpoints (
    checkpoint_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id        TEXT NOT NULL,
    epoch             INTEGER NOT NULL,
    saved_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sge_state_json    TEXT NOT NULL,
    trigger           TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 4 层细粒度表
CREATE TABLE identity_history (
    id, student_id, epoch, identity_text, length_chars, crystallized_at
);
CREATE TABLE narrative_history (
    id, student_id, epoch, narrative_text, length_chars, built_at
);
CREATE TABLE hawking_memory (
    id, student_id, inserted_at, weight, content_json
);
CREATE TABLE crystallizer_clusters (
    id, student_id, cluster_id, vec_json, weight, count
);

-- 学科掌握
CREATE TABLE subject_mastery (
    id, student_id, subject_name, overall_score, emotional_valence,
    last_updated, topics_json, UNIQUE(student_id, subject_name)
);

-- 审计 + GDPR
CREATE TABLE access_log (
    id, student_id, accessor_id, operation, timestamp, ip_address
);
CREATE TABLE retention_policy (
    student_id TEXT PRIMARY KEY,
    graduation_date DATE,
    deletion_date DATE,
    status TEXT
);

CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT);
```

---

## 5. Python API 设计（sge/persistence.py）

```python
import sqlite3
import json
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any

class TwinStateDB:
    """学生数字孪生状态持久化"""
    
    def __init__(self, db_path: str = "twins.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")  # 并发读
        self._init_schema()
    
    def _init_schema(self):
        """创建表（首次运行时）"""
        # ... SQL from §4 ...
    
    def save_full_state(self, student_id: str, sge_state: dict, 
                        app_state: dict, epoch: int, trigger: str = 'auto_100'):
        """全量保存（每 100 epoch 或 session end）"""
        with self.conn:
            self.conn.execute(
                """UPDATE students SET 
                   sge_state_json=?, app_state_json=?, 
                   last_epoch=?, last_active_at=CURRENT_TIMESTAMP
                   WHERE student_id=?""",
                (json.dumps(sge_state), json.dumps(app_state), 
                 epoch, student_id)
            )
            self.conn.execute(
                """INSERT INTO checkpoints (student_id, epoch, sge_state_json, trigger)
                   VALUES (?, ?, ?, ?)""",
                (student_id, epoch, json.dumps(sge_state), trigger)
            )
    
    def save_incremental(self, student_id: str, layer: str, 
                         data: list, epoch: int):
        """增量保存单层"""
        # identity / narrative / hawking 各有专门处理
        ...
    
    def load_full_state(self, student_id: str) -> Tuple[dict, dict, int]:
        """加载完整状态"""
        row = self.conn.execute(
            "SELECT sge_state_json, app_state_json, last_epoch FROM students WHERE student_id=?",
            (student_id,)
        ).fetchone()
        if not row:
            return None, None, 0
        return json.loads(row[0]), json.loads(row[1]), row[2]
    
    def load_layer(self, student_id: str, layer: str) -> list:
        """细粒度恢复"""
        ...
    
    def delete_student(self, student_id: str):
        """GDPR right-to-deletion"""
        with self.conn:
            for table in ['identity_history', 'narrative_history',
                          'hawking_memory', 'crystallizer_clusters',
                          'subject_mastery', 'checkpoints',
                          'access_log', 'retention_policy', 'students']:
                self.conn.execute(
                    f"DELETE FROM {table} WHERE student_id=?",
                    (student_id,)
                )
```

---

## 6. 集成到 SGEOrchestrator

```python
class SGEOrchestrator:
    def __init__(self, ..., db: Optional[TwinStateDB] = None, 
                 student_id: Optional[str] = None):
        ...
        self.db = db
        self.student_id = student_id
    
    def step(self, epoch: int) -> OrchestratorStep:
        trace = self._do_step(epoch)
        # 自动 checkpoint hook
        if self.db and self.student_id and (epoch + 1) % 100 == 0:
            self._save_checkpoint()
        return trace
    
    def _save_checkpoint(self):
        sge_state = {
            'hawking_memory': self.hawking.memory,
            'crystallizer_clusters': self.crystallizer.clusters,
            'value_state': self.value_layer.value_state,
            'drive_state': self.agent.drive_state,
            'frustration': self.drive_metabolism.frustration,
            'identity_history': self.identity_layer.identity_history,
            'narrative_history': self.narrative_builder.narrative_history,
            'event_history': self.event_generator.event_history,
        }
        self.db.save_full_state(
            self.student_id, sge_state, {},
            epoch=self.current_epoch, trigger='auto_100'
        )
```

---

## 7. 写入策略

| 触发 | 频率 | 内容 |
|------|------|------|
| 每 100 epoch | 自动 | 全量 JSON |
| Identity 结晶 | 事件 | 单条 INSERT |
| Narrative 构建 | 事件 | 单条 INSERT |
| Session 结束 | 应用层 | 全量 |
| Phase Transition | 事件 | 全量 |
| 手动 | 用户触发 | 全量 |

---

## 8. Schema 版本管理

```python
# sge_state_json 内部结构
{
    "_schema_version": "1.0",
    "_saved_at": "2026-06-21T...",
    "_sge_version": "0.1.0",
    "data": {"hawking_memory": [...], ...}
}

def migrate(state_json, from_v, to_v):
    if from_v == '1.0' and to_v == '2.0':
        # rename 'frustration' → 'frustration_per_drive'
        ...
```

---

## 9. 解决 M2.2 chunk reset

```
E4 v4 (chunk 模式):        E4 v5 (持久化模式):
  chunk 0: ep 0-249          chunk 0: ep 0-249
    save in log                save → DB
  chunk 1: ep 250-499       chunk 1: ep 250-499
    [Hawking 状态丢失!]         LOAD ← DB
    save in log                save → DB
```

---

## 10. 实施清单

| 子任务 | 工作量 |
|--------|--------|
| `sge/persistence.py` (TwinStateDB) | 1.5 天 |
| 单元测试（save/load 各层）| 0.5 天 |
| SGEOrchestrator 集成 hook | 0.5 天 |
| Migration 框架 | 0.5 天 |
| 文档 + 示例 | 0.5 天 |
| **总计** | **3.5 天** |

---

## 11. 关联文档

- [README.md §P0 任务](../README.md)
- [02-architecture.md §应用层边界](../../00-overview/02-architecture.md)
- [02-session.md](./02-session.md) — Session 层（依赖 persistence）
- [04-risks.md §R2/R4/R10](../../00-overview/04-risks.md) — chunk reset + GDPR + 数据隔离

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-22
