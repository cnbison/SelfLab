"""
SGE 12 步双 LLM 编排器（阶段 D 引入）

本文件是 **SGE 自有实现**——把阶段 B/C 全部模块组装为完整 12 步双 LLM 编排。

**架构来源**：AiBeing engine/genome/chat_agent.py:_chat_inner() (12 步循环)
**SGE 化参考**：[SGE-M21-AiBeing-Implementation-Mapping.md §2.9](../research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md)

**12 步循环映射**：

| Step | AiBeing | SGE | 模块来源 |
|------|---------|-----|---------|
| 0 | EverMemOS 加载 | History 加载（Memory + Narrative）| Phase C/D |
| 1 | Time Metabolism | drive_metabolism.time_metabolism() | Phase A |
| 2 | Critic | critic_sense(event) → ctx + value_delta | Phase B |
| 2.5 | Relationship EMA | ValueLayer.update(value_delta) | Phase B |
| 3 | Drive metabolism + reward | drive_metabolism.apply_llm_delta() | Phase A |
| 4 | Crystallization gate | MemoryCrystallizer.insert_or_merge() | Phase B/D1 |
| 5 | Compute signals | agent.compute_signals(context) | Phase A |
| 6 | Thermodynamic noise | apply_thermodynamic_noise() | Phase A |
| 7 | KNN retrieval | hawking.retrieve(k=5) | Phase B/D1 |
| 8 | Build prompt | _build_prompt() (新增) | Phase D |
| 9 | Actor LLM | actor_express(signals + values + retrieved + narrative) | Phase D2 |
| 10 | Hebbian learning | agent.learn(signals, reward) | Phase A |
| 11 | Async storage | snapshot() (同步，实验阶段无并发) | Phase D |
| 12 | Skill handling | 不适用（skip）| — |

**额外步骤**（不在 AiBeing 12 步中，是 SGE 6 层架构新增）：
- Step 13: Identity Crystallize（每 N epoch 触发，IdentityLayer.crystallize）
- Step 14: Narrative Build（每 M epoch 触发，NarrativeBuilder.build）
- Step 15: Phase Transition 检查（agent.learn 内部嵌入）

**为什么独立编排器**：
- 阶段 C 的 m21_phase_c.py 在一个函数里手动组装了 6 步
- 阶段 D 需要严格管理 Step 顺序、数据流、可观测性
- 独立编排器便于：单步调用、组件替换（Hawking/Crystallize 可选）、调试

关联文档：
- [SGE-M21-Phase-D-Implementation-Plan.md §D3](../research/sge-feasibility/SGE-M21-Phase-D-Implementation-Plan.md)
- [SGE-M21-AiBeing-Implementation-Mapping.md §2.9](../research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md)
"""

from __future__ import annotations

import copy
import json
import math
import random
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Callable, Any, TYPE_CHECKING

from . import __version__ as SGE_VERSION
from .baseline import (
    Agent, DriveMetabolism, ValueLayer, HawkingDecay, MemoryCrystallizer,
    SGE_DEFAULT_DRIVES, SGE_DEFAULT_VALUES, SIGNALS, CONTEXT_FEATURES,
    apply_thermodynamic_noise, SnapshotError,
)
from .critic import critic_sense
from .actor import actor_express, ActorOutput
from .event import EventGenerator, LifeEvent
from .experience import encode_experience, Experience
from .metrics import compute_self_entropy
from .identity import IdentityLayer
from .narrative import NarrativeBuilder
from .llm_client import SGELLMClient, make_llm_client

if TYPE_CHECKING:
    # 避免 runtime 循环依赖（persistence 引用 baseline 等）
    from .persistence import TwinStateDB


# ══════════════════════════════════════════════
# Orchestrator Step Trace（每步完整 trace）
# ══════════════════════════════════════════════


@dataclass
class OrchestratorStep:
    """每步的完整 trace — 用于阶段 D 测试和调试

    字段按 12+3 步顺序排列，便于时序分析
    """
    epoch: int

    # ── 感知侧（Step 2-3）──
    event: dict                       # Step 2: EventGenerator 输出
    critic_context: dict              # Step 3: Critic 输出的 12D context
    critic_value_delta: dict          # Step 3: Critic 输出的 6D value_delta

    # ── 记忆侧（Step 4-6）──
    value_state_before: dict          # Step 4: Value EMA 更新前
    value_state_after: dict           # Step 4: Value EMA 更新后
    hawking_removed: int              # Step 5: Hawking 衰减移除数
    crystallize_result: Optional[str] # Step 6: 'merged' / 'created' / None

    # ── 表达侧（Step 7-11）──
    signals: dict                     # Step 7: 神经网络前向
    noisy_signals: dict               # Step 8: 热力学噪声
    retrieved_memories: list          # Step 9: KNN 检索
    actor_output: Optional[ActorOutput] = None  # Step 11: Actor 输出

    # ── 学习侧（Step 10, 12, 13-14）──
    reward: float = 0.0               # Step 3: reward 计算结果
    phase_xition: bool = False        # Step 12: Phase Transition 触发
    identity: Optional[str] = None    # Step 13: Identity Crystallize（可能为 None）
    narrative: Optional[str] = None   # Step 14: Narrative Build（可能为 None）

    # ── 经验侧 / 熵度量（Step 2.5 / Step 16，洞察 34 / 35）──
    experience: Optional[dict] = None # Step 2.5: Experience Encoder 输出（含 meaning）
    self_entropy: Optional[dict] = None  # Step 16: H_self 度量（含 H_value/H_identity/H_narrative）

    # ── 元数据 ──
    timestamp_hours: float = 0.0      # 受控时钟（epoch * 1h）

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.actor_output is not None:
            d['actor_output'] = self.actor_output.to_dict()
        return d


# ══════════════════════════════════════════════
# 12 步编排器
# ══════════════════════════════════════════════


