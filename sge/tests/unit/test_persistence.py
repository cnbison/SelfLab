"""sge.persistence pytest 单元测试 — TwinStateDB 完整 20 + migration 5 = 25 个 case。

Phase 3.2 conversion 3/N。
"""

from __future__ import annotations

import datetime
import json
from datetime import date, timedelta

import pytest

from sge import TwinStateDB
from sge.persistence import (
    SUPPORTED_SCHEMA_VERSIONS,
    _MIGRATIONS,
    PersistenceError, StudentNotFoundError, StudentExistsError,
    StudentDeletedError, SchemaVersionError, MigrationError,
    InvalidLayerError,
)


# ── commit 1: 7 个基础测试 ──


def test_create_and_full_round_trip(tmp_db_path):
    """ create + save + load 全等（JSON 深层结构 + epoch）。 """
    with TwinStateDB(tmp_db_path) as db:
        db.create_student('stu_001', name='Alice', app_state={'grade': 5})
        sge_state_in = {
            'value_state': {'safety': 0.5, 'creativity': 0.3},
            'hawking_memory': [{'timestamp': 1.0, 'weight': 1.0, 'content': {'k': 'v'}}],
            'identity_history': [{'epoch': 19, 'identity': '我是探索者'}],
        }
        app_state_in = {'mastery': {'math': 0.7}}
        db.save_full_state('stu_001', sge_state_in, app_state_in, epoch=100, trigger='auto_100')

    with TwinStateDB(tmp_db_path) as db:
        sge_state_out, app_state_out, epoch_out = db.load_full_state('stu_001')
    assert epoch_out == 100
    assert sge_state_out == sge_state_in
    assert app_state_out == app_state_in


def test_cross_connection_persistence(tmp_db_path):
    """ 关闭 → 重开 → load 恢复。 """
    with TwinStateDB(tmp_db_path) as db:
        db.create_student('stu_002')
        db.save_full_state('stu_002', {'val': 0.42}, {}, epoch=50, trigger='manual')

    with TwinStateDB(tmp_db_path) as db:
        sge_state, _, epoch = db.load_full_state('stu_002')
    assert epoch == 50
    assert sge_state == {'val': 0.42}


def test_checkpoint_history_ordering_and_limit(tmp_db_path):
    """ 多次 save → checkpoint history 完整 + 按 epoch DESC + limit 工作。 """
    with TwinStateDB(tmp_db_path) as db:
        db.create_student('stu_003')
        for i, (epoch, trigger) in enumerate([
            (100, 'auto_100'),
            (200, 'auto_100'),
            (300, 'phase_xition'),
            (350, 'session_end'),
        ]):
            db.save_full_state('stu_003', {'step': i}, {}, epoch=epoch, trigger=trigger)

    with TwinStateDB(tmp_db_path) as db:
        history = db.get_checkpoint_history('stu_003')
    assert len(history) == 4
    assert [h['epoch'] for h in history] == [350, 300, 200, 100]
    assert [h['trigger'] for h in history] == ['session_end', 'phase_xition', 'auto_100', 'auto_100']

    with TwinStateDB(tmp_db_path) as db:
        history_limited = db.get_checkpoint_history('stu_003', limit=2)
    assert len(history_limited) == 2
    assert history_limited[0]['epoch'] == 350


def test_schema_version_validation(tmp_db_path):
    """ schema_meta 写入 + 不兼容版本抛 SchemaVersionError。 """
    with TwinStateDB(tmp_db_path) as db:
        row = db.conn.execute(
            "SELECT value FROM schema_meta WHERE key='current_schema_version'"
        ).fetchone()
        assert row is not None
        assert row['value'] == '1.0'

    with pytest.raises(SchemaVersionError):
        TwinStateDB(tmp_db_path, schema_version='99.0')


def test_student_not_found_returns_empty(tmp_db_path):
    """ load 不存在的 student 返回 ({}, {}, 0)；get_checkpoint_history 返回 []。 """
    with TwinStateDB(tmp_db_path) as db:
        sge_state, app_state, epoch = db.load_full_state('ghost')
        assert sge_state == {} and app_state == {} and epoch == 0
        assert db.get_checkpoint_history('ghost') == []


