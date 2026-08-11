# SGE Python Package

Self-Generating Engine — 通过"经历 → 解释 → 人格"形成 AI 持续自我认同。

## 状态

**Phase 3 Alpha** — 从 M2.x 实验脚本演化而来。包化目标：让 SGE 核心组件可被其他项目 import、可 pip install、可单元测试。

## 历史

| 阶段 | 里程碑 | 数据 |
|------|--------|------|
| M2.1 A/B/C/D | 完整架构实现 | stub + real LLM 混合验证 |
| M2.1 D6 | 真实 LLM 单 baby 验证 | 5/5 PASS |
| M2.2 E1-E6 | 三胞胎 1000 epoch × 真实 LLM | 12/12 chunks, personality_divergence 0.9884 |
| M2.3 | 个人真实测试 | challenged 一致性 6.00, L4 identity 9.0/10 |
| M2.3 fix | Hawking unit mismatch bug | 4/4 unit tests PASS |
| **Phase 3** | **sge/ 包化** | ← 当前 |

## 公开 API

```python
from sge import (
    # 核心机制
    Agent, DriveMetabolism, ValueLayer, MemoryCrystallizer, HawkingDecay,
    # 事件生成
    EventGenerator, LifeEvent,
    # 经验编码（洞察 34）
    Experience, encode_experience,
    # 自我熵度量（洞察 35）
    compute_self_entropy, entropy_reduction_rate,
    # LLM 适配层
    SGELLMClient, make_llm_client,
    # Critic / Actor
    critic_sense, actor_express, ActorOutput, BEHAVIOR_LABELS,
    # Identity / Narrative
    IdentityLayer, NarrativeBuilder,
    # Orchestrator
    SGEOrchestrator, OrchestratorStep,
    # Persistence（Phase 3.1 · 动作 1）
    TwinStateDB, SUPPORTED_SCHEMA_VERSIONS,
    PersistenceError, StudentNotFoundError, StudentExistsError,
    StudentDeletedError, SchemaVersionError, MigrationError,
    # Session（Phase 3.1 · 动作 2）
    TwinSession,
    SessionError, SessionLockedError, SessionNotFoundError,
)
```

## 安装

```bash
# Editable install（推荐 for development）
pip install -e sge/

# 运行测试
cd sge
pytest tests/
```

## 快速使用

```python
from sge import (
    Agent, DriveMetabolism, ValueLayer, HawkingDecay, MemoryCrystallizer,
    EventGenerator, SGELLMClient, SGEOrchestrator,
    IdentityLayer, NarrativeBuilder,
)

# 初始化核心组件
drives = ['exploration', 'safety', 'creativity', 'connection', 'autonomy']
agent = Agent(seed=42, drives=drives)
value_layer = ValueLayer()
hawking = HawkingDecay(gamma=0.01)
crystallizer = MemoryCrystallizer(n_dims=11)

# LLM
llm = make_llm_client(provider='minimax')
llm.warmup(n_calls=2)

# 12 步编排器
orchestrator = SGEOrchestrator(
    agent=agent, value_layer=value_layer,
    drive_metabolism=DriveMetabolism(drives=drives),
    event_generator=EventGenerator(baby_id='demo', seed=42),
    identity_layer=IdentityLayer(),
    narrative_builder=NarrativeBuilder(),
    hawking=hawking, crystallizer=crystallizer,
    use_real_llm=True, llm=llm,
)

# 跑 N epoch
traces = orchestrator.run(n_epochs=1000)
```

## 持久化（Phase 3.1 · 动作 1）

`TwinStateDB` 是 SGE 的 SQLite + JSON 持久化层。它把 `SGEOrchestrator.snapshot_all()` 输出的
完整 state（含 7 个子模块 + EventGenerator history）写入数据库，支持：

- **多用户隔离**（每 student 独立 schema + app state + checkpoints）
- **GDPR 合规**（软删除 + 硬删除脱敏 + retention_policy）
- **跨连接持久化**（关闭 → 重开 → load 恢复 state）
- **自动 checkpoint**（集成 SGEOrchestrator 后每 N epoch 自动 save）
- **schema 迁移**（v1.0 → v1.1 真实执行 DDL）

### 基础用法

```python
from sge import TwinStateDB

# 1. 创建 DB + 注册学生
with TwinStateDB('twins.db') as db:
    db.create_student('stu_001', name='Alice', app_state={'grade': 7})

# 2. 后续连接 load + 写入
with TwinStateDB('twins.db') as db:
    sge_state = {'value_state': {...}, 'identity': [...]}
    app_state = {'grade': 7, 'subject': 'math'}
    db.save_full_state(
        student_id='stu_001',
        sge_state=sge_state,
        app_state=app_state,
        epoch=100,
        trigger='manual',
    )

# 3. 再连接 load（跨进程恢复）
with TwinStateDB('twins.db') as db:
    sge_state, app_state, epoch = db.load_full_state('stu_001')
    history = db.get_checkpoint_history('stu_001', limit=10)
```

