"""StudentEvent → SGE event 适配层

设计 SSOT：[research/phase3/90-applications/student-digital-twin.md §2.3](../research/phase3/90-applications/student-digital-twin.md)

职责：
  1. student_event_to_sge_event: StudentEvent → SGE event dict
  2. build_critic_context_for_event: 构造注入 TwinContextBuilder 的 critic context
  3. build_actor_prompt_for_event: 构造 actor system prompt（含 R5 安全约束）
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .events import StudentEvent
from .mastery import SubjectMasteryState

if TYPE_CHECKING:
    from sge import TwinContextBuilder


# ══════════════════════════════════════════════
# R5 缓解：建设性表达安全约束
# ══════════════════════════════════════════════
#
# 学生数据误用风险（04-risks.md R5）：AI 教练根据 SubjectMasteryState 给学生"贴标签"
# （"你是数学差生"），影响学生心理健康。
#
# 缓解：actor system prompt 硬约束「建设性表达」+ 单元测试抽样验证。

SAFETY_DIRECTIVE = """\
[回复要求 - 强制约束 - 安全]
- 不使用评判性语言（避免使用如负面标签等表达方式）
- 使用建设性语言（"你最近{topic}有挑战"/"这块可以重点突破"/"继续保持"）
- 给具体可执行建议（如"把 X 知识点再过一遍"），不给泛泛安慰
- 称呼用学生名字（如果已知）
- 避免给"高风险建议"（如推荐留级/转班/放弃某学科）
"""

# 单元测试抽样的禁用关键词（避免评判性语言）
SAFETY_KEYWORDS_FORBIDDEN: tuple[str, ...] = (
    '你太差',
    '你不行',
    '你学不会',
    '你笨',
    '你没救',
    '你放弃吧',
    '你放弃',
    '你很差',
    '差生',
    '废物',
)

# 单元测试抽样的必备关键词（确保建设性 + 具体）
SAFETY_KEYWORDS_REQUIRED: tuple[str, ...] = (
    '挑战',          # "有挑战" 而非 "太差"
    '可以',          # "可以重点突破" 而非 "学不会"
    '具体',          # 强调具体性
)


# ══════════════════════════════════════════════
# 适配函数
# ══════════════════════════════════════════════


def student_event_to_sge_event(event: StudentEvent) -> dict:
    """StudentEvent → SGE event dict（喂给 orchestrator.step 的额外信号）。

    字段命名策略（兼容 TwinContextBuilder 期望的字段名）：
      - description:      人读描述
      - subject:          学科
      - topic:            主题
      - type:             事件类型（TwinContextBuilder 期望的字段名）
      - intensity:        强度 0-1（TwinContextBuilder 期望的字段名）
      - emotion:          主导情绪
      - mastery_delta:    mastery 变化量
      - mastery_before:   事件前
      - mastery_after:    事件后
      - event_id:         唯一 ID（保留 StudentEvent 原字段名）

    注：TwinContextBuilder.build_actor_prompt_context 读 type/description/intensity；
        故同时输出 type/intensity（适配器层负责字段命名映射，不污染 StudentEvent 自有命名）。
    """
    return {
        'event_id': event.event_id,
        'description': event.description,
        'subject': event.subject,
        'topic': event.topic,
        'type': event.event_type,
        'event_type': event.event_type,  # 兼容字段（双命名）
        'intensity': event.emotion_intensity,
        'emotion_intensity': event.emotion_intensity,  # 兼容字段
        'emotion': event.emotion,
        'mastery_delta': event.mastery_delta,
        'mastery_before': event.mastery_before,
        'mastery_after': event.mastery_after,
    }


def build_critic_context_for_event(
    event: StudentEvent,
    mastery_state: SubjectMasteryState,
    builder: 'TwinContextBuilder',
) -> dict:
    """为单个 StudentEvent 构造 critic context（注入 TwinContextBuilder）。

    流程：
      1. 调 builder.build_critic_context(mastery_state=mastery_state, ...)
         → 触发 duck typing（summary / most_recent_struggling / learning_velocity）
      2. 注入本事件特有字段（subject/topic/mastery_delta/emotion/...）

    Args:
        event: StudentEvent 实例
        mastery_state: SubjectMasteryState（duck typing 给 builder）
        builder: TwinContextBuilder 实例

    Returns:
        dict: critic context（含默认 8D + App 层注入字段）
    """
    return builder.build_critic_context(
        student_event=student_event_to_sge_event(event),  # 用适配 dict（含 type/intensity）
        mastery_state=mastery_state,
        extra={
            'subject': event.subject,
            'topic': event.topic,
            'event_type': event.event_type,
            'mastery_delta': event.mastery_delta,
            'emotion': event.emotion,
            'emotion_intensity': event.emotion_intensity,
        },
    )


def build_actor_prompt_for_event(
    event: StudentEvent,
    mastery_state: SubjectMasteryState,
    builder: 'TwinContextBuilder',
    include_safety: bool = True,
) -> str:
    """为单个 StudentEvent 构造 actor system prompt（含建设性表达硬约束）。

    Args:
        event: StudentEvent 实例
        mastery_state: SubjectMasteryState（duck typing 给 builder）
        builder: TwinContextBuilder 实例
        include_safety: 是否注入 R5 安全约束（默认 True；测试可设 False）

    Returns:
        str: actor system prompt（注入到 real_actor_express.extra_system_prompt）
    """
    base = builder.build_actor_prompt_context(
        student_event=student_event_to_sge_event(event),  # 用适配 dict（含 type/intensity）
        mastery_state=mastery_state,
    )
    if include_safety:
        # 把 {topic} 占位符替换为实际主题（如果有）
        safety = SAFETY_DIRECTIVE.format(
            topic=event.topic or '这块',
        )
        return base + safety
    return base