def test_save_full_state_raises_student_not_found(tmp_db_path):
    """ save 到不存在的 student 抛 StudentNotFoundError。 """
    with TwinStateDB(tmp_db_path) as db:
        with pytest.raises(StudentNotFoundError):
            db.save_full_state('ghost', {}, {}, epoch=10, trigger='manual')


def test_create_student_duplicate_raises(tmp_db_path):
    """ 重复 create_student 抛 StudentExistsError。 """
    with TwinStateDB(tmp_db_path) as db:
        db.create_student('stu_dup')
        with pytest.raises(StudentExistsError):
            db.create_student('stu_dup')


def test_empty_state_round_trip(tmp_db_path):
    """ 空 dict 可 round-trip。 """
    with TwinStateDB(tmp_db_path) as db:
        db.create_student('stu_empty')
        db.save_full_state('stu_empty', {}, {}, epoch=0, trigger='manual')

    with TwinStateDB(tmp_db_path) as db:
        sge_state, app_state, epoch = db.load_full_state('stu_empty')
    assert sge_state == {} and app_state == {} and epoch == 0


def test_wal_and_foreign_keys_enabled(tmp_db_path):
    """ WAL 模式 + foreign_keys 开启 + context manager。 """
    with TwinStateDB(tmp_db_path, wal=True) as db:
        fk = db.conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1
        mode = db.conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == 'wal'


def test_context_manager_closes_on_exit(tmp_db_path):
    """ with 语句退出后 _closed=True。 """
    with TwinStateDB(tmp_db_path) as db:
        assert not db._closed
    assert db._closed


# ── commit 2: 8 个追加测试 ──


def test_incremental_save_load_4_layers(tmp_db_path):
    """ identity / narrative / hawking / crystallizer 4 层增量。 """
    with TwinStateDB(tmp_db_path) as db:
        db.create_student('stu_layers')
        db.save_incremental('stu_layers', 'identity', [
            {'epoch': 19, 'identity': '我是探索者'},
            {'epoch': 39, 'identity': '我重视连接'},
        ], epoch=39)
        db.save_incremental('stu_layers', 'narrative', [
            {'epoch': 49, 'narrative': '我经历了探索与连接...'},
        ], epoch=49)
        db.save_incremental('stu_layers', 'hawking', [
            {'timestamp': 1.0, 'weight': 1.0, 'content': {'epoch': 1, 'ctx': {'safety': 0.5}}},
            {'timestamp': 2.0, 'weight': 0.9, 'content': {'epoch': 2, 'ctx': {'safety': 0.7}}},
        ], epoch=2)
        db.save_incremental('stu_layers', 'crystallizer', [
            {'cluster_id': 'c1', 'vec': [0.1, 0.2, 0.3], 'weight': 1.0, 'count': 5},
        ], epoch=10)

        identity = db.load_layer('stu_layers', 'identity')
        assert len(identity) == 2 and identity[0]['identity'] == '我是探索者'
        narrative = db.load_layer('stu_layers', 'narrative')
        assert len(narrative) == 1 and '探索与连接' in narrative[0]['narrative']
        hawking = db.load_layer('stu_layers', 'hawking')
        assert len(hawking) == 2 and hawking[0]['content']['ctx']['safety'] == 0.5
        crystallizer = db.load_layer('stu_layers', 'crystallizer')
        assert len(crystallizer) == 1 and crystallizer[0]['vec'] == [0.1, 0.2, 0.3]


def test_save_incremental_unknown_layer_raises(tmp_db_path):
    """ 未知 layer 抛 InvalidLayerError。 """
    with TwinStateDB(tmp_db_path) as db:
        db.create_student('stu_layers')
        with pytest.raises(InvalidLayerError):
            db.save_incremental('stu_layers', 'unknown', [], epoch=0)


