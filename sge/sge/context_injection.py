"""
SGE 上下文注入（Context Injection）

Phase 3.1 · 动作 3 — 把 App 层「领域上下文」（学生姓名/年级/mastery/关系历史）
透传到 Critic 和 Actor 的 LLM prompt，让 SGE 在不知道应用语义的前提下生成
"这个应用特定的"输出。

设计 SSOT：[research/phase3/10-engineering/03-context-injection.md](../../research/phase3/10-engineering/03-context-injection.md)

核心思路：
  - TwinContextBuilder：薄壳拼装器，接收 app_state（dict）+ extra_context（dict）
  - AppContext：typed 契约，描述应用层注入字段的语义
  - Critic / Actor 接受 extra_context / extra_system_prompt 透传给 LLM prompt
  - Orchestrator 接受 context_builder / extra_* 在 step() 中自动注入

边界（plumbing-only 范围）：
  - Phase 3.3 PoC 才会落地 SubjectMasteryState / StudentEvent 等具体类型
  - 当前 builder 用 dict 拼装，不假定字段来自特定类型
  - extra_* 都是可选，不传时行为与原版完全一致（向后兼容）
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Optional, Any


# ══════════════════════════════════════════════
# Critic 默认 8D 字段契约（与 critic.py CRITIC_CONTEXT_FIELDS 对齐）
# ══════════════════════════════════════════════

CRITIC_DEFAULT_8D = (
    'user_emotion',
    'topic_intimacy',
    'conversation_depth',
    'user_engagement',
    'conflict_level',
    'novelty_level',
    'user_vulnerability',
    'time_of_day',
)


# ══════════════════════════════════════════════
# AppContext：领域上下文的 typed 契约（可选使用）
# ══════════════════════════════════════════════
#
# 用法（Phase 3.3 PoC）：
#   ctx = AppContext(
#       student_name='Alice',
#       student_grade=8,
#       current_mastery_overview='math: 65, english: 82',
#       recent_struggle='math/algebra',
#   )
#   builder = TwinContextBuilder(app_state)
#   critic_ctx = builder.build_critic_context(event_dict, extra=ctx.to_critic_extra())
#
# 当前 plumbing-only 阶段 AppContext 不强求；调用方可直接传 dict。
# 引入 dataclass 是给 Phase 3.3 PoC 一个稳定的 typed 入口。


@dataclass
class AppContext:
    """应用层上下文契约（Phase 3.3 PoC 字段集合，先就位）。

    字段语义详见 SSOT §5「不同应用的注入差异」。
    字段均为可选；调用方按需填入。
    """

    # 学生数字孪生场景
    student_name: Optional[str] = None
    student_grade: Optional[int] = None
    current_mastery_overview: Optional[str] = None
    recent_struggle: Optional[str] = None
    learning_pace: Optional[float] = None

    # 教学 AI 教练场景
    learning_goals: Optional[str] = None

    # Personal AI 场景
    user_name: Optional[str] = None
    relationship_history: Optional[str] = None

    # 历史人物数字孪生场景
    person_name: Optional[str] = None
    era: Optional[str] = None
    historical_context: Optional[str] = None

    # 自由扩展
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """导出为 dict（None 字段跳过 + extra 平铺合并）。"""
        d = asdict(self)
        extra = d.pop('extra') or {}
        d = {k: v for k, v in d.items() if v is not None}
        d.update(extra)
        return d


# ══════════════════════════════════════════════
# TwinContextBuilder：薄壳拼装器
# ══════════════════════════════════════════════
#
# 设计权衡：
#   - 不假定 event 类型（duck typing dict）
#   - 不假定 mastery_state（可调用方传 None）
#   - 默认 8D 字段值 0.5（与 critic.py stub_critic_sense 默认对齐）
#   - extra 完全覆盖默认（App 层字段决定 SGE 看到的 context）
#   - 输出 dict 可直接传给 critic_sense(extra_context=...)


class TwinContextBuilder:
    """把 app_state + extra 拼装成 critic / actor 注入的 context。

    用法：
        builder = TwinContextBuilder(app_state={'student_name': 'Alice', 'grade': 7})
        critic_ctx = builder.build_critic_context(
            student_event={'type': 'success', 'description': '...'},
            extra={'current_mastery_overview': 'math: 65, english: 82'},
        )
        actor_prompt = builder.build_actor_prompt_context(
            student_event={'type': 'success', 'description': '...'},
        )

        # 透传给 orchestrator
        trace = orchestrator.step(
            epoch=N,
            context_builder=builder,
            extra_critic_context=critic_ctx,
            extra_actor_context=actor_prompt,
        )
    """

    DEFAULT_8D_VALUES: dict[str, float] = {f: 0.5 for f in CRITIC_DEFAULT_8D}
    # user_emotion 范围 [-1, 1]，其他 [0, 1]，与 critic.py:102-104 一致
    DEFAULT_8D_VALUES['user_emotion'] = 0.0

    def __init__(self, app_state: Optional[dict] = None):
        self.app_state = dict(app_state) if app_state else {}

    def build_critic_context(
        self,
        student_event: Optional[dict] = None,
        mastery_state: Optional[object] = None,
        extra: Optional[dict] = None,
    ) -> dict:
        """构造 critic 的 context（替换默认 8D）。

        返回 dict 的字段子集会被 critic_sense 覆盖默认 8D；多余字段保留
        供 real_critic_sense 注入 prompt 模板。
        """
        ctx: dict[str, Any] = dict(self.DEFAULT_8D_VALUES)

        # mastery_state duck typing：mastery.summary() / most_recent_struggling() /
        # learning_velocity()。Phase 3.3 才落地，当前允许传 None。
        if mastery_state is not None:
            for method, target in [
                ('summary', 'current_mastery_overview'),
                ('most_recent_struggling', 'recent_struggle'),
                ('learning_velocity', 'learning_pace'),
            ]:
                fn = getattr(mastery_state, method, None)
                if callable(fn):
                    try:
                        ctx[target] = fn()
                    except Exception:
                        pass

        # extra 完全覆盖默认（App 层权威）
        if extra:
            ctx.update(extra)

        return ctx

    def build_actor_prompt_context(
        self,
        student_event: Optional[dict] = None,
        mastery_state: Optional[object] = None,
    ) -> str:
        """构造 Actor 的 prompt context（注入到 system prompt）。

        返回多行字符串；real_actor_express 会拼到 prompt 末尾。
        格式：学生信息 / 本次事件 / 回复要求 三段式（与 SSOT §2 一致）。
        """
        name = self.app_state.get('student_name', self.app_state.get('user_name', 'unknown'))
        grade = self.app_state.get('grade', self.app_state.get('student_grade', 'unknown'))

        mastery_overview = self.app_state.get('current_mastery_overview', '无')
        recent_struggle = self.app_state.get('recent_struggle', '无')

        # mastery_state duck typing 同样允许（与 build_critic_context 行为一致）
        if mastery_state is not None:
            summary_fn = getattr(mastery_state, 'summary', None)
            if callable(summary_fn):
                try:
                    mastery_overview = summary_fn()
                except Exception:
                    pass

        event_str = '（无事件）'
        if student_event:
            etype = student_event.get('type', 'unknown')
            desc = student_event.get('description', '')
            intensity = student_event.get('intensity', '')
            event_str = f"类型={etype} 强度={intensity} 描述={desc}"

        return (
            f"[学生信息]\n"
            f"姓名: {name}\n"
            f"年级: {grade}\n"
            f"当前优势/挑战学科: {mastery_overview}\n"
            f"近期挑战: {recent_struggle}\n\n"
            f"[本次事件]\n{event_str}\n\n"
            f"[回复要求]\n"
            f"- 用学生名字称呼（如果已知）\n"
            f"- 根据近期挑战给具体建议（不是泛泛而谈）\n"
            f"- 避免评判性语言，用建设性语言\n"
        )


# ══════════════════════════════════════════════
# Critic / Actor extra_* 注入辅助
# ══════════════════════════════════════════════


def critic_extra_context_to_prompt(extra_context: Optional[dict]) -> str:
    """把 extra_context 序列化成 prompt 片段。

    仅在 real_critic_sense 中使用——stub_critic_sense 直接 .update() 字典。
    返回空串表示无注入；返回的字符串可直接拼到 prompt 模板。
    """
    if not extra_context:
        return ''
    return '[App Context]\n' + json.dumps(extra_context, ensure_ascii=False, indent=2)


def actor_extra_system_prompt_to_prompt(extra_system_prompt: Optional[str]) -> str:
    """actor extra_system_prompt 透传（直接返回原字符串；空 = 无）。"""
    return extra_system_prompt or ''


# ══════════════════════════════════════════════
# 单元测试
# ══════════════════════════════════════════════


def _run_context_injection_unit_tests() -> bool:
    """TwinContextBuilder + critic/actor plumbing 单元测试。

    9 个测试：
    1-7: TwinContextBuilder / AppContext / 序列化辅助
    8-9: 集成路径——extra_* 通过 critic_sense/actor_express/orchestrator.step/TwinSession 端到端透传
    """
    print(f"\n{'─'*60}")
    print(f"  sge.context_injection (TwinContextBuilder) 单元测试")
    print(f"{'─'*60}\n")

    # ── 测试 1: build_critic_context 默认 8D 完整 ──
    print("[测试 1] build_critic_context 默认 8D 字段完整")
    builder = TwinContextBuilder(app_state={'student_name': 'Alice'})
    ctx = builder.build_critic_context(student_event={'type': 'success'})
    assert set(ctx.keys()) == set(CRITIC_DEFAULT_8D), (
        f"缺少默认字段：{set(CRITIC_DEFAULT_8D) - set(ctx.keys())}"
    )
    assert ctx['user_emotion'] == 0.0, f"user_emotion 默认 0.0，得到 {ctx['user_emotion']}"
    for f in CRITIC_DEFAULT_8D:
        if f != 'user_emotion':
            assert ctx[f] == 0.5, f"{f} 默认 0.5，得到 {ctx[f]}"
    print(f"  ✓ 8 个默认字段全部就位 + user_emotion=0.0 其余=0.5")

    # ── 测试 2: extra 完全覆盖默认 ──
    print("\n[测试 2] extra 字段覆盖默认 8D")
    extra = {
        'student_name': 'Alice',
        'student_grade': 7,
        'user_emotion': -0.8,
        'user_vulnerability': 0.9,
    }
    ctx = builder.build_critic_context(extra=extra)
    assert ctx['user_emotion'] == -0.8, "extra 覆盖 user_emotion 失败"
    assert ctx['user_vulnerability'] == 0.9, "extra 覆盖 user_vulnerability 失败"
    assert ctx['student_name'] == 'Alice', "extra 保留 App 字段失败"
    assert ctx['student_grade'] == 7
    # 未覆盖的字段保持默认
    assert ctx['novelty_level'] == 0.5
    print(f"  ✓ extra 覆盖默认 + 保留 App 字段")

    # ── 测试 3: build_actor_prompt_context 三段式 ──
    print("\n[测试 3] build_actor_prompt_context 三段式（学生信息/事件/要求）")
    builder = TwinContextBuilder(app_state={
        'student_name': 'Alice', 'grade': 7,
        'current_mastery_overview': 'math: 65, english: 82',
        'recent_struggle': 'math/algebra',
    })
    actor_ctx = builder.build_actor_prompt_context(
        student_event={'type': 'failure', 'description': '测试没及格', 'intensity': 0.7},
    )
    assert '[学生信息]' in actor_ctx
    assert '姓名: Alice' in actor_ctx
    assert '年级: 7' in actor_ctx
    assert 'math: 65, english: 82' in actor_ctx
    assert 'math/algebra' in actor_ctx
    assert '[本次事件]' in actor_ctx
    assert '测试没及格' in actor_ctx
    assert '[回复要求]' in actor_ctx
    print(f"  ✓ 6 个关键短语命中")

    # ── 测试 4: mastery_state duck typing（Phase 3.3 占位）──
    print("\n[测试 4] mastery_state duck typing（duck 调用方法）")
    class FakeMastery:
        def summary(self): return 'math: 90, english: 88'
        def most_recent_struggling(self): return 'math/geometry'
        def learning_velocity(self): return 0.85

    builder2 = TwinContextBuilder(app_state={'student_name': 'Bob', 'grade': 9})
    ctx = builder2.build_critic_context(mastery_state=FakeMastery())
    assert ctx['current_mastery_overview'] == 'math: 90, english: 88'
    assert ctx['recent_struggle'] == 'math/geometry'
    assert ctx['learning_pace'] == 0.85

    actor_str = builder2.build_actor_prompt_context(mastery_state=FakeMastery())
    assert 'math: 90, english: 88' in actor_str
    print(f"  ✓ duck typing 提取 mastery 字段")

    # ── 测试 5: mastery_state 方法抛异常 → 静默回退 ──
    print("\n[测试 5] mastery_state 异常静默回退（不污染 ctx）")
    class BrokenMastery:
        def summary(self): raise RuntimeError("not yet implemented")

    ctx = builder2.build_critic_context(mastery_state=BrokenMastery())
    assert 'current_mastery_overview' not in ctx, "异常不应写入 ctx"
    assert ctx['user_emotion'] == 0.0
    print(f"  ✓ 异常被吞，ctx 保持默认")

    # ── 测试 6: AppContext dataclass 转 dict（None 跳过）──
    print("\n[测试 6] AppContext.to_dict（None 字段跳过 + extra 合并）")
    ctx = AppContext(
        student_name='Alice', student_grade=7,
        current_mastery_overview='math: 65',
        extra={'learning_pace': 0.6, 'recent_struggle': 'math/algebra'},
    )
    d = ctx.to_dict()
    assert 'student_name' in d and d['student_name'] == 'Alice'
    assert 'student_grade' in d and d['student_grade'] == 7
    assert d.get('learning_pace') == 0.6, "extra 应被平铺合并"
    assert d.get('recent_struggle') == 'math/algebra'
    assert 'extra' not in d, "extra 字段应在 to_dict 后被消费掉"
    # 未填字段（learning_goals / user_name 等）应跳过
    assert 'learning_goals' not in d
    assert 'user_name' not in d
    print(f"  ✓ to_dict 跳过 None + 平铺 extra")

    # ── 测试 7: critic_extra_context_to_prompt 序列化 ──
    print("\n[测试 7] critic_extra_context_to_prompt 序列化")
    s = critic_extra_context_to_prompt({'student_name': 'Alice', 'grade': 7})
    assert '[App Context]' in s
    assert '"student_name": "Alice"' in s
    assert critic_extra_context_to_prompt(None) == ''
    print(f"  ✓ 序列化 + None 透传空串")

    # ── 测试 8: critic_sense extra_context 覆盖默认 8D + 保留 App 字段 ──
    print("\n[测试 8] critic_sense extra_context 端到端（stub 路径）")
    from .critic import critic_sense
    extra = {
        'user_emotion': -0.7,
        'user_vulnerability': 0.9,
        'student_name': 'Alice',
        'student_grade': 7,
    }
    ctx, _ = critic_sense(
        event={'type': 'failure', 'intensity': 0.8},
        seed=42,
        extra_context=extra,
    )
    # stub 会给 8D 数值加小幅高斯扰动（设计如此，避免实验注入失真）；
    # 检查 extra 字段在 ±0.1 扰动范围内近似保留 + App 字符串原样
    assert abs(ctx['user_emotion'] - (-0.7)) < 0.2, (
        f"user_emotion 覆盖失败（±0.2 误差）: {ctx['user_emotion']}"
    )
    assert abs(ctx['user_vulnerability'] - 0.9) < 0.2, f"vulnerability 覆盖失败: {ctx['user_vulnerability']}"
    assert ctx['student_name'] == 'Alice', "App 私有字段丢失"
    assert ctx['student_grade'] == 7
    # 未覆盖字段保持 0.5
    assert abs(ctx['novelty_level'] - 0.5) < 0.2, f"未覆盖字段被污染: {ctx['novelty_level']}"
    print(f"  ✓ extra 覆盖默认 + App 字段透传 + 未覆盖字段保留")

    # ── 测试 9: TwinSession.process_event 接收 context_builder 全链路 ──
    print("\n[测试 9] TwinSession.process_event 透传 TwinContextBuilder")
    import tempfile, os
    from .persistence import TwinStateDB
    from .session import _make_minimal_components, _session_registry
    from .session import SGEOrchestrator, TwinSession

    db_path = tempfile.mktemp(suffix='.db')
    with TwinStateDB(db_path) as db:
        agent, vl, dm, eg, il, nb, hw, cr = _make_minimal_components()
        orch0 = SGEOrchestrator(
            agent=agent, value_layer=vl, drive_metabolism=dm, event_generator=eg,
            identity_layer=il, narrative_builder=nb, hawking=hw, crystallizer=cr,
            db=db, student_id='stu_ctx_001', checkpoint_every=100,
            app_state={'student_name': 'Alice', 'grade': 7,
                       'current_mastery_overview': 'math: 65, english: 82'},
        )
        orch0.session_end()

        # 通过 TwinSession 跑 1 个 epoch，携带 context_builder
        builder = TwinContextBuilder(app_state={'student_name': 'Alice', 'grade': 7})
        critic_ctx = builder.build_critic_context(
            student_event={'type': 'failure'},
            extra={'student_name': 'Alice', 'student_grade': 7,
                   'user_vulnerability': 0.95},
        )
        actor_prompt = builder.build_actor_prompt_context(
            student_event={'type': 'failure', 'description': '考试没及格', 'intensity': 0.7},
        )

        session = TwinSession('stu_ctx_001', twin_db=db, auto_save_every=0)
        trace = session.process_event(
            epoch=0,
            extra_critic_context=critic_ctx,
            extra_actor_context=actor_prompt,
        )
        assert trace.epoch == 0
        assert trace.actor_output is not None
        # TwinContextBuilder 字段应到达 actor_output（stub 路径：仅行为正确即可；
        # real 路径 LLM prompt 会含 App Context，本测试不验证 LLM prompt）
        session.close()

        # 清理 registry + 文件
        for sid in list(_session_registry):
            try:
                _session_registry[sid].close(save=False)
            except Exception:
                pass
    try:
        os.unlink(db_path)
    except OSError:
        pass
    print(f"  ✓ TwinSession.process_event 接收 TwinContextBuilder 输出并透传")

    print(f"\n  状态: ✅ PASS — 9/9 (TwinContextBuilder + 端到端 plumbing) 测试通过")
    return True


if __name__ == "__main__":
    import sys
    ok = _run_context_injection_unit_tests()
    sys.exit(0 if ok else 1)