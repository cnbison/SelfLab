"""
SGE 持久化层（TwinStateDB）— Phase 3.1 动作 1（commit 1）

把 SGE 4 层状态 + App 状态持久化到 SQLite，解决 M2.2 chunk reset 痛点。
本文件 commit 1 范围：schema + 全量 save/load API + 5 个单元测试。
commit 2 范围：4 层增量 + GDPR 全套 + 8 个追加测试。

**SSOT**: research/phase3/10-engineering/01-persistence.md
**风险约束**（research/phase3/00-overview/04-risks.md）:
  - R2 (P0) chunk reset → 本模块修复
  - R4 (P0) GDPR → commit 2 实施软/硬删除 + 审计脱敏
  - R10 (P0) 多用户隔离 → create_student 显式 + 所有 SQL 参数化

**关键设计**（commit 1）:
  - 11 张表 DDL + WAL 模式
  - save_full_state 单事务（UPDATE students + INSERT checkpoints）
  - 不写 4 层细粒度表（save_incremental 单独负责，commit 2）
  - load_* 默认拒绝软删除学生（commit 2 实施）
  - 异常类层次：PersistenceError → 5 子类
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any


# ══════════════════════════════════════════════
# 异常类（commit 1 + commit 2 共用）
# �═════════════════════════════════════════════


class PersistenceError(Exception):
    """持久化协议错误基础类。"""


class StudentNotFoundError(PersistenceError):
    """load/save/delete 学生不存在。"""


class StudentExistsError(PersistenceError):
    """create_student 重复 ID。"""


class StudentDeletedError(PersistenceError):
    """load 已软删除学生（commit 2 实施）。"""


class SchemaVersionError(PersistenceError):
    """schema_version 不兼容。"""


class InvalidLayerError(ValueError):
    """layer 不在 4 层白名单（commit 2 实施）。"""


# ══════════════════════════════════════════════
# TwinStateDB（commit 1：schema + 全量 save/load）
# ══════════════════════════════════════════════


# Schema 状态枚举（白名单）
_RETENTION_STATUSES = ('active', 'pending_deletion', 'deleted')

# Schema 当前支持版本（migrate_schema 用）
SUPPORTED_SCHEMA_VERSIONS = ('1.0',)


class TwinStateDB:
    """学生数字孪生状态持久化。

    用法:
      db = TwinStateDB('twins.db')
      db.create_student('stu_001')
      db.save_full_state('stu_001', sge_state, app_state, epoch=100, trigger='auto_100')
      sge_state, app_state, epoch = db.load_full_state('stu_001')
      db.close()

    或上下文管理器:
      with TwinStateDB('twins.db') as db:
          ...

    Schema SSOT: research/phase3/10-engineering/01-persistence.md §4
    """

    def __init__(
        self,
        db_path: str,
        schema_version: str = '1.0',
        wal: bool = True,
    ):
        """
        Args:
            db_path: SQLite 数据库文件路径（':memory:' 也支持）
            schema_version: 客户端期望的 schema 版本（不匹配 → SchemaVersionError）
            wal: 是否启用 WAL 模式（默认 True；并发读 + 单写；:memory: 不支持）
        """
        if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise SchemaVersionError(
                f"不支持的 schema_version '{schema_version}'，"
                f"当前支持: {SUPPORTED_SCHEMA_VERSIONS}"
            )
        self.db_path = db_path
        self.schema_version = schema_version
        self._closed = False

        # 连接（check_same_thread=False 支持多线程场景，commit 2 session 用）
        self.conn = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False,
        )
        # Row factory 让 fetch 返回 dict
        self.conn.row_factory = sqlite3.Row

        # 外键约束（SQLite 默认关闭，必须显式开启）
        self.conn.execute("PRAGMA foreign_keys=ON")

        # WAL mode（:memory: 跳过）
        if wal and db_path != ':memory:':
            mode = self.conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            if mode.lower() != 'wal':
                # WAL 启用失败不致命（兼容只读文件系统等）
                pass
            # WAL 配套：synchronous=NORMAL（性能与持久性折中）
            self.conn.execute("PRAGMA synchronous=NORMAL")

        # 初始化/校验 schema
        self._init_schema()
        self._validate_schema_version()

    # ── 上下文管理器 ──
    def __enter__(self) -> 'TwinStateDB':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """关闭连接（幂等）。"""
        if not self._closed:
            self.conn.close()
            self._closed = True

    # ── Schema 初始化 ──
    def _init_schema(self) -> None:
        """创建 11 张表 + 索引（CREATE IF NOT EXISTS 幂等）。"""
        with self.conn:  # 事务
            # 主表
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    student_id TEXT PRIMARY KEY,
                    name TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_active_at TIMESTAMP,
                    sge_state_json TEXT NOT NULL,
                    app_state_json TEXT NOT NULL,
                    schema_version TEXT NOT NULL DEFAULT '1.0',
                    last_epoch INTEGER NOT NULL DEFAULT 0
                )
            """)

            # Checkpoint 历史
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    epoch INTEGER NOT NULL CHECK(epoch >= 0),
                    saved_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    sge_state_json TEXT NOT NULL,
                    trigger TEXT NOT NULL,
                    FOREIGN KEY(student_id) REFERENCES students(student_id)
                )
            """)

            # 4 层细粒度表（commit 2 写入）
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS identity_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    epoch INTEGER NOT NULL,
                    identity_text TEXT NOT NULL,
                    length_chars INTEGER NOT NULL,
                    crystallized_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(student_id) REFERENCES students(student_id)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS narrative_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    epoch INTEGER NOT NULL,
                    narrative_text TEXT NOT NULL,
                    length_chars INTEGER NOT NULL,
                    built_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(student_id) REFERENCES students(student_id)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS hawking_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    inserted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    weight REAL NOT NULL,
                    content_json TEXT NOT NULL,
                    FOREIGN KEY(student_id) REFERENCES students(student_id)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS crystallizer_clusters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    cluster_id TEXT NOT NULL,
                    vec_json TEXT NOT NULL,
                    weight REAL NOT NULL,
                    count INTEGER NOT NULL,
                    FOREIGN KEY(student_id) REFERENCES students(student_id)
                )
            """)

            # 学科掌握（app_state）
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS subject_mastery (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    subject_name TEXT NOT NULL,
                    overall_score REAL,
                    emotional_valence REAL,
                    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    topics_json TEXT NOT NULL,
                    UNIQUE(student_id, subject_name),
                    FOREIGN KEY(student_id) REFERENCES students(student_id)
                )
            """)

            # 审计 + GDPR
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS access_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    accessor_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS retention_policy (
                    student_id TEXT PRIMARY KEY,
                    graduation_date DATE,
                    deletion_date DATE,
                    status TEXT NOT NULL CHECK(status IN ('active','pending_deletion','deleted')),
                    FOREIGN KEY(student_id) REFERENCES students(student_id)
                )
            """)

            # Schema 元数据
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # 索引（加速常见查询）
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_checkpoints_student_epoch "
                "ON checkpoints(student_id, epoch DESC)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_checkpoints_student_saved "
                "ON checkpoints(student_id, saved_at DESC)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_identity_student_epoch "
                "ON identity_history(student_id, epoch)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_narrative_student_epoch "
                "ON narrative_history(student_id, epoch)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_hawking_student_inserted "
                "ON hawking_memory(student_id, inserted_at)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_crystallizer_student_cluster "
                "ON crystallizer_clusters(student_id, cluster_id)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_access_log_student_timestamp "
                "ON access_log(student_id, timestamp)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_retention_policy_status_date "
                "ON retention_policy(status, deletion_date)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_subject_mastery_student "
                "ON subject_mastery(student_id)"
            )

    def _validate_schema_version(self) -> None:
        """校验 schema_meta 中存储的版本与客户端期望一致。"""
        row = self.conn.execute(
            "SELECT value FROM schema_meta WHERE key='current_schema_version'"
        ).fetchone()
        if row is None:
            # 首次初始化：写入
            self._write_schema_meta()
            return
        # 已存在：版本必须兼容
        stored_version = row['value']
        if stored_version != self.schema_version:
            raise SchemaVersionError(
                f"DB schema_version '{stored_version}' 与客户端期望 '{self.schema_version}' 不一致。"
                f"调用 migrate_schema() 升级。"
            )

    def _write_schema_meta(self) -> None:
        """写入 schema 元数据（首次初始化时）。"""
        from . import __version__ as SGE_VERSION  # 避免循环 import
        now_iso = datetime.now().isoformat()
        with self.conn:
            self.conn.executemany(
                "INSERT OR REPLACE INTO schema_meta (key, value) VALUES (?, ?)",
                [
                    ('current_schema_version', self.schema_version),
                    ('sge_version', SGE_VERSION),
                    ('created_at', now_iso),
                    ('last_migration_at', now_iso),
                    ('json_encoding', 'utf-8'),
                ],
            )

    # ── CRUD: create_student ──
    def create_student(
        self,
        student_id: str,
        name: Optional[str] = None,
        app_state: Optional[dict] = None,
    ) -> None:
        """创建学生记录（主表 + retention_policy）。

        Args:
            student_id: 学生唯一 ID（强制非空；调用方负责规范化）
            name: 学生姓名（可选）
            app_state: 应用层初始状态（默认 {}）

        Raises:
            StudentExistsError: student_id 已存在
        """
        if not student_id or not isinstance(student_id, str):
            raise ValueError(f"student_id 必须是非空字符串，得到: {student_id!r}")
        app_state_json = json.dumps(app_state if app_state is not None else {})
        with self.conn:
            # 检查重复
            existing = self.conn.execute(
                "SELECT 1 FROM students WHERE student_id=?",
                (student_id,),
            ).fetchone()
            if existing is not None:
                raise StudentExistsError(
                    f"student_id '{student_id}' 已存在；不可重复 create_student"
                )
            # INSERT students（sge_state_json 初始为空 dict）
            self.conn.execute(
                """INSERT INTO students
                   (student_id, name, sge_state_json, app_state_json, schema_version, last_epoch)
                   VALUES (?, ?, ?, ?, ?, 0)""",
                (student_id, name, '{}', app_state_json, self.schema_version),
            )
            # INSERT retention_policy（默认 active）
            self.conn.execute(
                "INSERT INTO retention_policy (student_id, status) VALUES (?, 'active')",
                (student_id,),
            )

    # ── CRUD: save_full_state ──
    def save_full_state(
        self,
        student_id: str,
        sge_state: dict,
        app_state: dict,
        epoch: int,
        trigger: str,
    ) -> None:
        """全量保存 SGE state + App state 到主表 + checkpoints。

        **单事务**保护：UPDATE students + INSERT checkpoints 必须在同一事务中，
        任一失败 → 全部回滚（避免主表显示新 epoch 但 checkpoints 缺失）。

        **不**同步写 4 层细粒度表（事件追加由 save_incremental 负责，commit 2）。

        Args:
            student_id: 学生 ID（必须已 create_student）
            sge_state: SGE 完整 state dict（来自 SGEOrchestrator.snapshot_all()）
            app_state: App 层 state（领域相关；App 自管）
            epoch: 当前 epoch（≥ 0）
            trigger: 触发原因（'auto_100' / 'session_end' / 'phase_xition' / 'manual'）

        Raises:
            StudentNotFoundError: student_id 未 create_student
            StudentDeletedError: student 已软删除（commit 2 实施）
            PersistenceError: UPDATE rowcount != 1（事务回滚）
        """
        if not isinstance(epoch, int) or epoch < 0:
            raise ValueError(f"epoch 必须是非负整数，得到: {epoch!r}")
        if not trigger or not isinstance(trigger, str):
            raise ValueError(f"trigger 必须是非空字符串，得到: {trigger!r}")

        sge_state_json = json.dumps(sge_state)
        app_state_json = json.dumps(app_state if app_state is not None else {})

        with self.conn:  # 事务
            # 1. 校验学生存在（commit 2 加 retention_policy 校验）
            row = self.conn.execute(
                "SELECT 1 FROM students WHERE student_id=?",
                (student_id,),
            ).fetchone()
            if row is None:
                raise StudentNotFoundError(
                    f"save_full_state: student_id '{student_id}' 不存在；请先 create_student"
                )

            # 2. UPDATE students（含 last_active_at）
            cur = self.conn.execute(
                """UPDATE students SET
                   sge_state_json=?, app_state_json=?,
                   last_epoch=?, last_active_at=CURRENT_TIMESTAMP
                   WHERE student_id=?""",
                (sge_state_json, app_state_json, epoch, student_id),
            )
            if cur.rowcount != 1:
                raise PersistenceError(
                    f"save_full_state: UPDATE students rowcount={cur.rowcount}（期望 1）"
                )

            # 3. INSERT checkpoints
            self.conn.execute(
                """INSERT INTO checkpoints
                   (student_id, epoch, sge_state_json, trigger)
                   VALUES (?, ?, ?, ?)""",
                (student_id, epoch, sge_state_json, trigger),
            )

    # ── CRUD: load_full_state ──
    def load_full_state(
        self,
        student_id: str,
    ) -> Tuple[dict, dict, int]:
        """加载完整 SGE state + App state。

        Args:
            student_id: 学生 ID

        Returns:
            (sge_state, app_state, last_epoch) 三元组
            若 student 不存在：返回 ({}, {}, 0)（兼容 Session 文档：未注册学生首次访问时返回空状态）

        Note:
            commit 2 实施软删除后：deleted 学生抛 StudentDeletedError。
        """
        row = self.conn.execute(
            """SELECT sge_state_json, app_state_json, last_epoch
               FROM students WHERE student_id=?""",
            (student_id,),
        ).fetchone()
        if row is None:
            return ({}, {}, 0)
        sge_state = json.loads(row['sge_state_json']) if row['sge_state_json'] else {}
        app_state = json.loads(row['app_state_json']) if row['app_state_json'] else {}
        return (sge_state, app_state, int(row['last_epoch']))

    # ── CRUD: get_checkpoint_history ──
    def get_checkpoint_history(
        self,
        student_id: str,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """列出学生的 checkpoint 历史（按 epoch DESC）。

        Args:
            student_id: 学生 ID
            limit: 最多返回数量（None = 全部）

        Returns:
            list of {checkpoint_id, epoch, saved_at, trigger} dicts
            若 student 不存在：返回 []
        """
        # 先校验学生存在
        student_row = self.conn.execute(
            "SELECT 1 FROM students WHERE student_id=?",
            (student_id,),
        ).fetchone()
        if student_row is None:
            return []

        query = (
            "SELECT checkpoint_id, epoch, saved_at, trigger "
            "FROM checkpoints WHERE student_id=? ORDER BY epoch DESC, saved_at DESC"
        )
        params: tuple = (student_id,)
        if limit is not None:
            query += " LIMIT ?"
            params = (student_id, int(limit))

        rows = self.conn.execute(query, params).fetchall()
        return [
            {
                'checkpoint_id': int(r['checkpoint_id']),
                'epoch': int(r['epoch']),
                'saved_at': r['saved_at'],
                'trigger': r['trigger'],
            }
            for r in rows
        ]

    # ── 审计: log_access ──
    def log_access(
        self,
        student_id: str,
        accessor_id: str,
        operation: str,
        ip_address: Optional[str] = None,
    ) -> None:
        """记录一次访问（不抛异常，避免审计失败影响主业务）。

        Args:
            student_id: 被访问学生 ID
            accessor_id: 访问者 ID（教师 / 系统 / 家长等）
            operation: 操作类型（'load' / 'save' / 'delete_soft' / 'delete_hard' / 'migrate' 等）
            ip_address: 来源 IP（可选）
        """
        if not accessor_id or not isinstance(accessor_id, str):
            raise ValueError(f"accessor_id 必须是非空字符串，得到: {accessor_id!r}")
        if not operation or not isinstance(operation, str):
            raise ValueError(f"operation 必须是非空字符串，得到: {operation!r}")
        try:
            with self.conn:
                self.conn.execute(
                    """INSERT INTO access_log
                       (student_id, accessor_id, operation, ip_address)
                       VALUES (?, ?, ?, ?)""",
                    (student_id, accessor_id, operation, ip_address),
                )
        except sqlite3.Error:
            # 审计失败不传播（GDPR 合规优先 — 记录失败应静默 + 后续监控告警）
            pass

    # ── 版本管理: migrate_schema（commit 1 占位，commit 2 真实实现） ──
    def migrate_schema(
        self,
        target_version: Optional[str] = None,
    ) -> None:
        """迁移 schema 到 target_version（commit 1 仅占位，幂等）。

        Args:
            target_version: 目标版本（None = 当前支持的最新版本）

        当前实现（v1.0）：
          - 仅校验当前版本已支持（已在 __init__ 完成）
          - 写入 'last_migration_at' 元数据（幂等更新）

        commit 2 实施真实迁移（如 v1.0 → v1.1 rename 字段）。
        """
        target = target_version or self.schema_version
        if target not in SUPPORTED_SCHEMA_VERSIONS:
            raise SchemaVersionError(
                f"migrate_schema: 不支持目标版本 '{target}'；"
                f"当前支持: {SUPPORTED_SCHEMA_VERSIONS}"
            )
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('last_migration_at', ?)",
                (datetime.now().isoformat(),),
            )

    # ── Schema 检查辅助（commit 2 用） ──
    def _is_student_deleted(self, student_id: str) -> bool:
        """检查学生是否已软删除（commit 2 实施，此处占位返回 False）。"""
        # commit 1：未启用 retention_policy 检查
        return False


