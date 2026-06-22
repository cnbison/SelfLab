# 20 - K12 学生认知结构（领域知识）

> **状态**：📋 探索中（占位文件，Phase 3.1 实施期间可同步填充）
> **关联**：[README.md §5 个研究维度](../../README.md)、[01-applications.md §应用 1](../../00-overview/01-applications.md)

---

## 这个目录要研究什么

学生数字孪生和 AI 教练需要**教育学和认知科学的领域知识**——不是 SGE 引擎本身能提供的。这一目录收集 K12 学生认知结构的相关研究。

## 拟研究的主题

| 主题 | 关联 | 用途 |
|------|------|------|
| **认知发展阶段理论**（Piaget / Vygotsky）| SubjectMasteryState 建模 | 不同年级学生的认知模式 |
| **学科特有认知结构**（数学 vs 阅读）| Subject 维度设计 | 数学/语文用不同的 value/drive 映射 |
| **ZPD（最近发展区）**| AI 教练的转移设计 | A→B 状态的"难度梯度" |
| **形成性评估 vs 总结性评估** | SubjectMasteryState update | 测试是"诊断"还是"评分" |
| **学习障碍识别** | Risk R5 数据误用 | 区分"暂时困难"vs"需要干预" |
| **元认知（metacognition）**| Identity Layer 增强 | 学生对自己学习状态的认知 |

## 文件结构（待填充）

```
20-domain-k12/
├── README.md (本文件)
├── 01-developmental-stages.md   # Piaget / Vygotsky / 信息加工理论
├── 02-domain-specific.md       # 数学 / 阅读 / 科学的认知结构
├── 03-zpd.md                   # 最近发展区 + AI 教练应用
├── 04-assessment-theory.md     # 形成性 vs 总结性 + MasteryState 更新策略
├── 05-metacognition.md         # 元认知（学生在 SGE 框架下）
└── 06-learning-disorders.md    # 学习障碍识别
```

## 与 A→B 项目的关系

K12 认知结构是 A→B 学习状态迁移的**基础理论**：
- A→B 项目的 9D cognitive state 向量如何映射到 K12 学科结构？
- 学生在 A 状态（数学薄弱）的 ZPD 在哪？
- 怎么从 A 迁移到 B（数学掌握）需要哪些认知阶段？

详见 [30-atoB/](../../30-atoB/) 整合层。

## 与 sge/ 包的关系

K12 认知结构**不进 sge/ 包**——它是领域知识，不是引擎逻辑。
- sge/ 保持领域无关
- SubjectMasteryState 是 App 层用 K12 知识构造的领域模型

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-22
