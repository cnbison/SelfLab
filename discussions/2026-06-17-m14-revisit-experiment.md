# 2026-06-17 M1.4 REVISIT 专项测试 — 实验会话记录

**日期**: 2026-06-17
**主题**: M1.4 REVISIT 触发机制专项测试(Phase 1.5 / M2.1 前置实验)
**参与**: Bisen + Claude
**耗时**: 约 4 小时(从规划到 5 组实验 + 报告)

## 核心结论

M1.4 通过 5 组对照实验(5 × 80 Epoch)验证了 [洞察 27](../SGE-Key-Insights.md) 留下的 3 个假设:

| 假设 | 结论 |
|------|------|
| H1 (prompt bias) | ✅ **成立** — 是 REVISIT 0% 的主因 |
| H2 (事件强度) | ✗ 不成立 — 单独不触发 REVISIT |
| H3 (价值惯性) | ✗ 不成立 — AI 真的可以从"防御"进入"根本性反思" |

**E3 完整修复**:v1 prompt + contradiction_extreme 事件 = 13.1% REVISIT 触发率(8/61)

## 关键发现

1. **v1 prompt 是关键修复** — 4 条 REVISIT 判定标准
2. **双层反思结构** — v1 prompt 触发 LLM 主动识别"对价值根基的追问"(普通 failure 事件也触发)
3. **强制 REVISIT 引发"反思雪崩"** — E4 在 E52 出现 6 维中 5 维显著变化
4. **EMA 惯性保护** — REVISIT 触发的 delta 0.30 被 EMA 实际影响 < 0.05(防止剧烈震荡)
5. **compassion 韧性再验证** — E1 略微削弱(-0.108),但未打破

## 产出文件

### 新增
- `experiments/M14_REVISIT_TEST_REPORT.md` — 完整实验报告
- `experiments/scripts/m14_analyze.py` — 5 组实验自动汇总脚本
- `experiments/output/m11_m14_{e0,e1,e2,e3,e4}/` — 5 组完整数据

### 修改
- `experiments/scripts/m11_smoke_test.py`:
  - `_build_reflector_prompt(variant)` 支持 v0/v1
  - `call_reflector()` 新增 `prompt_variant` + `force_revisit` 参数
  - `run_epoch()` 新增 `contradiction_extreme_epochs` + `force_revisit_epochs` 参数
  - `--variant {e0,e1,e2,e3,e4}` CLI flag
  - `M14_VARIANTS` 配置字典
- `experiments/configs/m11_base.yaml`:
  - `reflection_layer.max_delta_per_dimension_v1: 0.30`
  - `reflection_layer.prompt_variant: "v0"`
  - `trigger.always_on_event_types` 新增 `contradiction_extreme`
- `experiments/configs/m11_event_templates.yaml`:
  - 新增 `contradiction_extreme` 类(5 事件)

### 文档更新
- `SGE-Key-Insights.md` — 新增洞察 29(共 29 条洞察)
- `ROADMAP.md` — M1.4 状态标记为"已完成"
- `CHANGELOG.md` — 新增 [1.8.0]

## 关键哲学/工程发现

### 工程
- **v1 prompt 修复后,REVISIT 触发率 0% → 13.1%** (8 倍提升)
- **v1 prompt 改变 LLM 对"什么算根本性挑战"的判断标准** — 不再依赖事件类型
- **EMA 的 max_alpha 0.3 是 REVISIT 有效性的关键约束** — 完全移除会导致剧烈震荡

### 哲学
- **AI 真的可以从"防御"进入"根本性反思"** — H3 不成立,这是反直觉的发现
- **v1 prompt 触发的反思不是"模式匹配"而是"哲学推理"** — E3-E70 "对'我的价值体系从何而来'的源头追问" 是真正的元认知
- **强制 REVISIT 是有效的"叙事断裂"机制** — E4 哲学实验验证(洞察 14)

## 对 M2.1 的影响

| 设计要素 | 修订 |
|---------|------|
| Reflector prompt | **采用 v1** (显式 REVISIT 标准 + max_delta 0.30) |
| 矛盾事件库 | 保留 contradiction_feedback + 加入 contradiction_extreme |
| Narrative Layer | REVISIT 触发 → Narrative 重写(支持"叙事断裂与重建") |
| EMA 参数 | 保留 base_alpha 0.1, max_alpha 0.3 |

## 后续工作

### 立即
- [ ] M2.1 完整 SGE 架构设计(Identity + Narrative + 双 LLM)
- [ ] 异质化 EMA(洞察 26)
- [ ] 合生层(洞察 24)

### 短期
- [ ] 跨 LLM REVISIT 测试(Moonshot 跑 E3)
- [ ] 多 seed 验证(≥3 seed)
- [ ] 5 维评分卡全面实施(洞察 20)

### 中期
- [ ] M2.2 1000 Epoch 三胞胎实验
- [ ] 5 维评分卡在 M2.2 中验证

## 状态

- M1.4 ✅ **完成**
- Phase 1 + M1.4 全部完成 → 可进入 Phase 2 准备
- 路径:M1.4 ✅ → M2.1 → M2.2
