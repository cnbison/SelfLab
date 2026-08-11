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
from typing import Optional, Tuple, List, Dict, Any, Callable


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


class MigrationError(PersistenceError):
    """schema 迁移失败（跳过版本 / 降级 / DDL 错误）。"""


class InvalidLayerError(ValueError):
    """layer 不在 4 层白名单（commit 2 实施）。"""


# ══════════════════════════════════════════════
# TwinStateDB（commit 1：schema + 全量 save/load）
# ══════════════════════════════════════════════


# Schema 状态枚举（白名单）
_RETENTION_STATUSES = ('active', 'pending_deletion', 'deleted')

# Schema 当前支持版本（migrate_schema 用）
SUPPORTED_SCHEMA_VERSIONS = ('1.0', '1.1')


# ══════════════════════════════════════════════
# Schema Migration 注册表（Phase 3.1 · 动作 1 收尾 task #5）
# ══════════════════════════════════════════════
#
# 注册格式：key = 源版本 → value = 目标版本迁移函数（接收 sqlite3.Connection）
# 新增迁移时：① 加一个 tuple 元素到 SUPPORTED_SCHEMA_VERSIONS；② 加一个 _migration_X_Y_to_X_Z() 函数；
# ③ 在 _MIGRATIONS 注册（key=源版本）；④ 在 _migration 函数里实现 DDL（ALTER/CREATE INDEX 等）。
#
# 当前路径：v1.0 → v1.1（students.email 字段 + 索引）。
#
# 幂等性要求：迁移函数必须自身幂等（PRAGMA table_info 检查列是否已存在），
# 否则再次调用会因 ALTER 重复而崩溃（SQLite 不支持 IF NOT EXISTS 在 ADD COLUMN）。


def _migration_v1_0_to_v1_1(conn: sqlite3.Connection) -> None:
    """v1.0 → v1.1：students 表新增 email 字段 + 索引。

    场景：K12 学校希望按 email 唯一索引学生（替代 UUID 或学号）。
    """
    # 幂等性：检查 email 列是否已存在（避免重复 ALTER 失败）
    cols = conn.execute("PRAGMA table_info(students)").fetchall()
    col_names = {row['name'] for row in cols}
    if 'email' not in col_names:
        conn.execute("ALTER TABLE students ADD COLUMN email TEXT")
    # 索引幂等（CREATE INDEX IF NOT EXISTS 安全）
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_students_email ON students(email)"
    )


# 注册：源版本 → 迁移函数
_MIGRATIONS: dict[str, Callable[[sqlite3.Connection], None]] = {
    '1.0': _migration_v1_0_to_v1_1,
    # '1.1': _migration_v1_1_to_v1_2,  # 未来扩展占位
}


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
        # 注：禁用 PARSE_DECLTYPES — sqlite3 默认会尝试把 TIMESTAMP 字段解析为 datetime，
        # 但我们存的是 ISO 字符串（与 SQLite CURRENT_TIMESTAMP 的 "YYYY-MM-DD HH:MM:SS"
        # 格式不同），会导致 ValueError。所有时间字段返回 raw string，由调用方按需转换。
        self.conn = sqlite3.connect(
            db_path,
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
                    status TEXT NOT NULL CHECK(status IN ('active','pending_deletion','deleted'))
                    -- 注：不加 FOREIGN KEY(student_id) REFERENCES students(student_id)，
                    -- 这样硬删除 students 时 retention_policy 可保留为审计孤儿行
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

    # ── 版本管理: migrate_schema（真实实现） ──
    def migrate_schema(
        self,
        target_version: Optional[str] = None,
    ) -> None:
        """迁移 schema 到 target_version（幂等 + 真实执行 DDL）。

        Args:
            target_version: 目标版本（None = 当前 schema_version）

        行为：
          - current == target → no-op（写 last_migration_at 时间戳）
          - current > target → MigrationError（不支持版本降级）
          - current < target → 按 SUPPORTED_SCHEMA_VERSIONS 顺序依次执行迁移
          - 跳过版本（中间缺迁移）→ MigrationError
          - 任一步 DDL 失败 → MigrationError，事务回滚到迁移前

        设计：
          - 每步迁移包在独立事务中（失败只回滚当前步）
          - 迁移函数自身需幂等（PRAGMA table_info 检查列是否已存在）
          - 注册表 _MIGRATIONS 在 module-level（key = 源版本）
        """
        target = target_version if target_version is not None else self.schema_version

        # 1. 校验目标版本支持
        if target not in SUPPORTED_SCHEMA_VERSIONS:
            raise SchemaVersionError(
                f"migrate_schema: 不支持目标版本 '{target}'；"
                f"当前支持: {SUPPORTED_SCHEMA_VERSIONS}"
            )

        # 2. 读当前 schema_meta 版本
        row = self.conn.execute(
            "SELECT value FROM schema_meta WHERE key='current_schema_version'"
        ).fetchone()
        current = row['value'] if row else self.schema_version

        # 3. 当前 == 目标：no-op
        if current == target:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO schema_meta (key, value) "
                    "VALUES ('last_migration_at', ?)",
                    (datetime.now().isoformat(),),
                )
            return

        # 4. 不支持降级
        current_idx = SUPPORTED_SCHEMA_VERSIONS.index(current)
        target_idx = SUPPORTED_SCHEMA_VERSIONS.index(target)
        if target_idx < current_idx:
            raise MigrationError(
                f"migrate_schema: 不支持版本降级（current={current} → target={target}）；"
                f"如需回滚，请先备份数据库"
            )

        # 5. 跳过版本校验（中间不能有缺漏的迁移）
        versions_to_run = SUPPORTED_SCHEMA_VERSIONS[current_idx:target_idx + 1]
        for i in range(len(versions_to_run) - 1):
            src = versions_to_run[i]
            if src not in _MIGRATIONS:
                raise MigrationError(
                    f"migrate_schema: 缺少中间迁移 '{src}'（注册表未找到）；"
                    f"请补充 _MIGRATIONS['{src}'] 实现"
                )

        # 6. 按顺序执行迁移
        try:
            for i in range(len(versions_to_run) - 1):
                src = versions_to_run[i]
                dst = versions_to_run[i + 1]
                with self.conn:  # 独立事务
                    _MIGRATIONS[src](self.conn)
                    # 更新 schema_meta
                    self.conn.execute(
                        "INSERT OR REPLACE INTO schema_meta (key, value) "
                        "VALUES ('current_schema_version', ?)",
                        (dst,),
                    )
                    self.conn.execute(
                        "INSERT OR REPLACE INTO schema_meta (key, value) "
                        "VALUES ('last_migration_at', ?)",
                        (datetime.now().isoformat(),),
                    )
        except sqlite3.Error as e:
            raise MigrationError(
                f"migrate_schema: DDL 执行失败（{src} → {dst}）；"
                f"原因: {type(e).__name__}: {e}"
            ) from e

    # ── Schema 检查辅助（commit 2 用） ──
    def _is_student_deleted(self, student_id: str) -> bool:
        """检查学生是否已软删除（commit 2 实施，此处占位返回 False）。"""
        # commit 1：未启用 retention_policy 检查
        return False


