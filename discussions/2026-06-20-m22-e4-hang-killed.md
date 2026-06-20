# 2026-06-20 — M2.2 E4 hang 杀死事件 + 修复

## 主题
M2.2 E4 主实验 hang 后手动杀死 + 修复 SGELLMClient timeout 缺陷 + 部分数据存档。

## 背景
E4 主实验昨晚 23:35 启动（3 baby × 1000 epoch 串行）。预期 ~8.5h 完成。

## 事件

### 进程状态（2026-06-20 09:59 检查时）

| 指标 | 值 | 解读 |
|------|---|------|
| 进程 ELAPSED | 10h 23min | 从启动到现在 |
| 最新 log 写入 | 09:49 | **10 分钟前完全没动** |
| 最新 checkpoint | epoch 300 | 完整数据 |
| 实际最高 epoch | 335 | 还有 ~35 epoch 没 checkpoint |
| CPU% | 0.0% | **进程空闲，不在跑** |
| MEM% | 0.1% | 正常 |

### E4 进度数据（仅 encouraged baby，跑了 33.5%）

**Checkpoint 时间序列（每 50 epoch 采样）**：

| Epoch | \|val\| | frustration | PT | calls | retry% |
|-------|---------|-------------|-----|-------|--------|
| 1 | 0.062 | 10.00 | 0 | 4 | 0.0% |
| 50 | 0.121 | 9.93 | 0 | 110 | 0.0% |
| 100 | 0.342 | 9.85 | 0 | 222 | 0.0% |
| 150 | 0.227 | 9.77 | 0 | 330 | 0.0% |
| 200 | 0.286 | 9.69 | 0 | 442 | 0.0% |
| 250 | 0.367 | 9.61 | 0 | 550 | 0.0% |
| 300 | 0.211 | 5.91 | **1** | 662 | 0.6% |

**观察**：
- Encouraged 婴儿期 PT 触发 1 次（epoch 200-300 之间）—— E3 pilot 100 epoch 没触发，**1000 epoch 验证 PT 假设**
- Frustration 从 10.00 缓慢下降 → 5.91（Hawking 衰减起作用）
- |val| 在波动中（0.06 → 0.37 → 0.21），还没收敛到稳定值
- Retry rate 0.6%：相比 E3 pilot 不算严重，但 server 整体慢

### 性能对比（关键发现）

| 指标 | E3 pilot v3（100 epoch）| E4 encouraged（335 epoch in 10h）|
|------|------------------------|----------------------------------|
| 总时间 | 978.7s | 10h 23min = 37380s |
| 平均速率 | 9.8 s/epoch | **115 s/epoch** |
| 退化比例 | (baseline) | **~12x 慢** |

**根因**：MiniMax server 在长时间运行后逐渐变慢（不是断连/SSL EOF，是单纯变慢），最后某个调用彻底 hang 住（socket 不返回也不超时）。

### 死亡分析

1. **Retry logic 抓到了 timeout**（3 次 retry 事件都是 timeout）
2. **Retry 之后还能跑**（retry 1 后继续到 epoch 335）—— retry 没坏
3. **最后 hang 死的调用** 既没 timeout 也没 retry —— 是 socket 层面死锁，litellm 没保护
4. **CPU 0%** 确认不是 Python 在计算 —— 完全等网络 I/O

## 修复

### `SGELLMClient.chat()` 加 explicit timeout

```python
def chat(self, messages, ..., timeout: float = 30.0):
    ...
    kwargs = dict(..., timeout=timeout)  # 传给 litellm.completion
```

**效果**：每个 LLM 调用 30s 硬超时。如果 server hang 死等，30s 后 `litellm.Timeout` 抛出 → 进入 retry 逻辑 → 5 次 retry 总耗时上限 ~3.25 min（30s × 5 + 退避 3+6+12+24s）。**不再可能 hang 10+ 分钟**。

### RETRYABLE_EXCEPTIONS 加 `litellm.APIError`（catch-all）

之前只 catch 5 个特定 exception。如果 MiniMax server 返回未知错误类型（HTTP 502/503/504 等），不会被 retry，会直接 raise 杀死脚本。`APIError` 是 litellm 的基类，覆盖更多边界情况。

## 部分数据存档

`experiments/output/m22_triplets/encouraged_partial_265epochs.log`（gitignored，82KB）—— 完整 log 包括：
- 335 epoch 每步进度（event type + actor + |val|）
- 7 个 checkpoint 详细数据
- 3 次 retry 事件
- 所有 Identity/Narrative 触发时的 LLM 完整输出（从 log 的 LLM raw content 段可提取）
- PT 触发的 epoch 列表

需要时可通过 `grep "IDENTITY\|NARRATIVE" /tmp/m22_triplets.log` 或读 log 文件恢复。

## 经验教训（M2.2+ 必读）

1. **MiniMax server 长跑不可靠**：从 M2.2 pilot 单 baby 17 min 到 E4 encouraged 10h 慢 12x，server 在长跑场景下会逐渐退化
2. **必须显式 timeout**：litellm 默认 socket timeout 很长（看起来 ≥10 min），不能信任
3. **进程空闲不等于卡死**：CPU 0% + log 不动 = socket hang，不是 Python bug
4. **监控信号**：每个 checkpoint 打印 elapsed_time + retry_rate，可提前发现 server 退化

## 下一步决策（待 Bisen）

E4 encouraged 跑到 33.5%，剩下 2 baby 没跑。**3 个选项**：

### 选项 A：现在立刻重启 E4（从 encouraged 重新开始）
- 优势：保留实验意图完整性
- 风险：server 可能在几小时后再次退化；30s timeout 可能会因为 server 持续慢而大量 retry

### 选项 B：今晚/明天 server 低峰期再跑（推荐）
- 优势：避开当前 MiniMax server 高负载期
- 风险：需要手动调度；不知道 server 低峰期是几点

### 选项 C：降级跑 — 缩短到 500 epoch（节省 50% 时间）
- 优势：减少总调用数（~3300 vs ~6600），降低单次实验 server 风险
- 风险：1000 epoch 是 M2.2 计划定义的目标，500 epoch 可能 PT/Hawking 不充分

## 产出文件

| 文件 | 类型 | 状态 |
|------|------|------|
| `experiments/output/m22_triplets/encouraged_partial_265epochs.log` | 部分数据 | gitignored，82KB |
| `_sge_llm_client.py` 修复 | explicit timeout + APIError in retry | ✅ |

## 维护者
Bisen & Claude

## 状态
⚠ E4 encouraged 33.5% 完成 + 进程 hang + 已 kill + 已修复 timeout — 待决策重启时机
