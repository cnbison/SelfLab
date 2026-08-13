# 2026-08-13 Phase 3 收窄决策讨论

> **参与人**：Bisen + Claude
> **类型**：战略调整决策（"深度探讨"模式 → 走完整闭环）
> **关联**：ROADMAP.md §Phase 3、CHANGELOG 1.41.0、SGE-Key-Insights §三十一 / §三十二 / §三十三

---

## 1. 决策背景

Bisen 在 Phase 3.3 完成（1.40.0 + 1.40.1）后，反思当前 SGE 走向：

> "先暂停一下，梳理总结一下 SGE 开发到现在，是个什么状况？我咋感觉越来越像在做类似 ECOS 项目的事情了呢？会不会方向偏移了？"

**核心担忧**：Phase 3.3 的两个 PoC（`student-digital-twin` + `teaching-ai-coach`）虽然在防火墙之内（洞察 31/32/33），但**名称与 ECOS（学生数字孪生 + AI 教学教练）高度重叠**，做下去感觉"像在给 ECOS 打前站"。

---

## 2. 现状盘点（决策前的真实状态）

### 2.1 已完成里程碑

| 阶段 | 状态 | 关键产出 |
|------|------|---------|
| Phase 0 理论奠基 | ✅ | 30+ 洞察 + 4 个 research 子目录 |
| Phase 1 最小验证 | ✅ | M1.1-M1.4 + 跨 LLM（MiniMax-M3 + Moonshot）|
| Phase 2 完整实验 | ✅ | M2.1 全 4 阶段 + M2.2 v6 长程验证 + M2.3 个人真实测试 |
| Phase 3.1 持久化基础 | ✅ | persistence + session + context_injection（1.32-1.36）|
| Phase 3.2 pytest 框架化 | ✅ | 14 模块 86% 覆盖率（1.37-1.39）|
| Phase 3.3 student-digital-twin PoC | ✅ | 512 行设计 + 5 源文件 + 真实 LLM 验证（1.40.0 + 1.40.1）|

### 2.2 核心命题的实验状态

**SGE 核心命题**（"AI 能否形成持续自我"）**已被稳健验证**：

- **M2.2 v6 长程验证**（2026-07-12，CHANGELOG 1.31.0）：6 个独立实验，H_self reduction mean +37.7%（5/6 > 30% 阈值），PT 触发 6/6 ≥ 1
- **PRD §6 双维度首次同时通过**：A 维度（|val| 增长 ≥ 20%）+ B 维度（H_self reduction > 30%）+ PT ≥ 1

### 2.3 仍未完成项

| 项 | 状态 |
|------|------|
| `sge/llm_cache.py` | ❌ 未创建 |
| `sge/prompts/` 目录 | ❌ 未创建 |
| teaching-ai-coach PoC | 📋 21 行占位，未投入 |
| Phase 3 总结报告 | ❌ 未写 |

---

## 3. 方向是否偏移的判断

### 3.1 没有偏移的部分

- **主线未变**：SGE 核心命题仍然是"AI 自我涌现"，Phase 0+1+2 全程围着这条主线
- **工程化服务主线**：Phase 3.1/3.2（persistence/session/llm_cache）为 SGE Runtime 服务
- **防火墙已立**（洞察 31/32/33）：
  - ECOS 已是独立项目（不在 SelfLab）
  - SGE value/drive 不可建模"对学生的理解"
  - SGE 定位是 Self Evolution Runtime，服务"AI 自身需要状态"场景

### 3.2 真正偏移的部分

- **PoC 名称与 ECOS 重叠度过高**：即使有防火墙，做下去就是给 ECOS 打前站
- **重心从研究主线滑向应用探索**：Phase 3.3 的 PoC 处于"研究主体已完成 → 应用探索"的过渡期，容易出现"做第二个 ECOS"风险

**核心判断**：**没有方向偏移，但有重心偏移风险**——SGE 走到了它的自然边界（研究主体已闭环），剩下的是"工程化交付"，不是"研究扩展"。

---

## 4. 决策内容

### 4.1 高层决策

**采用选项 A：保留 Phase 3 路线但收窄 PoC 范围**（Bisen 在三选项中选定）