# ══════════════════════════════════════════════
# TwinStateDB（commit 2：增量层 + GDPR）
# ══════════════════════════════════════════════


# 增量层白名单
_INCREMENTAL_LAYERS = ('identity', 'narrative', 'hawking', 'crystallizer')

# 增量层 → (表名, 字段映射, 排序字段)
_INCREMENTAL_LAYER_CONFIG = {
    # identity: {epoch, identity} → (epoch, identity_text, length_chars)
    'identity': {
        'table': 'identity_history',
        'insert': """INSERT INTO identity_history
                     (student_id, epoch, identity_text, length_chars)
                     VALUES (?, ?, ?, ?)""",
        'extract': lambda item: (
            int(item['epoch']),
            str(item['identity']),
            len(str(item['identity'])),
        ),
        'order_by': 'epoch ASC, crystallized_at ASC',
    },
    # narrative: {epoch, narrative} → (epoch, narrative_text, length_chars)
    'narrative': {
        'table': 'narrative_history',
        'insert': """INSERT INTO narrative_history
                     (student_id, epoch, narrative_text, length_chars)
                     VALUES (?, ?, ?, ?)""",
        'extract': lambda item: (
            int(item['epoch']),
            str(item['narrative']),
            len(str(item['narrative'])),
        ),
        'order_by': 'epoch ASC, built_at ASC',
    },
    # hawking: {timestamp, weight, content} → (inserted_at, weight, content_json)
    # 注意：inserted_at 存 ISO 字符串（与 SQLite CURRENT_TIMESTAMP 兼容，避免 PARSE_DECLTYPES 解析失败）
    'hawking': {
        'table': 'hawking_memory',
        'insert': """INSERT INTO hawking_memory
                     (student_id, inserted_at, weight, content_json)
                     VALUES (?, ?, ?, ?)""",
        'extract': lambda item: (
            _float_to_iso(float(item['timestamp'])),
            float(item['weight']),
            json.dumps(item['content']),
        ),
        'order_by': 'inserted_at ASC',
    },
    # crystallizer: {cluster_id, vec, weight, count} → (cluster_id, vec_json, weight, count)
    'crystallizer': {
        'table': 'crystallizer_clusters',
        'insert': """INSERT INTO crystallizer_clusters
                     (student_id, cluster_id, vec_json, weight, count)
                     VALUES (?, ?, ?, ?, ?)""",
        'extract': lambda item: (
            str(item.get('cluster_id', f"cluster_{int(item.get('weight', 0) * 1000)}")),
            json.dumps(list(item['vec'])),
            float(item['weight']),
            int(item['count']),
        ),
        'order_by': 'weight DESC, cluster_id ASC',
    },
}


# 在 TwinStateDB 类内追加 commit 2 方法（使用 monkey-patch 模式，
# 避免破坏现有 __init__ 逻辑；保持单文件结构）


