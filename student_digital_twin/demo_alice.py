"""Alice 200 epoch 端到端 PoC demo。

设计 SSOT：[research/phase3/90-applications/student-digital-twin.md §5](../research/phase3/90-applications/student-digital-twin.md)

用法：
    PYTHONPATH=sge:student_digital_twin python3 -m student_digital_twin.demo_alice \\
        --db twins_demo.db --events fixtures/alice_200_events.jsonl

    # 真实 LLM 模式（需配置 MiniMax API key）
    PYTHONPATH=sge:student_digital_twin python3 -m student_digital_twin.demo_alice \\
        --db twins_demo_real.db --events fixtures/alice_200_events.jsonl \\
        --use-real-llm --epochs 50

退出标准：见 research/phase3/90-applications/student-digital-twin.md §6
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .mastery import SubjectMasteryState
from .events import StudentEvent
from .adapter import (
    build_critic_context_for_event,
    build_actor_prompt_for_event,
)

# sge/ 包导入
from sge import (
    TwinStateDB, TwinSession, TwinContextBuilder, SGEOrchestrator,
    make_llm_client, EventGenerator, Agent, DriveMetabolism, ValueLayer,
    HawkingDecay, MemoryCrystallizer, IdentityLayer, NarrativeBuilder,
    compute_self_entropy,
    SGE_DEFAULT_DRIVES, SGE_DEFAULT_VALUES,
)


# ══════════════════════════════════════════════
# 事件加载
# ══════════════════════════════════════════════


def load_events(events_path: Path) -> list[StudentEvent]:
    """从 JSONL fixture 加载 StudentEvent 列表。"""
    events = []
    with open(events_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            events.append(StudentEvent.from_dict(d))
    return events


# ══════════════════════════════════════════════
# Alice PoC 报告生成
# ══════════════════════════════════════════════


def generate_alice_report(
    student_id: str,
    traces: list,
    student_events: list[StudentEvent],
    mastery_state: SubjectMasteryState,
    identity_history: list[tuple[int, str]],
    narrative_history: list[tuple[int, str]],
    h_self_trajectory: list[dict],
    total_seconds: float,
    used_real_llm: bool,
    output_path: Path,
) -> None:
    """生成 Markdown 报告（5 章节）。"""

    # ── 章节 1: 学生档案 ──
    summary = mastery_state.summary()
    struggling = mastery_state.most_recent_struggling()
    velocity = mastery_state.learning_velocity()

    # ── 章节 3: Identity 历次结晶 ──
    identity_section_lines = []
    for epoch, identity_text in identity_history:
        identity_section_lines.append(f"\n#### epoch {epoch}\n\n{identity_text}\n")
    identity_section = "\n".join(identity_section_lines) if identity_section_lines else "(未结晶)"

    # ── 章节 4: Narrative 完整文本 ──
    if narrative_history:
        last_narrative_epoch, last_narrative_text = narrative_history[-1]
        narrative_section = f"\n*（最后构建于 epoch {last_narrative_epoch}）*\n\n{last_narrative_text}\n"
    else:
        narrative_section = "(未构建 narrative)"

    # ── 章节 5: H_self 轨迹（按 epoch 50 一组聚合） ──
    h_self_lines = []
    if h_self_trajectory:
        # 按 epoch 范围分 chunk（每 50 epoch 一组）
        chunk_size = 50
        max_epoch = max(p['epoch'] for p in h_self_trajectory)
        chunks = []
        for chunk_start in range(0, max_epoch + 1, chunk_size):
            chunk_end = chunk_start + chunk_size - 1
            chunk_points = [p for p in h_self_trajectory
                           if chunk_start <= p['epoch'] <= chunk_end]
            if chunk_points:
                h_self_first = chunk_points[0]['H_self']
                h_self_last = chunk_points[-1]['H_self']
                h_value_last = chunk_points[-1].get('H_value', 0)
                h_identity_last = chunk_points[-1].get('H_identity', 0)
                h_narrative_last = chunk_points[-1].get('H_narrative', 0)
                chunks.append({
                    'epoch_start': chunk_start,
                    'epoch_end': chunk_points[-1]['epoch'],
                    'h_self_first': h_self_first,
                    'h_self_last': h_self_last,
                    'reduction_pct': (h_self_first - h_self_last) / h_self_first * 100
                        if h_self_first > 0 else 0,
                    'h_value': h_value_last,
                    'h_identity': h_identity_last,
                    'h_narrative': h_narrative_last,
                })
        for c in chunks:
            h_self_lines.append(
                f"- **chunk {c['epoch_start']}-{c['epoch_end']}**: "
                f"H_self {c['h_self_first']:.3f} → {c['h_self_last']:.3f} "
                f"(↓ {c['reduction_pct']:.1f}%) | "
                f"H_value={c['h_value']:.3f} H_identity={c['h_identity']:.3f} H_narrative={c['h_narrative']:.3f}"
            )
        h_self_section = "\n".join(h_self_lines)
    else:
        h_self_section = "(无 H_self 数据)"

    # ── 章节 2: 事件流总览（从 StudentEvent 统计，不混 SGE 内部 event） ──
    from collections import Counter
    student_event_types = Counter(e.event_type for e in student_events)
    event_subjects = Counter(e.subject for e in student_events if e.subject)

    # Actor 行为（来自 SGE 内部 actor_output）
    actor_behaviors = Counter(
        t.actor_output.behavior_label for t in traces
        if t.actor_output is not None and hasattr(t.actor_output, 'behavior_label')
    )

    event_overview = []
    for et, cnt in sorted(student_event_types.items(), key=lambda x: -x[1]):
        event_overview.append(f"  - `{et}`: {cnt}")
    event_overview_str = "\n".join(event_overview) if event_overview else "  (无)"

    subject_overview = []
    for subj, cnt in sorted(event_subjects.items(), key=lambda x: -x[1]):
        subject_overview.append(f"  - `{subj}`: {cnt}")
    subject_overview_str = "\n".join(subject_overview) if subject_overview else "  (无)"

    behavior_overview = []
    for label, cnt in sorted(actor_behaviors.items(), key=lambda x: -x[1]):
        behavior_overview.append(f"  - `{label}`: {cnt}")
    behavior_overview_str = "\n".join(behavior_overview) if behavior_overview else "  (无)"

    # ── 完整 Markdown ──
    md = f"""# Alice 数字孪生 PoC 报告

> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> **学生 ID**: `{student_id}`
> **总 epoch**: {len(traces)}
> **耗时**: {total_seconds:.1f}s（平均 {total_seconds/len(traces)*1000:.1f}ms/epoch）
> **LLM 模式**: {'真实 MiniMax' if used_real_llm else 'stub（确定性 fake_chat_json）'}

---

## 1. 学生档案

- **学生画像**: Alice，13 岁，8 年级
- **当前 mastery 总览**: {summary}
- **最近挣扎主题**: {struggling}
- **学习速率** (learning_pace): {velocity:.3f}（0=无变化, 1=高速）

---

## 2. 事件流总览

**StudentEvent 类型分布**（App 层原始事件）:
{event_overview_str}

**学科分布**:
{subject_overview_str}

**Actor 行为分布**（SGE 编排器输出行为标签）:
{behavior_overview_str}

---

## 3. Identity 历次结晶

本报告共记录 **{len(identity_history)}** 次 Identity 结晶。
{identity_section}

---

## 4. Narrative 完整文本

{narrative_section}

---

## 5. H_self 轨迹

H_self = w_v·H_value + w_i·H_identity + w_n·H_narrative（洞察 35）

**分 chunk 统计**（每 chunk 50 epoch）：
{h_self_section}

---

## 附录 A: 关键技术点

- **持久化**: TwinStateDB SQLite（多用户隔离 + GDPR + access_log 审计）
- **会话**: TwinSession（进程内 lock + 增量 save 每 20 epoch）
- **上下文注入**: TwinContextBuilder + AppContext + SubjectMasteryState duck typing
- **建设性表达**: actor system prompt 强制约束（"不使用评判性语言"）
- **数据 schema**: SubjectMasteryState v1.0（学科×主题二维）

## 附录 B: 风险缓解

- **R5 数据误用**: actor prompt 安全约束 + 单元测试验证（见 tests/unit/test_adapter_safety.py）
- **R10 多用户隔离**: student_id 强制参数 + 单元测试断言（见 tests/unit/test_demo_alice.py）
- **R4 GDPR**: delete_student(hard=True) 级联删除 9 业务表 + access_log 脱敏

## 附录 C: 关联文档