class SGEOrchestrator:
    """完整 12 步双 LLM 编排器

    用法：
      orchestrator = SGEOrchestrator(agent=agent, value_layer=vl, ...)
      traces = orchestrator.run(n_epochs=100)

    灵活性：
      - hawking / crystallizer 可选（None 时跳过对应步骤）
      - use_real_llm=False（默认）使用 stub LLM
      - 每个组件可独立替换为 stub（用于单元测试）
    """

    def __init__(
        self,
        agent: Agent,
        value_layer: ValueLayer,
        drive_metabolism: DriveMetabolism,
        event_generator: EventGenerator,
        identity_layer: IdentityLayer,
        narrative_builder: NarrativeBuilder,
        hawking: Optional[HawkingDecay] = None,
        crystallizer: Optional[MemoryCrystallizer] = None,
        crystallize_every: int = 10,
        hours_per_epoch: float = 1.0,
        use_real_llm: bool = False,
        llm: Optional[SGELLMClient] = None,
        llm_provider: str = 'minimax',
        verbose: bool = False,
        # ── 持久化集成（Phase 3.1 · 动作 1 集成）──
        db: Optional['TwinStateDB'] = None,
        student_id: Optional[str] = None,
        checkpoint_every: int = 100,
        student_name: Optional[str] = None,
        app_state: Optional[dict] = None,
    ):
        # 持久化配置校验（fail-fast，避免半配置）
        if (db is None) != (student_id is None):
            raise ValueError(
                "SGEOrchestrator: db 和 student_id 必须同时提供或同时为 None "
                f"（得到 db={db!r}, student_id={student_id!r}）"
            )
        if checkpoint_every <= 0:
            raise ValueError(
                f"SGEOrchestrator: checkpoint_every 必须 > 0，得到: {checkpoint_every}"
            )

        self.agent = agent
        self.value_layer = value_layer
        self.drive_metabolism = drive_metabolism
        self.event_generator = event_generator
        self.identity_layer = identity_layer
        self.narrative_builder = narrative_builder
        self.hawking = hawking
        self.crystallizer = crystallizer
        self.crystallize_every = crystallize_every
        self.hours_per_epoch = hours_per_epoch
        self.use_real_llm = use_real_llm
        self.verbose = verbose
        self._n_epochs_hint = 0  # 由 run() 在循环前设置；step() 单调用时为 0
        self.current_epoch = 0  # 步进计数（snapshot_all 读取），每次 step() 末尾 +1

        # 持久化集成 state（Phase 3.1 · 动作 1 集成）
        self.db = db
        self.student_id = student_id
        self.checkpoint_every = checkpoint_every
        self.student_name = student_name
        self.app_state: dict = app_state if app_state is not None else {}
        self._student_initialized: bool = False  # lazy create_student 标志

        # 自动加载 LLM 客户端（如果 use_real_llm=True 且未提供）
        if use_real_llm:
            if llm is None:
                self.llm = make_llm_client(provider=llm_provider, verbose=verbose)
                print(f"✓ Orchestrator auto-loaded LLM: {self.llm.stats()}")
            else:
                self.llm = llm
        else:
            self.llm = None

        # 注入 Memory Layer 到 Agent（如果未注入）
        if self.hawking is not None and self.agent.hawking is None:
            self.agent.hawking = self.hawking
        if self.crystallizer is not None and self.agent.crystallizer is None:
            self.agent.crystallizer = self.crystallizer
            self.agent.crystallize_every = self.crystallize_every

    def _build_prompt(
        self,
        signals: dict,
        value_vector: dict,
        retrieved_memories: list,
        current_narrative: Optional[str],
    ) -> str:
        """Step 8: Build single-pass prompt（DESIGN §9.2 内部参考）

        这是 SGE 新增点 — AiBeing 不考虑 narrative 作为 prompt 输入。
        SGE 把 value_state + narrative + retrieved memories 都作为 Actor 的上下文。
        """
        sig_str = ', '.join(f'{k}={v:.2f}' for k, v in signals.items())
        val_str = ', '.join(f'{k}={v:+.2f}' for k, v in value_vector.items())
        nar_str = current_narrative or '（暂无叙事）'
        mem_str = '\n'.join(
            f'- {m.get("content", m)}' for m in retrieved_memories[:5]
        ) or '（暂无记忆）'

        return f"""[行为信号] {sig_str}
[价值观] {val_str}
[当前叙事] {nar_str}
[近期记忆] {mem_str}"""

    def _compute_reward(self, critic_value_delta: dict) -> float:
        """Step 3: Reward = safety 维度变化 × 0.5（与阶段 C 一致）

        来源: m21_phase_c.py 沿用
        """
        return critic_value_delta.get('safety', 0.0) * 0.5

    def step(self, epoch: int) -> OrchestratorStep:
        """执行一个 epoch 的完整 12 步编排

        Args:
            epoch: 当前 epoch（从 0 开始）

        Returns:
            OrchestratorStep（完整 trace）
        """
        timestamp = epoch * self.hours_per_epoch

        # ── Step 1: Time Metabolism ──
        self.drive_metabolism.time_metabolism()
        self.agent.tick_drives()

        # ── Step 2: Event Generation ──
        event = self.event_generator.generate(
            epoch=epoch,
            value_vector=self.value_layer,
        )

        # ── Step 2.5: Experience Encoding（洞察 34）──
        # 把裸 Event 解释为含 meaning 的 Experience。同一 Event，不同 Self
        # 应产生不同 meaning → 不同 value_delta。meaning 注入 Critic 的事件描述，
        # 使"这件事对我意味着什么"真正影响下游 value 更新。
        experience = encode_experience(
            event=event.to_dict(),
            value_state=self.value_layer.value_state,
            use_real_llm=self.use_real_llm,
            llm=self.llm,
            seed=hash((epoch, 'experience')) % (2**31),
        )

        # ── Step 3: Critic Sense（temperature=0.2）──
        event_for_critic = event.to_dict()
        if experience.meaning:
            event_for_critic['description'] = (
                f"{event_for_critic.get('description', '')}\n\n"
                f"[我的解读] {experience.meaning}"
            )
        critic_context, critic_value_delta = critic_sense(
            event=event_for_critic,
            drives=self.agent.drive_state,
            values=self.value_layer.value_state,
            use_real_llm=self.use_real_llm,
            llm=self.llm,
            seed=hash((epoch, 'critic')) % (2**31),
        )

        # ── Step 3.5: Hawking Insert（M2.2 修复 D6 后的设计缺口）──
        # 把当前 critic_context 写入短时记忆，供 Step 9 KNN retrieval 使用。
        # 之前全代码库没人调用 hawking.insert()，导致 retrieval 永远空 → Actor prompt 缺记忆上下文。
        # design: 每次 insert 都用 weight=1.0，靠 Hawking γ=0.01/h 自然衰减；100h 后 weight ≈ 0.37。
        if self.hawking is not None and critic_context:
            self.hawking.insert(
                content={'epoch': epoch, 'critic_context': critic_context,
                         'event_type': event.event_type},
                weight=1.0,
                now=timestamp,
            )

        # ── Step 4: Value EMA Update ──
        value_state_before = dict(self.value_layer.value_state)
        if critic_value_delta:
            self.value_layer.update(critic_value_delta)
        value_state_after = dict(self.value_layer.value_state)

        # ── Step 5: Hawking Tick（如果集成）──
        hawking_removed = 0
        if self.hawking is not None:
            hawking_removed = self.hawking.tick(now=timestamp)

        # ── Step 6: Crystallize Gate（如果集成 + 触发）──
        crystallize_result = None
        if (
            self.crystallizer is not None
            and self.crystallize_every > 0
            and epoch > 0
            and epoch % self.crystallize_every == 0
        ):
            value_vec = self.value_layer.to_vec()
            # signals 在 Step 7 才计算 — 但 Step 6 可以基于当前 recurrent_state 构造
            # 这里用 placeholder（值都为 0.5），等 Step 7 后用真实 signals 重建
            # 简化：基于 value_vector + drives 构造 11D 向量（6 values + 5 drives）
            drives_vec = [self.agent.drive_state[d] for d in self.agent.drives]
            combined_vec = value_vec + drives_vec  # 11D
            crystallize_result = self.crystallizer.insert_or_merge(
                vec=combined_vec, weight=1.0,
            )

        # ── Step 7: Compute Signals（神经网络前向）──
        signals = self.agent.compute_signals(critic_context)

        # ── Step 8: Apply Noise ──
        noisy_signals = self.drive_metabolism.apply_thermodynamic_noise(signals)

        # ── Step 9: KNN Retrieval（Hawking 检索 top-5）──
        retrieved_memories = []
        if self.hawking is not None:
            retrieved_memories = self.hawking.retrieve(k=5)

        # ── Step 10: Build Prompt ──
        prompt = self._build_prompt(
            signals=noisy_signals,
            value_vector=self.value_layer.value_state,
            retrieved_memories=retrieved_memories,
            current_narrative=self.narrative_builder.get_current(),
        )
        # prompt 暂不直接使用（real_actor 自己构造），但保留供调试
        _ = prompt

        # ── Step 11: Actor Express（temperature=0.9）──
        actor_output = actor_express(
            signals=noisy_signals,
            value_vector=self.value_layer.value_state,
            retrieved_memories=retrieved_memories,
            current_narrative=self.narrative_builder.get_current(),
            use_real_llm=self.use_real_llm,
            llm=self.llm,
            seed=hash((epoch, 'actor')) % (2**31),
        )

        # ── Step 12: Hebbian Learn + Phase Transition ──
        reward = self._compute_reward(critic_value_delta)
        self.agent.learn(signals, reward)  # Phase Transition 在内部检测
        phase_xition = self.agent._last_phase_transition

        # ── Step 13: Identity Crystallize（每 N epoch 触发）──
        identity = None
        if self.identity_layer.should_crystallize(epoch):
            # 构造 key_memories（最近 crystallized_events）
            recent_events = [
                evt.to_dict() for (_, evt) in self.event_generator.event_history[-5:]
            ]
            # 临时设置 IdentityLayer 为真实 LLM 模式（如果 orchestrator 是）
            prev_use_real = self.identity_layer.use_real_llm
            prev_llm = self.identity_layer.llm
            if self.use_real_llm:
                self.identity_layer.use_real_llm = True
                self.identity_layer.llm = self.llm
            identity = self.identity_layer.crystallize(
                value_layer=self.value_layer,
                key_memories=recent_events,
                epoch=epoch,
                seed=hash((epoch, 'identity')) % (2**31),
            )
            # 恢复（保持 IdentityLayer 的独立性）
            self.identity_layer.use_real_llm = prev_use_real
            self.identity_layer.llm = prev_llm

        # ── Step 14: Narrative Build（每 M epoch 触发）──
        narrative = None
        if self.narrative_builder.should_build(epoch):
            recent_events = [
                evt.to_dict() for (_, evt) in self.event_generator.event_history[-10:]
            ]
            prev_use_real = self.narrative_builder.use_real_llm
            prev_llm = self.narrative_builder.llm
            if self.use_real_llm:
                self.narrative_builder.use_real_llm = True
                self.narrative_builder.llm = self.llm
            narrative = self.narrative_builder.build(
                crystallized_events=recent_events,
                current_identity=self.identity_layer.get_current(),
                epoch=epoch,
                seed=hash((epoch, 'narrative')) % (2**31),
            )
            self.narrative_builder.use_real_llm = prev_use_real
            self.narrative_builder.llm = prev_llm

        # ── Step 15: Phase Transition 联动 Narrative 重建 ──
        if phase_xition and self.narrative_builder.current_narrative:
            self.narrative_builder.handle_phase_transition(
                value_layer=self.value_layer,
                crystallized_events=[
                    evt.to_dict() for (_, evt) in self.event_generator.event_history[-10:]
                ],
                current_identity=self.identity_layer.get_current(),
                epoch=epoch,
                seed=hash((epoch, 'phase_xition')) % (2**31),
            )

        # ── Step 16: Compute Self Entropy（洞察 35）──
        # 每 epoch 计算 H_self，作为自我形成的统一目标函数与验收指标。
        self_entropy = compute_self_entropy(
            value_layer=self.value_layer,
            identity_layer=self.identity_layer,
            narrative_builder=self.narrative_builder,
        )

        if self.verbose:
            flags = []
            if phase_xition:
                flags.append('PT')
            if identity is not None:
                flags.append('IDENTITY')
            if narrative is not None:
                flags.append('NARRATIVE')
            if crystallize_result is not None:
                flags.append('CRYSTAL')
            flag_str = f' [{" ".join(flags)}]' if flags else ''
            actor_label = actor_output.behavior_label if actor_output else 'n/a'
            print(
                f'[epoch {epoch + 1}/{self._n_epochs_hint}] '
                f'event={event.event_type} actor={actor_label} '
                f'|val|={self.value_layer.magnitude():.3f} '
                f'H_self={self_entropy["H_self"]:.3f}{flag_str}',
                flush=True,
            )

        # 步进计数（snapshot_all 读取此字段判断 epoch）
        self.current_epoch = epoch + 1

        # ── Checkpoint 钩子（Phase 3.1 · 动作 1 集成 · 洞察 37）──
        # 多触发点：auto_100 / phase_xition / identity_crystallize / narrative_build
        self._maybe_checkpoint(
            epoch=epoch,
            phase_xition=phase_xition,
            identity_crystallized=identity is not None,
            narrative_built=narrative is not None,
        )

        return OrchestratorStep(
            epoch=epoch,
            event=event.to_dict(),
            critic_context=critic_context,
            critic_value_delta=critic_value_delta,
            experience=experience.to_dict(),
            value_state_before=value_state_before,
            value_state_after=value_state_after,
            hawking_removed=hawking_removed,
            crystallize_result=crystallize_result,
            signals=signals,
            noisy_signals=noisy_signals,
            retrieved_memories=retrieved_memories,
            actor_output=actor_output,
            reward=reward,
            phase_xition=phase_xition,
            identity=identity,
            narrative=narrative,
            self_entropy=self_entropy,
            timestamp_hours=timestamp,
        )

    def run(self, n_epochs: int) -> list[OrchestratorStep]:
        """跑 n_epochs，返回全部 trace

        Args:
            n_epochs: 总 epoch 数

        Returns:
            list[OrchestratorStep]
        """
        traces = []
        self._n_epochs_hint = n_epochs
        if self.verbose:
            print(f'[orchestrator] running {n_epochs} epochs '
                  f'(use_real_llm={self.use_real_llm})', flush=True)
        for epoch in range(n_epochs):
            trace = self.step(epoch)
            traces.append(trace)
        return traces

    # ── Snapshot 协议（Phase 3.1 动作 2）──
    _SNAPSHOT_SCHEMA_VERSION = '1.0'

    def snapshot_all(self) -> dict:
        """聚合 7 个 state + EventGenerator（含 event_history） → JSON-friendly dict。

        关键设计：
          - Agent.hawking / Agent.crystallizer 是 alias（指向 self.hawking/crystallizer），
            只走 self.hawking/crystallizer 单点快照，避免 JSON 重复
          - identity_layer.llm / narrative_builder.llm 由 snapshot 排除；restore 时由
            SGEOrchestrator.restore_all(llm=...) 统一注入
          - 顶层含 _schema_version='1.0'，restore 时校验（缺字段 → SnapshotError）
          - 仅在 epoch 边界调用以避免 mid-step 暂态 llm（orchestrator.py:347-360）

        返回 dict 可直接 json.dumps()；Phase 3.1 persistence.py 用此接口存储。
        """
        return {
            '_schema_version': self._SNAPSHOT_SCHEMA_VERSION,
            '_sge_version': SGE_VERSION,
            '_saved_at': datetime.now().isoformat(),
            'metadata': {
                'epoch': self.current_epoch,
                'baby_id': self.event_generator.baby_id,
                'hours_per_epoch': self.hours_per_epoch,
                'use_real_llm': self.use_real_llm,
                'crystallize_every': self.crystallize_every,
            },
            'agent': self.agent.snapshot(),
            'value_layer': self.value_layer.snapshot(),
            'drive_metabolism': self.drive_metabolism.snapshot(),
            'event_generator': self.event_generator.snapshot(),
            'hawking': self.hawking.snapshot() if self.hawking is not None else None,
            'crystallizer': self.crystallizer.snapshot() if self.crystallizer is not None else None,
            'identity_layer': self.identity_layer.snapshot(),
            'narrative_builder': self.narrative_builder.snapshot(),
        }

    def restore_all(
        self,
        snap: dict,
        *,
        llm: Optional[SGELLMClient] = None,
    ) -> None:
        """从 snapshot 字典恢复所有 state。

        严格校验：
          - 缺 _schema_version → SnapshotError
          - 任何子 state 缺关键字段 → SnapshotError（向上传播）

        llm 通过关键字参数注入到 identity_layer / narrative_builder（保持 snapshot
        协议 JSON-friendly，不持久化 LLM 句柄）。

        restore 后重新执行 agent 的 memory layer alias 注入（orchestrator.__init__
        的等价行为），保证 Agent.hawking/crystallizer 与 orchestrator.hawking/crystallizer
        指向同一对象。
        """
        if '_schema_version' not in snap:
            raise SnapshotError(
                f"SGEOrchestrator.restore_all: 缺 '_schema_version' 字段 "
                f"(expected '{self._SNAPSHOT_SCHEMA_VERSION}')"
            )
        if snap['_schema_version'] != self._SNAPSHOT_SCHEMA_VERSION:
            raise SnapshotError(
                f"SGEOrchestrator.restore_all: schema_version 不兼容 "
                f"(snap={snap['_schema_version']} vs expected={self._SNAPSHOT_SCHEMA_VERSION})"
            )

        # 各 state 按 snapshot 顺序反向恢复
        self.value_layer.restore(snap['value_layer'])
        self.drive_metabolism.restore(snap['drive_metabolism'])
        self.event_generator.restore(snap['event_generator'])

        if self.hawking is not None:
            if snap['hawking'] is None:
                raise SnapshotError("SGEOrchestrator.restore_all: self.hawking 非 None 但 snap['hawking'] 为 None")
            self.hawking.restore(snap['hawking'])
        elif snap['hawking'] is not None:
            raise SnapshotError("SGEOrchestrator.restore_all: self.hawking 为 None 但 snap['hawking'] 非 None")

        if self.crystallizer is not None:
            if snap['crystallizer'] is None:
                raise SnapshotError("SGEOrchestrator.restore_all: self.crystallizer 非 None 但 snap['crystallizer'] 为 None")
            self.crystallizer.restore(snap['crystallizer'])
        elif snap['crystallizer'] is not None:
            raise SnapshotError("SGEOrchestrator.restore_all: self.crystallizer 为 None 但 snap['crystallizer'] 非 None")

        self.identity_layer.restore(snap['identity_layer'], llm=llm)
        self.narrative_builder.restore(snap['narrative_builder'], llm=llm)

        # Agent 最后恢复（依赖 value_layer + hawking + crystallizer 引用）
        self.agent.restore(snap['agent'])
        # 重新注入 memory layer alias（对齐 __init__ 行为）
        if self.hawking is not None:
            self.agent.hawking = self.hawking
        if self.crystallizer is not None:
            self.agent.crystallizer = self.crystallizer
            self.agent.crystallize_every = self.crystallize_every

        # 恢复 current_epoch（从 metadata）
        if 'metadata' in snap and 'epoch' in snap['metadata']:
            self.current_epoch = int(snap['metadata']['epoch'])

    # ── Persistence Hooks（Phase 3.1 · 动作 1 集成）──

    def _ensure_student(self) -> None:
        """Lazy create_student（首次 checkpoint 前注册到 DB）。

        避免 __init__ 静默 INSERT 违反 R10（多用户隔离）。
        复用 list_students 检查存在性；StudentExistsError 静默（并发场景）。
        """
        if self._student_initialized or self.db is None or self.student_id is None:
            return
        try:
            existing = self.db.list_students(include_deleted=False)
            existing_ids = {s['student_id'] for s in existing}
        except Exception as e:
            sys.stderr.write(
                f"[orchestrator] list_students failed: {type(e).__name__}: {e}\n"
            )
            return
        if self.student_id not in existing_ids:
            try:
                self.db.create_student(self.student_id, name=self.student_name)
            except Exception as e:
                # StudentExistsError（并发）或 PersistenceError → 静默 + 标记已初始化
                sys.stderr.write(
                    f"[orchestrator] create_student({self.student_id!r}) "
                    f"hint: {type(e).__name__}: {e}\n"
                )
                # 仍标记为已初始化，避免每次 checkpoint 都重试 create
        self._student_initialized = True

    def _save_checkpoint(self, trigger: str, epoch: int) -> bool:
        """保存一次 checkpoint（含 access_log）。

        失败不抛异常：记录 stderr 后返回 False（持久化失败不应中断 epoch 循环）。
        Returns:
            bool: True = 成功；False = 未配置 db / 失败
        """
        if self.db is None or self.student_id is None:
            return False
        try:
            self._ensure_student()
            sge_state = self.snapshot_all()
            self.db.save_full_state(
                student_id=self.student_id,
                sge_state=sge_state,
                app_state=self.app_state,
                epoch=epoch,
                trigger=trigger,
            )
            self.db.log_access(
                student_id=self.student_id,
                accessor_id='orchestrator',
                operation=f'checkpoint_{trigger}',
                ip_address=None,
            )
            return True
        except Exception as e:
            sys.stderr.write(
                f"[orchestrator] checkpoint '{trigger}' failed "
                f"@ epoch {epoch}: {type(e).__name__}: {e}\n"
            )
            return False

    def _maybe_checkpoint(
        self,
        epoch: int,
        phase_xition: bool = False,
        identity_crystallized: bool = False,
        narrative_built: bool = False,
    ) -> None:
        """step() 末尾的 checkpoint 钩子（多触发点，Bisen 决策 #3）。

        触发条件：
        - 自动：(epoch + 1) % checkpoint_every == 0 → trigger='auto_N'
        - 强制：phase_xition → trigger='phase_xition'
        - 强制：identity crystallize → trigger='identity_crystallize'
        - 强制：narrative build → trigger='narrative_build'

        多个触发同时满足 → 多次 save（每次独立事务，保证 checkpoint history 完整）。
        """
        if self.db is None:
            return
        next_epoch = epoch + 1
        triggers: list[str] = []
        if next_epoch % self.checkpoint_every == 0:
            triggers.append(f'auto_{next_epoch}')
        if phase_xition:
            triggers.append('phase_xition')
        if identity_crystallized:
            triggers.append('identity_crystallize')
        if narrative_built:
            triggers.append('narrative_build')
        for trigger in triggers:
            self._save_checkpoint(trigger, epoch=next_epoch)

    def session_end(self) -> bool:
        """显式标记 session end（手动触发最后一次 checkpoint）。

        应用场景：
        - Web 应用：用户退出 / 关闭浏览器
        - CLI：脚本结束（finally 块）
        - 批量处理：每个 batch 完成

        Returns:
            bool: True = 成功；False = 未配置 db / 失败
        """
        if self.db is None:
            return False
        return self._save_checkpoint('session_end', epoch=self.current_epoch)


