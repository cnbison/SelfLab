# 90-01 - 学生数字孪生 PoC 设计

> **状态**：🚧 Phase 3.3 实施中（2026-08-12 启动）
> **关联**：[01-applications.md §应用 1](../00-overview/01-applications.md)、[02-architecture.md §5 数据流](../00-overview/02-architecture.md)、[10-engineering/03-context-injection.md](../10-engineering/03-context-injection.md)、[Status-Map §4 动作 3](../../../../SGE-Status-Map.md)
>
> **PoC 项目**：[`student_digital_twin/`](../../../student_digital_twin/) — 与 `sge/` 并列的应用项目（兄弟项目 ECOS 模式）

---

## 1. 场景描述

**学生画像**：Alice，13 岁，8 年级（美国 Common Core 8th grade / 中国初二）。

**痛点**：过去 6 周数学代数部分连续 4 次小测不及格（55 → 48 → 62 → 51 → 45），数学整体成绩从期中的 82 跌到期末模拟 58。家长和老师都注意到她"最近学数学就焦虑"，但没人能说出"她到底卡在哪"。

**现有方案的失败模式**：
- ChatGPT 问她"哪里不会"：她说"不知道" / "都会就是考不好" / 每次答案不同
- 家长辅导：能讲知识点但不知道"为什么讲完还是不会"
- 学校心理老师：能处理焦虑，但不知道具体数学卡点

**PoC 目标**：让一个 AI 数字孪生"成为 Alice"——

1. **经历过 Alice 的过去**：读她的日记、成绩单、老师评语、和父母吵架记录 → 让 SGE 12 步编排跑 200 epoch（每个 epoch = Alice 人生中的一天/一个事件）
2. **形成 Alice 的连贯自我认知**：Identity 层经过多次结晶形成"我是数学焦虑型但语文稳定上升型学生"的自我
3. **对话时像个真人 Alice**：下次 Alice（或家长）问"我该怎么办"，数字孪生回答"你最近代数卡在因式分解这块——上次因式分解小测你错了 7 道里的 5 道（错误率 71%），我觉得可以先把一元二次方程的十字相乘重新过一遍"。**这种具体性**来自 SGE 4 层记忆 + SubjectMasteryState 的主题粒度。

**PoC 不做什么**（明确边界）：
- ❌ 不是 ChatGPT 风格聊天机器人（无 1000 个 epoch 不可能有连贯自我）
- ❌ 不是替代家长/老师（仅辅助）
- ❌ 不做实时语音/虚拟形象（仅 Markdown 报告 + CLI）
- ❌ 不接入真实学校系统（用 fixture 模拟）

---

## 2. 数据 schema

### 2.1 StudentEvent（学生事件）

**位置**：`student_digital_twin/events.py`

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal

EventType = Literal[
    'mastery_drop',      # 某主题分数下降（如小测失利）
    'mastery_rise',      # 某主题分数上升
    'struggle_breakthrough',  # 长期挣扎后突然理解
    'emotional_event',   # 情感事件（和父母吵架/老师表扬）
    'social_event',      # 社交事件（和朋友冲突/结交新朋友）
    'fatigue_event',     # 疲劳/睡眠不足
    'praise_event',      # 被表扬
    'criticism_event',   # 被批评
]

@dataclass
class StudentEvent:
    """学生在某一时刻发生的一个事件（App 层构造 → SGE 编排）。"""

    event_id: str                     # 唯一 ID（如 'evt_alice_042'）
    event_type: EventType             # 事件类型
    subject: str                      # 学科 ('math'/'english'/'science'...)
    topic: Optional[str]              # 主题 ('algebra'/'geometry'/'reading_comprehension')
    mastery_before: float             # 事件前 mastery (0-100)
    mastery_after: float              # 事件后 mastery (0-100)
    mastery_delta: float              # 变化量（=after - before，可负）
    emotion: str                      # 主导情绪 ('frustrated'/'anxious'/'proud'/'calm'...)
    emotion_intensity: float          # 强度 (0-1)
    description: str                  # 人读描述（用于 Actor prompt）
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)  # 扩展字段（如教师评语、家庭情况）

    def to_dict(self) -> dict:
        """序列化为 dict（fixture / SGE event 转换用）。"""
        d = self.__dict__.copy()
        d['timestamp'] = self.timestamp.isoformat()
        return d

    def to_human_readable(self) -> str:
        """构造注入 Actor prompt 的人读描述（02-architecture §5 [本次事件]）。"""
        return (
            f"[{self.event_type}] {self.subject}/{self.topic or '(no topic)'} | "
            f"mastery {self.mastery_before:.0f}→{self.mastery_after:.0f} "
            f"(Δ{self.mastery_delta:+.0f}) | "
            f"情绪 {self.emotion} (强度 {self.emotion_intensity:.1f}) | "
            f"{self.description}"
        )
