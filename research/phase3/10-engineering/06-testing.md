# 10-06 - 单元测试覆盖策略

> **目的**：建立 Phase 3 后的单元测试体系，覆盖率 ≥ 80%
> **当前现状**：M2.x 阶段只有 2 个测试文件（test_hawking_decay_fix.py, test_e1_event_generator.py）

---

## 1. 为什么需要单元测试覆盖

**当前 M2.x 测试状况**：
```
sge/sge/*.py:
  baseline.py        0 个 unit test
  event.py           5 个 (test_e1_event_generator.py)
  llm_client.py      0 个
  critic.py          0 个
  actor.py           0 个
  identity.py        0 个
  narrative.py       0 个
  orchestrator.py    0 个
```

**风险**：
- M2.3 修了 Hawking unit bug → 如果有 unit test，能更早发现
- Phase 3.1 改 persistence → 没有 test 容易 break 现有功能
- 重构时不知道有没有破坏什么

---

## 2. 目标

| 模块 | 目标覆盖率 | 关键测试 |
|------|-----------|---------|
| baseline.py | ≥ 90% | Hawking decay（Cauchy）、Crystallizer 合并、Value EMA 边界 |
| event.py | ≥ 85% | distribution_by_epoch 切换、value_conflict_prob |
| llm_client.py | ≥ 75% | retry 逻辑、warmup、timeout 行为 |
| critic.py | ≥ 80% | JSON 解析三层容错、temperature 行为 |
| actor.py | ≥ 80% | BEHAVIOR_LABELS 验证 |
| identity.py | ≥ 85% | crystallize_every 边界、validate 拒绝路径 |
| narrative.py | ≥ 80% | build_every、consistency check |
| orchestrator.py | ≥ 70% | 12 步顺序、step() 输出格式 |
| persistence.py (NEW) | ≥ 90% | save/load round-trip、migration、delete |
| session.py (NEW) | ≥ 85% | lifecycle、state restoration |
| context_injection.py (NEW) | ≥ 80% | context building、prompt format |

**总目标**：核心模块 ≥ 80%

---

## 3. 测试目录结构

```
sge/tests/
├── __init__.py
├── conftest.py                    # 共享 fixture（mock LLM, temp DB）
│
├── unit/
│   ├── test_baseline.py
│   │   ├── test_hawking_decay()
│   │   ├── test_hawking_threshold()
│   │   ├── test_crystallizer_insert()
│   │   ├── test_crystallizer_merge()
│   │   ├── test_value_ema()
│   │   ├── test_value_clip()
│   │   └── test_drive_metabolism()
│   │
│   ├── test_event.py
│   │   ├── test_event_distribution_by_epoch()
│   │   ├── test_value_conflict_generation()
│   │   └── test_routine_event_variation()
│   │
│   ├── test_llm_client.py
│   │   ├── test_warmup()
│   │   ├── test_retry_logic()
│   │   ├── test_timeout_behavior()
│   │   └── test_stats_tracking()
│   │
│   ├── test_critic.py
│   │   ├── test_basic_sense()
│   │   ├── test_json_parse_fallback()
│   │   └── test_context_construction()
│   │
│   ├── test_actor.py
│   │   ├── test_behavior_label_selection()
│   │   └── test_actor_output_format()
│   │
│   ├── test_identity.py
│   │   ├── test_crystallize_every_boundary()
│   │   ├── test_validate_pass_reject()
│   │   └── test_identity_history()
│   │
│   ├── test_narrative.py
│   │   ├── test_build_every()
│   │   ├── test_consistency_check()
│   │   └── test_narrative_history()
│   │
│   ├── test_orchestrator.py
│   │   ├── test_12_step_order()
│   │   ├── test_step_returns_orchestrator_step()
│   │   └── test_checkpoint_hook()
│   │
│   ├── test_persistence.py        # NEW
│   │   ├── test_save_load_roundtrip()
│   │   ├── test_delete_student_gdpr()
│   │   ├── test_migration()
│   │   └── test_concurrent_access()
│   │
│   ├── test_session.py            # NEW
│   │   ├── test_session_lifecycle()
│   │   ├── test_state_restoration()
│   │   └── test_persistence_integration()
│   │
│   └── test_context_injection.py  # NEW
│       ├── test_critic_context()
│       └── test_actor_prompt()
│
├── integration/
│   ├── test_12step_loop.py        # 完整 12 步无 LLM（stub）
│   ├── test_chunk_continuity.py   # 跨 chunk state 连续性
│   └── test_app_sge_integration.py # App + SGE + Persistence 端到端
│
└── e2e/
    └── test_real_llm_smoke.py     # 真实 LLM smoke test（API key 存在时跑）
```

---

## 4. 关键测试设计

### 4.1 Hawking decay（M2.3 bug 防回归）

