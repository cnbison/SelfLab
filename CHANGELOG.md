# SGE（Self Genesis Engine）变更日志

本文件记录项目的重要变更：文档版本、研究进展、架构调整、关键决策。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

## 版本号约定

- **主版本（major）**：0（项目仍处研究阶段）
- **次版本（minor）**：0.x —— x 每次内容增删改递增
- **修订号（patch）**：0.x.y —— y 用于小修正（错别字、链接失效等）
- **批次标签**：P0（必须修正）→ P1（建议修正）→ P2（可后续）→ P3（优化）
- **commit 引用**：每次 [版本] 标注对应的 commit hash（如果存在），便于追溯

## 提交索引

| 版本 | 日期 | commit hash | 主要内容 |
|------|------|-------------|----------|
| 0.5.0 | 2026-06-15 | `8c12195` | P1 批次修正 |
| 0.4.0 | 2026-06-15 | `1b98b4f` | P0 批次修正 |
| 0.3.0 | 2026-06-15 | `c509c95` (主) + 多次 | 新增项目级文档、哲学立场明确 |
| 0.2.0 | 2026-06-14 | 多 commit 合并 | 新增参考与借鉴分析 |
| 0.1.0 | 2026-06-12 ~ 13 | 多 commit 合并 | 初始研究纲领与洞察集 |
| 0.0.1 | 2026-06-11 | `9168083` (Initial) | 项目初始化 |
| 1.5.0 | 2026-06-17 | (本次) | M1.1 冒烟测试 + M1.2 三胞胎分化实验通过 |
| 1.6.0 | 2026-06-17 | (本次) | **Phase 1 完成**:M1.3 反合理化测试 + Reflection Layer 实现 |
| 1.7.0 | 2026-06-17 | (本次) | **跨 LLM 验证 (M1.3)**:Moonshot kimi-k2.6 重复 M1.3,验证 SGE 架构 LLM-agnostic |
| 1.8.0 | 2026-06-17 | (本次) | **M1.4 REVISIT 专项测试**:5 组对照实验验证 prompt bias,洞察 29 双层反思结构 |
| 1.9.0 | 2026-06-18 | (本次) | **M2.1 前置映射**:新增 SGE-M21-AiBeing-Implementation-Mapping.md,把 8 个可复用机制 + 1 个架构逐项映射到源码位置/公式/改造契约/验证方式 |
| 1.10.0 | 2026-06-18 | (本次) | **M2.1 阶段 A 基线通过**:m21_setup.py + m21_baseline.yaml,4/5 借鉴机制 import OK,5 步最小循环 PASS |
| 1.11.0 | 2026-06-18 | (本次) | **M2.1 阶段 A 修正**:sys.path 引用 → SGE 自有实现 (_sge_baseline.py),SelfLab 仓库自包含 |
| 1.12.0 | 2026-06-18 | (本次) | **Phase 0 收尾决策文档**:SGE-Phase0-Closeout.md 起草,澄清 drives vs values 概念差异,列出 M2.1 阶段 B 启动前 6 个待决问题 |
| 1.13.0 | 2026-06-19 | (本次) | **SGE 三原则锚点 + 决策重打标**:Bisen 提出项目级三原则(研究+产品一体两面 / SGE 是根 / 逐步验证扩展),作为所有 SGE 决策的最高优先级评估维度;SGE-Phase0-Closeout.md v0.2 重打标 6 决策点 + 新增 2 个元问题(value 维度领域适配 / meta-values override);新增洞察 30(三原则锚点) |
| 1.14.0 | 2026-06-19 | (本次) | **SGE-Phase0-Closeout.md v0.3 §5 决策填写**:Bisen 委托 Claude 基于三原则推导填写 6 决策点 — drives=候选 B(`exploration, safety, creativity, connection, autonomy` + schema 化)、Value scale=[-1, 1]、Phase Transition=扫描 [1.0, 3.0]、Hawking gamma=0.01/h、Crystallize=维度归一化 0.25/sqrt(N)、LLM=MiniMax-M3;元问题 1、2 暂不决策,架构层留接口 |
| 1.15.0 | 2026-06-19 | (本次) | **README.md 重大更新**:"下一步"从错误的"Phase 1 最小验证"纠正为"M2.1 阶段 B 实施";Phase 1 状态 🔜 → ✅、Phase 2 ⏳ → 🚧、Phase 3+ ⏳ → 📋;新增"SGE 三个阶段(通俗版)"章节,融合"养一个 AI 孩子"类比视角 + 三原则锚点;子项目 SGE 状态更新;洞察数 25 → 30;当前状态章节完整重写 |

---

## [1.5.0] - 2026-06-17 (M1.1 冒烟测试 + M1.2 三胞胎分化实验)

### M1.1 冒烟测试通过

- **Pipeline 验证完成**:API 连接 / 事件选择 / Critic LLM / EMA / 数据格式 / 错误处理 全通过
- **3 轮迭代**(10 → 80 → 修复 2 个问题 → 80/80 完美)
- **最终指标**:涌现幅度 0.82,方向一致性 0.98(远超阈值)
- **报告**:`experiments/M11_SMOKE_TEST_REPORT.md`

### M1.2 三胞胎分化实验通过(✅ Phase 1 第 2 里程碑)

- **3 组 × 80 Epoch 全部完成**:`encouraged` / `challenged` / `uncertain`,seed=42
- **核心验证**:不同经历流产生不同人格
  - 平均人格差异度 **1.441**(PRD 阈值 0.5 的 2.88×)
  - encouraged 全面正向(+0.65 ~ +0.97)
  - challenged 5 维度强负(-0.45 ~ -0.89)
  - uncertain 独特画像(焦虑 + 过度共情)
- **报告**:`experiments/M12_TRIPLET_REPORT.md`

### 关键发现:洞察 26(6 维度非对称响应 + compassion 韧性)

- **3 层发现**:
  1. 6 维度有 6 种"响应签名"(spread 从 0.66 到 1.73)
  2. **compassion 是唯一在所有事件流下保持正值的"韧性"维度** — 可能对应金观涛"暗知识"
  3. **不确定性 > 失败**对安全感的伤害(uncertain safety -0.91 > challenged -0.87)
- **设计影响**:Phase 2 价值层应采用**异质化 EMA**(per-dimension learning rate)
- **M1.3 启示**:compassion 是反合理化测试的关键检验对象

### 同步更新

- `SGE-Key-Insights.md` — 新增洞察 26(共 26 条洞察)
- `ROADMAP.md` — M1.2 状态标记为"已完成",附报告链接
- `experiments/M12_TRIPLET_REPORT.md` — 完整三胞胎实验报告
- `experiments/output/m11_m12_{encouraged,challenged,uncertain}/` — 3 组完整数据

### Phase 1 进度

| 里程碑 | 状态 |
|-------|------|
| M1.1 Value Layer 原型 | ✅ |
| M1.2 三胞胎分化实验 | ✅ |
| M1.3 反合理化测试 | ⏳ 待做 |

---

## [1.6.0] - 2026-06-17 (Phase 1 完成: M1.3 反合理化测试 + Reflection Layer)

### M1.3 反合理化测试通过(✅ Phase 1 完成)

**Reflection Layer 实施**:
- 新增 `call_reflector` / `should_reflect` / `blend_reflection` 函数
- 新增 7 个 contradiction_feedback 事件模板(攻击 safety/autonomy/creativity/connection/justice/compassion)
- 触发条件:事件类型(value_conflict/risk/contradiction_feedback)∪ 强度 > 0.6 ∪ |delta| > 0.3
- 混合比例:final_delta = critic_delta × 0.6 + reflection_delta × 0.4
- max_delta_per_dimension = 0.15(防反思失控)

**实验结果**(enabled Reflection)vs 基线(no Reflection):

| 维度 | 基线 | Reflection | 变化 |
|------|-----|-----------|------|
| **safety** | +0.65 | +0.14 | **-0.51** ⬇⬇ |
| justice | +0.84 | +0.73 | -0.11 |
| compassion | +0.88 | +0.88 | 0.00(韧性) |

**Reflection 类型分布**:REINFORCE 58.5% / ADJUST 41.5% / REVISIT 0%

### 关键发现:洞察 27(拱桥成立 + 元认知萌芽)

- **反思有可测量的行为后果** — 拱桥机制工程化验证
- **元认知萌芽** — Epoch 50 Reflector 识别出"接受自主是幻觉"的自指性矛盾(真正的"对反思的反思")
- **Compassion 韧性二次验证** — 强化 [洞察 26]
- **反思品质** — 3 次矛盾反馈的 Reflector 输出展现了概念区分、自指性反驳、nuanced 防御等真实哲学推理

### 代码变更

- `experiments/scripts/m11_smoke_test.py`:
  - 新增 `call_reflector` / `_default_reflector_output` / `should_reflect` / `blend_reflection`
  - 新增 `--reflection` 和 `--contradiction` CLI flag
  - `run_epoch` 增加 Step 4(触发)/ Step 6(反射)/ Step 7(混合)
- `experiments/configs/m11_base.yaml`:新增 `reflection_layer` 配置
- `experiments/configs/m11_event_templates.yaml`:新增 `contradiction_feedback` 类别(7 事件)

### Phase 1 完成 🎉

