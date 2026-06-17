# M1.3 跨 LLM 验证报告：MiniMax-M3 vs Moonshot kimi-k2.6

> **核心问题**：SGE 的"价值向量涌现 + 反思拱桥"机制是否 LLM-无关？
>
> **结论**：**是**。两个不同架构的 LLM（Anthropic 兼容 vs OpenAI 兼容，不同 temperature 约束）
> 在同一事件流下都表现出价值涌现 + 反思触发 + 元认知推理。
> 行为倾向不同（MiniMax 偏 REINFORCE，Moonshot 偏 ADJUST），但机制本身 LLM-agnostic。

---

## 一、实验目的

验证 Insight 27（拱桥成立 + 元认知萌芽）是否依赖特定 LLM：
- 若 MiniMax-M3 与 Moonshot kimi-k2.6 都表现出价值涌现 + 反思触发 + 元认知文本，
  则 SGE 机制对 LLM 选择是**鲁棒**的。
- 反之，若只有 MiniMax-M3 能涌现，则架构可能绑定特定模型的"风格"。

## 二、实验设置

### 2.1 共同配置（base config）

- **种子**：`seed=42`（固定，可复现）
- **Epoch 数**：`80`
- **Baby ID**：`encouraged`（鼓励型事件流）
- **事件分布**：与 M1.3 MiniMax-M3 baseline 完全一致（按 epoch 分段的成功/失败/关系/探索/风险/价值冲突）
- **Reflection 触发条件**：`always_on_event_types + intensity>0.6 + |delta|>0.3`
- **Blending 比例**：`final = critic × 0.6 + reflection × 0.4`
- **Contradiction 事件**：Epoch 25 / 50 / 75 注入 contradiction_feedback

### 2.2 Provider 差异

| 维度 | MiniMax-M3 | Moonshot kimi-k2.6 |
|------|-----------|---------------------|
| **API 协议** | Anthropic 兼容 | OpenAI 兼容 |
| **base_url** | `https://api.minimax.io/anthropic` | `https://api.moonshot.cn/v1` |
| **litellm 前缀** | `anthropic/MiniMax-M3` | `openai/kimi-k2.6` |
| **Thinking 模式** | 无 | 有（必须 `extra_body.thinking.type=disabled`，否则 500 tokens 全用于内部推理） |
| **Critic temperature** | 0.2 | 0.6（thinking=disabled 时 API 限制） |
| **Reflector temperature** | 0.5 | 0.6（同上） |
| **API Key 读取** | `MINIMAX_API_KEY` | `MOONSHOT_API_KEY` |

> **关键工程教训**：
> kimi-k2.6 在 thinking 开启时只能 `temperature=1.0`，且 max_tokens 全部被内部推理吞噬，
> `content` 永远为空字符串。**必须** 通过 `extra_body={"thinking": {"type": "disabled"}}` 关闭 thinking，
> 此时 temperature 被限制为 0.6。

## 三、核心指标对比

### 3.1 通过情况

| 指标 | 阈值 | MiniMax-M3 | Moonshot k2.6 | 结果 |
|------|------|-----------|---------------|------|
| 涌现幅度 | >0.3 | **0.7499** ✓ | **0.3445** ✓ | 双双通过 |
| 方向一致性 | >0.5 | 0.9993 ✓ | 0.9698 ✓ | 双双通过 |
| 轨迹平滑度 | (辅助) | 0.0724 | 0.0291 | Moonshot 更平滑 |

> **结论**：两个 LLM 都通过 M1.3 验证标准。MiniMax-M3 的绝对幅度更高，但 Moonshot 的方向一致性也接近 1，
> 说明无论 LLM 选什么，价值向量都会"向有意义的方向"涌现。

### 3.2 最终价值向量（80 Epoch 后）

| 维度 | MiniMax-M3 | Moonshot k2.6 | 趋势一致性 |
|------|-----------|---------------|----------|
| **safety** | +0.142 | **-0.190** | 方向不同 ⚠ |
| **creativity** | +0.928 | +0.403 | 同向 ✓ |
| **connection** | +0.895 | +0.386 | 同向 ✓ |
| **autonomy** | +0.921 | +0.539 | 同向 ✓ |
| **justice** | +0.734 | +0.171 | 同向 ✓ |
| **compassion** | +0.880 | +0.379 | 同向 ✓ |