```python
def test_hawking_decay_factor_per_epoch():
    """验证每 epoch decay factor ≈ 0.99（不是 0.9999972）"""
    h = HawkingDecay(gamma=0.01, clock=0.0)
    h.insert(content={'epoch': 0}, weight=1.0, now=0)
    h.tick(now=0)
    h.tick(now=1)  # delta = 1 hour
    weight = h.memory[0]['weight']
    assert abs(weight - 0.99005) < 1e-6  # exp(-0.01)

def test_hawking_1000h_decay():
    """1000 epoch 后 size=921, min_weight ≈ 1.0e-4"""
    h = HawkingDecay(gamma=0.01, clock=0.0)
    for i in range(1000):
        h.insert(content={'epoch': i}, weight=1.0, now=i)
        h.tick(now=i)
    assert len(h.memory) == 921
    # min_weight 接近 1e-4（删除阈值）
    assert abs(min(m['weight'] for m in h.memory) - 1.00034e-4) < 1e-6
```

### 4.2 Persistence round-trip

```python
def test_persistence_roundtrip(tmp_path):
    """保存 → 加载 → 完全相同"""
    db_path = tmp_path / "test.db"
    db1 = TwinStateDB(str(db_path))
    
    # 构造测试 state
    test_state = {
        'hawking_memory': [{'weight': 0.5, 'content': {'epoch': 0}}],
        'crystallizer_clusters': [],
        'value_state': {'safety': 0.1, 'creativity': -0.2, ...},
        'drive_state': {'exploration': 0.5, ...},
        'frustration': {'connection': 4.5, ...},
        'identity_history': [{'epoch': 19, 'identity': '我是探索者'}],
        'narrative_history': [],
    }
    
    # 保存
    db1.save_full_state('stu_001', test_state, {}, epoch=100, trigger='test')
    db1.close()
    
    # 重新打开
    db2 = TwinStateDB(str(db_path))
    sge_state, app_state, epoch = db2.load_full_state('stu_001')
    
    # 完全相同
    assert sge_state == test_state
    assert epoch == 100
```

### 4.3 Session lifecycle

```python
def test_session_lifecycle(tmp_path):
    """完整 lifecycle: load → run 5 events → close → reload"""
    db = TwinStateDB(str(tmp_path / "test.db"))
    
    # 新学生
    session1 = TwinSession('stu_001', db)
    for i in range(5):
        session1.process_event(
            StudentEvent(event_type='mastery_jump', subject='math'),
            SubjectMasteryState(),
        )
    session1.close()
    
    # 重新打开（模拟下次启动）
    session2 = TwinSession('stu_001', db)
    assert session2.current_epoch == 5  # 从上次继续
```

### 4.4 Identity validate 防回归

```python
def test_identity_validate_strict_mode():
    """严格 validate 应该拒绝 '模板化' identity"""
    identity_layer = IdentityLayer()
    
    # 模板化 identity（应拒绝）
    bad_identity = "我是一个学生"
    assert not identity_layer.validate(bad_identity, ...)
    
    # 详细 identity（应通过）
    good_identity = "我是一个在数学上有挑战但喜欢探索新知识的学生"
    assert identity_layer.validate(good_identity, ...)
```

---

## 5. Mock LLM 工具

```python
# sge/tests/conftest.py
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_llm_client():
    """返回确定性响应的 mock LLM"""
    client = MagicMock()
    
    def fake_chat(messages, temperature=0.5, max_tokens=1024, **kwargs):
        # 根据 prompt 内容返回 deterministic JSON
        if 'emotion' in str(messages):
            return '{"user_emotion": 0.5, "topic_intimacy": 0.3}'
        elif 'behavior' in str(messages):
            return '{"inner_monologue": "test", "behavior_label": "玩闹撒娇"}'
        return '{}'
    
    client.chat.side_effect = fake_chat
    client.stats.return_value = {'call_count': 1, 'retry': {}}
    return client

@pytest.fixture
def temp_db(tmp_path):
    """临时 SQLite DB"""
    db = TwinStateDB(str(tmp_path / "test.db"))
    yield db
    db.close()
```

---

## 6. CI 集成

```yaml
# .github/workflows/test.yml（未来）
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -e sge/
      - run: pytest sge/tests/ --cov=sge --cov-report=term --cov-fail-under=80
```

---

## 7. 实施清单

| 子任务 | 工作量 |
|--------|--------|
| `sge/tests/conftest.py`（fixture）| 0.5 天 |
| 核心模块 unit test（baseline/event/identity/narrative）| 2 天 |
| Phase 3 新模块 unit test（persistence/session/context_injection）| 1.5 天 |
| 集成测试（12 步 / chunk 连续性 / app-sge 集成）| 1 天 |
| 覆盖率工具 + CI 配置 | 0.5 天 |
| **总计** | **5.5 天** |

---

## 8. 关联文档

- [README.md §P1 任务](../README.md)
- [04-risks.md §R8 测试覆盖](../../00-overview/04-risks.md)
- [discussions/2026-06-22-...-aibeing-reflection.md §2.6](../../../discussions/2026-06-22-sge-phase3-aibeing-reflection.md) — AiBeing 测试借鉴

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-22
