# 10-04 - LLM Response Caching

> **目的**：避免重复调用 LLM（节省 MiniMax API 成本 + 调试可重现性）
> **来源**：借鉴 AiBeing `cache/` + 通用 LRU cache 模式

---

## 1. 为什么需要 LLM Cache

**M2.2 实测**：
- 12 chunks × ~550 calls = ~6600 LLM calls
- chunk 1/2/3 中相同事件（如 epoch 0 "初始事件"）重复调用
- 调试时：同 prompt 改 1 行代码 → 重跑 → 又调一次 LLM
- 成本：~6600 calls × $0.01/call ≈ $66

**Solution**：基于 prompt hash 的本地缓存

---

## 2. 设计

```python
import hashlib
import json
from pathlib import Path

class SGELLMCache:
    """LLM 响应缓存（避免重复调用）
    
    存储格式：
        cache_dir/
            <prompt_hash>.json
            {
                "_cached_at": "2026-06-21T...",
                "_model": "anthropic/MiniMax-M3",
                "_temperature": 0.2,
                "response": "..."
            }
    
    Hash 策略：messages + model + temperature 的 SHA256
    """
    
    def __init__(self, cache_dir: str = ".sge_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def cached_chat(
        self,
        client: SGELLMClient,
        messages: list,
        temperature: float = 0.5,
        max_tokens: int = 1024,
        **kwargs,
    ) -> str:
        """带缓存的 chat 调用"""
        cache_key = self._compute_key(messages, client.model, temperature, kwargs)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            data = json.loads(cache_file.read_text())
            return data['response']
        
        # 缓存未命中 → 调用 LLM
        response = client.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        
        # 写入缓存
        cache_file.write_text(json.dumps({
            '_cached_at': time.time(),
            '_model': client.model,
            '_temperature': temperature,
            'response': response,
        }))
        
        return response
    
    def _compute_key(self, messages, model, temperature, kwargs) -> str:
        """计算 cache key（SHA256）"""
        payload = json.dumps({
            'messages': messages,
            'model': model,
            'temperature': temperature,
            'kwargs': kwargs,
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]
    
    def clear(self):
        """清空缓存（开发时用）"""
        for f in self.cache_dir.glob('*.json'):
            f.unlink()
    
    def stats(self) -> dict:
        """缓存统计"""
        files = list(self.cache_dir.glob('*.json'))
        return {
            'total_entries': len(files),
            'total_size_mb': sum(f.stat().st_size for f in files) / 1024 / 1024,
        }
```

---

## 3. 集成到 SGELLMClient

```python
# 方案 A：透明包装（推荐）
cache = SGELLMCache(cache_dir='.sge_cache')

client = make_llm_client(provider='minimax')
# 原始 chat
response = client.chat(messages, temperature=0.5)
# 带缓存
response = cache.cached_chat(client, messages, temperature=0.5)
```

```python
# 方案 B：直接集成到 SGELLMClient
class SGELLMClient:
    def __init__(self, ..., enable_cache: bool = False):
        self.cache = SGELLMCache() if enable_cache else None
    
    def chat(self, messages, ...):
        if self.cache:
            return self.cache.cached_chat(self, messages, ...)
        # 原始逻辑
        ...
```

---

## 4. 缓存策略

### 4.1 什么该缓存

| ✅ 缓存 | ❌ 不缓存 |
|--------|---------|
| Critic 感知（temperature=0.2 稳定）| 高 temperature（>0.7）随机生成 |
| Actor 表达（temperature=0.9 每次不同，**不缓存**）| — |
| Identity 结晶（稳定）| Narrative 生成（每次不同）|
| Deterministic 部分 | Random 部分 |

### 4.2 缓存失效

| 触发 | 处理 |
|------|------|
| 缓存文件损坏 | 重新调用 LLM |
| 模型变更 | 失效（hash 含 model）|
| Temperature 变更 | 失效（hash 含 temperature）|
| 用户主动 `clear()` | 删除所有缓存 |

### 4.3 存储位置

```
~/.sge_cache/                # 默认（用户级）
./.sge_cache/                # 项目级（gitignored）
/tmp/sge_cache/              # 临时（CI/测试）
```

**.gitignore** 应包含：`.sge_cache/`

---

## 5. 性能影响

| 场景 | 无缓存 | 有缓存 | 节省 |
|------|--------|--------|------|
| M2.2 chunk 重跑 | 6600 calls × 5s = 9h | 6600 calls × 0.5s (hash) = 55min | 8h |
| 单元测试（mock LLM）| 100 calls × 5s = 8min | 1 call + 99 cache hit = 10s | 8min |
| 调试时改 prompt | 全部重跑 | 仅变化部分重跑 | — |

**关键价值**：调试时可重现性（同样的 prompt 同样的 response）。

---

## 6. 实施清单

| 子任务 | 工作量 |
|--------|--------|
| `sge/llm_cache.py` (SGELLMCache) | 0.5 天 |
| 单元测试（hash 唯一性、缓存命中、失效）| 0.5 天 |
| 集成到 SGELLMClient（可选开关）| 0.5 天 |
| 文档 + 示例 | 0.5 天 |
| **总计** | **2 天** |

---

## 7. 关联文档

- [README.md §P1 任务](../README.md)
- [02-architecture.md §LLM cache 放 SGE 包 vs App](../../00-overview/02-architecture.md)
- [discussions/2026-06-22-...-aibeing-reflection.md §2.3](../../../discussions/2026-06-22-sge-phase3-aibeing-reflection.md) — AiBeing cache 借鉴

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-22