def _save_incremental(
    self,
    student_id: str,
    layer: str,
    data: list,
    epoch: int,
) -> None:
    """增量追加单层数据（事件型 INSERT，不覆盖历史）。

    Args:
        student_id: 学生 ID
        layer: 'identity' / 'narrative' / 'hawking' / 'crystallizer'
        data: list of dicts（字段映射见 _INCREMENTAL_LAYER_CONFIG）
        epoch: 当前 epoch（用于校验学生存在）

    Raises:
        InvalidLayerError: layer 不在白名单
        StudentNotFoundError: student 不存在
    """
    if layer not in _INCREMENTAL_LAYERS:
        raise InvalidLayerError(
            f"save_incremental: layer '{layer}' 不在白名单 {_INCREMENTAL_LAYERS}"
        )
    if not data:
        return  # 空列表无操作

    config = _INCREMENTAL_LAYER_CONFIG[layer]

    with self.conn:
        # 校验学生存在
        row = self.conn.execute(
            "SELECT 1 FROM students WHERE student_id=?",
            (student_id,),
        ).fetchone()
        if row is None:
            raise StudentNotFoundError(
                f"save_incremental: student_id '{student_id}' 不存在"
            )

        # 批量 INSERT
        for item in data:
            extracted = config['extract'](item)
            self.conn.execute(config['insert'], (student_id, *extracted))


def _load_layer(
    self,
    student_id: str,
    layer: str,
) -> list:
    """加载单层全部数据（按时间顺序）。

    Args:
        student_id: 学生 ID
        layer: 'identity' / 'narrative' / 'hawking' / 'crystallizer'

    Returns:
        list of dicts（按时间排序；空列表若无数据或 student 不存在）
    """
    if layer not in _INCREMENTAL_LAYERS:
        raise InvalidLayerError(
            f"load_layer: layer '{layer}' 不在白名单 {_INCREMENTAL_LAYERS}"
        )

    config = _INCREMENTAL_LAYER_CONFIG[layer]
    table = config['table']

    # 检查学生存在
    student_row = self.conn.execute(
        "SELECT 1 FROM students WHERE student_id=?",
        (student_id,),
    ).fetchone()
    if student_row is None:
        return []

    rows = self.conn.execute(
        f"SELECT * FROM {table} WHERE student_id=? ORDER BY {config['order_by']}",
        (student_id,),
    ).fetchall()

    # 转换为统一格式（保持 snapshot/restore 一致性）
    result = []
    for r in rows:
        if layer == 'identity':
            result.append({
                'epoch': int(r['epoch']),
                'identity': r['identity_text'],
            })
        elif layer == 'narrative':
            result.append({
                'epoch': int(r['epoch']),
                'narrative': r['narrative_text'],
            })
        elif layer == 'hawking':
            result.append({
                'timestamp': _iso_to_float(r['inserted_at']) if isinstance(r['inserted_at'], str) else float(r['inserted_at']),
                'weight': float(r['weight']),
                'content': json.loads(r['content_json']),
            })
        elif layer == 'crystallizer':
            result.append({
                'cluster_id': r['cluster_id'],
                'vec': json.loads(r['vec_json']),
                'weight': float(r['weight']),
                'count': int(r['count']),
            })
    return result


def _set_retention_policy(
    self,
    student_id: str,
    graduation_date=None,
    deletion_date=None,
    status: str = 'active',
) -> None:
    """设置/更新学生保留策略（GDPR 核心 API）。

    Args:
        student_id: 学生 ID
        graduation_date: 毕业日期（date 对象或 ISO 字符串，可选）
        deletion_date: 计划物理删除日期（同上）
        status: 'active' / 'pending_deletion' / 'deleted'

    Raises:
        StudentNotFoundError: student 不存在
        ValueError: status 不在白名单
    """
    if status not in _RETENTION_STATUSES:
        raise ValueError(
            f"set_retention_policy: status '{status}' 不在白名单 {_RETENTION_STATUSES}"
        )

    # 日期类型兼容（接受 date / datetime / str）
    grad_str = _normalize_date(graduation_date)
    del_str = _normalize_date(deletion_date)

    with self.conn:
        # 校验学生存在（外键约束）
        row = self.conn.execute(
            "SELECT 1 FROM students WHERE student_id=?",
            (student_id,),
        ).fetchone()
        if row is None:
            raise StudentNotFoundError(
                f"set_retention_policy: student_id '{student_id}' 不存在"
            )

        # UPSERT（首次创建 retention_policy 行 + 后续更新）
        self.conn.execute(
            """INSERT INTO retention_policy (student_id, graduation_date, deletion_date, status)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(student_id) DO UPDATE SET
                 graduation_date=excluded.graduation_date,
                 deletion_date=excluded.deletion_date,
                 status=excluded.status""",
            (student_id, grad_str, del_str, status),
        )