def test_multi_user_isolation(tmp_db_path):
    """ 两个学生完全隔离 + 删除 B 不影响 A。 """
    with TwinStateDB(tmp_db_path) as db:
        db.create_student('stu_A')
        db.create_student('stu_B')
        db.save_full_state('stu_A', {'val': 1.0}, {}, epoch=10, trigger='manual')
        db.save_full_state('stu_B', {'val': 2.0}, {}, epoch=20, trigger='manual')

        sge_A, _, epoch_A = db.load_full_state('stu_A')
        sge_B, _, epoch_B = db.load_full_state('stu_B')
        assert sge_A == {'val': 1.0} and sge_A != sge_B
        assert epoch_A == 10 and epoch_B == 20

        db.save_incremental('stu_A', 'identity', [{'epoch': 19, 'identity': 'A 身份'}], epoch=19)
        assert db.load_layer('stu_B', 'identity') == []
        assert len(db.load_layer('stu_A', 'identity')) == 1

        db.delete_student('stu_B', hard=True)
        sge_A2, _, epoch_A2 = db.load_full_state('stu_A')
        assert sge_A2 == {'val': 1.0} and epoch_A2 == 10


def test_soft_delete_blocks_subsequent_access(tmp_db_path):
    """ 软删除 → status='deleted' + 后续读写抛 StudentDeletedError + audit 事件。 """
    with TwinStateDB(tmp_db_path) as db:
        db.create_student('stu_soft')
        db.save_full_state('stu_soft', {'val': 0.5}, {}, epoch=50, trigger='auto_100')
        db.delete_student('stu_soft', hard=False, accessor_id='teacher_001')

        row = db.conn.execute(
            "SELECT status, deletion_date FROM retention_policy WHERE student_id=?",
            ('stu_soft',),
        ).fetchone()
        assert row['status'] == 'deleted'
        assert row['deletion_date'] is not None

        with pytest.raises(StudentDeletedError):
            db.load_full_state('stu_soft')
        with pytest.raises(StudentDeletedError):
            db.save_full_state('stu_soft', {}, {}, epoch=60, trigger='manual')

        audit = db.conn.execute(
            "SELECT operation FROM access_log WHERE student_id='stu_soft' AND operation='delete_soft'"
        ).fetchall()
        assert len(audit) == 1


def test_hard_delete_anonymizes_audit_log(tmp_db_path):
    """ 硬删除 → 9 业务表无数据 + access_log 脱敏为 deleted:<hash>。 """
    with TwinStateDB(tmp_db_path) as db:
        db.create_student('stu_hard')
        db.save_full_state('stu_hard', {'val': 0.7}, {}, epoch=70, trigger='manual')
        db.save_incremental('stu_hard', 'identity', [{'epoch': 19, 'identity': 'hard'}], epoch=19)
        db.delete_student('stu_hard', hard=True, accessor_id='teacher_001')

        for table in [
            'identity_history', 'narrative_history', 'hawking_memory',
            'crystallizer_clusters', 'subject_mastery', 'checkpoints', 'students',
        ]:
            count = db.conn.execute(
                f"SELECT COUNT(*) AS cnt FROM {table} WHERE student_id='stu_hard'"
            ).fetchone()['cnt']
            assert count == 0, f"{table} 仍有 stu_hard 数据 ({count} 行)"

        anonymized = db.conn.execute(
            "SELECT student_id, ip_address FROM access_log WHERE student_id LIKE 'deleted:%'"
        ).fetchall()
        assert len(anonymized) >= 1
        for r in anonymized:
            assert r['student_id'].startswith('deleted:')
            assert r['ip_address'] is None


def test_large_state_round_trip(tmp_db_path):
    """ >1 MB JSON round-trip 无截断。 """
    big_value = 'x' * (1024 * 1024)
    big_state = {'data': [big_value] * 2}

    with TwinStateDB(tmp_db_path) as db:
        db.create_student('stu_large')
        db.save_full_state('stu_large', big_state, {}, epoch=100, trigger='auto_100')

    with TwinStateDB(tmp_db_path) as db:
        sge_state, _, _ = db.load_full_state('stu_large')
    assert sge_state == big_state


def test_transaction_rollback_on_save_failure(tmp_db_path, monkeypatch):
    """ save 抛异常 → checkpoints 数不变 + last_epoch 不变（事务回滚）。 """
    with TwinStateDB(tmp_db_path) as db:
        db.create_student('stu_tx')
        db.save_full_state('stu_tx', {'step': 1}, {}, epoch=10, trigger='manual')

        original_dumps = json.dumps
        def bad_dumps(obj, **kwargs):
            if obj == {'bad': True}:
                raise ValueError("simulated JSON error")
            return original_dumps(obj, **kwargs)
        monkeypatch.setattr('sge.persistence.json.dumps', bad_dumps)

        with pytest.raises(ValueError):
            db.save_full_state('stu_tx', {'bad': True}, {}, epoch=20, trigger='manual')

    with TwinStateDB(tmp_db_path) as db:
        cnt = db.conn.execute(
            "SELECT COUNT(*) AS cnt FROM checkpoints WHERE student_id='stu_tx'"
        ).fetchone()['cnt']
        assert cnt == 1
        row = db.conn.execute(
            "SELECT last_epoch FROM students WHERE student_id='stu_tx'"
        ).fetchone()
        assert row['last_epoch'] == 10


