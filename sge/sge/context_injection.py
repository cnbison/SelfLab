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
        learning_pace = self.app_state.get('learning_pace', None)

        # mastery_state duck typing 同样允许（与 build_critic_context 行为一致）
        if mastery_state is not None:
            summary_fn = getattr(mastery_state, 'summary', None)
            if callable(summary_fn):
                try:
                    mastery_overview = summary_fn()
                except Exception:
                    pass
            # Phase 3.3 PoC：actor prompt 也 duck type 挣扎主题 + 学习速率
            struggling_fn = getattr(mastery_state, 'most_recent_struggling', None)
            if callable(struggling_fn):
                try:
                    recent_struggle = struggling_fn()
                except Exception:
                    pass
            velocity_fn = getattr(mastery_state, 'learning_velocity', None)
            if callable(velocity_fn):
                try:
                    learning_pace = velocity_fn()
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
            f"近期挑战: {recent_struggle}\n"
            f"学习速率: {learning_pace if learning_pace is not None else '无'}\n\n"
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
# Phase 3.2: 测试已迁移到 sge/tests/unit/test_context_injection.py
# 此处保留薄 shim 以兼容 `python -m sge.context_injection`


def _run_context_injection_unit_tests() -> bool:
    """兼容层：转调 pytest（Phase 3.2 起的测试已在 sge/tests/unit/）。"""
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, '-m', 'pytest',
         'tests/unit/test_context_injection.py', '-v', '--tb=short'],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run_context_injection_unit_tests() else 1)