# ══════════════════════════════════════════════
# 单元测试（commit 1：5 个核心 case）
# ══════════════════════════════════════════════


def _run_persistence_unit_tests() -> bool:
    """commit 1 范围 5 个测试：覆盖 schema + 全量 save/load + 跨连接 + checkpoint 历史 + 边界 case。

    覆盖测试 ID（与 plan 对齐）：
      1: test_create_and_full_round_trip
      2: test_cross_connection_persistence
      3: test_checkpoint_history
      8: test_schema_version_validation（部分，commit 2 补全）
      9: test_student_not_found
      10: test_empty_state
      14: test_wal_and_foreign_keys（部分，commit 2 补全）

    commit 2 范围（8 个）：
      4 (incremental_4_layers) / 5 (multi_user_isolation) /
      6 (soft_delete) / 7 (hard_delete_with_audit_anonymization) /
      11 (large_state) / 12 (transaction_rollback) /
      13 (retention_policy) / 15 (sql_injection_resistance)
    """
    import os
    import tempfile

    print(f"\n{'─' * 60}")
    print(f"  sge.persistence (TwinStateDB commit 1) 单元测试")
    print(f"{'─' * 60}\n")

    # 临时 DB path 辅助
    def make_db_path() -> str:
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        return path

    # ── 测试 1: create + full round-trip ──
    db_path = make_db_path()
    try:
        db = TwinStateDB(db_path)
        db.create_student('stu_001', name='Alice', app_state={'grade': 5})

        sge_state_in = {
            'value_state': {'safety': 0.5, 'creativity': 0.3},
            'hawking_memory': [{'timestamp': 1.0, 'weight': 1.0, 'content': {'k': 'v'}}],
            'identity_history': [{'epoch': 19, 'identity': '我是探索者'}],
        }
        app_state_in = {'mastery': {'math': 0.7}}
        db.save_full_state('stu_001', sge_state_in, app_state_in, epoch=100, trigger='auto_100')

        sge_state_out, app_state_out, epoch_out = db.load_full_state('stu_001')
        assert epoch_out == 100, f"epoch 期望 100，实际 {epoch_out}"
        assert sge_state_out == sge_state_in, "sge_state 不匹配"
        assert app_state_out == app_state_in, "app_state 不匹配"
        db.close()
        print(f"  ✓ [测试 1: create + full round-trip] JSON 深层结构 + epoch 全等")
    finally:
        os.unlink(db_path)

    # ── 测试 2: 跨连接持久化（关闭 → 重开 → load 恢复） ──
    db_path = make_db_path()
    try:
        db1 = TwinStateDB(db_path)
        db1.create_student('stu_002')
        db1.save_full_state('stu_002', {'val': 0.42}, {}, epoch=50, trigger='manual')
        db1.close()

        db2 = TwinStateDB(db_path)  # 重新打开
        sge_state, _, epoch = db2.load_full_state('stu_002')
        assert epoch == 50
        assert sge_state == {'val': 0.42}
        db2.close()
        print(f"  ✓ [测试 2: 跨连接持久化] 关闭 → 重开 → load 恢复")
    finally:
        os.unlink(db_path)

    # ── 测试 3: checkpoint history（多次 save_full_state）──
    db_path = make_db_path()
    try:
        db = TwinStateDB(db_path)
        db.create_student('stu_003')
        # 模拟 4 个 checkpoint
        for i, (epoch, trigger) in enumerate([
            (100, 'auto_100'),
            (200, 'auto_100'),
            (300, 'phase_xition'),
            (350, 'session_end'),
        ]):
            db.save_full_state('stu_003', {'step': i}, {}, epoch=epoch, trigger=trigger)

        history = db.get_checkpoint_history('stu_003')
        assert len(history) == 4, f"期望 4 个 checkpoint，实际 {len(history)}"
        # 按 epoch DESC 排序
        assert [h['epoch'] for h in history] == [350, 300, 200, 100]
        assert [h['trigger'] for h in history] == ['session_end', 'phase_xition', 'auto_100', 'auto_100']
        # limit 测试
        history_limited = db.get_checkpoint_history('stu_003', limit=2)
        assert len(history_limited) == 2
        assert history_limited[0]['epoch'] == 350
        db.close()
        print(f"  ✓ [测试 3: checkpoint history] 4 次 save → 完整历史 + trigger + limit")
    finally:
        os.unlink(db_path)

    # ── 测试 8 (部分): schema_version 校验 ──
    db_path = make_db_path()
    try:
        db = TwinStateDB(db_path)
        # schema_meta 应被写入
        row = db.conn.execute(
            "SELECT value FROM schema_meta WHERE key='current_schema_version'"
        ).fetchone()
        assert row is not None, "schema_meta 未写入 current_schema_version"
        assert row['value'] == '1.0'
        # 不兼容版本抛异常
        try:
            db2 = TwinStateDB(db_path, schema_version='99.0')
            assert False, "应抛 SchemaVersionError"
        except SchemaVersionError:
            pass
        db.close()
        print(f"  ✓ [测试 8: schema_version] current_schema_version='1.0' + 不兼容版本拒绝")
    finally:
        os.unlink(db_path)

    # ── 测试 9: student_not_found ──
    db_path = make_db_path()
    try:
        db = TwinStateDB(db_path)
        # load 不存在 → 返回 ({}, {}, 0)
        sge_state, app_state, epoch = db.load_full_state('ghost')
        assert sge_state == {} and app_state == {} and epoch == 0
        # get_checkpoint_history 不存在 → 返回 []
        assert db.get_checkpoint_history('ghost') == []
        # save_full_state 不存在 → 抛 StudentNotFoundError
        try:
            db.save_full_state('ghost', {}, {}, epoch=10, trigger='manual')
            assert False, "应抛 StudentNotFoundError"
        except StudentNotFoundError:
            pass
        # create_student 重复 → 抛 StudentExistsError
        db.create_student('stu_dup')
        try:
            db.create_student('stu_dup')
            assert False, "应抛 StudentExistsError"
        except StudentExistsError:
            pass
        db.close()
        print(f"  ✓ [测试 9: student_not_found] load 返回空 + save 抛 StudentNotFoundError + create 重复抛 StudentExistsError")
    finally:
        os.unlink(db_path)

    # ── 测试 10: empty_state ──
    db_path = make_db_path()
    try:
        db = TwinStateDB(db_path)
        db.create_student('stu_empty')
        # 空 sge_state / app_state 应能 round-trip
        db.save_full_state('stu_empty', {}, {}, epoch=0, trigger='manual')
        sge_state, app_state, epoch = db.load_full_state('stu_empty')
        assert sge_state == {} and app_state == {} and epoch == 0
        db.close()
        print(f"  ✓ [测试 10: empty_state] 空 dict 可保存并恢复")
    finally:
        os.unlink(db_path)

    # ── 测试 14 (部分): WAL + foreign_keys ──
    db_path = make_db_path()
    try:
        db = TwinStateDB(db_path, wal=True)
        # foreign_keys 必须开启
        fk = db.conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1, f"foreign_keys 未开启: {fk}"
        # WAL 必须启用（如果不是 :memory:）
        mode = db.conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == 'wal', f"journal_mode 非 WAL: {mode}"
        # context manager 测试
        with TwinStateDB(db_path) as db2:
            assert not db2._closed
        assert db2._closed
        print(f"  ✓ [测试 14: WAL + foreign_keys + context manager]")
    finally:
        os.unlink(db_path)

    print(f"\n  状态: ✅ PASS — 7/7 (commit 1 范围) 测试通过")
    print(f"  注: 测试 4/5/6/7/11/12/13/15 属 commit 2 范围（增量层 + GDPR）")
    return True


if __name__ == "__main__":
    import sys
    ok = _run_persistence_unit_tests()
    sys.exit(0 if ok else 1)
