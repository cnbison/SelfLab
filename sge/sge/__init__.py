"""
SGE Python Package — Self-Generating Engine 的核心实现

Phase 3+ 正式 Python 包化（M2.x 一直是 scripts/ 下的临时实现）。

公开 API：
    from sge import (
        # Core mechanisms
        Agent, DriveMetabolism, ValueLayer, MemoryCrystallizer,
        HawkingDecay, MemoryCrystallizer,
        # Event
        EventGenerator, LifeEvent,
        # LLM 适配层
        SGELLMClient, make_llm_client,
        critic_sense, actor_express, ActorOutput,
        IdentityLayer, NarrativeBuilder,
        # Orchestrator
        SGEOrchestrator, OrchestratorStep,
    )

历史：
    - M2.1 阶段 D（commit b40f541）：临时 _sge_*.py 文件
    - M2.2（commit 83ed0a1）：~17h 1000 epoch × 3 baby 验证
    - M2.3（commit 102fd9f）：个人真实测试
    - M2.3 Hawking fix（commit 1a88452）：修复 unit mismatch bug
    - Phase 3（commit TBD）：sge/ 包化 + Reflection Layer 等

关联文档：
    - [SGE-Memory-Layer-Design.md](../../research/sge-core/SGE-Memory-Layer-Design.md)
    - [DESIGN.md](../../DESIGN.md)
    - [M22_TRIPLETS_REPORT.md](../../experiments/M22_TRIPLETS_REPORT.md)
"""

__version__ = "0.1.0"

# Core mechanisms
from .baseline import (
    Agent, DriveMetabolism, ValueLayer, MemoryCrystallizer,
    HawkingDecay,
    SGE_DEFAULT_DRIVES, SGE_DEFAULT_VALUES, SGE_DEFAULT_HUNGER_RATES,
    SGE_HAWKING_GAMMA,
)

# Event
from .event import (
    EventGenerator, LifeEvent,
    make_event_id,
    generate_value_conflict,
    EVENT_TEMPLATES,
)

# LLM 适配层
from .llm_client import SGELLMClient, make_llm_client

# Critic / Actor / Identity / Narrative
from .critic import critic_sense, real_critic_sense, stub_critic_sense, CRITIC_CONTEXT_FIELDS, VALUE_DELTA_FIELDS
from .actor import actor_express, real_actor_express, stub_actor_express, ActorOutput, BEHAVIOR_LABELS
from .identity import IdentityLayer, real_crystallize_identity, real_validate_identity, stub_crystallize_identity
from .narrative import NarrativeBuilder, real_build_narrative, real_check_narrative_consistency, stub_build_narrative

# Orchestrator
from .orchestrator import SGEOrchestrator, OrchestratorStep


__all__ = [
    # Core
    'Agent', 'DriveMetabolism', 'ValueLayer', 'MemoryCrystallizer',
    'HawkingDecay',
    'SGE_DEFAULT_DRIVES', 'SGE_DEFAULT_VALUES', 'SGE_DEFAULT_HUNGER_RATES',
    'SGE_HAWKING_GAMMA',
    # Event
    'EventGenerator', 'LifeEvent',
    'make_event_id', 'generate_value_conflict',
    'EVENT_TEMPLATES',
    # LLM
    'SGELLMClient', 'make_llm_client',
    # Components
    'critic_sense', 'real_critic_sense', 'stub_critic_sense',
    'CRITIC_CONTEXT_FIELDS', 'VALUE_DELTA_FIELDS',
    'actor_express', 'real_actor_express', 'stub_actor_express',
    'ActorOutput', 'BEHAVIOR_LABELS',
    'IdentityLayer', 'real_crystallize_identity', 'real_validate_identity',
    'stub_crystallize_identity',
    'NarrativeBuilder', 'real_build_narrative',
    'real_check_narrative_consistency', 'stub_build_narrative',
    # Orchestrator
    'SGEOrchestrator', 'OrchestratorStep',
]