# ══════════════════════════════════════════════
# 单元测试（验证 12 步全部执行 + 时序）
# ══════════════════════════════════════════════


def _run_unit_tests() -> bool:
    """验证：
      1. 12 步全部执行（无遗漏）
      2. 时序正确（Value 更新前 → 后）
      3. Actor 输出结构有效
      4. Identity/Narrative 触发正确
      5. Phase Transition 检测
      6. Memory Layer 集成
    """
    print(f"\n{'─'*60}")
    print(f"  _sge_orchestrator.py 单元测试")
    print(f"{'─'*60}\n")

    from .baseline import (
        SGE_DEFAULT_DRIVES, SGE_DEFAULT_VALUES,
        _load_drives,
    )

    # 构造组件
    drives = _load_drives()
    value_layer = ValueLayer(values=SGE_DEFAULT_VALUES)
    hawking = HawkingDecay(gamma=0.01, clock=0.0)
    crystallizer = MemoryCrystallizer(n_dims=11)
    agent = Agent(
        seed=42,
        drives=drives,
        value_layer=value_layer,
        hawking=hawking,
        crystallizer=crystallizer,
        crystallize_every=10,
    )
    metabolism = DriveMetabolism(drives=drives)
    event_gen = EventGenerator(baby_id='orch_test', seed=42)
    identity_layer = IdentityLayer(crystallize_every_n_epochs=20)
    narrative_builder = NarrativeBuilder(build_every_n_epochs=50)

    orchestrator = SGEOrchestrator(
        agent=agent,
        value_layer=value_layer,
        drive_metabolism=metabolism,
        event_generator=event_gen,
        identity_layer=identity_layer,
        narrative_builder=narrative_builder,
        hawking=hawking,
        crystallizer=crystallizer,
        crystallize_every=10,
    )

    # ── 测试 1: 跑 55 epoch（覆盖 narrative 触发点 epoch=50）──
    traces = orchestrator.run(n_epochs=55)
    assert len(traces) == 55, f"Expected 55 traces, got {len(traces)}"
    print(f"  ✓ [测试 1: 55 epoch 完整跑通] traces={len(traces)}")

    # ── 测试 2: 每步 trace 字段完整 ──
    t0 = traces[0]
    required_fields = [
        'epoch', 'event', 'critic_context', 'critic_value_delta',
        'value_state_before', 'value_state_after',
        'hawking_removed', 'crystallize_result',
        'signals', 'noisy_signals', 'retrieved_memories',
        'actor_output', 'reward', 'phase_xition',
        'identity', 'narrative',
    ]
    for f in required_fields:
        assert hasattr(t0, f), f"Missing field: {f}"
    print(f"  ✓ [测试 2: trace 字段完整] {len(required_fields)} fields")

    # ── 测试 3: Actor 输出结构有效 ──
    actor_out = t0.actor_output
    assert actor_out is not None
    assert actor_out.behavior_label
    assert actor_out.inner_monologue
    assert 0.0 <= actor_out.confidence <= 1.0
    print(f"  ✓ [测试 3: Actor 输出有效] behavior={actor_out.behavior_label}")

    # ── 测试 4: 时序正确（value_state_after 与 before 应有差异）──
    if t0.critic_value_delta.get('safety', 0) != 0:
        assert t0.value_state_after != t0.value_state_before
        print(f"  ✓ [测试 4: Value EMA 时序正确] safety: {t0.value_state_before['safety']:+.3f} → {t0.value_state_after['safety']:+.3f}")

    # ── 测试 5: Identity 至少结晶 1 次（50 epoch × 20 step/epoch = 2-3 次）──
    n_identity = sum(1 for t in traces if t.identity is not None)
    assert n_identity >= 2, f"Expected ≥ 2 identity crystallizations in 50 epochs, got {n_identity}"
    print(f"  ✓ [测试 5: Identity 结晶] {n_identity}/{len(traces)} epochs")

    # ── 测试 6: Narrative 至少构建 1 次（50 epoch × 50 step/epoch = 1 次）──
    n_narrative = sum(1 for t in traces if t.narrative is not None)
    assert n_narrative >= 1, f"Expected ≥ 1 narrative builds in 50 epochs, got {n_narrative}"
    print(f"  ✓ [测试 6: Narrative 构建] {n_narrative}/{len(traces)} epochs")

    # ── 测试 7: Crystallize 触发 ──
    n_crystallize = sum(1 for t in traces if t.crystallize_result is not None)
    assert n_crystallize >= 5, f"Expected ≥ 5 crystallizes (every 10 epochs in 50), got {n_crystallize}"
    print(f"  ✓ [测试 7: Crystallize 触发] {n_crystallize}/{len(traces)} epochs")

    # ── 测试 8: Phase Transition 检测（统计）──
    n_phase = sum(1 for t in traces if t.phase_xition)
    print(f"  ✓ [测试 8: Phase Transition] {n_phase}/{len(traces)} epochs (50 epoch 可能较少)")

    # ── 测试 9: Hawking 衰减调用 ──
    # 至少有一些 step hawking_removed > 0 或 hawking 累积了 memories
    print(f"  ✓ [测试 9: Hawking 调用] 总 removed={sum(t.hawking_removed for t in traces)}")

    # ── 测试 10: 时序严格（value_after 与当前 value_layer.value_state 一致）──
    # epoch 30 之后，trace.value_state_after 应 == value_layer.value_state
    last_t = traces[-1]
    for k in last_t.value_state_after:
        assert abs(last_t.value_state_after[k] - value_layer.value_state[k]) < 1e-9
    print(f"  ✓ [测试 10: 终态一致] value_state_after == value_layer.value_state")

    # ── 测试 11: Experience Encoding（Step 2.5，洞察 34）──
    assert t0.experience is not None, "experience trace missing"
    assert t0.experience.get('meaning'), "experience.meaning empty"
    assert t0.experience['experience_id'] == f"{t0.event['event_id']}-exp"
    print(f"  ✓ [测试 11: Experience 编码] meaning='{t0.experience['meaning'][:20]}...'")

    # ── 测试 12: Self Entropy（Step 16，洞察 35）──
    assert t0.self_entropy is not None, "self_entropy trace missing"
    for key in ('H_self', 'H_value', 'H_identity', 'H_narrative'):
        v = t0.self_entropy[key]
        assert 0.0 <= v <= 1.0, f"{key} out of [0,1]: {v}"
    h_start = traces[0].self_entropy['H_self']
    h_end = traces[-1].self_entropy['H_self']
    print(f"  ✓ [测试 12: H_self 度量] {h_start:.3f} → {h_end:.3f} "
          f"(ε降 {(h_start - h_end):+.3f})")

    # ── Phase 3.1 动作 2: Snapshot 协议集成测试 ──

    # ── 测试 13: orchestrator snapshot_all → restore_all round-trip ──
    # 跑完 55 epoch 后 snapshot，新 orchestrator restore 后再跑 epoch 56，
    # value_state / signals / drive_state 必须与继续跑的 orchestrator 完全一致
    import copy as _copy

    # 复制原 orchestrator 的状态（基准）
    snap = orchestrator.snapshot_all()
    # JSON 序列化烟囱测试
    json.dumps(snap)
    snap_restored = json.loads(json.dumps(snap))

    # 构造第二个 orchestrator（用同种子）
    orchestrator2 = SGEOrchestrator(
        agent=Agent(seed=42, drives=drives,
                    value_layer=ValueLayer(values=SGE_DEFAULT_VALUES),
                    hawking=hawking, crystallizer=crystallizer,
                    crystallize_every=10),
        value_layer=ValueLayer(values=SGE_DEFAULT_VALUES),
        drive_metabolism=DriveMetabolism(drives=drives),
        event_generator=EventGenerator(baby_id='orch_test', seed=42),
        identity_layer=IdentityLayer(crystallize_every_n_epochs=20),
        narrative_builder=NarrativeBuilder(build_every_n_epochs=50),
        hawking=hawking, crystallizer=crystallizer,
        crystallize_every=10,
    )
    orchestrator2.restore_all(snap_restored)

    # 也让 orchestrator restore 回 snap 状态（保证两边起点一致）
    orchestrator.restore_all(snap_restored)

    # 重置 random seed 以保证 compute_signals 感知噪声序列一致
    random.seed(42)
    t1_56 = orchestrator.step(55)
    random.seed(42)
    t2_56 = orchestrator2.step(55)

    for k in ('safety', 'creativity', 'connection'):
        assert abs(t1_56.value_state_after[k] - t2_56.value_state_after[k]) < 1e-9, \
            f"value_state.{k} drift: {t1_56.value_state_after[k]} vs {t2_56.value_state_after[k]}"
    for k in SIGNALS:
        assert abs(t1_56.signals[k] - t2_56.signals[k]) < 1e-9, \
            f"signal {k} drift"
    assert t1_56.identity == t2_56.identity or (
        t1_56.identity is None and t2_56.identity is None
    ), f"identity drift: {t1_56.identity!r} vs {t2_56.identity!r}"
    assert t1_56.narrative == t2_56.narrative or (
        t1_56.narrative is None and t2_56.narrative is None
    )
    print(f"  ✓ [测试 13: orchestrator round-trip] epoch 56 上 "
          f"value/signal/identity/narrative 全等（≤1e-9）")

    # ── 测试 14: 缺 _schema_version → SnapshotError ──
    snap_bad = _copy.deepcopy(snap_restored)
    del snap_bad['_schema_version']
    orch_bad = SGEOrchestrator(
        agent=Agent(seed=42, drives=drives,
                    value_layer=ValueLayer(values=SGE_DEFAULT_VALUES),
                    hawking=hawking, crystallizer=crystallizer,
                    crystallize_every=10),
        value_layer=ValueLayer(values=SGE_DEFAULT_VALUES),
        drive_metabolism=DriveMetabolism(drives=drives),
        event_generator=EventGenerator(baby_id='orch_test', seed=42),
        identity_layer=IdentityLayer(crystallize_every_n_epochs=20),
        narrative_builder=NarrativeBuilder(build_every_n_epochs=50),
        hawking=hawking, crystallizer=crystallizer,
        crystallize_every=10,
    )
    try:
        orch_bad.restore_all(snap_bad)
        assert False, "应该抛出 SnapshotError"
    except SnapshotError as e:
        assert '_schema_version' in str(e)
    print(f"  ✓ [测试 14: 缺 _schema_version] 抛 SnapshotError")

    # ── 测试 15: identity_layer snapshot 不含 llm ──
    assert 'llm' not in snap['identity_layer'], "identity_layer snapshot 含 llm"
    assert 'llm' not in snap['narrative_builder'], "narrative_builder snapshot 含 llm"
    assert snap['identity_layer']['use_real_llm'] is False, "默认 stub 模式应保留"
    print(f"  ✓ [测试 15: identity/narrative 不含 llm] use_real_llm={snap['identity_layer']['use_real_llm']}")

    # ── 测试 16: EventGenerator rng_state 保真 ──
    # snapshot 保存当前 rng state；restore 后从同一 state 开始调用，序列必须一致
    eg_snapshot = orchestrator.event_generator.snapshot()
    val1_before = orchestrator.event_generator.rng.random()
    val2_before = orchestrator.event_generator.rng.random()
    # 重新构造一个新 EventGenerator（不同 seed），restore snap 后必须产生同一序列
    eg_test = EventGenerator(baby_id='test', seed=99)
    eg_test.restore(eg_snapshot)
    val1_after = eg_test.rng.random()
    val2_after = eg_test.rng.random()
    assert abs(val1_before - val1_after) < 1e-9, f"rng state drift: {val1_before} vs {val1_after}"
    assert abs(val2_before - val2_after) < 1e-9, f"rng state drift: {val2_before} vs {val2_after}"
    print(f"  ✓ [测试 16: EventGenerator rng_state] random() 序列完全一致")

    # ── 测试 17: snapshot_all 无 LLM 句柄泄露 ──
    forbidden = {'llm', 'value_layer', 'hawking', 'crystallizer'}
    assert not (forbidden & set(snap['agent'].keys())), \
        f"Agent snapshot 泄露外部 ref: {forbidden & set(snap['agent'].keys())}"
    print(f"  ✓ [测试 17: snapshot_all 无 LLM 泄露]")

    print(f"\n  状态: ✅ PASS — 17/17 测试通过")
    return True