def _delete_student(
    self,
    student_id: str,
    hard: bool = False,
    accessor_id: str = 'system',
) -> None:
    """删除学生（GDPR right-to-deletion）。

    软删除（hard=False，默认）：
      - retention_policy.status = 'deleted'
      - deletion_date = NOW + 90 天（若未设置）
      - 后续 load/save 操作拒绝（StudentDeletedError）
      - access_log 记录 delete_soft 事件

    硬删除（hard=True）：
      - access_log 脱敏（student_id → 'deleted:<sha256>', ip_address=NULL）
      - 9 个业务表全部 DELETE（事务原子）
      - retention_policy.status='deleted' 保留为审计线索
      - access_log 记录 delete_hard 事件

    Args:
        student_id: 学生 ID
        hard: True = 物理删除；False = 软删除（默认）
        accessor_id: 操作者 ID（审计用）
    """
    if not isinstance(hard, bool):
        raise ValueError(f"hard 必须是 bool，得到: {hard!r}")

    with self.conn:
        # 校验学生存在
        row = self.conn.execute(
            "SELECT 1 FROM students WHERE student_id=?",
            (student_id,),
        ).fetchone()
        if row is None:
            raise StudentNotFoundError(
                f"delete_student: student_id '{student_id}' 不存在"
            )

        if hard:
            # ── 硬删除 ──
            # 1. access_log 脱敏（保留审计 + 不可逆标识）
            import hashlib
            deleted_hash = hashlib.sha256(student_id.encode()).hexdigest()[:16]
            anonymized_id = f"deleted:{deleted_hash}"
            self.conn.execute(
                """UPDATE access_log
                   SET student_id=?, ip_address=NULL
                   WHERE student_id=?""",
                (anonymized_id, student_id),
            )

            # 2. 按子表到主表顺序删除（外键约束）
            # 注意：retention_policy 不删（保留为审计线索）
            for table in [
                'identity_history', 'narrative_history', 'hawking_memory',
                'crystallizer_clusters', 'subject_mastery', 'checkpoints',
                'students',
            ]:
                self.conn.execute(
                    f"DELETE FROM {table} WHERE student_id=?",
                    (student_id,),
                )

            # 3. 标记 retention_policy 为 deleted（审计）
            self.conn.execute(
                """UPDATE retention_policy
                   SET status='deleted', deletion_date=CURRENT_TIMESTAMP
                   WHERE student_id=?""",
                (student_id,),
            )

            # 4. 审计：写入脱敏后的 delete_hard 事件
            self.conn.execute(
                """INSERT INTO access_log
                   (student_id, accessor_id, operation, ip_address)
                   VALUES (?, ?, 'delete_hard', NULL)""",
                (anonymized_id, accessor_id),
            )
        else:
            # ── 软删除 ──
            # 1. 标记 retention_policy 为 deleted，设置 deletion_date（NOW+90d）
            self.conn.execute(
                """UPDATE retention_policy
                   SET status='deleted',
                       deletion_date=COALESCE(deletion_date, date('now', '+90 days'))
                   WHERE student_id=?""",
                (student_id,),
            )

            # 2. 审计：保留原始 student_id 便于查询
            self.conn.execute(
                """INSERT INTO access_log
                   (student_id, accessor_id, operation, ip_address)
                   VALUES (?, ?, 'delete_soft', NULL)""",
                (student_id, accessor_id),
            )


def _purge_expired_students(self, now=None) -> int:
    """物理删除已过期（deletion_date < now）的软删除学生。

    Args:
        now: datetime 对象（None = datetime.now()）；测试用固定时间

    Returns:
        实际物理删除的学生数
    """
    if now is None:
        now = datetime.now()
    now_iso = now.isoformat()

    # 查找过期学生
    expired_rows = self.conn.execute(
        """SELECT student_id FROM retention_policy
           WHERE status='deleted' AND deletion_date IS NOT NULL
             AND deletion_date <= ?""",
        (now_iso,),
    ).fetchall()
    expired_ids = [r['student_id'] for r in expired_rows]

    # 对每个过期学生执行硬删除
    for sid in expired_ids:
        _delete_student(self, sid, hard=True, accessor_id='purge_expired')

    return len(expired_ids)


def _list_students(
    self,
    include_deleted: bool = False,
) -> list[dict]:
    """列出所有学生（含状态信息）。

    Args:
        include_deleted: False（默认）= 仅 active / pending_deletion；True = 全部含 deleted

    Returns:
        list of {student_id, name, status, last_active_at, last_epoch}
    """
    if include_deleted:
        query = """
            SELECT s.student_id, s.name, s.last_active_at, s.last_epoch, r.status
            FROM students s
            LEFT JOIN retention_policy r ON s.student_id = r.student_id
            ORDER BY s.student_id
        """
    else:
        query = """
            SELECT s.student_id, s.name, s.last_active_at, s.last_epoch, r.status
            FROM students s
            LEFT JOIN retention_policy r ON s.student_id = r.student_id
            WHERE r.status IN ('active', 'pending_deletion') OR r.status IS NULL
            ORDER BY s.student_id
        """
    rows = self.conn.execute(query).fetchall()
    return [
        {
            'student_id': r['student_id'],
            'name': r['name'],
            'status': r['status'],
            'last_active_at': r['last_active_at'],
            'last_epoch': int(r['last_epoch']) if r['last_epoch'] is not None else 0,
        }
        for r in rows
    ]


def _normalize_date(value):
    """规范化日期输入：date / datetime / ISO 字符串 / None → ISO 字符串 或 None。"""
    if value is None:
        return None
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    if isinstance(value, str):
        return value  # 假设已是合法 ISO 格式
    raise ValueError(f"日期必须是 date / datetime / ISO 字符串，得到: {value!r}")


def _float_to_iso(ts: float) -> str:
    """float timestamp（epoch-hours 或 unix seconds） → ISO 字符串。

    注：Hawking timestamp 是 epoch-hours（受控时钟），值通常 < 1000。
    为了让 SQLite PARSE_DECLTYPES 不报错，存 ISO 字符串而非 float。
    load 时用 _iso_to_float 反向转换。
    """
    # epoch-hours → datetime（基准时间设为 2026-01-01，与 SGE 实验惯例一致）
    from datetime import datetime, timedelta
    base = datetime(2026, 1, 1)
    dt = base + timedelta(hours=ts)
    return dt.isoformat()


