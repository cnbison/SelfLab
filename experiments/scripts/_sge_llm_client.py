"""
SGE LLM 客户端统一封装（阶段 D 真实 LLM 验证引入）

本文件解决两个问题：
  1. _sge_critic.py 用 litellm，_sge_actor.py 用 anthropic-style — 不一致
  2. Orchestrator 缺统一的 LLM 实例加载入口

**为什么是独立文件**：
- SGE 所有 LLM 调用走同一个客户端（避免分散配置）
- 与 _sge_critic.py / _sge_actor.py 解耦（API 变化不影响业务代码）
- 为 Phase 3 多 LLM provider 留接口（MiniMax / Moonshot / OpenAI）

**当前支持**：
- MiniMax-M3（默认，Anthropic 兼容协议，litellm）

**未来扩展**（Phase 3）：
- Moonshot kimi-k2.6（OpenAI 兼容协议）
- OpenAI gpt-4o
- 自部署模型

关联文档：
- [SGE-M21-Phase-D-Implementation-Plan.md](../research/sge-feasibility/SGE-M21-Phase-D-Implementation-Plan.md)
- [m11_smoke_test.py setup_environment()](../m11_smoke_test.py)（M1.1 已验证的 LLM 调用模式）
"""

from __future__ import annotations

import os
import json
import logging
from typing import Optional, Any

# 自动加载 .env（如果 python-dotenv 可用）
try:
    from dotenv import load_dotenv
    load_dotenv()  # 在 SGE 仓库根目录查找 .env
except ImportError:
    pass  # 没有 dotenv 就靠用户手动 export

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════
# LLM Provider 配置（SSOT）
# ══════════════════════════════════════════════

LLM_PROVIDER_CONFIG = {
    'minimax': {
        'api_key_env': 'MINIMAX_API_KEY',
        'base_url': 'https://api.minimax.io/anthropic',
        'model': 'anthropic/MiniMax-M3',
        'default_temperature': 0.5,
    },
    'moonshot': {
        'api_key_env': 'MOONSHOT_API_KEY',
        'base_url': 'https://api.moonshot.cn/v1',
        'model': 'openai/kimi-k2.6',
        'default_temperature': 0.6,
        'extra_body': {'thinking': {'type': 'disabled'}},  # 关闭 kimi 内部推理
    },
}


# ══════════════════════════════════════════════
# SGE LLM Client 统一类
# ══════════════════════════════════════════════