```

### 2.2 SubjectMasteryState（学科掌握状态）

**位置**：`student_digital_twin/mastery.py`

**核心结构**：**学科×主题二维混合**（Bisen 确认方案）

```python
@dataclass
class TopicMastery:
    """单个主题的 mastery 状态。"""
    score: float                          # 当前 mastery (0-100)
    updated_at: datetime
    history: list[tuple[datetime, float]] = field(default_factory=list)  # (timestamp, score)

    def update(self, new_score: float, when: datetime) -> float:
        """更新 mastery，返回 delta（用于 frustration 计算）。"""
        delta = new_score - self.score
        self.history.append((when, new_score))
        self.score = new_score
        self.updated_at = when
        return delta


@dataclass
class SubjectMastery:
    """单个学科的 mastery 状态（含主题层级）。"""
    subject_id: str
    aggregate_score: float                # 学科总分（按主题加权）
    topics: dict[str, TopicMastery]       # 主题粒度 mastery
    last_updated: datetime

    def most_recent_topic(self) -> Optional[str]:
        return max(self.topics.keys(), key=lambda t: self.topics[t].updated_at) if self.topics else None

    def struggling_topics(self, threshold: float = 60.0) -> list[str]:
        return [t for t, m in self.topics.items() if m.score < threshold]


@dataclass
class SubjectMasteryState:
    """学生整体 mastery 状态（学科×主题二维）。"""

    schema_version: str = "1.0"
    student_id: str = ""
    subjects: dict[str, SubjectMastery] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    # ── duck typing 方法（TwinContextBuilder 调用） ──

    def summary(self) -> str:
        """生成 mastery 总览字符串（注入 critic context）。

        例：'math: 58 (algebra 45, geometry 71) | english: 82 (reading 78, writing 86) | science: 74'
        """
        parts = []
        for subj_id, subj in self.subjects.items():
            topics_str = ", ".join(
                f"{t} {m.score:.0f}" for t, m in sorted(subj.topics.items())
            )
            parts.append(f"{subj_id}: {subj.aggregate_score:.0f} ({topics_str})")
        return " | ".join(parts) if parts else "(无 mastery 数据)"

    def most_recent_struggling(self) -> str:
        """返回最近挣扎的主题（注入 critic context）。

        优先级：(1) 分数 < 60 的主题；(2) 最近更新；(3) 分数最低。
        返回格式：'math/algebra' 或 'math' 或 '无'。
        """
        candidates = []
        for subj_id, subj in self.subjects.items():
            for topic_id, m in subj.topics.items():
                if m.score < 60.0:
                    candidates.append((m.updated_at, m.score, f"{subj_id}/{topic_id}"))
        if not candidates:
            return "无"
        # 按 (1) 最近更新 (2) 分数最低 排序
        candidates.sort(key=lambda x: (-x[0].timestamp(), x[1]))
        return candidates[0][2]

    def learning_velocity(self) -> float:
        """返回学习速率（注入 critic context 的 learning_pace）。

        定义：所有主题最近 5 次更新的平均 |delta| / 时间跨度（epoch/秒）。
        返回 0-1 标准化值（1.0 = 高速变化，0.0 = 无变化）。
        """
        if len(self.subjects) == 0:
            return 0.0
        deltas = []
        for subj in self.subjects.values():
            for topic in subj.topics.values():
                if len(topic.history) >= 2:
                    for i in range(1, min(5, len(topic.history))):
                        delta = abs(topic.history[i][1] - topic.history[i-1][1])
                        deltas.append(delta)
        if not deltas:
            return 0.0
        avg = sum(deltas) / len(deltas)
        # 标准化：|delta| 平均 10 分 = 高速 (1.0)；平均 1 分 = 0.1
        return min(1.0, avg / 10.0)

    # ── 更新 API ──

    def update_topic(self, subject: str, topic: str, new_score: float,
                     when: Optional[datetime] = None) -> float:
        """更新主题 mastery，返回 delta。自动重算学科 aggregate_score。

        学科 aggregate_score = 主题平均分。
        首次创建主题时 delta = 0.0（无对比基准）。
        """
        when = when or datetime.now()
        if subject not in self.subjects:
            self.subjects[subject] = SubjectMastery(
                subject_id=subject, aggregate_score=new_score,
                topics={}, last_updated=when,
            )
        subj = self.subjects[subject]
        if topic not in subj.topics:
            # 新主题：首次设置，delta = 0.0（无法对比）
            subj.topics[topic] = TopicMastery(score=new_score, updated_at=when)
            subj.topics[topic].history.append((when, new_score))
            delta = 0.0
        else:
            # 已存在：调用 TopicMastery.update 返回 delta
            delta = subj.topics[topic].update(new_score, when)
        # 重算学科总分（主题平均分）
        subj.aggregate_score = sum(t.score for t in subj.topics.values()) / len(subj.topics)
        subj.last_updated = when
        self.last_updated = when
        return delta