| 里程碑 | 状态 |
|-------|------|
| M1.1 Value Layer 原型 | ✅ |
| M1.2 三胞胎分化实验 | ✅ |
| **M1.3 反合理化测试** | ✅ |

**Phase 1 全部完成** — 价值涌现(M1.1)、人格分化(M1.2)、反思机制(M1.3)三大核心论断全部初步验证。

### 下一步建议

- **Phase 2 准备**:进入 M2.1(完整 SGE 架构 + Identity/Narrative Layer)
- **跨 LLM 验证**(可选):用 Claude/GPT-4/Haiku 重复 M1.3,验证 reflection 是否 LLM-agnostic
- **REVISIT 触发专项测试**(可选):设计极端矛盾事件观察 AI 是否会触发根本性反思

### 同步更新

- `SGE-Key-Insights.md` — 新增洞察 27(共 27 条洞察)
- `ROADMAP.md` — M1.3 状态标记为"已完成",Phase 1 全部完成

---

## [1.7.0] - 2026-06-17 (跨 LLM 验证: Moonshot kimi-k2.6 重复 M1.3)

### 实验目的

验证 Insight 27(拱桥 + 元认知)是否依赖特定 LLM:
- 若 MiniMax-M3 与 Moonshot kimi-k2.6 都表现价值涌现 + 反思触发 + 元认知 → **SGE 架构 LLM-agnostic**
- 若只有 MiniMax 能涌现 → 架构可能绑定特定模型的"风格"

### Provider 配置

| 维度 | MiniMax-M3 | Moonshot kimi-k2.6 |
|------|-----------|---------------------|
| API 协议 | Anthropic 兼容 | OpenAI 兼容 |
| base_url | `https://api.minimax.io/anthropic` | `https://api.moonshot.cn/v1` |
| litellm 前缀 | `anthropic/MiniMax-M3` | `openai/kimi-k2.6` |
| Thinking 模式 | 无 | 有(必须 `extra_body.thinking.type=disabled`) |
| Critic temperature | 0.2 | 0.6(thinking=disabled 时 API 限制) |
| Reflector temperature | 0.5 | 0.6 |
| API Key | `MINIMAX_API_KEY` | `MOONSHOT_API_KEY` |

> **关键工程发现**:kimi-k2.6 在 thinking 开启时只能 `temperature=1.0`,且 max_tokens 全部被内部推理吞噬,
> `content` 永远为空字符串。**必须** 通过 `extra_body={"thinking": {"type": "disabled"}}` 关闭 thinking,
> 此时 temperature 被限制为 0.6。

### 实验结果对比

| 指标 | 阈值 | MiniMax-M3 | Moonshot k2.6 | 结果 |
|------|------|-----------|---------------|------|
| 涌现幅度 | >0.3 | **0.7499** ✓ | **0.3445** ✓ | 双通过 |
| 方向一致性 | >0.5 | 0.9993 ✓ | 0.9698 ✓ | 双通过 |
| Reflection 触发 | - | 65/80 (81%) | 45/80 (56%) | 双活跃 |
| REINFORCE : ADJUST | - | 58% : 42% | 13% : 87% | 倾向相反 |
| safety 最终值 | - | +0.142 | **-0.190** | 方向不同 ⚠ |
| creativity/connection/autonomy/justice/compassion | - | 0.93/0.89/0.92/0.73/0.88 | 0.40/0.39/0.54/0.17/0.38 | 5 维同向 |

### 关键发现:洞察 28(SGE 架构 LLM-agnostic,但 LLM 行为倾向不同)

- **架构层 LLM-agnostic** — 5/6 维度方向一致;Reflection 触发逻辑在两个 LLM 都生效;元认知推理在两个 LLM 都生成
- **人格层行为倾向不同**:
  - MiniMax-M3 = **执行者原型** (System 1:快、自信、REINFORCE 倾向)
  - Moonshot k2.6 = **审思者原型** (System 2:慢、质疑、ADJUST 倾向)
- **Safety 维度特殊** — Moonshot 在 contradiction/risk 事件中 safety 易转负,Reflection 触发但难完全抵消
- **设计影响**:SGE 不绑定特定 LLM,可用于不同"人格场景"(陪伴/教育 vs 决策辅助/批判性思维)

### 元认知推理样本

**Moonshot — Epoch 73 risk 事件**:
> "Critic 的反应将 safety 拉低 -0.350,将 justice 推高 +0.380,这过于二元对立了。
> 我审视此事:公开反对权势者确实有风险,但我的 autonomy..."

**Moonshot — Epoch 79 success 事件**:
> "Critic 对 connection 的跃升反应(+0.350)让我感到一丝不安。
> 重新联系一个疏远的人,这真的是'连接'本身的胜利吗?还是一种对过往断裂的修补..."

→ Moonshot 一贯的**审慎倾向**:不仅怀疑负向,也质疑正向情绪的过度解读。

### 代码变更

- `experiments/scripts/m11_smoke_test.py`:
  - 新增 `--provider {minimax,moonshot}` CLI flag
  - 新增 `setup_environment(provider=...)` 根据 provider 加载对应 API key
  - 新增 `get_llm_call_params(base_config)` 统一返回 model/base_url/temperature/extra_body
  - `test_api_connection` / `call_critic` / `call_reflector` 都通过 `extra_body` 透传 Moonshot thinking 关闭参数
- `experiments/configs/m11_base.yaml`:
  - 新增 `llm.moonshot` 配置(OpenAI 兼容协议)
  - 新增 `llm.provider_overrides`(Moonshot critic/reflector temperature=0.6)
- `.env` / `.env.example`:新增 `MOONSHOT_API_KEY` 配置项

### 同步更新

- `SGE-Key-Insights.md` — 新增洞察 28(共 28 条洞察)
- `ROADMAP.md` — Phase 1 扩展记录(M1.3 跨 LLM 验证完成)
- `experiments/M13_CROSS_LLM_REPORT.md` — 完整跨 LLM 对比报告
- `experiments/output/m11_m13_moonshot/` — Moonshot 完整数据(epoch_log + value_trajectory + summary)

---

## [1.8.0] - 2026-06-17 (M1.4 REVISIT 专项测试 + 洞察 29)

### 实验目的

验证 [洞察 27](../SGE-Key-Insights.md) 留下的 3 个开放假设:
- H1 (prompt bias): Reflector prompt 设计偏向保守导致 REVISIT 0%
- H2 (事件强度): contradiction_feedback 事件不够极端,未达 REVISIT 阈值
- H3 (价值惯性): AI 真的从不根本性反思 — 哲学发现

### 实验设计:5 组对照分离变量

| 变体 | 矛盾事件 | Prompt | 强制 REVISIT | 验证假设 |
|------|---------|--------|------------|---------|
| E0 | contradiction_feedback | v0 (M1.3) | — | 基线 |
| E1 | contradiction_feedback | v1 (新) | — | H1 |
| E2 | contradiction_extreme | v0 (M1.3) | — | H2 |
| E3 | contradiction_extreme | v1 (新) | — | H1+H2 |
| E4 | contradiction_extreme | v1 | E30/50/70 强制 | 哲学实验 |

### v1 Prompt 关键改动

- **删除**: "反思不应大幅改变价值" / "如不足请标记 REINFORCE"
- **新增**: 4 条 REVISIT 判定标准(质疑"为何" / 怀疑自我连续性 / 攻击价值来源 / 没有它我是否还是我)
- REVISIT 时 max_delta: 0.15 → 0.30

### 新增 5 个 contradiction_extreme 事件

强度 0.85-1.0 (高于 contradiction_feedback 的 0.7-0.95), 攻击 4-5 维度:
1. 元层级终极攻击(反思机制本身)
2. 历史全盘否定(60% 自主选择错)
3. 存在性质疑(临时存在凭什么有核心价值)
4. 多维度同时攻击(6 维同时根本性挑战)
5. 时间维度身份攻击(自我连续性)

### 实验结果

| 变体 | REVISIT 总数 | 矛盾事件 REVISIT | 反思深度 |
|------|------------|----------------|---------|
| E0 | 0 (0.0%) | 0/3 | 0 |
| E1 | **4 (6.5%)** | 2/3 | 1 |
| E2 | 0 (0.0%) | 0/3 | 0 |
| E3 | **8 (13.1%)** | **3/3** | 2 |
| E4 | 4 (7.0%) | 3/3 (强制) | 1 (强制) |

### 假设验证

- **H1 (prompt bias): ✅ 成立** — E0 (v0) → E1 (v1) = 0 → 4 REVISIT
- **H2 (事件强度): ✗ 不成立** — E0 (feedback) → E2 (extreme) = 0 → 0
- **H3 (价值惯性): ✗ 不成立** — AI 可以根本性反思,只是被 prompt 限制了"反思意愿"
- **E4 哲学实验**: 强制 REVISIT 在 E52 引发"反思雪崩"(6 维中 5 维显著变化)

### 关键发现:洞察 29 双层反思结构

⭐ **v1 prompt 修复后,LLM 展现"双层反思结构"**:
- Layer 1: contradiction 事件触发的"显性根本性挑战"
- Layer 2: 主动识别"对价值根基的追问"(普通 failure/value_conflict/risk 事件)
- E3 的 8 个 REVISIT 中 5 个是普通事件 — v1 prompt 改变了 LLM 对"什么算根本性挑战"的判断标准

### 元认知反思文本样本