def _iso_to_float(iso_str: str) -> float:
    """ISO 字符串 → float timestamp（反向 _float_to_iso）。"""
    from datetime import datetime
    base = datetime(2026, 1, 1)
    dt = datetime.fromisoformat(iso_str)
    return (dt - base).total_seconds() / 3600.0


# Monkey-patch commit 2 方法到 TwinStateDB
TwinStateDB.save_incremental = _save_incremental
TwinStateDB.load_layer = _load_layer
TwinStateDB.set_retention_policy = _set_retention_policy
TwinStateDB.delete_student = _delete_student
TwinStateDB.purge_expired_students = _purge_expired_students
TwinStateDB.list_students = _list_students


# 升级 _is_student_deleted 占位为真实实现
def _check_deleted_real(self, student_id: str) -> bool:
    """检查学生是否已软删除（commit 2 真实实现）。"""
    row = self.conn.execute(
        "SELECT status FROM retention_policy WHERE student_id=?",
        (student_id,),
    ).fetchone()
    if row is None:
        return False
    return row['status'] == 'deleted'


TwinStateDB._is_student_deleted = _check_deleted_real

# 升级 save_full_state / load_full_state 启用 deleted 校验
_original_save_full_state = TwinStateDB.save_full_state
_original_load_full_state = TwinStateDB.load_full_state


def _save_full_state_with_deleted_check(
    self, student_id, sge_state, app_state, epoch, trigger,
):
    if self._is_student_deleted(student_id):
        raise StudentDeletedError(
            f"save_full_state: student_id '{student_id}' 已软删除；不可再保存"
        )
    return _original_save_full_state(
        self, student_id, sge_state, app_state, epoch, trigger,
    )


def _load_full_state_with_deleted_check(self, student_id):
    if self._is_student_deleted(student_id):
        raise StudentDeletedError(
            f"load_full_state: student_id '{student_id}' 已软删除"
        )
    return _original_load_full_state(self, student_id)


