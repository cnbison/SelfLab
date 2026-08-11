"""
SGE 持久化端到端 Demo（Phase 3.1 · 动作 1 收尾 task #6）

演示场景：模拟 K12 学生数字孪生场景
- 创建 stu_demo
- 用 SGEOrchestrator(stub LLM) 跑 50 epoch，checkpoint_every=10
- 验证自动 checkpoint 历史 + access_log 审计
- session_end 触发最后一次 checkpoint
- 跨连接持久化验证（关闭 → 重开 → load）
- 模拟 GDPR 软删除 + load 抛 StudentDeletedError
- 模拟 retention_policy + purge_expired_students

运行：python sge/examples/persistence_demo.py
"""

import datetime
import os
import sys
import tempfile

from sge import (
    Agent, DriveMetabolism, ValueLayer, HawkingDecay, MemoryCrystallizer,
    EventGenerator, IdentityLayer, NarrativeBuilder,
    SGEOrchestrator, TwinStateDB,
    StudentDeletedError,
)


def main():
    print("=" * 70)
    print("SGE 持久化 Demo（Phase 3.1 · 动作 1）")
    print("=" * 70)

    # 1. 创建临时 DB + 学生
    db_path = tempfile.mktemp(suffix='.db')
    print(f"\n[1] 创建临时 DB: {db_path}")

    with TwinStateDB(db_path) as db:
        db.create_student(
            student_id='stu_demo',
            name='Demo Student',
            app_state={'grade': 7, 'subject': 'math'},
        )
        print(f"  ✓ stu_demo 创建完成（app_state: grade=7, subject=math）")

    # 2. 跑 50 epoch × checkpoint_every=10（stub LLM，无需 API key）
    print(f"\n[2] 跑 50 epoch × checkpoint_every=10（stub LLM）")
    with TwinStateDB(db_path) as db:
        # 构造组件
        drives = ['exploration', 'safety', 'creativity', 'connection', 'autonomy']
        value_layer = ValueLayer()
        hawking = HawkingDecay(gamma=0.01, clock=0.0)
        crystallizer = MemoryCrystallizer(n_dims=11)
        agent = Agent(
            seed=42,
            drives=drives,
            value_layer=value_layer,
            hawking=hawking,
            crystallizer=crystallizer,
            crystallize_every=10,
        )

        orchestrator = SGEOrchestrator(
            agent=agent,
            value_layer=value_layer,
            drive_metabolism=DriveMetabolism(drives=drives),
            event_generator=EventGenerator(baby_id='demo', seed=42),
            identity_layer=IdentityLayer(crystallize_every_n_epochs=20),
            narrative_builder=NarrativeBuilder(build_every_n_epochs=50),
            hawking=hawking,
            crystallizer=crystallizer,
            db=db,
            student_id='stu_demo',
            checkpoint_every=10,
            student_name='Demo Student',
            app_state={'grade': 7, 'subject': 'math'},
            verbose=False,
        )

        orchestrator.run(n_epochs=50)

        # session_end 触发最后一次 checkpoint
        orchestrator.session_end()
        print(f"  ✓ session_end checkpoint 触发完成")

        history = db.get_checkpoint_history('stu_demo', limit=20)
        print(f"  ✓ 50 epoch + session_end 产生 {len(history)} 个 checkpoint")
        for h in history:
            print(f"    epoch={h['epoch']}, trigger={h['trigger']}")

    # 3. 跨连接持久化验证（关闭 → 重开 → load）
    print(f"\n[3] 跨连接持久化验证（关闭 → 重开 → load）")
    with TwinStateDB(db_path) as db:
        sge_state, app_state, epoch = db.load_full_state('stu_demo')
        print(f"  ✓ load 成功: epoch={epoch}, app_state={app_state}")
        print(f"    sge_state schema_version={sge_state['_schema_version']}")
        print(f"    sge_state keys: {list(sge_state.keys())}")

    # 4. Access log 审计（验证 orchestrator 触发的 checkpoint 都有 access_log）
    print(f"\n[4] Access log 审计")
    with TwinStateDB(db_path) as db:
        cursor = db.conn.execute(
            "SELECT accessor_id, operation, COUNT(*) AS cnt "
            "FROM access_log WHERE student_id='stu_demo' "
            "GROUP BY accessor_id, operation ORDER BY cnt DESC"
        )
        rows = cursor.fetchall()
        print(f"  ✓ 共 {sum(r['cnt'] for r in rows)} 条 access_log 记录")
        for r in rows:
            print(f"    accessor={r['accessor_id']}, op={r['operation']}, cnt={r['cnt']}")

    # 5. GDPR 软删除
    print(f"\n[5] GDPR 软删除")
    with TwinStateDB(db_path) as db:
        db.delete_student('stu_demo', hard=False, accessor_id='teacher_jane')
        print(f"  ✓ 软删除成功（status='deleted'，后续读写拒绝）")

        try:
            db.load_full_state('stu_demo')
            print(f"  ✗ 期望 StudentDeletedError，未抛")
        except StudentDeletedError as e:
            print(f"  ✓ load 抛 StudentDeletedError: {type(e).__name__}")

    # 6. Retention policy（模拟第二个学生）
    print(f"\n[6] Retention policy + purge（第二个学生）")
    with TwinStateDB(db_path) as db:
        db.create_student('stu_graduated', name='Graduated Student')
        # 模拟一年前毕业
        past_graduation = datetime.date.today() - datetime.timedelta(days=400)
        db.set_retention_policy(
            student_id='stu_graduated',
            graduation_date=past_graduation,
            deletion_date=None,
            status='pending_deletion',
        )
        # 软删除 → retention_policy.status='deleted' + deletion_date=NOW+90d
        db.delete_student('stu_graduated', hard=False, accessor_id='admin')
        # 手动模拟"过期"：直接调 purge，传入 now=未来时间（deletion_date 已过期）
        future_now = datetime.datetime.now() + datetime.timedelta(days=91)
        n_purged = db.purge_expired_students(now=future_now)
        print(f"  ✓ retention_policy 设置 + 软删除 + purge(now=future) 清理: {n_purged} 个学生")
        # 验证已物理删除
        try:
            db.load_full_state('stu_graduated')
            print(f"  ✗ 期望 StudentNotFoundError，未抛")
        except Exception as e:
            print(f"  ✓ purge 后 load 抛 {type(e).__name__}")

    # 7. 清理
    try:
        os.unlink(db_path)
    except OSError:
        pass
    print(f"\n[7] 清理临时 DB: {db_path}")

    print(f"\n{'=' * 70}")
    print(f"✅ Demo 完成")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Demo 失败: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)