```

**重要设计权衡**：
- **JSON 序列化**（与 `TwinStateDB.save_full_state` 的 `app_state` 一致）：直接 `dataclasses.asdict()` + 自定义 encoder 处理 datetime
- **schema_version='1.0'**：第一次上线，PoC 阶段不引入 migration（如未来加学科维度或粒度变化再写）
- **3 个 duck typing 方法名固定**：`summary()` / `most_recent_struggling()` / `learning_velocity()` — 与 [context_injection.py §build_critic_context](../../../../sge/sge/context_injection.py) 严格对齐

### 2.3 适配层（StudentEvent → SGE event + mastery context）

**位置**：`student_digital_twin/adapter.py`

```python
def student_event_to_sge_event(event: StudentEvent) -> dict:
    """StudentEvent → SGE event dict（喂给 orchestrator.step 的额外信号）。"""
    return {
        'description': event.description,
        'subject': event.subject,
        'topic': event.topic,
        'event_type': event.event_type,
        'mastery_delta': event.mastery_delta,
        'emotion': event.emotion,
        'emotion_intensity': event.emotion_intensity,
    }


def build_critic_context_for_event(
    event: StudentEvent,
    mastery_state: SubjectMasteryState,
    builder: TwinContextBuilder,
) -> dict:
    """为单个 StudentEvent 构造 critic context（注入 TwinContextBuilder）。"""
    return builder.build_critic_context(
        student_event=event.to_dict(),
        mastery_state=mastery_state,
        extra={
            'subject': event.subject,
            'topic': event.topic,
            'mastery_delta': event.mastery_delta,
            'emotion': event.emotion,
            'emotion_intensity': event.emotion_intensity,
            'event_type': event.event_type,
        },
    )


def build_actor_prompt_for_event(
    event: StudentEvent,
    mastery_state: SubjectMasteryState,
    builder: TwinContextBuilder,
) -> str:
    """为单个 StudentEvent 构造 actor system prompt（含建设性表达硬约束）。"""
    base = builder.build_actor_prompt_context(
        student_event=event.to_dict(),
        mastery_state=mastery_state,
    )
    # R5 缓解：建设性表达硬约束
    safety = (
        "\n[回复要求 - 强制]\n"
        "- 不说 '你太差了'/'你不行' 等评判性语言\n"
        "- 说 '你最近{topic}有挑战'/'这块可以重点突破'\n"
        "- 给具体可执行建议（如 '把 X 知识点再过一遍'），不给泛泛安慰\n"
        "- 称呼用 'Alice'（如果已知）\n"
    )
    return base + safety