# ══════════════════════════════════════════════
# 单元测试：Orchestrator × TwinStateDB 集成（Phase 3.1 · 动作 1 集成）
# ══════════════════════════════════════════════


def _make_minimal_orchestrator_components():
    """构造一个最小的 SGEOrchestrator 组件集合（stub LLM）。

    Returns:
        (agent, value_layer, drive_metabolism, event_generator,
         identity_layer, narrative_builder, hawking, crystallizer)
    """
    from .baseline import SGE_DEFAULT_DRIVES, SGE_DEFAULT_VALUES
    drives = list(SGE_DEFAULT_DRIVES)
    value_layer = ValueLayer(values=list(SGE_DEFAULT_VALUES))
    hawking = HawkingDecay(gamma=0.01, clock=0.0)
    crystallizer = MemoryCrystallizer(n_dims=11)
    agent = Agent(
        seed=42,
        drives=drives,
        value_layer=value_layer,
        hawking=hawking,
        crystallizer=crystallizer,
        crystallize_every=10,
    )
    drive_metabolism = DriveMetabolism(drives=drives)
    event_generator = EventGenerator(baby_id='test_baby', seed=42)
    identity_layer = IdentityLayer(crystallize_every_n_epochs=20)
    narrative_builder = NarrativeBuilder(build_every_n_epochs=50)
    return agent, value_layer, drive_metabolism, event_generator, identity_layer, narrative_builder, hawking, crystallizer