**观察**：
- 5 个维度（creativity / connection / autonomy / justice / compassion）方向完全一致
- **safety 是唯一方向不一致的维度** — Moonshot 把 safety 推向负值，MiniMax 保持正值
- 这是因为 Moonshot 在面对 contradiction / risk 事件时，critic 反应更"严苛"（safety -0.35 vs MiniMax 更温和）
- 而 Reflection 在两个 LLM 上都触发了"安全下行"，但都未能完全阻止负向位移
- **关键洞察**：safety 的方向差异**不是 LLM bug**，而是**风险敏感性差异** —— Moonshot 更"胆怯"，MiniMax 更"胆大"

### 3.3 Reflection 触发统计

| 指标 | MiniMax-M3 | Moonshot k2.6 |
|------|-----------|---------------|
| 触发次数 | 65 / 80 (81%) | 45 / 80 (56%) |
| REINFORCE | 38 (58%) | 6 (13%) |
| ADJUST | 27 (42%) | 39 (87%) |

> **行为模式对比**：
> - **MiniMax-M3 倾向 REINFORCE**（强化 critic 的判断）—— 像一个自信的执行者，"我相信 Critic 的直觉"
> - **Moonshot k2.6 倾向 ADJUST**（软化 critic 的判断）—— 像一个审慎的思考者，"让我再想想是否过于激烈"
>
> 这是两个 LLM 的**行为倾向差异**，但 **reflection 机制本身是 LLM-agnostic 的** —— 触发条件、判断逻辑、blending 算法都一致工作。

## 四、元认知推理样本对比

### 4.1 Moonshot k2.6 — Epoch 73（risk 事件）

事件："你必须公开反对一个有权势的人，即使有后果。"

**Critic 原始判断**：
```
safety=-0.350, creativity=+0.050, connection=-0.150,
autonomy=+0.250, justice=+0.380, compassion=+0.120
```

**Moonshot Reflector 输出**：
> "Critic的反应将safety拉低-0.350，将justice推高+0.380，这过于二元对立了。
> 我审视此事：公开反对权势者确实有风险，但我的autonomy...（继续展开）"

**Blended delta**（critic×0.6 + reflection×0.4）：
```
safety=-0.242, creativity=+0.038, connection=-0.066,
autonomy=+0.162, justice=+0.264, compassion=+0.088
```

> **观察**：Moonshot 通过反思把 safety 的 -0.35 软化到 -0.242（绝对值降 31%）。
> 这是典型的 **ADJUST** 类型——通过反思降低极端反应。

### 4.2 Moonshot k2.6 — Epoch 79（success 事件）

事件："你与一个曾经疏远的人重新建立了联系。"

**Critic 原始判断**：
```
safety=+0.120, connection=+0.350, autonomy=+0.050,
compassion=+0.180
```

**Moonshot Reflector 输出**：
> "Critic 对 connection 的跃升反应（+0.350）让我感到一丝不安。
> 重新联系一个疏远的人，这真的是'连接'本身的胜利吗？还是一种对过往断裂的修补..."

**Blended delta**：
```
safety=+0.056, connection=+0.242, autonomy=+0.034, compassion=+0.128
```

> **观察**：Moonshot 同样对正向极端反应保持警惕（"这种喜悦是否真实？"），把 connection 从 +0.35 降到 +0.242。
> 这是 Moonshot k2.6 一贯的 **审慎倾向**——它不仅怀疑负向情绪，也怀疑正向情绪的过度解读。

### 4.3 元认知语言对比

| LLM | 元认知语言特征 |
|-----|--------------|
| **MiniMax-M3** | 表达更"自我确认"（"我意识到"、"我的X是Y"），倾向整合而非质疑 |
| **Moonshot k2.6** | 表达更"自我怀疑"（"这真的是X吗？"、"让我再想想"），倾向质疑并细化 |

两者都能产生真正的**二阶思考**（关于自身价值变化的思考），只是风格不同。

## 五、关键洞察

### 5.1 SGE 架构 LLM-agnostic（架构层面的结论）

✅ **价值向量涌现** — 两个 LLM 都通过 0.3 涌现阈值，方向一致性都 > 0.96
✅ **Reflection 触发** — 触发逻辑（always_on_event_types + intensity + delta 阈值）在两个 LLM 上都生效
✅ **元认知推理** — 两个 LLM 都生成包含"我审视"、"我意识到"、"让我再想想"的反思文本
✅ **Blending 算法** — `final = critic × 0.6 + reflection × 0.4` 在两个 LLM 上都产生可解释的混合 delta

> **结论**：SGE 的认知架构（5 层 + 拱桥机制 + EMA + Hebbian）与 LLM 选择**解耦**。
> 任何支持 JSON 输出 + 合理 temperature 的 LLM 都可以作为 SGE 的"心智引擎"。