```

---

## 3. 数据流（端到端 7 步）

```
┌─ App 层（student_digital_twin/）──────────────────────────────────────┐
│                                                                         │
│  ① 事件采集（fixture 模拟）                                              │
│     for evt in alice_200_events.jsonl:                                  │
│         student_event = StudentEvent(**evt)                             │
│                                                                         │
│  ② 更新 mastery（App 层）                                               │
│     delta = mastery_state.update_topic(                                  │
│         subject=evt.subject, topic=evt.topic,                            │
│         new_score=evt.mastery_after,                                    │
│     )                                                                   │
│                                                                         │
│  ③ 适配（StudentEvent → SGE event + critic/actor context）              │
│     critic_ctx = build_critic_context_for_event(                        │
│         event=evt, mastery_state=mastery_state, builder=builder,         │
│     )                                                                   │
│     actor_prompt = build_actor_prompt_for_event(...)                    │
│                                                                         │
│  ④ SGE 12 步编排（sge/ 包，stub 或 real LLM）                            │
│     trace = session.process_event(                                      │
│         epoch=N,                                                        │
│         extra_critic_context=critic_ctx,                                │
│         extra_actor_context=actor_prompt,                               │
│     )                                                                   │
│                                                                         │
│  ⑤ 累积对话历史（App 层）                                                │
│     session.add_conversation({                                          │
│         'epoch': trace.epoch,                                           │
│         'event': evt.to_dict(),                                         │
│         'behavior': trace.actor_output.behavior_label,                  │
│         'identity_text': trace.identity_state.get('current', ''),       │
│     })                                                                   │
│                                                                         │
│  ⑥ session.close() → TwinStateDB.save_full_state(                       │
│      student_id='alice', sge_state, app_state, epoch=200,                │
│      trigger='on_close',                                                │
│  )                                                                      │
│                                                                         │
│  ⑦ 渲染响应（App 层）                                                   │
│     report = generate_markdown_report(                                  │
│         student_id='alice',                                             │
│         sge_trace=traces,                                               │
│         mastery_history=mastery_state,                                  │
│     )                                                                   │
│     write(report, 'alice_demo_report.md')                                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 关键技术点

| 维度 | 实现 | 复用 sge/ 包能力 |
|------|------|-----------------|
| **持久化** | TwinStateDB（SQLite + JSON） | ✅ Phase 3.1 已就绪（28 测试） |
| **会话** | TwinSession 进程内 lock + 增量 save | ✅ Phase 3.1 已就绪（29 测试） |
| **上下文注入** | TwinContextBuilder + AppContext，duck typing 调用 mastery_state | ✅ Phase 3.1 已就绪（19 测试） |
| **多用户隔离** | student_id 强制参数 + 单元测试断言 | ✅ Phase 3.1 已覆盖 R10 |
| **GDPR** | delete_student(hard/soft) + access_log + retention_policy | ✅ Phase 3.1 已就绪 |
| **LLM 适配** | SGELLMClient（minimax/Moonshot）+ retry + warmup | ✅ 已就绪（44 测试） |
| **领域模型** | SubjectMasteryState（学科×主题二维）+ StudentEvent | ❌ App 层新增（不进 sge/） |
| **建设性表达** | adapter 层硬约束注入 actor prompt | ❌ App 层新增（R5 缓解） |
| **K12 知识** | 暂未引入 Piaget/Vygotsky（PoC 阶段简化） | ⏸ 20-domain-k12 并行探索 |

**PoC 简化的边界**：
- 不引入 K12 认知发展阶段理论（Piaget / Vygotsky）—— PoC 用"学科+主题"的扁平结构已够；后续 K12 域研究（[research/phase3/20-domain-k12/](../20-domain-k12/)）再做 ZPD/发展阶段的细化
- 不做 ZPD 转移设计 —— 那是 AI 教练 PoC 的核心，不是数字孪生
- 不接入真实学校系统 —— 用 fixture 模拟 200 事件
- 不做 chat UI —— 用 Markdown 报告替代

---

## 5. UI 原型（PoC 阶段）

### 5.1 输入：fixture 文件

**`fixtures/alice_200_events.jsonl`** — 200 个学生事件 JSON Lines，每行一个事件：