def test_retention_policy_and_purge(tmp_db_path):
    """ retention_policy 设置 + 过期 purge + 非法 status 拒绝。 """
    today = date.today()
    past_date = (today - timedelta(days=1)).isoformat()

    with TwinStateDB(tmp_db_path) as db:
        db.create_student('stu_ret')
        db.set_retention_policy(
            'stu_ret', graduation_date=today, deletion_date=past_date,
            status='pending_deletion',
        )
        db.delete_student('stu_ret', hard=False, accessor_id='teacher_002')

        row = db.conn.execute(
            "SELECT status FROM retention_policy WHERE student_id='stu_ret'"
        ).fetchone()
        assert row['status'] == 'deleted'

        purged = db.purge_expired_students(now=datetime.datetime.now())
        assert purged == 1

        student_exists = db.conn.execute(
            "SELECT 1 FROM students WHERE student_id='stu_ret'"
        ).fetchone()
        assert student_exists is None

        policy = db.conn.execute(
            "SELECT status FROM retention_policy WHERE student_id='stu_ret'"
        ).fetchone()
        assert policy is not None and policy['status'] == 'deleted'

        with pytest.raises(ValueError):
            db.set_retention_policy('stu_ret', status='invalid_status')


def test_sql_injection_resistance(tmp_db_path):
    """ SQL 注入字符串作为 student_id 不破坏 schema。 """
    malicious_id = "stu'; DROP TABLE students; --"
    with TwinStateDB(tmp_db_path) as db:
        db.create_student(malicious_id)
        db.save_full_state(malicious_id, {'val': 1}, {}, epoch=10, trigger='manual')

    with TwinStateDB(tmp_db_path) as db:
        sge_state, _, _ = db.load_full_state(malicious_id)
    assert sge_state == {'val': 1}

    with TwinStateDB(tmp_db_path) as db:
        tables = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='students'"
        ).fetchall()
        assert len(tables) == 1


# ── Migration 框架（5 个测试） ──


def test_supported_schema_versions_constant():
    assert '1.0' in SUPPORTED_SCHEMA_VERSIONS
    assert '1.1' in SUPPORTED_SCHEMA_VERSIONS


def test_migration_v1_0_to_v1_1_adds_email_column(tmp_db_path):
    """ v1.0 → v1.1 迁移成功（email 字段 + 索引 + schema_meta=1.1）。 """
    with TwinStateDB(tmp_db_path, schema_version='1.0') as db:
        db.create_student('stu_mig_001', name='Migration Test')
        db.save_full_state('stu_mig_001', {'val': 'old_data'}, {}, epoch=10, trigger='manual')

    with TwinStateDB(tmp_db_path, schema_version='1.0') as db:
        cols = {r['name'] for r in db.conn.execute("PRAGMA table_info(students)").fetchall()}
        assert 'email' not in cols

    with TwinStateDB(tmp_db_path, schema_version='1.0') as db:
        db.migrate_schema('1.1')

    with TwinStateDB(tmp_db_path, schema_version='1.1') as db:
        row = db.conn.execute(
            "SELECT value FROM schema_meta WHERE key='current_schema_version'"
        ).fetchone()
        assert row['value'] == '1.1'
        cols = {r['name'] for r in db.conn.execute("PRAGMA table_info(students)").fetchall()}
        assert 'email' in cols


def test_migration_idempotent(tmp_db_path):
    """ 连续调用 2 次迁移无副作用。 """
    with TwinStateDB(tmp_db_path, schema_version='1.0') as db:
        db.create_student('stu_mig_002')

    with TwinStateDB(tmp_db_path, schema_version='1.0') as db:
        db.migrate_schema('1.1')

    with TwinStateDB(tmp_db_path, schema_version='1.1') as db:
        # current=1.1, target=1.1 → no-op
        db.migrate_schema('1.1')