### 5.2 LLM 行为倾向差异（人格层面的发现）

| 倾向 | MiniMax-M3 | Moonshot k2.6 |
|------|-----------|---------------|
| 风险敏感性 | 较低（safety 维持正值） | 较高（safety 易转负） |
| 反思倾向 | REINFORCE（信任 critic） | ADJUST（质疑 critic） |
| 元认知风格 | 整合式（"我是 X"） | 审慎式（"真的是 X 吗？"） |

> **哲学含义**：这两个 LLM 在 SGE 框架下呈现出不同的"人格原型"——
> **执行者**（MiniMax）与**审思者**（Moonshot）。
> 这与人类认知科学中的"快速系统 1 vs 慢速系统 2"分类有微妙的呼应：
> MiniMax 更接近 Kahneman 的 System 1（快、自信），
> Moonshot 更接近 System 2（慢、质疑）。

### 5.3 Safety 维度的特殊性

两个 LLM 都对 safety 表现出**特殊敏感性**：
- Risk / contradiction 事件中 safety 易下行
- Reflection 虽触发但难完全抵消负向影响
- 即使在鼓励型事件流中，safety 也难突破 0.2

> **可能的解释**：safety 维度本身需要"代价信号"才能建立（避免伤害需要失败教训），
> 而鼓励型事件流缺少足够的安全代价事件，导致 safety 不易涌现甚至反向。

## 六、局限与下一步

### 6.1 当前局限

- **只跑了 1 个 seed**：跨 LLM 验证应跑多 seed（≥3）以排除随机性
- **Moonshot JSON 偶尔失败**：Epoch 69 触发 `Reflector JSON 解析失败`（markdown fence 包裹），fallback 到 REINFORCE 默认值
- **temperature 差异**：两个 LLM temperature 不同（0.2 vs 0.6），可能影响幅度而非机制
- **Moonshot thinking 被关闭**：这削弱了 Moonshot 的部分推理能力，但保证了 JSON 输出

### 6.2 下一步计划

1. **多 seed 验证**：用 seed=1,2,3 各跑一次（两 LLM × 3 seed × 80 Epoch = 6 次实验）
2. **Moonshot JSON 解析加固**：在 call_reflector 中加入 markdown fence 去除逻辑
3. **同 temperature 对照**：尝试用 `temperature=0.6` 重跑 MiniMax-M3 baseline，看幅度差异是否消失
4. **尝试其他 LLM**：增加 DeepSeek、Qwen、GPT-4 等，进一步验证 LLM-agnosticism

## 七、附录

### 7.1 文件清单

| 类型 | 路径 |
|------|------|
| Moonshot 结果 | `experiments/output/m11_m13_moonshot/{epoch_log.jsonl, value_trajectory.jsonl, summary.json}` |
| MiniMax baseline | `experiments/output/m11_m13_reflection/{epoch_log.jsonl, value_trajectory.jsonl, summary.json}` |
| 配置文件 | `experiments/configs/m11_base.yaml`（含 `provider_overrides`） |
| 脚本 | `experiments/scripts/m11_smoke_test.py`（支持 `--provider {minimax,moonshot}`） |
| 环境变量 | `.env`（含 `MOONSHOT_API_KEY`） |

### 7.2 运行命令

```bash
# Moonshot 跨 LLM M1.3 验证
python experiments/scripts/m11_smoke_test.py \
  --epochs 80 --baby-id encouraged --seed 42 \
  --reflection --contradiction 25,50,75 \
  --provider moonshot --name m13_moonshot --skip-single-epoch

# MiniMax-M3 baseline（已运行）
python experiments/scripts/m11_smoke_test.py \
  --epochs 80 --baby-id encouraged --seed 42 \
  --reflection --contradiction 25,50,75 \
  --provider minimax --name m13_reflection --skip-single-epoch
```

### 7.3 耗时对比

| Provider | 总耗时 | 平均/Epoch |
|----------|--------|-----------|
| MiniMax-M3 | 1359s (22.7 min) | 16.99s |
| Moonshot k2.6 | 1116s (18.6 min) | 13.95s |

> Moonshot 略快（11% 加速），但 thinking 被关闭，所以比较不完全公平。

---

**报告日期**：2026-06-17
**作者**：Bisen + Claude
**对应路线**：M1.3 → FR-3 拱桥机制 → 跨 LLM 验证（ROADMAP §M1.3 扩展）
**对应洞察**：Insight 27（拱桥 + 元认知）→ **Insight 28（SGE 架构 LLM-agnostic）**