> Phase 3.3 的两个 PoC 砍掉一个（或都降级为最小演示），重点把 SGE Runtime 的核心 API 打磨好，不再做新的应用探索，把 Phase 3 的边界收紧在"让 SGE 包可以被加载和调用"。

### 4.2 三个子决策

| 子决策 | 选择 | 理由 |
|--------|------|------|
| **student-digital-twin 处理** | ✅ **保留为 Runtime Demo，重命名定位** | 已投入大量工作（512 行设计 + 5 源文件 + 真实 LLM 验证），但定位从"应用 PoC"→"Runtime API 调用演示"，不再往前推新功能 |
| **teaching-ai-coach 处理** | ⏸ **标记为 M4+ 延后** | 仍只是 21 行占位，无投入；不在 Phase 3 范围；保留占位文档作为未来参考 |
| **Phase 3.2 缺口（llm_cache + prompts）** | 🔧 **划为 Phase 3.2 收尾** | 本次只做文档重定位 + Runtime 收尾报告；llm_cache + prompts 划到 Phase 3.2 收尾任务，下次启动 |

### 4.3 Phase 3.3 重新定义

| 原 Phase 3.3 | 收窄后 |
|-------------|--------|
| **PoC 验证**（应用原型） | **Runtime 可加载性验证**（证明 sge/ 包可被外部项目加载调用）|
| student-digital-twin PoC | student-digital-twin Runtime Demo |
| teaching-ai-coach PoC | M4+ 延后 |
| Phase 3.3 评估 + 总结报告 | **Phase 3 Runtime 收尾报告**（总结"包已可调用"而非"应用可行"）|

**核心边界**：Phase 3.3 收尾 = 把 1.40.0/1.40.1 的成果**定性归档**，不再往前推。

---

## 5. 影响范围

### 5.1 文档更新（本次执行）

- `research/phase3/90-applications/student-digital-twin.md`：顶部状态 + 加收窄边界声明段
- `research/phase3/90-applications/teaching-ai-coach.md`：顶部状态改为 M4+ 延后
- `research/phase3/00-overview/03-roadmap.md`：Phase 3.3 章节重写 + 加 Phase 3.2 收尾待办
- `ROADMAP.md`：Phase 3 当前状态描述更新
- `CHANGELOG 1.41.0`：本次决策记录

### 5.2 不变项

- `student_digital_twin/` 代码（不动）：mastery/events/adapter/demo_alice 保持现状
- sge/ 包 14 模块（不动）：pytest 覆盖率 86% 保持
- insights 33（Self Evolution Runtime 定位）：不变

### 5.3 后续非阻塞任务

- Phase 3.2 收尾：llm_cache.py + prompts/ 版本管理（下次启动）
- Phase 3 Runtime 收尾报告：本文档为基础，CHANGELOG 1.41.0 之后单独写

---

## 6. 与已有洞察的关系

| 已有洞察 | 关系 |
|---------|------|
| 洞察 30（SGE 三原则锚点）| **强化** —— 原则 1（"SGE 是根"）的边界现在更清晰：Phase 3 收尾在 Runtime 工程化，不是应用探索 |
| 洞察 31（ECOS 独立项目）| **强化** —— PoC 名称虽像 ECOS，但通过收窄边界避免被误读为"做 ECOS 的前站"|
| 洞察 32（SGE value/drive 不适合建模他人）| **支撑** —— Runtime Demo 只调用 mastery_state 的 duck typing 方法（summary/most_recent_struggling/learning_velocity），不涉及 SGE 内部 value 建模学生认知 |
| 洞察 33（Self Evolution Runtime 定位）| **强化** —— Runtime Demo 直接证明 sge/ 包可作为外部 Runtime 被加载调用，符合定位 |

---

## 7. 决策实施

本次执行：

1. ✅ 讨论记录（本文档）
2. ✅ student-digital-twin.md 顶部 + 收窄边界声明
3. ✅ teaching-ai-coach.md 顶部状态改 M4+ 延后
4. ✅ phase3/00-overview/03-roadmap.md 重写 Phase 3.3 章节
5. ✅ ROADMAP.md Phase 3 当前状态描述更新
6. ✅ CHANGELOG 1.41.0
7. ✅ git commit + push

---

**记录者**：Bisen & Claude
**创建日期**：2026-08-13
**类型**：战略调整决策
