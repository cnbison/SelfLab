"""student_digital_twin — Phase 3.3 学生数字孪生 PoC 应用层

把学生领域模型（SubjectMasteryState + StudentEvent）和适配层（StudentEvent → SGE event）
从 sge/ 包解耦（CLAUDE.md §实验代码约定 — 领域模型不进 sge/，保持引擎领域无关）。

公开 API：
    from student_digital_twin import (
        # 领域模型
        SubjectMasteryState, SubjectMastery, TopicMastery,
        StudentEvent, EventType,
        # 适配层
        student_event_to_sge_event,
        build_critic_context_for_event,
        build_actor_prompt_for_event,
    )

关联文档：
    - research/phase3/90-applications/student-digital-twin.md
    - research/phase3/00-overview/02-architecture.md §5 数据流
    - sge/sge/context_injection.py §build_critic_context（duck typing 契约）
"""

__version__ = "0.1.0"

from .mastery import (
    SubjectMasteryState, SubjectMastery, TopicMastery,
    MASTERY_SCHEMA_VERSION, DEFAULT_STRUGGLE_THRESHOLD,
)
from .events import (
    StudentEvent, EventType, ALL_EVENT_TYPES,
)
from .adapter import (
    student_event_to_sge_event,
    build_critic_context_for_event,
    build_actor_prompt_for_event,
    SAFETY_DIRECTIVE, SAFETY_KEYWORDS_FORBIDDEN, SAFETY_KEYWORDS_REQUIRED,
)


__all__ = [
    # 领域模型
    'SubjectMasteryState', 'SubjectMastery', 'TopicMastery',
    'MASTERY_SCHEMA_VERSION', 'DEFAULT_STRUGGLE_THRESHOLD',
    # 事件
    'StudentEvent', 'EventType', 'ALL_EVENT_TYPES',
    # 适配层
    'student_event_to_sge_event',
    'build_critic_context_for_event',
    'build_actor_prompt_for_event',
    'SAFETY_DIRECTIVE', 'SAFETY_KEYWORDS_FORBIDDEN', 'SAFETY_KEYWORDS_REQUIRED',
]