def test_migration_skip_version_raises(monkeypatch, tmp_db_path):
    """ 缺中间迁移 → MigrationError（'缺少中间迁移'）。 """
    with TwinStateDB(tmp_db_path, schema_version='1.0') as db:
        db.create_student('stu_mig_003')

    orig = dict(_MIGRATIONS)
    _MIGRATIONS.pop('1.0', None)
    try:
        with TwinStateDB(tmp_db_path, schema_version='1.0') as db:
            with pytest.raises(MigrationError, match="缺少中间迁移"):
                db.migrate_schema('1.1')
    finally:
        _MIGRATIONS.clear()
        _MIGRATIONS.update(orig)


def test_migration_downgrade_raises(tmp_db_path):
    """ 版本降级 → MigrationError（'不支持版本降级'）。 """
    with TwinStateDB(tmp_db_path, schema_version='1.0') as db:
        db.create_student('stu_mig_004')
        db.migrate_schema('1.1')

    with TwinStateDB(tmp_db_path, schema_version='1.1') as db:
        with pytest.raises(MigrationError, match="不支持版本降级"):
            db.migrate_schema('1.0')


def test_migration_preserves_data(tmp_db_path):
    """ 迁移后 sge_state / app_state / epoch 完整 + email=NULL。 """
    with TwinStateDB(tmp_db_path, schema_version='1.0') as db:
        db.create_student('stu_mig_005', name='保留测试')
        db.save_full_state(
            'stu_mig_005',
            {'value': 'preserved'},
            {'grade': 7},
            epoch=20,
            trigger='auto_20',
        )

    with TwinStateDB(tmp_db_path, schema_version='1.0') as db:
        db.migrate_schema('1.1')

    with TwinStateDB(tmp_db_path, schema_version='1.1') as db:
        sge_state, app_state, epoch = db.load_full_state('stu_mig_005')
        assert sge_state == {'value': 'preserved'}
        assert app_state == {'grade': 7}
        assert epoch == 20
        row = db.conn.execute(
            "SELECT name, email FROM students WHERE student_id='stu_mig_005'"
        ).fetchone()
        assert row['name'] == '保留测试'
        assert row['email'] is None


def test_log_access_records_audit(tmp_db_path):
    """ log_access 写入 access_log（含 accessor_id / operation / ip_address）。 """
    with TwinStateDB(tmp_db_path) as db:
        db.create_student('stu_audit')
        db.log_access('stu_audit', accessor_id='teacher_x', operation='view',
                      ip_address='192.168.1.1')
        rows = db.conn.execute(
            "SELECT accessor_id, operation, ip_address FROM access_log "
            "WHERE student_id='stu_audit' ORDER BY id DESC LIMIT 1"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]['accessor_id'] == 'teacher_x'
        assert rows[0]['operation'] == 'view'
        assert rows[0]['ip_address'] == '192.168.1.1'


def test_list_students_includes_active_excludes_deleted_by_default(tmp_db_path):
    """ list_students 默认不含已删除学生。 """
    with TwinStateDB(tmp_db_path) as db:
        db.create_student('stu_active')
        db.create_student('stu_deleted')
        db.delete_student('stu_deleted', hard=False, accessor_id='admin')

        listed = db.list_students()
        ids = {s['student_id'] for s in listed}
        assert 'stu_active' in ids
        assert 'stu_deleted' not in ids

        listed_all = db.list_students(include_deleted=True)
        ids_all = {s['student_id'] for s in listed_all}
        assert 'stu_deleted' in ids_all


def test_purge_expired_students_returns_count(tmp_db_path):
    """ purge_expired_students 返回清理的学生数。 """
    today = date.today()
    past_date = (today - timedelta(days=400)).isoformat()

    with TwinStateDB(tmp_db_path) as db:
        db.create_student('stu_p1')
        db.create_student('stu_p2')
        for sid in ('stu_p1', 'stu_p2'):
            db.set_retention_policy(
                sid, graduation_date=today, deletion_date=past_date,
                status='pending_deletion',
            )
            db.delete_student(sid, hard=False, accessor_id='admin')

        purged = db.purge_expired_students(now=datetime.datetime.now())
        assert purged == 2