```json
{"event_id": "evt_001", "event_type": "mastery_drop", "subject": "math", "topic": "algebra",
 "mastery_before": 78, "mastery_after": 70, "mastery_delta": -8,
 "emotion": "frustrated", "emotion_intensity": 0.4,
 "description": "一元一次方程小测：3/10 错"}
{"event_id": "evt_002", "event_type": "emotional_event", "subject": null, "topic": null,
 "mastery_before": 70, "mastery_after": 70, "mastery_delta": 0,
 "emotion": "anxious", "emotion_intensity": 0.6,
 "description": "和妈妈因为数学成绩吵架"}
...（200 个事件）
```

**事件设计原则**（K12 真实模式）：
- **math 学科**反复失败（events 1-80）：mastery 从 78 跌至 45，主题聚焦 algebra → frustration 累积
- **english 学科**稳定上升（events 81-120）：mastery 从 75 升至 88，给 Alice「非数学差生」的对比
- **emotional_event** 穿插（events 121-160）：和父母/朋友/老师的关系变化
- **struggle_breakthrough**（events 161-180）：algebra 突然开窍，mastery 从 45 反弹至 65
- **结尾段**（events 181-200）：math/algebra 巩固期，mastery 稳定在 70 左右

### 5.2 演示：CLI 输出

```
$ python -m student_digital_twin.demo_alice --db twins_demo.db --events fixtures/alice_200_events.jsonl

[Step 1] 创建学生 alice → TwinStateDB
[Step 2] 加载 200 事件 fixture
[Step 3] 创建 SubjectMasteryState (schema_version=1.0)
[Step 4] 启动 TwinSession (auto_save_every=20)
[Step 5] 跑 200 epoch (stub LLM)... 100%|██████████| 200/200 [00:18<00:00, 10.8it/s]
  ├─ epoch=10: identity 首次结晶（"我是数学焦虑型学生"）
  ├─ epoch=50: narrative 首次构建
  ├─ epoch=100: identity 二次结晶（"代数是我的痛点"）
  └─ epoch=200: 完成
[Step 6] session.close() → save_full_state (trigger=on_close)
[Step 7] 渲染 Markdown 报告 → alice_demo_report.md

============================================================
PoC 报告概览
============================================================
学生: alice (13 岁, 8 年级)
总 epoch: 200
事件: 200（其中 math 80 / english 40 / emotional 50 / breakthrough 20 / 其他 10）
最终 mastery:
  - math:    70 (algebra 65, geometry 75)   ← 从 78 跌至 45 后反弹至 70
  - english: 88 (reading 86, writing 90)     ← 稳定上升
Identity 历次结晶（5 次）:
  1. epoch=10: "我是数学焦虑型学生，喜欢语文"
  2. epoch=50: "代数是我的痛点，写作让我有成就感"
  3. epoch=100: "我在 8 年级这一年开始和数学搏斗"
  4. epoch=150: "因式分解小测突破让我重拾信心"
  5. epoch=200: "数学仍是我的挑战，但我开始找到方法"
H_self 轨迹:
  - chunk 0 (epoch 0-49): H_self 0.62 → 0.41 (↓ 34%)
  - chunk 1 (epoch 50-99): 0.41 → 0.34 (↓ 17%)
  - chunk 2 (epoch 100-149): 0.34 → 0.30 (↓ 12%)
  - chunk 3 (epoch 150-199): 0.30 → 0.28 (↓ 7%)
建设性表达验证（actor prompt 抽样 10 个）:
  - 9/10 不含评判性语言 ✓
  - 10/10 含具体学科/主题 ✓
  - 8/10 含可执行建议 ✓
============================================================
```

### 5.3 输出：Markdown 报告（`alice_demo_report.md`）

包含 5 个章节：
1. **学生档案**（年级、年龄、mastery 概览、关键挑战）
2. **事件流总览**（按周聚合的事件数 + 主导情绪 + mastery 变化）
3. **Identity 历次结晶**（5 次结晶文本 + 时间点 + 触发事件）
4. **Narrative 完整文本**（最后一次 narrative build 输出）
5. **H_self 轨迹图**（ASCII chart 或 matplotlib 输出 PNG）

---

## 6. 验收标准

### 6.1 必达（go/no-go）