- 设计 SSOT: [research/phase3/90-applications/student-digital-twin.md](../../research/phase3/90-applications/student-digital-twin.md)
- Status-Map: [Status-Map §4 动作 3](../../SGE-Status-Map.md)
- sge 包: [sge/README.md](../../sge/README.md)
"""

    output_path.write_text(md, encoding='utf-8')
    print(f"\n✓ 报告已写入: {output_path}")


# ══════════════════════════════════════════════
# CLI 主函数
# ══════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(description='Alice 200 epoch PoC demo')
    parser.add_argument('--db', type=str, default='twins_demo.db',
                        help='TwinStateDB SQLite 文件路径（默认 twins_demo.db）')
    parser.add_argument('--events', type=str,
                        default=str(Path(__file__).parent / 'fixtures' / 'alice_200_events.jsonl'),
                        help='事件 fixture JSONL 文件路径')
    parser.add_argument('--student-id', type=str, default='alice',
                        help='学生 ID（默认 alice）')
    parser.add_argument('--epochs', type=int, default=200,
                        help='运行 epoch 数（默认 200，<= events 数）')
    parser.add_argument('--use-real-llm', action='store_true',
                        help='使用真实 MiniMax LLM（需配置 MINIMAX_API_KEY 环境变量）')
    parser.add_argument('--auto-save-every', type=int, default=20,
                        help='每 N epoch 增量保存（默认 20）')
    parser.add_argument('--report', type=str, default=None,
                        help='Markdown 报告输出路径（默认 alice_demo_report.md）')
    args = parser.parse_args()

    db_path = Path(args.db)
    events_path = Path(args.events)
    report_path = Path(args.report or 'alice_demo_report.md')

    print(f'=== Alice PoC Demo ===')
    print(f'DB: {db_path}')
    print(f'Events: {events_path}')
    print(f'LLM: {"真实 MiniMax" if args.use_real_llm else "stub"}')
    print()

    # ── Step 1: 加载事件 ──
    print(f'[Step 1] 加载事件 fixture ...')
    events = load_events(events_path)
    print(f'  ✓ 加载 {len(events)} 个事件')

    # 截取到 args.epochs
    if args.epochs < len(events):
        events = events[:args.epochs]
        print(f'  → 截取到 {len(events)} 个事件（--epochs={args.epochs}）')

    # ── Step 2: 创建/打开 TwinStateDB + 注册学生 ──
    print(f'[Step 2] 初始化 TwinStateDB ...')
    with TwinStateDB(str(db_path)) as db:
        try:
            db.create_student(
                student_id=args.student_id,
                name='Alice',
                app_state={'student_name': 'Alice', 'student_grade': 8},
            )
            print(f'  ✓ 创建学生 {args.student_id!r}')
        except Exception as e:
            if 'exists' in str(e).lower() or 'StudentExistsError' in type(e).__name__:
                print(f'  → 学生 {args.student_id!r} 已存在，复用')
            else:
                raise

        # ── Step 3: 创建 SubjectMasteryState（初始空，从 fixture 累积） ──
        print(f'[Step 3] 初始化 SubjectMasteryState (schema_version=1.0) ...')
        mastery_state = SubjectMasteryState(student_id=args.student_id)

        # ── Step 4: 创建 TwinContextBuilder ──
        print(f'[Step 4] 创建 TwinContextBuilder ...')
        builder = TwinContextBuilder(app_state={
            'student_name': 'Alice',
            'student_grade': 8,
        })

        # ── Step 5: 启动 TwinSession ──
        print(f'[Step 5] 启动 TwinSession (auto_save_every={args.auto_save_every}) ...')
        use_real_llm = args.use_real_llm
        llm = None
        if use_real_llm:
            llm = make_llm_client(provider='minimax')
            llm.warmup(n_calls=2)
            print('  ✓ 真实 LLM 已 warmup')
        with TwinSession(
            student_id=args.student_id,
            twin_db=db,
            use_real_llm=use_real_llm,
            llm=llm,
            auto_save_every=args.auto_save_every,
        ) as session:
            print(f'  ✓ Session 启动, current_epoch={session.current_epoch}')

            # ── Step 6: 跑 N epoch ──
            print(f'[Step 6] 跑 {len(events)} epoch ...')
            traces = []
            identity_history = []
            narrative_history = []
            h_self_trajectory = []
            t_start = time.time()

            for i, evt in enumerate(events):
                # 1. 更新 mastery_state
                if evt.subject and evt.topic:
                    mastery_state.update_topic(
                        subject=evt.subject, topic=evt.topic,
                        new_score=evt.mastery_after, when=evt.timestamp,
                    )

                # 2. 构造 critic context + actor prompt
                critic_ctx = build_critic_context_for_event(evt, mastery_state, builder)
                actor_prompt = build_actor_prompt_for_event(evt, mastery_state, builder)

                # 3. SGE 12 步编排
                trace = session.process_event(
                    extra_critic_context=critic_ctx,
                    extra_actor_context=actor_prompt,
                )
                traces.append(trace)

                # 4. 累积 Identity / Narrative
                if trace.identity:
                    identity_history.append((trace.epoch, trace.identity))
                if trace.narrative:
                    narrative_history.append((trace.epoch, trace.narrative))

                # 5. 计算 H_self（每 10 epoch 一次节省时间）
                if trace.self_entropy and i % 10 == 0:
                    h_self_trajectory.append({
                        'epoch': trace.epoch,
                        **trace.self_entropy,
                    })

                # 进度条
                if (i + 1) % 20 == 0 or i == len(events) - 1:
                    mastery_summary = mastery_state.summary()
                    print(f'  [{i+1:3d}/{len(events)}] mastery: {mastery_summary[:80]}...')

            t_end = time.time()
            total_seconds = t_end - t_start
            print(f'  ✓ 完成 {len(events)} epoch，耗时 {total_seconds:.1f}s')

        # session.close() 自动调用（with 退出）
        print(f'[Step 7] TwinSession.close() 完成（on_close checkpoint）')

        # ── Step 8: 渲染 Markdown 报告 ──
        print(f'[Step 8] 生成 Markdown 报告 ...')
        generate_alice_report(
            student_id=args.student_id,
            traces=traces,
            student_events=events,
            mastery_state=mastery_state,
            identity_history=identity_history,
            narrative_history=narrative_history,
            h_self_trajectory=h_self_trajectory,
            total_seconds=total_seconds,
            used_real_llm=use_real_llm,
            output_path=report_path,
        )

    print()
    print('========================================')
    print('PoC 完成 ✓')
    print(f'Report: {report_path}')
    print('========================================')


if __name__ == '__main__':
    main()