### 与 SGEOrchestrator 集成（自动 checkpoint）

```python
from sge import TwinStateDB, SGEOrchestrator, ...

with TwinStateDB('twins.db') as db:
    db.create_student('stu_001')

    orchestrator = SGEOrchestrator(
        agent=agent, value_layer=vl, ...,
        db=db,                          # ← 持久化集成
        student_id='stu_001',           # ← 必填
        checkpoint_every=100,           # ← 每 100 epoch 自动 save
        app_state={'grade': 7},         # ← 初始 app_state（可外部修改）
    )

    orchestrator.run(n_epochs=500)
    # → 自动产生 5 次 auto_100/200/300/400/500 checkpoint
    # → Phase Transition / Identity Crystallize / Narrative Build 也自动触发额外 checkpoint
    # → 每次 save 都伴随 access_log 审计记录

    orchestrator.session_end()  # ← 手动触发 session_end checkpoint（应用退出场景）
```

### GDPR 操作

```python
# 软删除（status='deleted'，后续读写拒绝，但审计保留）
db.delete_student('stu_001', hard=False, accessor_id='teacher_jane')

# 硬删除（9 业务表事务原子删，access_log 脱敏 student_id → 'deleted:<sha256>'）
db.delete_student('stu_001', hard=True, accessor_id='admin')

# 设置保留策略（90 天后自动 purge）
import datetime
db.set_retention_policy(
    student_id='stu_002',
    graduation_date=datetime.date(2026, 6, 15),
    deletion_date=datetime.date(2026, 9, 15),
    status='pending_deletion',
)
n_purged = db.purge_expired_students()  # 清理过期学生
```

### Schema 迁移

```python
# 当 DB 是 v1.0 而客户端是 v1.1 时：
# 第一阶段：用 v1.0 打开 → 迁移 → 关闭
with TwinStateDB('twins.db', schema_version='1.0') as db:
    db.migrate_schema('1.1')  # 执行 v1.0 → v1.1 DDL（students.email 字段 + 索引）

# 第二阶段：以 v1.1 打开正常使用
with TwinStateDB('twins.db', schema_version='1.1') as db:
    ...
```

### 应用层集成模式

- **多 user**：每个 user 一个 `student_id`（UUID / 业务 ID），完全隔离（R10 风险已测试覆盖）
- **多 session**：用 `session_end()` 显式标记会话边界，区分长程/短程
- **A/B 测试**：同一 user 多个 `student_id` 跑不同 drives 配置，比较 personality 分化
- **生产部署**：建议用文件 DB + WAL + 定期备份；`:memory:` 仅用于单进程实验

### 完整 Demo

参见 [`examples/persistence_demo.py`](./examples/persistence_demo.py)（端到端 demo：自动
checkpoint + GDPR delete + retention policy + session_end）。

## 会话管理（Phase 3.1 · 动作 2）

`TwinSession` 是 `TwinStateDB` 之上的会话层。`TwinStateDB` 回答"state 存哪里"，
`TwinSession` 回答"一次交互从哪开始、到哪结束"——它把「从 DB 加载 state → 重建
SGEOrchestrator → 逐 event 推进 → 保存」这条链路收敛成 3 个调用。

与直接用 `SGEOrchestrator(db=..., student_id=...)` 的区别：

| | SGEOrchestrator + db | TwinSession |
|---|---|---|
| 组件构造 | 调用方手工组装 8 个组件 | 从 DB state 自动重建 |
| 跨进程续跑 | 需手工 `load_full_state` + `restore_all` | 构造即恢复（`current_epoch` 自动续上） |
| 防并发 | 无 | 进程内 SessionLock（同 student 重复打开报错） |
| 适用 | 批量跑 N epoch 的实验 | 应用层交互式会话 |

### 基础用法

```python
from sge import TwinStateDB, TwinSession

with TwinStateDB('twins.db') as db:
    with TwinSession('stu_001', twin_db=db, auto_save_every=10) as session:
        for student_event in incoming_events:
            trace = session.process_event()      # 跑 1 个 epoch，epoch 自动递增
            session.add_conversation({           # App 层历史（存 app_state）
                'epoch': trace.epoch,
                'behavior': trace.actor_output.behavior_label,
            })
    # with 退出 → 自动 close(save=True) → on_close checkpoint
```

再次打开时 state 自动续上：

