# 90-02 - 教学 AI 教练 PoC 设计（占位 → M4+ 延后）

> **状态**：⏸ **M4+ 延后（不在 Phase 3 范围，2026-08-13 决策）**
> **决策依据**：[2026-08-13 Phase 3 收窄决策讨论](../../../discussions/2026-08-13-phase3-narrowing-decision.md) §4.2 + [ROADMAP.md §Phase 3 M4+ 延后范围](../../../ROADMAP.md#phase-3系统完善)
>
> **关联（历史）**：[01-applications.md §应用 2](../../00-overview/01-applications.md)、[30-atoB/](../../30-atoB/) 整合（保留作为未来参考）

---

## 为什么延后

**Phase 3 收窄决策（2026-08-13）**：

- 本 PoC 原计划在 Phase 3.3 W9-W10 实施（与 student-digital-twin 并列）
- 但 2026-08-13 Bisen 反思后决定收窄 Phase 3.3 范围 → 不再做新应用探索
- student-digital-twin 保留为"Runtime API 调用演示"（不是应用 PoC）
- teaching-ai-coach 仍未投入（仅 21 行占位文档），直接标记延后

**为什么是 M4+ 而非彻底删除**：

- 占位文档保留作为未来参考（认知状态迁移的接口契约、A→B 整合入口）
- 如果未来 Phase 4+ 启动教学 AI 教练方向，本文件是入口
- 本次决策不删除文件，避免未来重启时需要从 git 历史恢复

---

## 待填充章节（保留作为未来参考）

1. 场景描述（AI 教练 vs 通用助手的关键差异）
2. A→B 整合设计（如何用 9D cognitive state 设计转移路径）
3. 数据 schema（coach-specific 扩展）
4. 关键技术点（含 A→B 状态映射）
5. UI 原型（个性化教学建议生成）
6. 验收标准（学生 A→B 转移效果）
7. 风险 + 缓解（个性化幻觉、安全护栏）

---

## 未来重启条件（非阻塞）

如果未来要重启本 PoC，需要先回答：

- Phase 3 Runtime Demo（student-digital-twin）已完成 sge/ 包的可加载性验证，是否要在此基础上扩展？
- 与独立项目 ECOS（`/Users/loubicheng/project/ecos/`）的关系如何？是 SelfLab 内的应用 Demo 还是 ECOS 项目的一部分？
- A→B 认知状态迁移是否需要独立的状态估计工程（IRT/BKT/DKT）？

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-22
**最后更新**：2026-08-13（M4+ 延后决策）