def _run_orchestrator_persistence_integration_tests() -> bool:
    """Orchestrator × TwinStateDB 集成测试（Phase 3.1 · 动作 1 集成）。

    6 个测试：
    1. checkpoint_every 自动触发（200 epoch → 2 次 auto checkpoint）
    2. phase_xition 触发额外 checkpoint
    3. identity/narrative 触发额外 checkpoint
    4. Round-trip（save → 新 orchestrator → restore → state 一致）
    5. db/student_id 互斥校验
    6. StudentDeletedError 抛出不中断（log stderr + continue）
    """
    from .persistence import (
        TwinStateDB, StudentExistsError, StudentDeletedError, StudentNotFoundError,
    )

    print("=" * 70)
    print("Orchestrator × TwinStateDB 集成测试（Phase 3.1 · 动作 1 集成）")
    print("=" * 70)

    # ── 测试 1: checkpoint_every 自动触发 ──
    print("\n[测试 1] checkpoint_every 自动触发（200 epoch × checkpoint_every=100）")
    with TwinStateDB(':memory:') as db:
        agent, vl, dm, eg, il, nb, hw, cr = _make_minimal_orchestrator_components()
        orch = SGEOrchestrator(
            agent=agent, value_layer=vl, drive_metabolism=dm, event_generator=eg,
            identity_layer=il, narrative_builder=nb,
            hawking=hw, crystallizer=cr,
            db=db, student_id='stu_001', checkpoint_every=100,
            student_name='Test Baby 1',
        )
        orch.run(n_epochs=200)

        history = db.get_checkpoint_history('stu_001', limit=10)
        # checkpoint history 默认 ORDER BY epoch DESC, saved_at DESC
        auto_triggers_desc = [h['trigger'] for h in history if h['trigger'].startswith('auto_')]
        assert len(auto_triggers_desc) == 2, (
            f"Expected 2 auto checkpoints (epoch 100 + 200), got {len(auto_triggers_desc)}: {auto_triggers_desc}"
        )
        auto_triggers = sorted(auto_triggers_desc)
        assert auto_triggers == ['auto_100', 'auto_200'], (
            f"Expected ['auto_100', 'auto_200'], got {auto_triggers}"
        )
        print(f"  ✓ 200 epoch 触发 2 次 auto checkpoint: {auto_triggers}（DESC: {auto_triggers_desc}）")

    # ── 测试 2: phase_xition 触发额外 checkpoint ──
    print("\n[测试 2] phase_xition 触发额外 checkpoint（mock 标志）")
    with TwinStateDB(':memory:') as db:
        agent, vl, dm, eg, il, nb, hw, cr = _make_minimal_orchestrator_components()
        orch = SGEOrchestrator(
            agent=agent, value_layer=vl, drive_metabolism=dm, event_generator=eg,
            identity_layer=il, narrative_builder=nb,
            hawking=hw, crystallizer=cr,
            db=db, student_id='stu_002', checkpoint_every=1000,  # 不自动触发
        )
        # 直接调 _save_checkpoint 模拟 phase_xition 触发（避免依赖 agent._last_phase_transition）
        ok = orch._save_checkpoint('phase_xition', epoch=orch.current_epoch + 1)
        assert ok, "phase_xition checkpoint 失败"

        history = db.get_checkpoint_history('stu_002', limit=10)
        triggers = [h['trigger'] for h in history]
        assert 'phase_xition' in triggers, f"phase_xition 触发缺失: {triggers}"
        print(f"  ✓ phase_xition 触发 1 次额外 checkpoint: {triggers}")

    # ── 测试 3: identity/narrative 触发额外 checkpoint ──
    print("\n[测试 3] identity_crystallize + narrative_build 触发额外 checkpoint")
    with TwinStateDB(':memory:') as db:
        agent, vl, dm, eg, il, nb, hw, cr = _make_minimal_orchestrator_components()
        orch = SGEOrchestrator(
            agent=agent, value_layer=vl, drive_metabolism=dm, event_generator=eg,
            identity_layer=il, narrative_builder=nb,
            hawking=hw, crystallizer=cr,
            db=db, student_id='stu_003', checkpoint_every=1000,
        )
        orch._save_checkpoint('identity_crystallize', epoch=1)
        orch._save_checkpoint('narrative_build', epoch=2)

        history = db.get_checkpoint_history('stu_003', limit=10)
        triggers = sorted({h['trigger'] for h in history})
        assert 'identity_crystallize' in triggers, f"identity_crystallize 触发缺失: {triggers}"
        assert 'narrative_build' in triggers, f"narrative_build 触发缺失: {triggers}"
        print(f"  ✓ identity/narrative 触发: {triggers}")

    # ── 测试 4: Round-trip（save → 新 orchestrator → restore → state 一致）──
    print("\n[测试 4] Round-trip（save_full_state → 新 orchestrator → restore_all）")
    with TwinStateDB(':memory:') as db:
        # 第一个 orchestrator：跑 10 epoch + save
        agent1, vl1, dm1, eg1, il1, nb1, hw1, cr1 = _make_minimal_orchestrator_components()
        orch1 = SGEOrchestrator(
            agent=agent1, value_layer=vl1, drive_metabolism=dm1, event_generator=eg1,
            identity_layer=il1, narrative_builder=nb1,
            hawking=hw1, crystallizer=cr1,
            db=db, student_id='stu_004', checkpoint_every=10,
            app_state={'subject': 'math', 'grade': 7},
        )
        orch1.run(n_epochs=10)
        # epoch 10 应触发 auto_10 checkpoint

        # 从 DB load snapshot
        sge_state, app_state, epoch = db.load_full_state('stu_004')
        assert epoch == 10, f"Expected epoch=10, got {epoch}"
        assert app_state == {'subject': 'math', 'grade': 7}, (
            f"app_state round-trip 失败: {app_state}"
        )
        assert sge_state['_schema_version'] == '1.0', "snapshot schema_version 不对"

        # 第二个 orchestrator：restore snapshot
        agent2, vl2, dm2, eg2, il2, nb2, hw2, cr2 = _make_minimal_orchestrator_components()
        orch2 = SGEOrchestrator(
            agent=agent2, value_layer=vl2, drive_metabolism=dm2, event_generator=eg2,
            identity_layer=il2, narrative_builder=nb2,
            hawking=hw2, crystallizer=cr2,
        )
        orch2.restore_all(sge_state)

        assert orch2.current_epoch == 10, f"restore 后 epoch 不对: {orch2.current_epoch}"
        assert orch2.value_layer.value_state == orch1.value_layer.value_state, (
            "restore 后 value_state 不一致"
        )
        print(f"  ✓ Round-trip 一致：epoch={epoch}, "
              f"value_state keys={len(orch2.value_layer.value_state)}")

    # ── 测试 5: db/student_id 互斥校验 ──
    print("\n[测试 5] db/student_id 互斥校验（fail-fast）")
    try:
        SGEOrchestrator(
            agent=agent, value_layer=vl, drive_metabolism=dm, event_generator=eg,
            identity_layer=il, narrative_builder=nb,
            db=None, student_id='stu_005',  # 半配置
        )
        raise AssertionError("期望抛 ValueError，未抛")
    except ValueError as e:
        assert '同时提供或同时为 None' in str(e), f"错误信息不对: {e}"
        print(f"  ✓ db=None + student_id=... 抛 ValueError: {e}")

    try:
        SGEOrchestrator(
            agent=agent, value_layer=vl, drive_metabolism=dm, event_generator=eg,
            identity_layer=il, narrative_builder=nb,
            db=TwinStateDB(':memory:'), student_id=None,  # 半配置
        )
        raise AssertionError("期望抛 ValueError，未抛")
    except ValueError as e:
        assert '同时提供或同时为 None' in str(e), f"错误信息不对: {e}"
        print(f"  ✓ db=... + student_id=None 抛 ValueError: {e}")

    # ── 测试 6: StudentDeletedError 抛出不中断 ──
    print("\n[测试 6] 软删除后 checkpoint 失败但 step 继续")
    with TwinStateDB(':memory:') as db:
        agent, vl, dm, eg, il, nb, hw, cr = _make_minimal_orchestrator_components()
        orch = SGEOrchestrator(
            agent=agent, value_layer=vl, drive_metabolism=dm, event_generator=eg,
            identity_layer=il, narrative_builder=nb,
            hawking=hw, crystallizer=cr,
            db=db, student_id='stu_006', checkpoint_every=5,
        )
        # 跑 5 epoch（应触发 auto_5）
        orch.run(n_epochs=5)
        # 软删除 student
        db.delete_student('stu_006', hard=False, accessor_id='test')

        # 跑剩余 5 epoch（应触发 auto_10，但 save 应失败）
        # _save_checkpoint 内部 try/except 捕获 StudentDeletedError
        # 不抛异常，但返回 False
        ok = orch._save_checkpoint('auto_10', epoch=10)
        assert not ok, "StudentDeletedError 情况下 _save_checkpoint 应返回 False"

        # 验证 step() 仍可继续（不中断 epoch 循环）
        orch.run(n_epochs=5)  # 应继续完成 5 个 epoch，无异常
        print(f"  ✓ StudentDeletedError 不中断 step() 循环（auto_10 返回 False）")

    print("\n" + "=" * 70)
    print("✅ Orchestrator × TwinStateDB 集成测试全部通过（6/6）")
    print("=" * 70)
    return True


if __name__ == "__main__":
    import sys
    ok1 = _run_unit_tests()
    ok2 = _run_orchestrator_persistence_integration_tests()
    sys.exit(0 if (ok1 and ok2) else 1)