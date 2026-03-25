import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


class LLMAdapter(ABC):
    """Base class for LLM adapters"""

    @abstractmethod
    async def chat(self, messages: list, system_prompt: str, user_api_key: str = None) -> str:
        """Send chat request and get response"""
        pass

    @abstractmethod
    async def chat_stream(self, messages: list, system_prompt: str, user_api_key: str = None) -> AsyncGenerator[str, None]:
        """Stream chat response"""
        pass


class ClaudeAdapter(LLMAdapter):
    """Anthropic Claude API adapter"""

    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        self.model = model
        self.base_url = "https://api.anthropic.com/v1"

    async def chat(self, messages: list, system_prompt: str, user_api_key: str = None) -> str:
        """Send chat request to Claude API"""
        import httpx
        from backend.core.config import get_settings

        settings = get_settings()
        api_key = user_api_key or settings.llm_providers.get("claude", {}).get("api_key", "")

        if not api_key:
            return "请先在设置中配置API Key"

        # Convert messages to Claude format
        claude_messages = []
        for msg in messages:
            claude_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 1024,
                        "system": system_prompt,
                        "messages": claude_messages
                    },
                    timeout=60.0
                )
                if response.status_code == 200:
                    data = response.json()
                    usage = data.get("usage", {})
                    logger.info(
                        "LLM usage: provider=claude model=%s in_tokens=%d out_tokens=%d",
                        self.model,
                        usage.get("input_tokens", 0),
                        usage.get("output_tokens", 0),
                    )
                    return data.get("content", [{}])[0].get("text", "")
                else:
                    return f"API调用失败: {response.status_code}"
            except Exception as e:
                return f"API调用错误: {str(e)}"

    async def chat_stream(self, messages: list, system_prompt: str, user_api_key: str = None) -> AsyncGenerator[str, None]:
        """Stream chat response (Claude doesn't support streaming, yield chunks)"""
        response = await self.chat(messages, system_prompt, user_api_key)
        # Simple chunking for demo
        for word in response.split():
            yield word + " "


class OpenAIAdapter(LLMAdapter):
    """OpenAI API adapter"""

    def __init__(self, model: str = "gpt-4"):
        self.model = model

    async def chat(self, messages: list, system_prompt: str, user_api_key: str = None) -> str:
        """Send chat request to OpenAI API"""
        import httpx
        from backend.core.config import get_settings

        settings = get_settings()
        api_key = user_api_key or settings.llm_providers.get("openai", {}).get("api_key", "")

        if not api_key:
            return "请先在设置中配置API Key"

        # Convert messages to OpenAI format with system prompt
        openai_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            openai_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "content-type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": openai_messages,
                        "max_tokens": 1024
                    },
                    timeout=60.0
                )
                if response.status_code == 200:
                    data = response.json()
                    usage = data.get("usage", {})
                    logger.info(
                        "LLM usage: provider=openai model=%s in_tokens=%d out_tokens=%d",
                        self.model,
                        usage.get("prompt_tokens", 0),
                        usage.get("completion_tokens", 0),
                    )
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                else:
                    return f"API调用失败: {response.status_code}"
            except Exception as e:
                return f"API调用错误: {str(e)}"

    async def chat_stream(self, messages: list, system_prompt: str, user_api_key: str = None) -> AsyncGenerator[str, None]:
        """Stream chat response"""
        # Placeholder for streaming implementation
        response = await self.chat(messages, system_prompt, user_api_key)
        for word in response.split():
            yield word + " "


class LocalAdapter(LLMAdapter):
    """Local model adapter (Ollama, etc.)"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "llama2"

    async def chat(self, messages: list, system_prompt: str, user_api_key: str = None) -> str:
        """Send chat request to local model"""
        import httpx

        # Convert messages format
        local_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            local_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": local_messages,
                        "stream": False
                    },
                    timeout=120.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("message", {}).get("content", "")
                else:
                    return f"本地模型调用失败: {response.status_code}"
            except Exception as e:
                return f"本地模型调用错误: {str(e)}"

    async def chat_stream(self, messages: list, system_prompt: str, user_api_key: str = None) -> AsyncGenerator[str, None]:
        """Stream from local model"""
        import httpx

        local_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            local_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": local_messages,
                    "stream": True
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json
                        try:
                            data = json.loads(line)
                            if "message" in data:
                                yield data["message"].get("content", "")
                        except:
                            pass


def get_llm_adapter(provider: str = "claude") -> LLMAdapter:
    """Factory function to get LLM adapter"""
    from backend.core.config import get_settings

    settings = get_settings()

    if provider == "claude":
        model = settings.llm_providers.get("claude", {}).get("model", "claude-3-5-sonnet-20241022")
        return ClaudeAdapter(model=model)
    elif provider == "openai":
        model = settings.llm_providers.get("openai", {}).get("model", "gpt-4")
        return OpenAIAdapter(model=model)
    elif provider == "local":
        return LocalAdapter()
    else:
        return ClaudeAdapter()