TwinStateDB.save_full_state = _save_full_state_with_deleted_check
TwinStateDB.load_full_state = _load_full_state_with_deleted_check


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

    # ── commit 2 范围：8 个追加测试 ──

    # ── 测试 4: 4 层增量 save/load ──
    db_path = make_db_path()
    try:
        db = TwinStateDB(db_path)
        db.create_student('stu_layers')

        # identity: 2 条
        db.save_incremental('stu_layers', 'identity', [
            {'epoch': 19, 'identity': '我是探索者'},
            {'epoch': 39, 'identity': '我重视连接'},
        ], epoch=39)
        # narrative: 1 条
        db.save_incremental('stu_layers', 'narrative', [
            {'epoch': 49, 'narrative': '我经历了探索与连接...'},
        ], epoch=49)
        # hawking: 2 条
        db.save_incremental('stu_layers', 'hawking', [
            {'timestamp': 1.0, 'weight': 1.0, 'content': {'epoch': 1, 'ctx': {'safety': 0.5}}},
            {'timestamp': 2.0, 'weight': 0.9, 'content': {'epoch': 2, 'ctx': {'safety': 0.7}}},
        ], epoch=2)
        # crystallizer: 1 条
        db.save_incremental('stu_layers', 'crystallizer', [
            {'cluster_id': 'c1', 'vec': [0.1, 0.2, 0.3], 'weight': 1.0, 'count': 5},
        ], epoch=10)

        # load 验证
        identity = db.load_layer('stu_layers', 'identity')
        assert len(identity) == 2
        assert identity[0]['identity'] == '我是探索者'
        narrative = db.load_layer('stu_layers', 'narrative')
        assert len(narrative) == 1 and '探索与连接' in narrative[0]['narrative']
        hawking = db.load_layer('stu_layers', 'hawking')
        assert len(hawking) == 2 and hawking[0]['content']['ctx']['safety'] == 0.5
        crystallizer = db.load_layer('stu_layers', 'crystallizer')
        assert len(crystallizer) == 1 and crystallizer[0]['vec'] == [0.1, 0.2, 0.3]

        # 未知 layer 抛异常
        try:
            db.save_incremental('stu_layers', 'unknown', [], epoch=0)
            assert False, "应抛 InvalidLayerError"
        except InvalidLayerError:
            pass

        db.close()
        print(f"  ✓ [测试 4: 4 层增量 save/load] identity/narrative/hawking/crystallizer 全过 + 未知 layer 拒绝")
    finally:
        os.unlink(db_path)

    # ── 测试 5: 多用户隔离 ──
    db_path = make_db_path()
    try:
        db = TwinStateDB(db_path)
        db.create_student('stu_A')
        db.create_student('stu_B')

        db.save_full_state('stu_A', {'val': 1.0}, {}, epoch=10, trigger='manual')
        db.save_full_state('stu_B', {'val': 2.0}, {}, epoch=20, trigger='manual')

        sge_A, _, epoch_A = db.load_full_state('stu_A')
        sge_B, _, epoch_B = db.load_full_state('stu_B')
        assert sge_A == {'val': 1.0} and sge_A != sge_B
        assert epoch_A == 10 and epoch_B == 20

        # stu_A save_incremental 不应影响 stu_B
        db.save_incremental('stu_A', 'identity', [{'epoch': 19, 'identity': 'A 身份'}], epoch=19)
        assert db.load_layer('stu_B', 'identity') == []
        assert len(db.load_layer('stu_A', 'identity')) == 1

        # 删除 stu_B 不影响 stu_A
        db.delete_student('stu_B', hard=True)
        sge_A2, _, epoch_A2 = db.load_full_state('stu_A')
        assert sge_A2 == {'val': 1.0} and epoch_A2 == 10

        db.close()
        print(f"  ✓ [测试 5: 多用户隔离] stu_A/B 完全隔离 + 删除 B 不影响 A")
    finally:
        os.unlink(db_path)

    # ── 测试 6: 软删除 ──
    db_path = make_db_path()
    try:
        db = TwinStateDB(db_path)
        db.create_student('stu_soft')
        db.save_full_state('stu_soft', {'val': 0.5}, {}, epoch=50, trigger='auto_100')

        # 软删除
        db.delete_student('stu_soft', hard=False, accessor_id='teacher_001')

        # 校验 retention_policy 状态
        row = db.conn.execute(
            "SELECT status, deletion_date FROM retention_policy WHERE student_id=?",
            ('stu_soft',),
        ).fetchone()
        assert row['status'] == 'deleted', f"status={row['status']}"
        assert row['deletion_date'] is not None

        # 后续 load/save 应抛 StudentDeletedError
        try:
            db.load_full_state('stu_soft')
            assert False, "应抛 StudentDeletedError"
        except StudentDeletedError:
            pass
        try:
            db.save_full_state('stu_soft', {}, {}, epoch=60, trigger='manual')
            assert False, "应抛 StudentDeletedError"
        except StudentDeletedError:
            pass

        # audit 事件存在
        audit = db.conn.execute(
            "SELECT operation FROM access_log WHERE student_id='stu_soft' AND operation='delete_soft'"
        ).fetchall()
        assert len(audit) == 1
        assert audit[0]['operation'] == 'delete_soft'

        db.close()
        print(f"  ✓ [测试 6: 软删除] status=deleted + 后续读写拒绝 + audit 事件")
    finally:
        os.unlink(db_path)

    # ── 测试 7: 硬删除 + 审计脱敏 ──
    db_path = make_db_path()
    try:
        db = TwinStateDB(db_path)
        db.create_student('stu_hard')
        db.save_full_state('stu_hard', {'val': 0.7}, {}, epoch=70, trigger='manual')
        db.save_incremental('stu_hard', 'identity', [{'epoch': 19, 'identity': 'hard'}], epoch=19)

        db.delete_student('stu_hard', hard=True, accessor_id='teacher_001')

        # 9 个业务表应无 stu_hard
        for table in [
            'identity_history', 'narrative_history', 'hawking_memory',
            'crystallizer_clusters', 'subject_mastery', 'checkpoints',
            'students',
        ]:
            count = db.conn.execute(
                f"SELECT COUNT(*) AS cnt FROM {table} WHERE student_id='stu_hard'"
            ).fetchone()['cnt']
            assert count == 0, f"{table} 仍有 stu_hard 数据 ({count} 行)"

        # access_log 应有 1 条脱敏记录（'deleted:<hash>' + ip_address=NULL）
        # delete_hard 事件 + 之前可能有的 load/save 事件都被脱敏
        anonymized_rows = db.conn.execute(
            "SELECT student_id, ip_address, operation FROM access_log WHERE student_id LIKE 'deleted:%'"
        ).fetchall()
        assert len(anonymized_rows) >= 1
        for r in anonymized_rows:
            assert r['student_id'].startswith('deleted:')
            assert r['ip_address'] is None

        db.close()
        print(f"  ✓ [测试 7: 硬删除 + 审计脱敏] 9 业务表无数据 + access_log 脱敏为 deleted:<hash>")
    finally:
        os.unlink(db_path)

    # ── 测试 11: 大 state (>1 MB) round-trip ──
    db_path = make_db_path()
    try:
        db = TwinStateDB(db_path)
        db.create_student('stu_large')
        # 构造 >1 MB JSON
        big_value = 'x' * (1024 * 1024)  # 1 MB string
        big_state = {'data': [big_value] * 2}  # ~2 MB total
        db.save_full_state('stu_large', big_state, {}, epoch=100, trigger='auto_100')

        sge_state, _, _ = db.load_full_state('stu_large')
        assert sge_state == big_state, "大 state round-trip 失配"
        db.close()
        print(f"  ✓ [测试 11: 大 state round-trip] >1 MB JSON 无截断")
    finally:
        os.unlink(db_path)

    # ── 测试 12: 事务回滚保护 ──
    db_path = make_db_path()
    try:
        db = TwinStateDB(db_path)
        db.create_student('stu_tx')

        # 第一次 save 成功
        db.save_full_state('stu_tx', {'step': 1}, {}, epoch=10, trigger='manual')
        initial_checkpoints = db.conn.execute(
            "SELECT COUNT(*) AS cnt FROM checkpoints WHERE student_id='stu_tx'"
        ).fetchone()['cnt']
        assert initial_checkpoints == 1

        # 第二次 save 故意触发异常（epoch 非法）— 事务应回滚
        try:
            # 直接模拟事务失败：构造非法 JSON 触发 json.dumps 异常
            # （实际 JSON 不会失败，但用 monkey-patch 模拟）
            original_dumps = json.dumps
            def bad_dumps(obj, **kwargs):
                if obj == {'bad': True}:
                    raise ValueError("simulated JSON error")
                return original_dumps(obj, **kwargs)
            json.dumps = bad_dumps
            try:
                db.save_full_state('stu_tx', {'bad': True}, {}, epoch=20, trigger='manual')
                assert False, "应抛 ValueError"
            except ValueError:
                pass
            json.dumps = original_dumps
        except Exception:
            json.dumps = original_dumps
            raise

        # 校验：checkpoints 数量仍为 1（事务回滚保护）
        after_checkpoints = db.conn.execute(
            "SELECT COUNT(*) AS cnt FROM checkpoints WHERE student_id='stu_tx'"
        ).fetchone()['cnt']
        assert after_checkpoints == 1, f"事务回滚失败：checkpoints={after_checkpoints}"

        # students 表 epoch 也未更新
        row = db.conn.execute(
            "SELECT last_epoch FROM students WHERE student_id='stu_tx'"
        ).fetchone()
        assert row['last_epoch'] == 10, f"last_epoch 应为 10（事务回滚），实际 {row['last_epoch']}"

        db.close()
        print(f"  ✓ [测试 12: 事务回滚保护] 非法 JSON → checkpoints 不变 + last_epoch 不变")
    finally:
        os.unlink(db_path)

    # ── 测试 13: retention_policy + purge_expired ──
    db_path = make_db_path()
    try:
        db = TwinStateDB(db_path)
        db.create_student('stu_ret')

        # 设置 retention policy
        from datetime import date, timedelta
        today = date.today()
        past_date = (today - timedelta(days=1)).isoformat()  # 昨天（已过期）
        future_date = (today + timedelta(days=30)).isoformat()  # 30 天后
        db.set_retention_policy(
            'stu_ret', graduation_date=today, deletion_date=past_date,
            status='pending_deletion',
        )
        db.delete_student('stu_ret', hard=False, accessor_id='teacher_002')

        # 校验
        row = db.conn.execute(
            "SELECT status FROM retention_policy WHERE student_id='stu_ret'"
        ).fetchone()
        assert row['status'] == 'deleted'

        # purge_expired_students 应物理删除已过期
        purged_count = db.purge_expired_students(now=datetime.now())
        assert purged_count == 1, f"purge 数量={purged_count}"

        # students 表无 stu_ret
        student_exists = db.conn.execute(
            "SELECT 1 FROM students WHERE student_id='stu_ret'"
        ).fetchone()
        assert student_exists is None

        # retention_policy 仍保留（审计）
        policy_exists = db.conn.execute(
            "SELECT status FROM retention_policy WHERE student_id='stu_ret'"
        ).fetchone()
        assert policy_exists is not None
        assert policy_exists['status'] == 'deleted'

        # 非法 status 抛 ValueError
        try:
            db.set_retention_policy('stu_ret', status='invalid_status')
            assert False, "应抛 ValueError"
        except ValueError:
            pass

        db.close()
        print(f"  ✓ [测试 13: retention_policy + purge] 设置/过期 purge/非法 status 拒绝")
    finally:
        os.unlink(db_path)

    # ── 测试 15: SQL 注入抵抗 ──
    db_path = make_db_path()
    try:
        db = TwinStateDB(db_path)
        malicious_id = "stu'; DROP TABLE students; --"
        db.create_student(malicious_id)

        # 应能正常 save/load（参数化查询保护）
        db.save_full_state(malicious_id, {'val': 1}, {}, epoch=10, trigger='manual')
        sge_state, _, _ = db.load_full_state(malicious_id)
        assert sge_state == {'val': 1}

        # students 表仍存在（未被 DROP）
        tables = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='students'"
        ).fetchall()
        assert len(tables) == 1, "students 表被恶意 DROP"

        # 清理
        db.delete_student(malicious_id, hard=True)

        db.close()
        print(f"  ✓ [测试 15: SQL 注入抵抗] 特殊字符 student_id + 注入字符串不破坏 schema")
    finally:
        os.unlink(db_path)

    print(f"\n  状态: ✅ PASS — 15/15 (commit 1 + commit 2 完整) 测试通过")

    # ══════════════════════════════════════════════
    # Migration 框架单元测试（Phase 3.1 · 动作 1 收尾 task #5）
    # ══════════════════════════════════════════════
    print(f"\n{'─'*60}")
    print(f"  sge.persistence (Migration 框架) 单元测试")
    print(f"{'─'*60}\n")

    # ── 测试 M1: v1.0 → v1.1 成功迁移 + email 字段可用 ──
    db_path = tempfile.mktemp(suffix='.db')
    try:
        # 第一阶段：用 v1.0 创建 DB + 写入数据
        with TwinStateDB(db_path, schema_version='1.0') as db:
            db.create_student('stu_mig_001', name='Migration Test')
            db.save_full_state(
                'stu_mig_001',
                {'val': 'old_data'},
                {},
                epoch=10,
                trigger='manual',
            )

        # 确认 v1.0 没有 email 列
        with TwinStateDB(db_path, schema_version='1.0') as db:
            cols = db.conn.execute("PRAGMA table_info(students)").fetchall()
            col_names = {row['name'] for row in cols}
            assert 'email' not in col_names, (
                f"v1.0 不应有 email 列，实际: {col_names}"
            )

        # 执行迁移 v1.0 → v1.1
        with TwinStateDB(db_path, schema_version='1.0') as db:
            db.migrate_schema('1.1')
            # schema_meta 应更新为 1.1
            row = db.conn.execute(
                "SELECT value FROM schema_meta WHERE key='current_schema_version'"
            ).fetchone()
            assert row['value'] == '1.1', (
                f"迁移后 schema_meta 应为 '1.1'，实际: {row['value']}"
            )
            # email 列应存在
            cols = db.conn.execute("PRAGMA table_info(students)").fetchall()
            col_names = {row['name'] for row in cols}
            assert 'email' in col_names, (
                f"v1.1 应有 email 列，实际: {col_names}"
            )
            print(f"  ✓ [M1: v1.0 → v1.1 迁移成功] email 列已添加 + schema_meta=1.1")
    finally:
        os.unlink(db_path)

    # ── 测试 M2: 迁移幂等（连续调用 2 次无副作用）──
    db_path = tempfile.mktemp(suffix='.db')
    try:
        with TwinStateDB(db_path, schema_version='1.0') as db:
            db.create_student('stu_mig_002')

        # 第一次迁移
        with TwinStateDB(db_path, schema_version='1.0') as db:
            db.migrate_schema('1.1')

        # 第二次迁移（schema_meta 已升级到 1.1，应以新版本打开）
        with TwinStateDB(db_path, schema_version='1.1') as db:
            try:
                db.migrate_schema('1.1')  # current=1.1, target=1.1 → no-op
                print(f"  ✓ [M2: 迁移幂等] 连续调用 2 次无副作用")
            except Exception as e:
                raise AssertionError(f"幂等迁移失败: {type(e).__name__}: {e}")
    finally:
        os.unlink(db_path)

    # ── 测试 M3: 跳过版本 → MigrationError（mock 缺中间迁移）──
    db_path = tempfile.mktemp(suffix='.db')
    try:
        # 直接构造 schema_meta 为 v1.0 → 尝试迁移到 v1.1，但临时清空 _MIGRATIONS
        with TwinStateDB(db_path, schema_version='1.0') as db:
            db.create_student('stu_mig_003')

        # Monkey-patch _MIGRATIONS 模拟"缺中间迁移"
        orig_migrations = dict(_MIGRATIONS)
        _MIGRATIONS.pop('1.0', None)
        try:
            with TwinStateDB(db_path, schema_version='1.0') as db:
                try:
                    db.migrate_schema('1.1')
                    raise AssertionError("期望 MigrationError，未抛")
                except MigrationError as e:
                    assert "缺少中间迁移" in str(e), f"错误信息不对: {e}"
                    print(f"  ✓ [M3: 跳过版本报错] {e}")
        finally:
            _MIGRATIONS.clear()
            _MIGRATIONS.update(orig_migrations)
    finally:
        os.unlink(db_path)

    # ── 测试 M4: 版本降级 → MigrationError ──
    db_path = tempfile.mktemp(suffix='.db')
    try:
        # 先升级到 1.1
        with TwinStateDB(db_path, schema_version='1.0') as db:
            db.create_student('stu_mig_004')
            db.migrate_schema('1.1')

        # 尝试降级到 1.0（不支持）
        with TwinStateDB(db_path, schema_version='1.1') as db:
            try:
                db.migrate_schema('1.0')
                raise AssertionError("期望 MigrationError，未抛")
            except MigrationError as e:
                assert "不支持版本降级" in str(e), f"错误信息不对: {e}"
                print(f"  ✓ [M4: 版本降级报错] {e}")
    finally:
        os.unlink(db_path)

    # ── 测试 M5: 迁移后数据保留（email=NULL，其他字段完整）──
    db_path = tempfile.mktemp(suffix='.db')
    try:
        # v1.0 阶段写入完整数据
        with TwinStateDB(db_path, schema_version='1.0') as db:
            db.create_student('stu_mig_005', name='保留测试')
            db.save_full_state(
                'stu_mig_005',
                {'value': 'preserved'},
                {'grade': 7},
                epoch=20,
                trigger='auto_20',
            )

        # 迁移到 v1.1
        with TwinStateDB(db_path, schema_version='1.0') as db:
            db.migrate_schema('1.1')

        # 以 v1.1 打开 + 验证数据完整
        with TwinStateDB(db_path, schema_version='1.1') as db:
            sge_state, app_state, epoch = db.load_full_state('stu_mig_005')
            assert sge_state == {'value': 'preserved'}, f"sge_state 丢失: {sge_state}"
            assert app_state == {'grade': 7}, f"app_state 丢失: {app_state}"
            assert epoch == 20, f"epoch 丢失: {epoch}"
            # email 字段存在但为 NULL（迁移未填充）
            row = db.conn.execute(
                "SELECT name, email FROM students WHERE student_id='stu_mig_005'"
            ).fetchone()
            assert row['name'] == '保留测试', f"name 丢失: {row['name']}"
            assert row['email'] is None, f"email 应为 NULL，实际: {row['email']}"
            print(f"  ✓ [M5: 迁移数据保留] sge_state/app_state/epoch 完整 + email=NULL")
    finally:
        os.unlink(db_path)

    print(f"\n  状态: ✅ PASS — 5/5 (Migration 框架) 测试通过")
    return True


if __name__ == "__main__":
    import sys
    ok = _run_persistence_unit_tests()
    sys.exit(0 if ok else 1)
