# 10-05 - Prompt 版本管理

> **目的**：A/B 测试不同 prompt + 版本控制 + 不破坏历史数据
> **来源**：借鉴 AiBeing `prompt/` 目录结构

---

## 1. 为什么需要 Prompt 管理

**当前问题**：
- Critic / Actor prompt 硬编码在 `sge/critic.py` / `sge/actor.py`
- 改 prompt → 改代码 → 重跑所有实验
- 无法 A/B 测试"哪个 prompt 让 AI 回答更连贯"
- 无法保留"老版本 prompt 生成的 Identity"以做对比

**Solution**：prompt 模板外置 + 版本管理

---

## 2. 目录结构

```
sge/prompts/
├── README.md                      # Prompt 管理说明
├── critic/
│   ├── v1_basic.txt              # 基础 prompt
│   ├── v2_with_subject.txt       # 加入学科 context
│   ├── v3_chain_of_thought.txt   # 加入 CoT 推理
│   └── current -> v3_chain_of_thought.txt   # symlink 当前版本
├── actor/
│   ├── v1_basic.txt
│   ├── v2_with_mastery.txt
│   └── current -> v2_with_mastery.txt
├── identity_crystallize/
│   └── v1_basic.txt
├── narrative_build/
│   └── v1_basic.txt
└── version_history.md            # 每个版本变更记录
```

**每个 prompt 文件格式**：纯文本 + `{variable}` 占位符

```txt
# sge/prompts/critic/v1_basic.txt
你是 SGE 的情感感知器（Critic），分析以下事件并输出 JSON。

[当前状态]
价值向量: {vv_str}
drives 状态: {drv_str}

[事件]
类型: {event_type}
描述: {event_description}
强度: {event_intensity}

[输出格式 - 仅 JSON，无其他文字]
{{
  "context": {{...}},
  "value_delta": {{...}},
  "frustration_delta": {{...}}
}}
```

---

## 3. PromptLoader

```python
import os
from pathlib import Path
from typing import Optional

class PromptLoader:
    """Prompt 模板加载器（支持版本切换）"""
    
    DEFAULT_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        self.prompts_dir = prompts_dir or self.DEFAULT_PROMPTS_DIR
    
    def load(self, category: str, version: str = 'current') -> str:
        """加载 prompt 模板
        
        Args:
            category: 'critic' / 'actor' / 'identity_crystallize' / 'narrative_build'
            version: 'v1_basic' / 'v2_with_subject' / 'current'
        """
        if version == 'current':
            # 跟随 symlink
            current_link = self.prompts_dir / category / "current"
            version_file = current_link.resolve()
        else:
            version_file = self.prompts_dir / category / f"{version}.txt"
        
        if not version_file.exists():
            raise FileNotFoundError(f"Prompt not found: {version_file}")
        
        return version_file.read_text(encoding='utf-8')
    
    def list_versions(self, category: str) -> list:
        """列出某 category 的所有版本"""
        cat_dir = self.prompts_dir / category
        return sorted([f.stem for f in cat_dir.glob("v*.txt")])
    
    def render(self, category: str, version: str = 'current', **variables) -> str:
        """加载 + 渲染 prompt"""
        template = self.load(category, version)
        return template.format(**variables)
```

---

## 4. 集成到 Critic / Actor

```python
# sge/critic.py
from .prompt_loader import PromptLoader

class CriticModule:
    def __init__(self, prompt_version: str = 'current'):
        self.prompt_loader = PromptLoader()
        self.prompt_version = prompt_version
    
    def sense(self, event, drives, values, llm, ...):
        # 加载 prompt（可指定版本）
        prompt = self.prompt_loader.render(
            category='critic',
            version=self.prompt_version,
            vv_str=', '.join(f"{k}={v:.3f}" for k, v in values.items()),
            drv_str=', '.join(f"{k}={v:.3f}" for k, v in drives.items()),
            event_type=event.get('event_type'),
            event_description=event.get('description'),
            event_intensity=event.get('intensity'),
        )
        
        # 调用 LLM
        return llm.chat_json(messages=[{"role": "user", "content": prompt}], ...)
```

**实验配置**：
```python
# 默认用 current（symlink 指向最新）
critic = CriticModule()

# A/B 测试用不同版本
critic_v1 = CriticModule(prompt_version='v1_basic')
critic_v3 = CriticModule(prompt_version='v3_chain_of_thought')
```

---

## 5. 版本管理实践

### 5.1 何时升级 prompt

- **新增字段支持** → 新版本（如 v2_with_subject）
- **改进推理逻辑** → 新版本（如 v3_chain_of_thought）
- **修复 bug** → 新版本（minor change）

### 5.2 版本历史

```markdown
# version_history.md

## v3_chain_of_thought (2026-06-25)
- 加入 chain-of-thought 推理
- 期望：提高 Critic 输出一致性

## v2_with_subject (2026-06-22)
- 加入 subject 字段（如 'math'）
- 期望：subject-specific 价值变化更准确

## v1_basic (2026-06-15)
- 初版
- 来源：M2.1 默认 critic.py 中的硬编码 prompt
```

### 5.3 不破坏历史数据

- 新版本用新文件名（v2, v3, ...）
- 老版本保留（不删除）
- 用 `current` symlink 指向当前推荐版本
- 老实验结果用对应版本 prompt 生成（不重新跑）

---

## 6. A/B 测试设计

```python
# 实验：v1 vs v3 critic prompt 对 Identity 一致性的影响
results_v1 = run_triplets(prompt_version='v1_basic')
results_v3 = run_triplets(prompt_version='v3_chain_of_thought')

# 对比 Identity 一致性（M2.3 评估方法）
from m23_evaluate_consistency import evaluate_consistency
consistency_v1 = evaluate_consistency(results_v1)
consistency_v3 = evaluate_consistency(results_v3)
# → 哪个 prompt 让 AI 回答更连贯？
```

---

## 7. 实施清单

| 子任务 | 工作量 |
|--------|--------|
| `sge/prompts/` 目录 + 初始 4 个 prompt 文件 | 0.5 天 |
| `sge/prompt_loader.py` (PromptLoader) | 0.5 天 |
| Critic / Actor 集成 PromptLoader | 0.5 天 |
| 文档 + A/B 测试示例 | 0.5 天 |
| **总计** | **2 天** |

---

## 8. 关联文档

- [README.md §P2 任务](../README.md)
- [02-architecture.md §Prompt 版本管理位置](../../00-overview/02-architecture.md)
- [discussions/2026-06-22-...-aibeing-reflection.md §2.5](../../../discussions/2026-06-22-sge-phase3-aibeing-reflection.md) — AiBeing prompt 管理借鉴

---

**维护者**：Bisen & Claude
**创建日期**：2026-06-22