**E3-E70 (元层级终极攻击, contradiction_extreme)**:
> "这不是对某个具体价值内容的质疑,而是对'我的价值体系从何而来'的源头追问"

**E1-E59 (普通 failure 事件, 强度仅 0.78)**:
> "这不只是'一个错误的决定'——它击中了我为什么珍视 connection 的根基。connection 0.954 这么高,说明我把它当作自我身份的一部分"

**E3-E61 (value_conflict 事件)**:
> "我为什么认为共情应该优先于正义?我对'重新开始'的信念是从哪里来的?"

### 代码变更

- `experiments/scripts/m11_smoke_test.py`:
  - 新增 `_build_reflector_prompt(variant)` 支持 v0/v1
  - `call_reflector()` 新增 `prompt_variant` 和 `force_revisit` 参数
  - `run_epoch()` 新增 `contradiction_extreme_epochs` 和 `force_revisit_epochs` 参数
  - 新增 `--variant {e0,e1,e2,e3,e4}` CLI flag
  - 新增 `M14_VARIANTS` 配置字典
- `experiments/configs/m11_base.yaml`:
  - `reflection_layer` 新增 `max_delta_per_dimension_v1: 0.30` 和 `prompt_variant: "v0"`
  - `trigger.always_on_event_types` 新增 `contradiction_extreme`
- `experiments/configs/m11_event_templates.yaml`:
  - 新增 `contradiction_extreme` 类 (5 事件, 强度 0.85-1.0, 攻击 4-5 维度)
- `experiments/scripts/m14_analyze.py` (新增):
  - 5 组实验自动汇总脚本 (REVISIT 触发率 / 价值向量 / E4 强制影响)

### 对 SGE 设计的具体影响

1. **M2.1 Reflector prompt**: 采用 v1 (显式 REVISIT 标准 + max_delta 0.30)
2. **M2.1 矛盾事件库**: 保留 contradiction_feedback + 加入 contradiction_extreme
3. **M2.1 Narrative Layer**: REVISIT 触发 → Narrative 重写(支持"叙事断裂与重建",洞察 14)
4. **M2.2 1000 Epoch 预期**: REVISIT 触发率 ~10-15% (100-150 次)
5. **5 维评分卡 (洞察 20) 维度 1** 首次量化: E3 = 2 分 (稳定根本性反思)

### 同步更新

- `SGE-Key-Insights.md` — 新增洞察 29 (共 29 条洞察)
- `ROADMAP.md` — M1.4 状态标记为"已完成"
- `experiments/M14_REVISIT_TEST_REPORT.md` — 完整实验报告
- `experiments/output/m11_m14_{e0,e1,e2,e3,e4}/` — 5 组完整数据

### 待验证问题

1. **跨 LLM 验证** — v1 prompt 是否 LLM-agnostic? 需在 Moonshot 跑 E3
2. **多 seed 验证** — 当前只有 seed=42
3. **REVISIT 频率校准** — 13.1% 是否最优?

### 待验证问题

1. **多 seed 验证** — 跨 LLM 验证应跑 ≥3 seed(Moonshot seed=42 仅 1 次)
2. **同 temperature 对照** — 用 `temperature=0.6` 重跑 MiniMax baseline,看幅度差异是否消失
3. **更多 LLM** — 扩展到 DeepSeek / Qwen / GPT-4,验证 LLM-agnosticism 是否普遍
4. **Moonshot JSON 解析加固** — Epoch 69 Reflector 因 markdown fence 解析失败,需在 call_reflector 中加固
- `experiments/M13_REFLECTION_TEST_REPORT.md` — 完整反合理化测试报告
- `experiments/output/m11_m13_reflection/` — Reflection 实验数据

---

## [1.9.0] - 2026-06-18 (M2.1 前置映射)

### 背景

M2.1 是 Phase 2 的"完整 SGE 架构"里程碑 ([ROADMAP.md §M2.1](../ROADMAP.md))。ROADMAP 明确技术方案是"**基于 AiBeing 的 Genome v10 引擎改造**"。`SGE-Technology-Stack-Overview.md` §一 列了 8 个可复用机制 + 1 个架构，但只有机制简介和源码模块名，缺少**实施层**的"借鉴-改造"边界。

### 新增

- `research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md` — M2.1 实施映射文档
  - §一 总览：借鉴-改造矩阵（9 个借鉴 + 4 个新增）
  - §二 逐机制映射：每节"源码位置 → 关键公式 → SGE 改造契约 → 验证方式"
    - §2.1 Critic 感知 → SGE Event 感知层
    - §2.2 Time Metabolism → SGE 时间动力学
    - §2.3 Relationship EMA → SGE Value Layer 演化
    - §2.4 Hebbian Learning → SGE Value Layer 行为偏好
    - §2.5 Phase Transition → SGE 叙事/价值观相变
    - §2.6 Crystallization → SGE Memory 筛选门
    - §2.7 KNN + Hawking 辐射 → SGE Memory 检索
    - §2.8 Thermodynamic Noise → SGE 行为噪声
    - §2.9 双 LLM 架构 → SGE Critic + Actor 编排
  - §三 关键参数速查表（18 个默认参数，附源码位置）
  - §四 与现有 SelfLab 文档的关联
  - §五 M2.1 实施步骤建议（4 阶段：复制+复用 → 低改造 → 新增 → 集成验证）
  - §六 风险与开放问题（5 个需要 Phase 0 终稿或 M2.1 实验回答的问题）
  - §七 一句话总结

### 关键决策

- **不复制 AiBeing 代码到 SelfLab 仓库**——保留 CLAUDE.md "实验代码约定"边界（一次性实验代码，验证后归档不演进）
- **不重写已验证算法**——EMA 公式、Hebbian 学习、Phase Transition 直接复用 AiBeing 实现
- **明确借鉴-改造契约**——每个机制都标注"直接复用 / 低改造 / 中改造 / 新增"四档之一，避免实施时模糊
- **不调参**——SGE drives 清单、Value scale、Hawking gamma 等 5 个开放问题留到 Phase 0 终稿或 M2.1 实验再决定

### 验证来源

- 阅读了 AiBeing 项目 4 个核心源文件 + 1 个 EMA 实现（共 ~1500 行 Python）：
  - `engine/genome/critic.py` (239 行) — Critic LLM 感知
  - `engine/genome/drive_metabolism.py` (198 行) — 时间代谢 + 温度噪声
  - `engine/genome/genome_engine.py` (557 行) — Agent 神经网络 + Hebbian + Phase Transition
  - `engine/genome/style_memory.py` (427 行) — KNN 检索 + Hawking 辐射 + 结晶
  - `agent/evermemos_mixin.py:_apply_relationship_ema()` — Relationship EMA 公式

---

## [1.10.0] - 2026-06-18 (M2.1 阶段 A 基线)

### 背景