class SGELLMClient:
    """SGE 统一 LLM 客户端（阶段 D 真实 LLM 验证引入）

    用法：
      client = SGELLMClient(provider='minimax')
      response = client.chat(
          messages=[{'role': 'user', 'content': '...'}],
          temperature=0.2,
      )

    设计原则：
      - 所有 SGE 模块（Critic / Actor / Identity / Narrative / Reflector）统一调用
      - 自动从 .env 加载 API key
      - 自动处理 JSON 解析（兼容 markdown fence）
      - 失败时回退到 stub（避免实验中断）

    Attributes:
        provider: str — LLM provider 名称（'minimax' / 'moonshot'）
        api_key: str — API key（从 env 读）
        base_url: str — API endpoint
        model: str — litellm 模型名（如 'anthropic/MiniMax-M3'）
        call_count: int — 总调用次数（用于成本统计）
    """

    def __init__(
        self,
        provider: str = 'minimax',
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        verbose: bool = False,
    ):
        if provider not in LLM_PROVIDER_CONFIG:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Supported: {list(LLM_PROVIDER_CONFIG.keys())}"
            )
        cfg = LLM_PROVIDER_CONFIG[provider]

        self.provider = provider
        self.api_key = api_key or os.environ.get(cfg['api_key_env'])
        if not self.api_key:
            raise ValueError(
                f"{cfg['api_key_env']} environment variable not set. "
                f"Please add it to your .env file or set it before running."
            )
        self.base_url = base_url or cfg['base_url']
        self.model = model or cfg['model']
        self.default_temperature = cfg['default_temperature']
        self.extra_body = cfg.get('extra_body')
        self.verbose = verbose
        self.call_count = 0

        # 检查 litellm 是否安装
        try:
            from litellm import completion  # noqa: F401
        except ImportError:
            raise ImportError(
                "litellm is required. Install with: pip install litellm"
            )

        if verbose:
            print(f"✓ SGELLMClient: provider={provider}, model={self.model}, "
                  f"base_url={self.base_url}, api_key={self.api_key[:8]}...")

    def chat(
        self,
        messages: list,
        temperature: Optional[float] = None,
        max_tokens: int = 1024,
        response_format: Optional[dict] = None,
    ) -> str:
        """调用 LLM 并返回 response 内容

        Args:
            messages: OpenAI-style message list（[{"role": "user", "content": "..."}]）
            temperature: 温度（None → 用 provider 默认）
            max_tokens: 最大输出 token
            response_format: 强制 JSON 输出（可选，{'type': 'json_object'}）

        Returns:
            response content (str)

        Raises:
            RuntimeError: LLM 调用失败（非网络问题也会回退到 stub 在 caller 端处理）
        """
        from litellm import completion

        if temperature is None:
            temperature = self.default_temperature

        kwargs = dict(
            model=self.model,
            messages=messages,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if response_format is not None:
            kwargs['response_format'] = response_format
        if self.extra_body is not None:
            kwargs['extra_body'] = self.extra_body

        response = completion(**kwargs)
        self.call_count += 1

        # 兼容 OpenAI / Anthropic 风格
        content = response.choices[0].message.content.strip()

        if self.verbose:
            logger.debug(f"[LLM call #{self.call_count}] temp={temperature} "
                         f"max_tokens={max_tokens} response_len={len(content)}")

        return content

    def chat_json(
        self,
        messages: list,
        temperature: Optional[float] = None,
        max_tokens: int = 1024,
        fallback_value: Any = None,
    ) -> Any:
        """调用 LLM 并解析 JSON

        自动处理 markdown fence（```json ... ```）。
        失败时返回 fallback_value（默认 None），让 caller 决定如何处理。

        Args:
            messages: OpenAI-style message list
            temperature: 温度
            max_tokens: 最大输出 token
            fallback_value: 解析失败时的回退值

        Returns:
            解析后的 dict/list/任何 JSON 类型
        """
        content = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return self._parse_json(content, fallback_value)

    @staticmethod
    def _parse_json(content: str, fallback_value: Any = None) -> Any:
        """解析 LLM 输出的 JSON（兼容多种格式）"""
        # 提取 ```json ... ``` 内容
        if '```json' in content:
            try:
                content = content.split('```json', 1)[1].split('```', 1)[0]
            except IndexError:
                pass
        elif '```' in content:
            try:
                content = content.split('```', 1)[1].split('```', 1)[0]
            except IndexError:
                pass

        content = content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"[LLM JSON parse failed] {e}")
            logger.warning(f"[LLM raw content] {content[:300]}")
            return fallback_value

    def stats(self) -> dict:
        """返回 LLM 调用统计"""
        return {
            'provider': self.provider,
            'model': self.model,
            'call_count': self.call_count,
        }


# ══════════════════════════════════════════════
# 便捷工厂函数
# ══════════════════════════════════════════════


def make_llm_client(
    provider: str = 'minimax',
    verbose: bool = False,
) -> SGELLMClient:
    """构造 SGELLMClient（推荐入口）

    用法：
      client = make_llm_client()
      response = client.chat_json([{"role": "user", "content": "..."}])
    """
    return SGELLMClient(provider=provider, verbose=verbose)


if __name__ == "__main__":
    # 模块直接运行：测试 SGELLMClient 是否能连通
    print("═" * 60)
    print("  SGELLMClient 连接测试")
    print("═" * 60)

    client = make_llm_client(provider='minimax', verbose=True)

    response = client.chat(
        messages=[{"role": "user", "content": "用一句话介绍你自己"}],
        temperature=0.5,
        max_tokens=200,
    )
    print(f"\n响应: {response[:300]}")

    print(f"\n统计: {client.stats()}")