```python
with TwinStateDB('twins.db') as db:
    session = TwinSession('stu_001', twin_db=db)
    print(session.current_epoch)   # ← 上次 close 时的 epoch
    print(session.app_state)       # ← 上次的 conversations / grade 等
    session.close()
```

### 生命周期

```
TwinSession(student_id, db)
  ├─ load_full_state()            从 DB 取 sge_state / app_state / epoch
  ├─ _build_orchestrator_from_state()  逐组件 restore（Agent / ValueLayer / …）
  └─ 注册 SessionLock

process_event(epoch=None)          epoch 默认取 self.current_epoch
  ├─ orchestrator.step()
  ├─ current_epoch += 1
  └─ 每 auto_save_every 个 epoch → save_full_state(trigger='auto_N')

close(save=True)
  ├─ snapshot_all() → save_full_state(trigger='on_close')
  ├─ log_access(operation='on_close')
  └─ 释放 SessionLock
```

### 并发约束

- **同一 student 不能并发**：`_session_registry` 是进程内 dict，重复打开抛 `SessionLockedError`。
  `close()` 后可重新打开。
- **不同 student 可以并发**：DB 层已隔离（R10），互不影响。
- **跨进程未加锁**：当前只有进程内锁；多进程写同一 student 依赖 SQLite WAL 串行化，
  不构成严格互斥。DB 级 `session_locks` 表留给后续迭代。

### 参数说明

| 参数 | 默认 | 说明 |
|------|------|------|
| `student_id` | 必填 | 必须已 `create_student`，否则抛 `StudentNotFoundError` |
| `twin_db` | 必填 | `TwinStateDB` 实例（生命周期由调用方管理） |
| `use_real_llm` / `llm` | `False` / `None` | 透传给重建出的 orchestrator |
| `auto_save_every` | `10` | 每 N epoch 全量保存；`0` = 只在 `close()` 时保存 |

> **注意**：`close(save=False)` 会丢弃本次 session 的所有推进（用于只读/探查场景）。

## 架构

```
sge/
├── __init__.py            # 公开 API
├── RUNTIME_AUDIT.md       # Self Evolution Runtime 定位审计（洞察 33）
├── baseline.py            # Agent / DriveMetabolism / ValueLayer / HawkingDecay / MemoryCrystallizer
├── event.py               # EventGenerator + LifeEvent
├── experience.py          # Experience + encode_experience（Step 2.5，洞察 34）
├── metrics.py             # compute_self_entropy / H_self（Step 16，洞察 35）
├── llm_client.py          # SGELLMClient (含 retry/warmup/timeout)
├── critic.py              # Critic LLM 适配
├── actor.py               # Actor LLM 适配
├── identity.py            # IdentityLayer
├── narrative.py           # NarrativeBuilder
├── orchestrator.py        # 12+3 步编排器（含 Step 2.5 Experience + Step 16 H_self）
└── tests/                 # 单元测试
```

> **Runtime 定位**：SGE 是 **Self Evolution Runtime**（自我演化运行时），而非 Memory Framework——
> 编排器提供受控时钟、单步执行、组件可插拔、逐步 trace。Step 2.5 把裸 Event 编码为含
> **meaning** 的 Experience（"这件事对我意味着什么"），Step 16 计算 **H_self**（自我认知熵）
> 作为自我形成的统一目标函数。详见 [RUNTIME_AUDIT.md](./RUNTIME_AUDIT.md) 与
> [SGE-Key-Insights 洞察 33-35](../SGE-Key-Insights.md)。

## Phase 3 路线图

> **权威 SSOT**：[research/phase3/00-overview/03-roadmap.md](../research/phase3/00-overview/03-roadmap.md)。本节为顶层摘要。

- **Phase 3.1**（P0 应用基础）— persistence.py + session.py + context_injection.py（W1-W3）
- **Phase 3.2**（P1 性能 + 测试）— llm_cache + 单元测试覆盖 ≥80% + prompt 版本管理（W4-W6）
- **Phase 3.3**（P2 PoC 验证）— student-digital-twin + teaching-ai-coach 两个 PoC（W7-W12）
- **M4+ 延后**（不在 Phase 3 时间线内）— Emotion / Meta-Cognition / Multi-AI Interaction（参见 [ROADMAP §Phase 3](../ROADMAP.md) 历史定义）

## 关联文档

- [SelfLab README](../../README.md)
- [SGE-Memory-Layer-Design.md](../../research/sge-core/SGE-Memory-Layer-Design.md)
- [DESIGN.md](../../DESIGN.md)
- [M22_TRIPLETS_REPORT.md](../../experiments/M22_TRIPLETS_REPORT.md) — M2.2 验证
- [M23_PERSONAL_REALITY_REPORT.md](../../experiments/M23_PERSONAL_REALITY_REPORT.md) — M2.3 验证
