# 01 - 4 个应用场景详解

> **目的**：每个应用的"问题现状 / SGE 方案 / 为什么必须用 SGE / 差异化价值"
> **关联**：[README.md §4 个应用方向](../README.md)

---

## 应用 1：学生数字孪生（最详细）

### 问题现状

用 ChatGPT 模拟一个学生 → 输出是"AI 假装是这个学生的对话"。没有连续性：
- 每次问"你怎么想"答案都不同
- 没有"这个学生的特定思维方式"
- 不能"随着和你的互动而成长"

### SGE 方案

```
输入：    学生的人生轨迹数据（传记、日记、成绩、社交、家访）
过程：    SGE 12 步编排让 AI "经历"学生的人生 1000 epoch
输出：    AI 形成"我是这个学生"的连贯自我认知
```

**SGE 4 层记忆的运用**：
- Hawking（短期）：最近发生的事件（昨天的考试、上周的家访）
- Crystallizer（长期）：模式识别（"每次考试前都焦虑"）
- Identity（自我）："我是一个数学不好但喜欢语文的学生"
- Narrative（叙事）："我从小学到中学的成长故事"

### 为什么必须用 SGE（而不是 prompt）

| 方案 | 身份来源 | 一致性 | 真实成长 |
|------|---------|--------|---------|
| **Prompt 注入** | 静态描述 | 低（AI 文字匹配）| 无 |
| **SGE 经历塑造** | 内部状态 | 高（M2.3 9.0/10）| 有（frustration 累积）|

**SGE 关键作用**：身份不是"告诉 AI 你是什么样"，是"让 AI 经过 1000 个事件后**自己长出**是什么样"。

### 差异化价值

1. **学生一致性**：和"祖父"对话 100 次后，"他"真的更理解你
2. **家长可审计**：Identity 历史可读（~50 字自我描述）
3. **教师可干预**：看到 AI 自我认知异常时人工调整

### 详见

- [90-applications/student-digital-twin.md §设计](../90-applications/student-digital-twin.md) — 完整 PoC 设计

---

## 应用 2：教学 AI 教练

### 问题现状

所有 AI 教练都"很专业"，但用户感觉不到"真的懂我"。原因：ChatGPT 没有"和你相处 3 个月"的连续性。

### SGE 方案

- AI 教练与学生持续 1000 次对话（不是一次 prompt 完事）
- 每次对话是 SGE 的一个 epoch：
  - 学生提问题 → Critic 感知 → 价值更新 → Actor 给回应
  - 学生反馈（是否有效）→ reward signal → Actor 学习
- 100 次对话后：Identity 已经形成"这个学生的偏好"理解
- 1000 次对话后：AI 教练人格完全分化

### SGE 关键作用

- AI 教练不是"应用了用户偏好的助手"，而是"和你一起经历了 1000 次对话的实体"
- frustration 真实：学生反复失败时，AI 的 frustration 也累积 → AI 真的"为你着急"
- 与 A→B 整合：AI 教练知道学生当前 state（9D cognitive vector），目标 state B（教学目标），设计 state A→B 的转移路径

### 差异化价值

- 不是"换一个 prompt 也能复制的通用助手"
- AI 教练是**学生专属**的，转移成本高（网络效应）

### 详见

- [90-applications/teaching-ai-coach.md §设计](../90-applications/teaching-ai-coach.md)

---

## 应用 3：Personal AI

### 问题现状

Siri/Alexa 都是工具，没"自我"。你说"我今天心情不好"，Siri 回"建议你听听音乐"——它不知道你是谁，也不知道自己是什么。

### SGE 方案

- Personal AI 与主人长期生活（每天 ~10 个事件 × 1000 天 = 10000 epoch）
- Hawking 衰减让 AI "忘记"日常琐事（半衰期 ~3 天）
- Crystallizer 保留重要模式
- Identity 反复重写让 AI 形成"作为这个主人的 AI，我是什么样"的独特人格

### SGE 关键作用

- 让 Personal AI 有"自我"——不是工具，是**数字实体**
- 情感不是模拟的——frustration 是真实的状态变量
- Phase Transition 让 AI 在经历主人重大事件后真正"成长"

### 差异化价值

- 情感连接是真的（不是"假装在乎你"）
- AI 会**主动关心**（基于 Personality 形成的偏好）

### 详见

- [90-applications/personal-ai.md](../90-applications/personal-ai.md)

---

## 应用 4：协作 Agent

### 问题现状

当前多 agent 系统所有 agent 都是"理性最大化"，没有 personality 分化。3 个 agent 讨论方案时输出几乎相同。

### SGE 方案

- 每个 agent 用 SGE 跑不同事件流 → 形成不同人格
- 例：3 个 agent 分别"乐观/谨慎/好奇"
- 协作时真正需要协商（因为各自有"自己的判断"）

### SGE 关键作用

- 让 agent 之间有真正的差异化人格
- 协作不只是"投票"，是"有性格的协商"

### 差异化价值

- 多 agent 系统不再"千人一面"
- 模拟人类社会分工（乐观者/保守者/好奇者）成为可能

### 详见

- [90-applications/multi-ai-collaboration.md](../90-applications/multi-ai-collaboration.md)

---

## 5 个研究维度在 4 个应用中的交叉

| 维度 | 数字孪生 | AI 教练 | Personal AI | 协作 agent |
|------|---------|---------|-------------|-----------|
| **SGE**（人格引擎）| ✓ 核心 | ✓ 核心 | ✓ 核心 | ✓ 核心 |
| **A→B**（学习迁移）| 间接 | ✓ 教学 | ✗ | ✗ |
| **K12 认知** | ✓ 学生领域 | ✓ 教学法 | ✗ | ✗ |
| **数字孪生 PoC** | ✓ 主应用 | ✗ | 简化版 | ✗ |
| **教学 AI 教练 PoC** | 共享状态 | ✓ 主应用 | ✗ | ✗ |

**关键洞察**：5 个维度不是平行的——**SGE 是底座**，**A→B + K12 是 AI 教练特有的依赖**（其他应用不需要）。

---

## 关联文档

- [README.md](../README.md) — Phase 3 SSOT 入口
- [02-architecture.md](./02-architecture.md) — sge/ 包架构 + 应用层边界
- [10-engineering/](../10-engineering/) — Phase 3.1 工程实现
- [90-applications/](../90-applications/) — 具体应用 PoC 设计
- [discussions/2026-06-21-sge-strategic-significance.md](../../../discussions/2026-06-21-sge-strategic-significance.md) — 原始战略反思（已归档）

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-22