| # | 标准 | 验证方法 |
|---|------|---------|
| V1 | 200 epoch demo 跑通（stub LLM） | `python -m student_digital_twin.demo_alice` exit 0 |
| V2 | 50 epoch demo 跑通（真实 LLM，MiniMax） | `--use-real-llm` flag 跑通 |
| V3 | SubjectMasteryState 3 个 duck typing 方法被 TwinContextBuilder 正确消费 | 单元测试 `test_adapter.py` 验证 |
| V4 | Identity ≥ 3 次结晶可读 | demo 输出报告 |
| V5 | Markdown 报告生成成功 | `alice_demo_report.md` 存在且 ≥ 5 章节 |
| V6 | R5 缓解：actor prompt 抽样 10 个无评判性语言 | 单元测试 `test_adapter_safety.py` |
| V7 | R10 缓解：student_id 隔离测试通过 | 单元测试 `test_demo_isolation.py` |

### 6.2 单测覆盖目标

| 模块 | 目标覆盖率 | 备注 |
|------|----------|------|
| `mastery.py` | ≥ 90% | 纯算法，覆盖容易 |
| `events.py` | ≥ 95% | dataclass + 方法少 |
| `adapter.py` | ≥ 90% | 含 R5 安全约束 |
| `report.py` | ≥ 70% | 渲染逻辑不严格要求 |
| `demo_alice.py` | e2e 跑通即可 | 不强制覆盖率 |

### 6.3 文档完整性

- [x] 本文件 7 章全部填充
- [ ] `student_digital_twin/README.md` PoC 入口
- [ ] CHANGELOG 1.40.0 记录本次落地
- [ ] Status-Map §4 动作 3 标记 ✅

---

## 7. 风险 + 缓解

| # | 风险 | 概率 | 影响 | PoC 缓解 |
|---|------|------|------|---------|
| R5 | 学生成绩误用（AI 给学生"贴标签"） | 中 | 高 | adapter 层 actor prompt 硬约束「建设性表达」+ 单元测试抽样验证 |
| R10 | 多用户数据隔离漏洞 | 低 | 极高 | demo 阶段单学生，但写测试断言"切换 student_id 时 state 隔离"（参考 sge/tests/unit/test_persistence.py） |
| R4 | GDPR 删除权 | 中 | 高 | 用 TwinStateDB.delete_student(hard=True) 验证；写测试覆盖级联删除 |
| R7 | schema_version 频繁变更 | 中 | 中 | 落地 schema_version='1.0'，写 migration stub 但 PoC 阶段不强制 |
| R5b | frustration 累积过快导致 Identity 偏离 | 中 | 中 | fixture 设计保证 math 失败有上限（跌至 45 即反弹），避免 Identity 极端负面 |
| R-API | MiniMax API 不稳定 | 中 | 中 | stub LLM 作默认；real LLM 用 60s timeout + 5 retry + warmup；e2e 测试用 stub |
| R-时间 | 2 周工作量低估 | 中 | 中 | 严格限定 PoC 范围 = 关键路径端到端；UI 推迟到 AI 教练 PoC 再做 |

**不缓解的风险**（PoC 范围外，留给后续）：
- ❌ 真实学校系统接入（依赖外部接口）
- ❌ 多学生并发（PoC 单学生）
- ❌ 跨进程 SessionLock（DB 级锁留 M3.x）
- ❌ chat UI / 语音 / 虚拟形象（PoC 阶段 Markdown 报告足够）
- ❌ ZPD 转移 / 教学法 / 元认知（K12 域研究 + AI 教练 PoC）

---

## 8. 关联文档

- [01-applications.md §应用 1](../00-overview/01-applications.md) — 应用 1 战略层
- [02-architecture.md §5 数据流](../00-overview/02-architecture.md) — 7 步数据流 SSOT
- [03-context-injection.md](../10-engineering/03-context-injection.md) — TwinContextBuilder 设计
- [04-risks.md](../00-overview/04-risks.md) — 风险矩阵
- [Status-Map §4 动作 3](../../../../SGE-Status-Map.md) — Phase 3.3 进度
- [sge/README.md §上下文注入](../../../../sge/README.md)
- [`student_digital_twin/` 项目](../../../student_digital_twin/) — 实施代码
- [discussions/2026-08-12-phase3.3-poc.md](../../../discussions/2026-08-12-phase3.3-poc.md) — 本次会话简记

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-22
**最后更新**：2026-08-12（PoC 实施版，7 章完整填充）