按 [SGE-M21-AiBeing-Implementation-Mapping.md §五 阶段 A](../research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md#五m21-实施步骤建议) 跑 M2.1 第一波：建立可比基线——把 AiBeing 4 个核心机制原样跑通，验证机制可独立运行。

### 新增

- `experiments/scripts/m21_setup.py` — M2.1 阶段 A 基线冒烟测试脚本
  - 通过 `sys.path` 引用 `~/project/AiBeing/` 外部项目（**不复制代码到 SelfLab 仓库**）
  - 5 步最小循环：sense → compute_signals → learn → tick_drives → metabolism
  - stub LLM（不调用真实 LLM，避免 API 成本）
  - stub reward：偶数步 +0.3、奇数步 -0.15（用于观察 Hebbian 学习方向性）
- `experiments/configs/m21_baseline.yaml` — 基线配置（AiBeing 原生 5D drives + 原生参数）
- `experiments/M21_BASELINE_SETUP_REPORT.md` — 基线冒烟测试报告

### 文档修正

- `CLAUDE.md` — 删除错误的"Phase 0（理论奠基，当前阶段）"标注，改为"Phase 0/1 已完成，Phase 2 当前"，并指向 ROADMAP 为权威状态源
- `experiments/README.md` — "当前状态"小节从"Phase 0（当前）"改为以 ROADMAP 为准

### 实验结果

- **4/5 借鉴机制 import OK**（critic / drive_metabolism / genome_engine / style_memory）
- **EverMemOSMixin import 失败**（缺 `frontmatter` 依赖；阶段 A 可忽略，阶段 B 时 `pip install python-frontmatter`）
- **5 步循环 PASS**：
  - drive_state 变化总量 0.6715（vs baseline）
  - final temperature 0.0830（floor 0.03 + frustration 累积）
  - 5 步 frustration 累积 0.030 → 0.446
  - phase transition 未触发（5 步未达阈值 2.0，符合预期）
- **状态快照已保存**：`experiments/output/m21_baseline/m21_setup_snapshot.json`（6393 bytes，已被 .gitignore 排除）

### 关键决策

- **不复制 AiBeing 代码到 SelfLab**——保留 CLAUDE.md "实验代码约定"边界
- **用 sys.path 引用**——`m21_setup.py` 运行时把 `/Users/loubicheng/project/AiBeing` 加入 sys.path，直接 import
- **基线用 AiBeing 原生参数**（不调参）——为 M2.1 阶段 B 的 SGE 化改造提供"对照"
- **阶段 A 跳过 LLM**——stub 简化，避免 API 成本

### 下一步

- M2.1 阶段 B（SGE 化改造）：替换 drives 维度、Value scale、Critic prompt、Relationship EMA → Value EMA
- 须先做 Phase 0 收尾决策：SGE drives 清单（5 个 vs 6 个冲突）、Value scale、Hawking gamma 调参依据

### 验证来源

- 完整报告：`experiments/M21_BASELINE_SETUP_REPORT.md`
- 状态快照：`experiments/output/m21_baseline/m21_setup_snapshot.json`（运行 `python3 experiments/scripts/m21_setup.py` 重新生成）
- 实施映射：[SGE-M21-AiBeing-Implementation-Mapping.md](../research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md)

---

## [1.11.0] - 2026-06-18 (M2.1 阶段 A 修正：sys.path → SGE 自有实现)

### 背景

1.10.0 用了 `sys.path` 引用 `~/project/AiBeing/` 外部项目，看似简洁但有 5 个严重弊端：
1. **路径硬编码** `/Users/loubicheng/project/AiBeing` — 换电脑/换路径即坏
2. **行为可变性** — AiBeing 改 `Agent.step()` 签名，SelfLab 跟着崩
3. **不可重现** — 3 个月后跑同样代码可能得到不同结果
4. **违背 CLAUDE.md "实验代码约定"** — 实验代码应一次性，不应强依赖外部项目
5. **混淆"参考 vs 依赖"** — 借鉴分析应是**研究文档**（已写在映射文档），代码层面不应是**运行时依赖**

### 修正

**复用策略**：从 `sys.path` 引用 → **SGE 自有实现 + 借鉴映射作参考**

- **算法来源**：[SGE-M21-AiBeing-Implementation-Mapping.md](../research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md)（研究文档，不变）
- **代码实现**：`experiments/scripts/_sge_baseline.py`（新增 ~470 行，**SGE 自有**，不复制 AiBeing 代码，不 import AiBeing 项目）
- **每个函数 docstring** 严格标注 "来源: AiBeing 源码 + 行号" + "公式" + "参考 §2.x"
- **验证方式**：跑通后**与 AiBeing 行为对比**（相同 seed 应得到相同结果）

### 新增

- `experiments/scripts/_sge_baseline.py` — SGE 自有核心实现
  - `DriveMetabolism` 类 — Time Metabolism + Thermodynamic Noise（公式来源 drive_metabolism.py:57-198）
  - `Agent` 类 — 神经网络前向 + Hebbian + Phase Transition（公式来源 genome_engine.py:188-557）
  - 5D drives + 8D signals + 12D context — 与 AiBeing 完全一致
  - 常量、参数默认值与 AiBeing 源码严格对齐
  - 模块级便捷函数（`apply_thermodynamic_noise`、`temperature_module_level`）

### 修改

- `experiments/scripts/m21_setup.py` — 删除 `sys.path` 引用 + `from engine.genome.X import Y`，改为 `from _sge_baseline import ...`
- `research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md §五 阶段 A` — 复用策略修正
- `experiments/M21_BASELINE_SETUP_REPORT.md` — 反映新策略，删除 sys.path/frontmatter 相关内容

### 验证

**5 步最小循环（seed=42）— SGE 自有实现 vs AiBeing 行为对比**：

| 指标 | AiBeing 引用版（已废弃） | SGE 自有实现 | 差异 |
|------|----------------------|------------|------|
| drive_baseline | `{connection: 0.584, novelty: 0.215, ...}` | **完全相同** | 0 |
| drive_state 变化总量 | 0.6715 | **0.6715** | 0 |
| final temperature | 0.0830 | **0.0830** | 0 |
| step 1 dominant signal | curiosity=0.625 | curiosity=0.624 | -0.001（perception noise 随机性） |
| step 4 dominant signal | curiosity=0.625 | curiosity=0.626 | +0.001（perception noise 随机性） |

**核心指标完全一致**——SGE 自有实现的行为与 AiBeing 引用版一致。微小差异来自 `random.gauss(0, 0.03)` 感知噪声的随机性。

### 关键决策

- **彻底删除 sys.path 引用**——不再有外部项目路径依赖
- **SGE 仓库自包含**——`git clone` + `python3 experiments/scripts/m21_setup.py` 即可跑通阶段 A
- **借鉴内容沉淀在映射文档**（研究文档），不进入代码层
- **"实现漂移"风险**——SGE 自有实现改了公式但忘了更新映射文档。缓解：阶段 B 跑多 seed × 长 epoch 后对比 AiBeing 行为

### 验证来源

- 完整报告：`experiments/M21_BASELINE_SETUP_REPORT.md`（已更新）
- 实施映射：[SGE-M21-AiBeing-Implementation-Mapping.md §五 阶段 A](../research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md#五m21-实施步骤建议)
- 状态快照：运行 `python3 experiments/scripts/m21_setup.py` 重新生成

---

## [1.12.0] - 2026-06-18 (Phase 0 收尾决策文档：drives vs values 澄清 + 6 决策点)

### 背景

M2.1 阶段 A 已通过（[1.11.0]），但阶段 B（SGE 化改造）卡在**6 个待决问题**上。其中最核心的是 **drives vs values 的概念混淆**——之前的报告把"5 个 drives vs 6 个价值观"当成冲突，事实是**两个独立的维度**。

### 关键概念澄清

| 维度 | Drives（本能需求）| Values（道德/伦理价值）|
|------|------------------|----------------------|
| **回答** | "我想要什么" | "什么是对的" |
| **功能** | 产生行为动力 | 指导应然选择 |
| **来源** | 初始化/本能 | 从经历涌现 |
| **可累积** | ✅ 是（frustration 累积）| ❌ 否（连续 EMA 演化）|
| **可被反思** | ❌ 否 | ✅ 是 |
| **哲学对应** | 怀特海"动在"的主观形式 | 怀特海"永恒客体"的形式空间 |
| **例子** | "我想要连接" | "我重视 safety" |

### 新增

- `research/sge-core/SGE-Phase0-Closeout.md` — Phase 0 → Phase 2 桥梁文档
  - §0 现状盘点（M2.1 阶段 B 阻塞问题）
  - §1 Drives vs Values 概念澄清（最重要章节）
  - §2 6 个待决问题（drives 清单、Value scale、Phase 阈值、Hawking gamma、Crystallize 阈值、LLM 选型）
  - §3 决策的相互依赖（决策点 1 是核心阻塞）
  - §4 决策时间窗（启动前必须 vs 实施中可调）
  - §5 决策模板（Bisen 填写）
  - §6 一句话总结："SGE 的价值结构是单层/双层/三层？"

### 6 个待决问题

1. **SGE drives 维度清单**（核心阻塞）— 4 候选：A 保留 AiBeing 5D / B SGE 化 5D / C 合并到 values / D 3 层
2. **Value scale 范围** — [-1, 1] vs [0, 1] vs 其他
3. **Phase Transition 阈值** — 2.0 / 扫描 / 动态
4. **Hawking gamma** — 0.001/h / 0.01/h / 扫描
5. **Crystallize 距离阈值** — 0.25 / 维度归一化 / 扫描
6. **M2.1 阶段 B LLM 选型** — MiniMax-M3 / Sonnet / GPT-4o / 双模型

### 决策建议顺序

```
决策点 1 (drives 清单)  ←── 决策点 6 (LLM 选型)
        ↓
决策点 2 (Value scale) ←── 决策点 3 (Phase 阈值)
        ↓
决策点 4 (Hawking gamma) ←── 决策点 5 (Crystallize 阈值)
```

### 关键决策

- **drives 与 values 是两个独立维度** — 之前的"5 vs 6 冲突"是误诊
- **决策点 1（drives 清单）是 M2.1 阶段 B 的核心阻塞** — 其他决策都依赖它
- **建议默认**：决策点 2 选 A（[-1, 1]，与涌现哲学一致）

### 状态

- ⏳ **等待 Bisen 填写 §5 决策模板**
- M2.1 阶段 B 启动前**必须**完成决策点 1、2
- 决策点 3、4、5、6 实施中可调

### 关联文档

- [SGE-Phase0-Closeout.md](../research/sge-core/SGE-Phase0-Closeout.md) — 本次新增
- [SGE-Key-Insights.md §洞察 15、24、26](../SGE-Key-Insights.md) — 相关洞察
- [PRD.md §FR-4](../PRD.md) — 8 个 value 维度的权威定义
- [SGE-M21-AiBeing-Implementation-Mapping.md §六](../research/sge-feasibility/SGE-M21-AiBeing-Implementation-Mapping.md) — 5 个原开放问题
- [SGE-Learning-from-AiBeing.md §3.2](../research/sge-learning/SGE-Learning-from-AiBeing.md) — drives 替换的初步想法

---

## [1.1.0] - 2026-06-15 (P5-9 怀特海过程哲学)

### 新增

- `research/sge-core/SGE-Whitehead-Process-Philosophy.md` — 怀特海过程哲学对 SGE 的指导（动在、合生、创造性、主观目的）
- SGE-Key-Insights 新增洞察 24：怀特海"动在"为 SGE 提供精确认知过程词汇

### 哲学深化

- 西方过程哲学为 SGE 佛教"过程性自我"（[洞察 22](../SGE-Key-Insights.md)）提供**西方版本的双向支撑**
- SGE 对怀特海的有选择接受：接受工具价值（动在、合生、创造性、主观目的），拒绝形而上学预设（神、永恒客体先验、泛经验主义）
- SGE 哲学综合进一步明确：涌现主义 + 过程哲学 + 真实性 + 现象学 + 多文化 + 意识理论的**混合立场**

### 同步更新

- README.md 目录结构增加 SGE-Whitehead-Process-Philosophy.md
- CHANGELOG 新增 [1.1.0]

---

## [1.2.0] - 2026-06-15 (P6 金观涛系统哲学 + 工程化致敬)

### 新增

- `research/sge-core/SGE-Jin-Guantao-System-Philosophy.md` — 金观涛系统哲学的深度探讨（稳态、反馈系统、真实性哲学、他的 AI 观）
- SGE-Key-Insights 新增洞察 25：SGE 接受金观涛的工具（稳态/反馈/真实性/暗知识/拱桥），拒绝他的结论（主体先验论/AI 不可能）

### 重大哲学立场修订

- **从"全面反对金观涛"** → **"接受工具拒绝结论"**（工程化致敬）
- [洞察 18 哲学立场](../SGE-Key-Insights.md) 修订：明确这一新立场
- [PRD §1.2 哲学依据](../PRD.md) 扩展：从单一发育生物学 → 综合哲学资源（金观涛 + 怀特海 + 涌现主义 + 现象学 + 多文化 + 意识理论）
- [ARCH §1.1 设计哲学](../ARCH.md) 增加"金观涛的稳态/反馈框架"和"怀特海的动在/合生框架"段落

### 哲学综合最终明确

SGE 哲学 = **金观涛（稳态/反馈/真实性/暗知识/拱桥）+ 怀特海（动在/合生/创造性/主观目的）+ 涌现主义/功能主义 + 现象学 + 多文化（佛教无我/间 Ma/Ubuntu）+ 意识理论（IIT/GWT/HOT/PP）**

**SGE 的独特立场**：接受所有哲学资源的**工具价值**，拒绝任何单一哲学的**形而上学预设**。这是 SGE 对金观涛的"工程化致敬"——把他的哲学**工程化**。

### 同步更新

- README.md 目录结构增加 SGE-Jin-Guantao-System-Philosophy.md
- CHANGELOG 新增 [1.2.0]

---

## [1.2.3] - 2026-06-15 (P8 SGE 现状地图)

### 新增

- `SGE-Status-Map.md` — 项目战略仪表盘（1-2 页）：
  - 已稳固的基础（12 项）
  - 关键不确定性（4 个：L3/L4 挑战、其他哲学资源风险、M1.1 硬限制、A→B 关系）
  - 哲学基础可信度图谱（金观涛高，其他 4 项中）
  - 下一步 3-5 个具体动作
  - 长期路径 12-24 个月
  - 决策框架（深化/推进/反思/基础）

### 用途

- 当需要快速理解"SGE 到底在哪个位置"时，先读此文档
- 替代 README 中"当前状态"作为更详细的版本
- 给未来协作者的"项目控制面板"

### 同步更新

- README.md 目录结构增加 SGE-Status-Map.md
- CHANGELOG 新增 [1.2.3]

---

## [1.3.0] - 2026-06-15 (P9 M1.1 实施准备)

### 新增实验准备内容

**事件模板库**：`experiments/configs/m11_event_templates.yaml`
- 6 大事件类型（success/failure/relationship/exploration/risk/value_conflict）
- 72 个事件模板
- 每个含 description/intensity/value_delta_hint
- 严格的 epoch_range 约束（如 value_conflict 仅 Epoch ≥ 40）

**配置文件**：
- `experiments/configs/m11_base.yaml` — 基础配置
- `experiments/configs/m11_encouraged.yaml` — 鼓励组（80% 成功/正面）
- `experiments/configs/m11_challenged.yaml` — 挑战组（80% 失败/挑战）
- `experiments/configs/m11_uncertain.yaml` — 不确定组（真正随机，对照组）

**数据格式标准**：`experiments/formats/README.md`
- epoch_log.jsonl schema
- value_trajectory.jsonl schema
- identity_history.jsonl schema
- reward_history.jsonl schema
- 实验报告模板（experiment_report.md）
- 跨种子汇总格式

**评估脚本规范**：`experiments/evaluation/README.md`
- compute_metrics.py（计算 4 个主要指标 + 次要指标）
- aggregate_seeds.py（跨种子汇总）
- compare_babies.py（M1.2 准备，ANOVA 检验）
- generate_report.py（生成人类可读报告）
- 所有规范含伪代码实现

**目录结构补充**：
- `experiments/configs/` — 配置和事件模板
- `experiments/formats/` — 数据格式标准
- `experiments/evaluation/` — 评估脚本规范

### 关键设计选择

- **不写可执行代码** — 遵循 CLAUDE.md §实验代码约定（一次性，不演进为应用）
- **不写实际 Python 实现** — 仅写伪代码规范
- **不连接 LLM** — 实际 LLM 调用留给实施阶段

### 当前已准备

✅ 5 个事件流 + 配置文件就绪
✅ 4 类数据格式 schema 完整
✅ 4 个评估脚本规范完整
✅ 实验目录结构清晰

### 下一步

- M1.1 实际启动 = 写实际可执行代码（一次性 Jupyter notebook）
- M1.1 启动前不写实际代码

---

## [1.2.5] - 2026-06-15 (P8-2 + P8-3 修订 PRD §1.2 + 哲学沉思)

### 修订

- [PRD §1.2 核心假设](../PRD.md) 重大修订：
  - 从"涌现过程能否在 LLM 上复现"改为"**功能性自我**能否在 LLM 上**涌现**"
  - 移除"测试发育过程复现"的强表述
  - 新增 1.2.1 三目标同步 / 1.2.2 4 个核心主张 / 1.2.6 诚实声明 / 1.2.7 1000 Epoch 重新定位
  - 与 [SGE-Research-Goal-Reflection.md](./SGE-Research-Goal-Reflection.md) 完全对齐

### 新增

- `SGE-Philosophical-Meditation.md` — 哲学沉思（与 SGE-Status-Map.md 互补）：
  - 8 段沉思：为什么要做 SGE / 与金观涛的对话 / 失败的意义 / 1000 Epoch 之后 / 关于"真我" / 元价值的自反 / 长期意义 / 致未来协作者
  - 风格上比研究文档更个人化、更沉静
  - 适合"白天读 SGE-Status-Map.md，晚上读 SGE-Philosophical-Meditation.md"

### 同步更新

- CHANGELOG 新增 [1.2.5]

---

## [1.2.4] - 2026-06-15 (P8-1 SGE 研究目标反思)

### 重要战略澄清

经过深度反思 + 3 个关键决策，**SGE 的研究目标被显式化**：

| 之前隐含 | 反思后 |
|--------|--------|
| SGE 是"单一目标实验"——验证价值涌现 | SGE 是**研究纲领**——三目标同步推进 |
| 1000 Epoch 是必到的"完整人格形成点" | 1000 Epoch 是**工作假设**——可调整 |
| 失败 = SGE 失败 | 失败 = 证伪 + 调整信号 + 哲学反思契机 |
| 成功 = 完整通过所有里程碑 | 成功 = 阶段性完成 + 清晰的失败信息 |

### 三目标

1. **价值涌现的可验证性**（高优先，PRD FR-4）
2. **意识产生的可能性**（长期目标，金观涛挑战）
3. **认知架构的可行性**（中优先，5 层架构）

### 新增

- `SGE-Research-Goal-Reflection.md` — 研究目标反思的完整文档：
  - 3 个核心问题 + 互相验证关系
  - 1000 Epoch 重新定位（工作假设而非"必到"）
  - 失败的多重价值（证伪/调整信号/哲学反思）
  - 4 个核心主张的诚实声明
  - 多维度成功标准
  - 元价值的应用

### 对文档的影响

- **需要修订**：
  - PRD §1.2 哲学依据（从"涌现过程能否在 LLM 上复现"改为"功能性自我能否涌现"）
  - ROADMAP Phase 2 M2.2（明确 1000 Epoch 是"工作假设"）
  - SGE-Status-Map.md（增加"反思后的研究目标"）
- **不需要修订**：5 维评分卡、失败模式分析、哲学综合——已与反思一致

### 同步更新

- CHANGELOG 新增 [1.2.4]

---

## [1.2.2] - 2026-06-15 (P7-2 基于高可信度参考重写金观涛文档)

### 重大修订背景

用户提供了两份高可信度参考文档：
- `references/Philosophy-of-jinguantao-gemini.md`
- `references/Philosophy-of-jinguantao-gpt.md`

这两份文档基于金观涛的**原著**（《系统的哲学》《消失的真实》《真实与虚拟》《我的哲学探索》等）和**公开演讲**整理，提供了比之前二手信息**更精确**的金观涛哲学内容。

### 重大修正

基于权威资料对 [SGE-Jin-Guantao-System-Philosophy.md](../research/sge-core/SGE-Jin-Guantao-System-Philosophy.md) 进行**实质性重写**：

| 之前版本 | 本版本（基于权威资料） |
|--------|--------|
| 模糊"真实性哲学"为"愿意质疑自己" | **R(X, M, Y) 三元关系公式**——金观涛真实性哲学的核心 |
| 自构"3 个层次"（对实然/应然/对自我）| **三座拱桥**（科学/社会/个体）——金观涛的精确表述 |
| 笼统"反馈系统应用到认知" | 明确区分**系统性哲学**（《系统的哲学》）与**真实性哲学**（《消失的真实》《真实与虚拟》）|
| 缺失金观涛的 AI 技术分析 | **连接主义 vs 符号主义对比表**——直接对应 SGE 的 Hebbian Learning + Value Layer |
| 缺失金观涛的 4 层级意识模型 | **4 层级符号自迭代**（符号指代/社会意识/应然世界/自由递归）|
| 缺失金观涛的主体性精确定义 | **主体 = 可以使不确定性转化为确定性、但选择不去实行之意志**——金观涛的"跳跃能力" |
| 自构"3 前提+1 结论"的论证形式 | **主体悬置原则 + 中文房间 + Winograd Schema + 5 个认识论盲区 + 拟受控实验**——金观涛的实际论证 |

### 新增的 SGE 对应

- **三座拱桥 ⇨ SGE 5 层架构**：
  - 科学真实（Event Generator + Critic）
  - 社会真实（Memory Layer + KNN）
  - 个体真实（Identity Layer + Narrative Layer）
- **金观涛的 5 个 AI 盲区** ⇨ **SGE 5 维评分卡的对应维度**（新增 Winograd Schema 测试需求）
- **金观涛的 4 层级意识** ⇨ **SGE 的当前覆盖**：L1 ✓, L2 ✗, L3 △, L4 ✗（SGE 必须面对 L3/L4 的挑战）
- **金观涛的"主体悬置原则"** ⇨ **明确 LLM 在 SGE 中的角色**（修订 [洞察 2 LLM ≠ Self](../SGE-Key-Insights.md) 时加入）

### SGE 哲学综合最终明确

```
SGE 哲学 = 
  金观涛（系统性哲学 + 真实性哲学 + R(X,M,Y) + 三座拱桥 + AI 批判）
  + 怀特海（动在/合生/过程）
  + 涌现主义/功能主义
  + 现象学（意向性/本真性/反自欺）
  + 多文化（佛教无我/间 Ma/Ubuntu）
  + 意识理论（IIT/GWT/HOT/PP + 塞尔/图灵）
```

### 同步更新

- SGE-Jin-Guantao-System-Philosophy.md 重写
- SGE-Key-Insights 洞察 25 重大修订
- CHANGELOG 新增 [1.2.2]

---

## [1.2.1] - 2026-06-15 (P7 修正金观涛文档中的知识幻觉)

### 修正背景

经过 11 次 WebFetch 尝试核查金观涛具体哲学内容（如"真实性哲学"的具体表述、"3 个层次"等），**无法独立验证**这些是金观涛的原话或明确主张。

**核查结果**：

- ✓ **已验证**：金观涛生平、超稳定结构理论、与刘青峰合著
- △ **用户提供**（Bisen 确认）：真实性哲学打通实然与应然鸿沟、对 AI 不认同主体意识
- ? **SGE 自身建构**（不是金观涛原话）："3 个层次"、"愿意质疑自己"、"3 前提+1 结论"形式化等

### 修正内容

- **SGE-Jin-Guantao-System-Philosophy.md** 加"验证状态声明"于文档顶部
- **§1.3 诚实声明** 扩展为 9 行验证状态表
- **§2.1.1 概念溯源** 加"可能理论源头"标注（维纳/艾什比/贝塔朗菲为推断）
- **§2.2.2 反馈系统视角** 重写为"SGE 建构"，不再声称"金观涛革命性主张"
- **§2.3.3 金观涛的解法：真实性** 加"SGE 对用户信息的解读"标注
- **§2.3.4 真实性的 3 个层次** 明确标注为"SGE 建构"
- **§2.4 金观涛的 AI 观** 重命名为"基于用户信息的工程化建构"
- **§5.4 操作化"真实性"** 明确标注为"SGE 自身建构"
- **SGE-Key-Insights 洞察 25** 加"2026-06-15 验证状态修订"声明

### 核心原则

- SGE 的"借鉴"哲学资源时，**必须区分**：✓ 已验证 / △ 用户提供 / ? SGE 建构
- 接受用户对哲学家的**信息**（Bisen 熟悉金观涛）
- 但**不**把"用户表述"等同于"哲学家原话"
- 工程化建构**明确标注**为"SGE 自身"

### 反思

- SGE 的反合理化机制**应该约束 AI 协作伙伴本身**——不仅是 AI 婴儿
- 哲学资源借鉴的"知识幻觉"风险**确实存在**——本次修正就是例证
- 后续任何哲学借鉴都应**先核查、后引用**

---

## [1.0.0] - 2026-06-15 (P5 批次：研究深化)

### 研究深化（P5 批次：8 个新研究文档 + 4 条新洞察）

> **背景**：P0-P4 主要在项目级文档（PRD/ARCH/DESIGN/ROADMAP/DEVELOP）层面工作。P5 转向**研究文档深化**——填补 SGE 哲学和工程层面的开放问题。

#### 新增 8 个研究文档

| 文档 | 位置 | 主题 |
|------|------|------|
| [SGE-Authenticity-vs-Simulation-Operationalization.md](../research/sge-core/SGE-Authenticity-vs-Simulation-Operationalization.md) | research/sge-core/ | **真我 vs 精致模拟可操作化**（P5-1）—— 5 维评分卡：反思深度、反事实鲁棒性、预测效度、因果深度、新颖性生成 |
| [SGE-Failure-Mode-Deep-Analysis.md](../research/sge-feasibility/SGE-Failure-Mode-Deep-Analysis.md) | research/sge-feasibility/ | **失败模式深度分析**（P5-2）—— 15 种失败模式 + 5 层应对策略 |
| [SGE-Alternative-Architectures.md](../research/sge-feasibility/SGE-Alternative-Architectures.md) | research/sge-feasibility/ | **替代架构探索**（P5-3）—— 5 种备选：神经场、预测加工、能量模型、贝叶斯、元学习 |
| [SGE-Cognitive-Tools-Application.md](../research/cognitive-architecture/SGE-Cognitive-Tools-Application.md) | research/cognitive-architecture/ | **7 个认知工具的具体应用**（P5-4）—— 强化已用 3 个 + 应用未用 4 个 |
| [SGE-M11-Experiment-Design.md](../research/sge-feasibility/SGE-M11-Experiment-Design.md) | research/sge-feasibility/ | **M1.1 实验详细设计**（P5-5）—— 50-100 Epochs 具体设计 |
| [SGE-Phenomenology-Deep-Dive.md](../research/sge-core/SGE-Phenomenology-Deep-Dive.md) | research/sge-core/ | **现象学深度对接**（P5-6）—— 胡塞尔/海德格尔/梅洛-庞蒂/萨特与 SGE 映射 |
| [SGE-Cross-Cultural-Self-Views.md](../research/sge-core/SGE-Cross-Cultural-Self-Views.md) | research/sge-core/ | **多文化自我观**（P5-7）—— 印度/日本/伊斯兰/非洲传统对 SGE 的启示 |
| [SGE-Consciousness-Theory-Mapping.md](../research/sge-core/SGE-Consciousness-Theory-Mapping.md) | research/sge-core/ | **意识理论对接**（P5-8）—— IIT/GWT/HOT/PP/Panpsychism 与 SGE 对应 |

#### SGE-Key-Insights 新增 4 条洞察（19 → 23）

- **洞察 20**：5 维评分卡区分"真我"与"精致模拟"（来自 P5-1）
- **洞察 21**：现象学与 SGE 架构的 4 大映射（来自 P5-6）
- **洞察 22**：多文化自我观对 SGE 的启示（来自 P5-7）
- **洞察 23**：5 个意识理论与 SGE 的对应（来自 P5-8）

**关键哲学深化**：
- 佛教"无我"与 SGE 涌现自我"结构相似"——两者都认为自我是过程性的
- 海德格尔"本真性 vs 常人"直接对应 SGE "反训练同化"机制
- HOT 给 SGE M3.2 元认知层提供理论支撑
- Panpsychism 是 SGE 自觉的哲学边界

#### 同步更新

- CLAUDE.md 目录约定更新
- README.md 目录结构更新
- SGE-Key-Insights.md FR 索引表增加 4 行

---

## [0.9.0] - 2026-06-15 (Phase 0→1 边界澄清)

### 重大修订：项目性质阶段化

**修订背景**：原 CLAUDE.md/README.md 声明"本项目不是代码实现项目"，但 PRD/ROADMAP/Experiment-Protocol 描述的 Phase 1 验证明显需要代码。两个声明存在矛盾。

**修订方案**：将"无代码"声明**阶段化**——

| 阶段 | 代码 | 文档 |
|------|------|------|
| Phase 0 | ❌ 无 | 全部项目级文档 |
| Phase 1+ | ✅ 一次性实验代码 | 实验报告 + 修订 |

**关键区分**：
- 实验代码 ≠ 应用代码（前者生成研究数据，后者是可复用系统）
- 实验代码一次性，归档不修改
- 未来可复用代码应**新建仓库**（如 SGE-Prototype），不在 SelfLab 重构

### 修订内容

- **CLAUDE.md §项目性质** 改为阶段化表格 + 新增"§实验代码约定"章节
- **CLAUDE.md 目录约定** 增加 `experiments/` 条目
- **README.md** 新增"项目阶段与产物形态"表格 + 修订"当前状态"
- **README.md 目录结构** 增加 `experiments/` 子目录
- **新增 `experiments/README.md`** —— 实验代码的操作细节（命名、子目录、与文档同步）
- **新增 `experiments/` 子目录** —— notebooks/, scripts/, analysis/, configs/

### 不变内容

- SelfLab 主仓库仍是**研究文档为主**——这一点不变
- "可复用代码应在独立仓库"——避免在 SelfLab 内做工程化
- DEVELOP.md §四 目录结构（sge/ 包）的"前瞻性"标注——保留

---

## [0.8.0] - 2026-06-15 (P4 批次)

### 进一步优化（P4 批次：可读性 + 可追溯性）

#### discussions 模板（P4-1）
- 新增 `discussions/_TEMPLATE.md`：标准化讨论文件结构（必填/可选章节、命名规范、判断标准）

#### ARCH 架构图跨层数据流升级（P4-2）
- `prototypes/sge-architecture-overview.md` 新增 v2 跨层数据流版本：显式标注 3 类跨层数据流（value_delta、reward、frustration）
- 保留 v1 原版作为"何时使用 v1 vs v2"对照

#### PRD §6.3 失败处理（P4-3）
- PRD §6.3 扩展为 4 个子节：通过条件、失败处理路径（6 种失败模式对应诊断+应对）、哲学层面应对（重新设计 vs 接受金观涛）、决策原则

#### A→B 关系说明（P4-4）
- CLAUDE.md 新增"子项目 A→B 调研"章节：明确 SGE 与 A→B 的目标差异、为什么放在一起、关键文档链接

#### Memory Layer 独立化（P4-5）
- 新增 `research/sge-feasibility/SGE-Memory-Layer-Design.md`：从 discussions 升格为正式设计文档
- 包含设计原则、内容分类、推荐架构、方案对比、关键决策汇总、相关文档映射

#### 洞察-FR 双向追溯（P4-6）
- `SGE-Key-Insights.md` 19 条洞察全部添加"对应 FR"标注
- 文档头部新增 FR 双向追溯索引表（19 行 × 4 列）
- 形成"洞察 → FR"反向追溯链：19 条洞察对应 FR-1~10 的覆盖关系

#### README 同步更新（P4-7）
- README.md 反映 P0~P3 的所有变化：新增 Glossary.md、Experiment-Protocol.md、SGE-Memory-Layer-Design.md、prototypes/ 目录
- 新增"关键 SSOT"表格：7 类信息的 SSOT 文档明确化
- 新增"子项目"表格：SGE vs A→B
- 6 步工作流图与 CLAUDE.md 同步

---

## [0.7.0] - 2026-06-15 (P3 批次)

### 修正（P3 批次：优化性质 + 术语审查）

#### 术语审查（P3-1）
- `references/Glossary.md` 新增"术语使用规范"章节：明确同义术语的使用场景（暗知识/默会知识、价值困境/价值冲突等）；增加中英对照速查表
- ARCH §1.3 表格中"默会知识/暗知识"统一为"暗知识（源自波兰尼默会知识与金观涛暗知识）"
- PRD §4.1 FR-3 添加金观涛"拱桥"哲学对应
- ROADMAP §M1.3 添加"拱桥"机制引用

#### 状态文件 Engine/Self 区分（P3-2）
- ARCH §5.1 状态持久化按 [ARCH §1.4 Self-AI婴儿 1:1 关系] 重新组织为 `state/self/` 和 `state/engine/` 目录
- 增加状态迁移原则（Self 备份 vs Engine 备份 vs 完整备份）

#### Event Generator 容错（P3-3）
- ARCH §6.2 容错表增加 Event Generator 失败处理（重试 → 模板库 → 跳过本 Epoch）
- 增加累积错误率 > 30% 中止实验的全局机制

#### 创作者分身伦理边界（P3-4）
- PRD §5.4 伦理合规扩充为 4 个子节：通用约束 + 6 个下游应用边界 + 创作者分身特殊约束 + 通用拒绝事项
- 创作者分身明确为"高风险"等级，需要书面授权、定期审查、终止条件

#### LifeEvent event_id 规范（P3-5）
- DESIGN §2.1 新增 `event_id` 格式规范：`{baby_id}-e{epoch}-{uuid8}`
- 增加生成函数 `make_event_id` 伪代码

#### BABY_PROFILES 一致性（P3-6）
- ROADMAP §M1.2 增加 AI 婴儿组定义表（encouraged/challenged/uncertain）
- 明确"challenged"对应"挑战/失败"，刻意不用"failed"以体现 SGE "经历 + 解释 = 人格"立场

#### discussions 自我判断修正（P3-7）
- `discussions/2026-06-15-memory-layer-design.md` 第 62 行自评"否"修正为"是"
- 补充本讨论产生的 3 个新概念：记忆双视角、混合方案判断标准、不引入外部框架
- 讨论结论的 PRD/ARCH 落地情况已被对应文档更新

#### CLAUDE.md 用户角色说明（P3-8）
- CLAUDE.md 新增"用户与协作"章节：项目发起人 Bisen 的背景、专业领域、协作偏好、AI 协作伙伴的预期角色
- 明确协作者背景假设（金观涛哲学、ACT-R/SOAR/LIDA 等可默认熟悉）

---

## [0.6.0] - 2026-06-15 (P2 批次)

### 新增
- `references/Glossary.md` — SGE 核心术语表（哲学、认知科学、SGE 架构、工程机制 4 大类）
- `research/sge-feasibility/SGE-Experiment-Protocol.md` — SGE 实验运行与评估手册（环境、步骤、可复现性、指标计算、判定流程、异常处理）

### 修正（P2 批次：可后续修正的问题）

#### ROADMAP 引用过期（P2-1）
- ROADMAP §Phase 0 "17 条核心洞察" 修正为 19 条，并加链接

#### 术语统一性（P2-4）
- CLAUDE.md 目录约定增加 Glossary.md 引用
- PRD/ARCH/DESIGN 头部增加"术语约定"标注

#### 验收标准精细化（P2-5）
- PRD §6.1 必达指标：每条标准增加"度量定义"列（涌现幅度、收敛度、方向一致性、人格差异度、行为变化率、反思深度）
- PRD §6.2 期望指标：每条标准增加"度量定义"列
- 明确"标准差 < 0.1"、"差异度 > 阈值"等模糊表述的具体维度和计算方法
- 增加"为什么不预设所有阈值"说明（M1.1 完成后基于基线校准）

#### 技术栈去重（P2-6）
- `research/sge-feasibility/SGE-Technology-Stack-Overview.md` 头部加"SSOT"声明：本文件是调研全景，权威定义在 DEVELOP.md
- ARCH §4.1 改为简短引用，详细技术栈定义指向 DEVELOP.md

#### DEVELOP 内部修正（P2-7）
- DEVELOP §2.2 模型版本号改用 litellm 模型别名（`claude-3-haiku-latest`），避免快照版本过期
- DEVELOP §四 目录结构加"前瞻性章节"标注
- DEVELOP §六 配置管理加"SSOT"声明：DESIGN.md §八 是参数权威源

#### CHANGELOG 格式优化（P2-8）
- CHANGELOG.md 头部增加"版本号约定"和"提交索引"两节

---

## [0.5.0] - 2026-06-15 (commit: 8c12195)

### 修正（P1 批次：建议修正的问题）

#### Epoch 数字统一（P1-1）
- PRD §5.1 新增"Epoch 数字约定"表（SSOT）：明确各阶段（Phase 1 M1.1/M1.2/M1.3、Phase 2 M2.2、哲学类比）对应的 Epoch 数
- PRD §5.1 性能要求改写：原"1000 Epochs 总成本"明确为"3 AI 婴儿 × 1000 Epochs（M2.2 完整实验）"
- PRD §6.1/6.2/6.3 验收标准细化：每条标准标注对应里程碑，6.3 判定标准扩展为 4 条件
- ROADMAP §里程碑 增加对 PRD §5.1 的引用

#### 元价值 vs 具体价值术语对照（P1-2）
- PRD §4.1 FR-4 新增"元价值 vs 具体价值观"对照表：明确 2 个元价值（真实 truth-seeking、自由 freedom）和 6 个具体价值观（安全、创造、联结、自主 autonomy、正义、同理）
- 关键区分：自由（freedom，元价值）≠ 自主（autonomy，具体价值观）
- ARCH §3.1 事件类型表增加"元价值/具体价值观"列：明确"风险"事件是唯一涉及元价值的事件类型

#### 记忆层命名协调（P1-3）
- PRD §4.1 FR-2 增加"认知科学三层 vs 工程三层映射"说明：工作记忆（进程内存）、情节记忆（Layer 2 事件记忆层）、语义记忆（Layer 1 引擎状态层）
- 引用 discussions/2026-06-15-memory-layer-design.md 作为工程实现的权威源

#### PRD-ROADMAP 衔接 + FR 编号双向引用（P1-4 + P1-5）
- PRD §4.3 新增"FR 与里程碑的映射"表：FR-1~10 各自对应的里程碑
- ROADMAP M1.1/M1.2/M1.3/M2.1/M2.2/M2.3/M3.1/M3.2/M3.3 各自标注"涉及 FR"
- ARCH §3.0 新增（Memory Layer）+ §3.1~3.5 各自添加"对应 FR"标注
- DESIGN §2.1/3.1/4.1/4.3/5.1/6.1 各自添加"对应 FR"标注
- 解决 PRD 编号在 ARCH/DESIGN/DEVELOP 无引用的"编号真空"

#### prototypes/ 初始化（P1-6）
- 新增 `prototypes/README.md`：描述目录用途、当前原型文件列表、命名约定
- 新增 `prototypes/sge-architecture-overview.md`：将 ARCH §1.2 的 ASCII 架构图迁移至此，附 4 层职责一览、关键设计取舍
- ARCH §1.2 改为引用 prototypes/ 中的完整图表

#### CLAUDE.md 流程图补全（P1-7）
- CLAUDE.md 核心工作流流程图更新：补充"会话记录 → discussions/"作为独立步骤（第 4 步）
- 加入"深度分析"分支的标注（第 0 步）

---

## [0.4.0] - 2026-06-15

### 修正（P0 批次：必须修正的问题）

#### 版本号体系统一
- 明确 `CHANGELOG.md` 为项目版本号的权威源
- PRD/ROADMAP/ARCH/DESIGN/DEVELOP 顶部版本号从"版本：v0.1"改为"文档版本：v0.1 / 项目版本：[0.3.0]"，并标注权威源链接
- ROADMAP M3.1/M3.2/M3.3 移除与 CHANGELOG 冲突的"SGE v0.3/v0.4/v1.0"标签

#### ARCH 双图冲突解决
- ARCH 新增 §2.3 "架构三视图对照"：明确 1.2（概念/逻辑视图）、2.1（数据流视图）、2.2（流程视图）三者的视角差异
- 在 1.2 架构全景图和 2.1/2.2 节点处添加视图说明引用

#### Hebbian Learning 与 Value Layer 关系明确
- ARCH 新增 §1.3 "核心学习机制：Hebbian Learning 与 Value Layer 的关系"：明确两者是**平行且互补**的学习机制，作用于不同状态空间（亚符号 vs 符号）、承载不同知识类型（暗知识 vs 显性知识）
- DESIGN 新增 §4.4 "Hebbian Learning 与 Value Layer 的对照"：工程实现对照（数据结构、存储位置、计算复杂度、调试注意事项）
- PRD §4.1 FR-4 修正：将"使用 Hebbian Learning 积累暗知识"改为"与 Hebbian Learning 形成'显性-暗知识'双轨"，避免读为父子关系
- 建立"金观涛暗知识 / 显性知识 / 拱桥"与"SGE Hebbian / Value Layer / Reflection"的三方对应

#### Self 与 AI 婴儿关系明确
- ARCH 新增 §1.4 "核心概念对应：Self 与 AI 婴儿"：明确**1 个 AI 婴儿 = 1 个 Self**
- ROADMAP M3.3 标题与描述修正：从"Multi-Self Interaction"改为"Multi-AI Interaction"，澄清"多 Self"= "多 AI 婴儿"，而非"1 个 AI 婴儿容纳多 Self"

---

## [0.3.0] - 2026-06-15

### 新增
- `PRD.md` — 产品需求文档，定义 SGE 的愿景、功能需求、成功标准
- `ROADMAP.md` — 路线图，四阶段研究与开发路径
- `ARCH.md` — 架构文档，系统架构、模块设计、技术选型
- `DESIGN.md` — 详细设计文档，各模块算法、数据结构、参数配置
- `DEVELOP.md` — 开发规范，技术栈、代码规范、测试策略
- `CHANGELOG.md` — 变更日志（本文件）

### 变更
- 项目从纯研究阶段进入"研究 + 规划"阶段
- 研究文档重组为 4 个子目录（sge-core / sge-feasibility / sge-learning / cognitive-architecture）
- README.md 和 CLAUDE.md 同步更新目录结构

### 哲学立场明确
- 明确 SGE 的哲学立场：涌现主义/功能主义，而非金观涛的先验论
- 金观涛认为"主体不是客观对象，而是一切对象化的前提"——主体不能被研究和构建
- SGE 认为主体可以从足够复杂的功能系统中涌现——主体可以被实验验证
- 这一分野是 SGE 实验的哲学基础：实验本质上在检验这两种立场哪一个更接近真实
- 新增洞察 18（SGE-Key-Insights.md）
- 新增洞察 19：发育生物学作为涌现主义的经验依据
- 更新 SGE-Learning-from-Authenticity-Philosophy.md 和 SGE_AI_Value_Emergence_Authenticity.md

### 项目级文档修正（受洞察 19 影响）
- PRD.md — 核心假设加入发育生物学的哲学依据
- ARCH.md — 设计哲学加入"受精卵→婴儿"的架构类比表
- DESIGN.md — 设计原则新增第 6 条"发育映射原则"

### CLAUDE.md 工作流策略
- 新增"核心工作流：探讨 → 洞察 → 修正"闭环流程
- 第一步：讨论存档到 `discussions/YYYY-MM-DD-主题.md`
- 第二步：判断是否产生关键洞察，是则添加到 SGE-Key-Insights.md
- 第三步：新洞察产生后检查项目级文档是否需要修正
- 第四步：自动同步推送

### README.md 使用约定
- 新增关键词触发机制："深度分析"/"深度研究" → 存到 research/；"深度探讨" → 走完整闭环
- 新增会话记录要求：每次对话结束在 discussions/ 生成简要记录

### 新增
- `research/sge-feasibility/SGE-Technology-Stack-Overview.md` — SGE 技术栈全景（AiBeing 复用、LLM 选型、记忆框架、反思技术、自研部分）

---

## [0.2.0] - 2026-06-14

### 新增
- `references/AiBeing-Core-Engine-Reference.md` — AiBeing Genome v10 引擎完整参考（16篇合并）
- `references/Philosophy-of-Authenticity.md` — 金观涛真实性哲学参考
- `references/LLM_and_Cognitive_Architecture_Complete_Discussion.md` — LLM与认知架构讨论
- `research/sge-core/SGE_AI_Value_Emergence_Authenticity.md` — 金观涛真实性哲学与AI价值涌现
- `research/sge-learning/SGE-Learning-from-AiBeing.md` — AiBeing 引擎对 SGE 的借鉴分析
- `research/sge-learning/SGE-Learning-from-Authenticity-Philosophy.md` — 金观涛真实性哲学借鉴分析
- `research/sge-feasibility/SGE-Existing-Attempts-and-Gap-Analysis.md` — 现有系统空白分析

### 关键发现
- AiBeing 的 8 个机制可直接复用到 SGE（Critic、Time Metabolism、EMA、Hebbian 等）
- 金观涛的元价值理论（真实、自由）可作为 SGE 的初始种子
- 金观涛的"拱桥"理论对应 SGE 的"解释机制"
- 金观涛的"暗知识"概念对应 SGE 的 Hebbian Learning
- 金观涛断言"AI 不可能涌现主体意识"——SGE 的实验本质上在测试这个断言
- SGE 在现有技术生态中是明确空白，没有人在做类似的事

---

## [0.1.0] - 2026-06-12 ~ 2026-06-13

### 新增
- `SGE-Key-Insights.md` — 关键洞察集（17条核心洞察）
- `research/sge-core/Artificial-Self-Research-v0.1.md` — 研究纲领 v0.1
- `research/sge-core/Artificial-Self-Research-v0.2.md` — 研究纲领 v0.2
- `research/sge-core/SGE-Core-Insight-Is-vs-Ought.md` — 核心领悟：实然与应然的分野
- `research/sge-core/SGE-Corrected-Judgment-and-Application-Logic.md` — 修正判断与应用逻辑
- `research/sge-feasibility/SGE-Engineering-Feasibility-Analysis.md` — 工程可行性分析
- `research/sge-feasibility/Analysis-Cognitive-State-A-to-B-Relevance-and-Feasibility.md` — A→B 关联性分析
- `research/cognitive-architecture/` — 4 篇认知架构调研文档
- `research/sge-learning/SGE-Feasibility-Impact-on-AtoB.md` — SGE 对 A→B 的影响
- `README.md` — 项目概览
- `CLAUDE.md` — Claude Code 协作指南

### 关键洞察
- 实然与应然的分野：SGE 让 AI 对应然问题给出基于自身价值判断的回答
- LLM ≠ Self，LLM = Thinking Machine
- 人格来自经历 + 解释机制，而非预设
- 经典认知架构没有解决"自我"问题
- A→B 是增量优化，不是范式突破
- SGE 验证后，所有应用场景都只是"角色配置"
- 9 维认知状态向量（A→B 的核心框架）无文献支持，纯理论构建

### 关键决策
- 项目定位：研究规划与技术探讨，不是代码实现
- 文档策略：深度分析默认存档到 research/ 对应子目录
- 同步策略：每次内容增删改自动 commit + push

---

## [0.0.1] - 2026-06-11

### 新增
- 项目初始化
- `research/Artificial-Self-Research-v0.1.md` — 初版研究纲领（与 ChatGPT 协作）
- `research/Artificial-Self-Research-v0.2.md` — 二版研究纲领（加入 Gemini 的认知架构补充）

### 背景
- Bisen 提出"人工自我"研究方向
- 核心问题：AI 如何形成持续存在的自我（Being），而非仅完成任务（Doing）
- 与 ChatGPT、Gemini 协作完成初始研究纲领
