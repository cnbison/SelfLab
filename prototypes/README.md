# SGE 架构原型

> 本目录存放 SGE 系统的**架构原型设计图与系统描述**（非可运行代码）。代码实现位于未来的 `sge/` 包中，参见 [DEVELOP.md §四](../DEVELOP.md) 的目录结构（Phase 1+ 才会用到）。

---

## 目录用途

`prototypes/` 用于在**实现之前**沉淀架构设计的可视化原型，主要包括：

- 架构图（系统分层、数据流、状态机）
- 时序图（认知循环、反思触发、身份结晶）
- 接口契约（模块间输入/输出协议）
- 关键算法的伪代码与流程图

每个原型文件聚焦于**一个具体的设计问题**，与 [ARCH.md](../ARCH.md) 章节交叉引用。

---

## 当前原型文件

| 文件 | 主题 | 对应 ARCH 章节 | 状态 |
|------|------|---------------|------|
| [sge-architecture-overview.md](./sge-architecture-overview.md) | SGE 整体架构（4 层视图：符号/经验/感知/表达） | [ARCH §1.2](../ARCH.md) | 草案 |

---

## 原型文件命名约定

- 短横线连接（kebab-case）
- 文件名应直接体现主题，如 `sge-cognitive-cycle.md`、`sge-value-ema-flow.md`
- 不超过 50 字符

---

## 与 ARCH/DESIGN 的关系

```
ARCH.md (架构总览，叙述性)
    ↓ 引用
prototypes/ (架构原型，可视化)
    ↓ 引用
DESIGN.md (详细设计，算法与数据结构)
    ↓ 引用
DEVELOP.md (开发规范，未来代码组织)
```

- **ARCH** 描述"是什么"和"为什么"
- **prototypes** 描述"长什么样"（图、流程、伪代码）
- **DESIGN** 描述"怎么做"（具体算法、参数）
- **DEVELOP** 描述"怎么组织"（代码模块、命名、测试）

当 ARCH 章节有重要更新时，先在 `prototypes/` 同步更新对应原型，再修改 DESIGN 算法细节。

---

## 添加新原型的工作流

1. 在 `prototypes/` 创建新文件，遵循命名约定
2. 在本 README.md 的"当前原型文件"表中添加条目
3. 在 ARCH/DESIGN 的对应章节添加引用链接
4. 在 CHANGELOG.md 记录
5. 按 CLAUDE.md 自动同步策略 commit + push
