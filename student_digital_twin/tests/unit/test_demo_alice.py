"""test_demo_alice.py — e2e demo 跑通 + R10 多用户隔离

e2e: pytest -xvs tests/unit/test_demo_alice.py::TestDemoAliceE2E::test_demo_runs_200_epochs
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # tests/unit/ → tests/ → student_digital_twin/ → SelfLab/
DEMO_PATH = Path(__file__).parent.parent / 'demo_alice.py'
FIXTURE_PATH = Path(__file__).parent.parent.parent / 'fixtures' / 'alice_200_events.jsonl'


# ══════════════════════════════════════════════
# e2e demo 跑通
# ══════════════════════════════════════════════


class TestDemoAliceE2E:
    def test_demo_runs_200_epochs(self, tmp_path):
        """端到端：200 epoch stub LLM 跑通，报告生成。"""
        db_path = tmp_path / 'test_demo.db'
        report_path = tmp_path / 'test_report.md'

        import os
        # 用绝对路径设置 PYTHONPATH（subprocess 不会继承 cwd）
        # sge 包根目录是 SelfLab/sge/，里面含 sge/__init__.py
        env = {
            **os.environ,
            'PYTHONPATH': f'{PROJECT_ROOT}/sge:{PROJECT_ROOT}/student_digital_twin',
        }

        result = subprocess.run(
            [
                sys.executable, '-m', 'student_digital_twin.demo_alice',
                '--db', str(db_path),
                '--report', str(report_path),
                '--epochs', '200',
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert result.returncode == 0, (
            f"Demo failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        assert db_path.exists(), "DB file not created"
        assert report_path.exists(), "Report file not created"

        # 报告应包含 5 个章节
        report_text = report_path.read_text(encoding='utf-8')
        for section in ['## 1. 学生档案', '## 2. 事件流总览',
                        '## 3. Identity 历次结晶', '## 4. Narrative 完整文本',
                        '## 5. H_self 轨迹']:
            assert section in report_text, f"报告缺章节: {section}"

    def test_demo_runs_small_subset(self, tmp_path):
        """小规模：50 epoch 跑通。"""
        db_path = tmp_path / 'test_demo_small.db'
        report_path = tmp_path / 'test_report_small.md'

        import os
        env = {
            **os.environ,
            'PYTHONPATH': f'{PROJECT_ROOT}/sge:{PROJECT_ROOT}/student_digital_twin',
        }

        result = subprocess.run(
            [
                sys.executable, '-m', 'student_digital_twin.demo_alice',
                '--db', str(db_path),
                '--report', str(report_path),
                '--epochs', '50',
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        assert report_path.exists()


# ══════════════════════════════════════════════
# R10 多用户隔离
# ══════════════════════════════════════════════


class TestR10MultiUserIsolation:
    """R10 风险：学生 A 的事件不能意外写入学生 B 的 DB row。"""

    def test_create_two_students_no_isolation_violation(self, tmp_path):
        """创建 2 个学生，验证 state 完全隔离。"""
        from sge import TwinStateDB

        db_path = tmp_path / 'test_isolation.db'
        with TwinStateDB(str(db_path)) as db:
            db.create_student('alice', name='Alice')
            db.create_student('bob', name='Bob')

            # 写入 alice 的 state
            db.save_full_state(
                student_id='alice',
                sge_state={'value_state': {'compassion': 0.9}},
                app_state={'grade': 8},
                epoch=10,
                trigger='manual',
            )

            # 写入 bob 的 state
            db.save_full_state(
                student_id='bob',
                sge_state={'value_state': {'justice': 0.95}},
                app_state={'grade': 9},
                epoch=20,
                trigger='manual',
            )

        # 重新打开验证隔离
        with TwinStateDB(str(db_path)) as db:
            alice_sge, alice_app, alice_epoch = db.load_full_state('alice')
            bob_sge, bob_app, bob_epoch = db.load_full_state('bob')

            assert alice_sge['value_state']['compassion'] == 0.9
            assert 'justice' not in alice_sge['value_state']
            assert alice_app['grade'] == 8
            assert alice_epoch == 10

            assert bob_sge['value_state']['justice'] == 0.95
            assert 'compassion' not in bob_sge['value_state']
            assert bob_app['grade'] == 9
            assert bob_epoch == 20

    def test_delete_one_student_does_not_affect_other(self, tmp_path):
        """删除 alice 不应影响 bob 的 state。"""
        from sge import TwinStateDB, StudentNotFoundError

        db_path = tmp_path / 'test_delete_isolation.db'
        with TwinStateDB(str(db_path)) as db:
            db.create_student('alice')
            db.create_student('bob')
            db.save_full_state('alice', sge_state={'x': 1}, app_state={}, epoch=1, trigger='manual')
            db.save_full_state('bob', sge_state={'y': 2}, app_state={}, epoch=1, trigger='manual')

            # 软删除 alice
            db.delete_student('alice', hard=False, accessor_id='test')

        # 重新打开
        with TwinStateDB(str(db_path)) as db:
            # alice 已软删除，load 应拒绝或抛异常
            with pytest.raises(Exception):  # StudentNotFoundError 或类似
                db.load_full_state('alice')

            # bob 仍可访问
            bob_sge, _, _ = db.load_full_state('bob')
            assert bob_sge['y'] == 2


# ══════════════════════════════════════════════
# fixture 文件存在性
# ══════════════════════════════════════════════


class TestFixtureExists:
    def test_alice_200_events_fixture_exists(self):
        """Alice 200 事件 fixture 必须存在。"""
        assert FIXTURE_PATH.exists(), f"Fixture not found: {FIXTURE_PATH}"

    def test_alice_fixture_has_200_events(self):
        """Fixture 应包含 200 个事件。"""
        import json
        count = 0
        with open(FIXTURE_PATH) as f:
            for line in f:
                if line.strip():
                    count += 1
        assert count == 200, f"Expected 200 events, got {count}"