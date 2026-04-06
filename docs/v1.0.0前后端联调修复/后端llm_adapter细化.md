# LLM Adapter 模块文档

> **文档类型**：接口文档
> **日期**：2026-04-06
> **更新**：2026-04-06 重构，精简为实现状态和接口清单

---

## 一、模块概述

LLM Adapter 模块位于 `backend/services/llm/`，提供统一的 LLM 调用接口。

### 文件结构

```
backend/services/llm/
├── adapter.py        # 适配器实现
├── budget.py         # Token 预算控制
├── errors.py         # 错误类型定义
├── manager.py        # Provider 管理器
├── models.py         # 模型信息
├── providers.py      # Provider 配置
├── providers.json    # Provider 列表
├── resilience.py     # 重试与熔断
├── types.py          # 类型定义
└── __init__.py      # 模块导出
```

---

## 二、已实现功能

### 2.1 适配器 (adapter.py)

| 类 | 说明 | 主要方法 |
|---|------|---------|
| `LLMAdapter` | 抽象基类 | `chat()`, `chat_stream()` |
| `ClaudeAdapter` | Anthropic Claude API | 继承 + SSE 流式 |
| `OpenAIAdapter` | OpenAI ChatGPT API | 继承 + SSE 流式 |
| `LocalAdapter` | Ollama 等本地模型 | 继承 + SSE 流式 |
| `OpenAICompatibleAdapter` | DeepSeek/Qwen/Groq 等 | 继承 + `chat_with_tools()` |

### 2.2 错误处理 (errors.py)

| 错误类型 | 说明 |
|---------|------|
| `LLMError` | 基类错误 |
| `RateLimitError` | 限流错误 (429) |
| `AuthError` | 认证错误 (401) |
| `QuotaError` | 配额超限 |
| `InvalidRequestError` | 无效请求 (400) |
| `ModelNotFoundError` | 模型不存在 (404) |
| `NetworkError` | 网络错误 |
| `TimeoutError` | 超时错误 |
| `ContextOverflowError` | 上下文溢出 |

### 2.3 模型信息 (models.py)

```python
class ModelInfo(BaseModel):
    name: Optional[str] = None
    max_tokens: int = 1024
    context_window: int = 128000
    supports_images: bool = False
    supports_reasoning: bool = False
    input_price: Optional[float] = None  # 每百万 token
    output_price: Optional[float] = None
```

### 2.4 Provider 配置 (providers.py)

支持 10+ Provider：claude, openai, deepseek, groq, ollama, gemini, qwen 等。

### 2.5 预算控制 (budget.py)

```python
class TokenBudget:
    """Token 预算管理器"""
    def check_budget(self, estimated_tokens: int) -> tuple[bool, str]
    def record_usage(self, input_tokens: int, output_tokens: int, ...)
    def get_status(self) -> BudgetStatus
```

### 2.6 弹性机制 (resilience.py)

- `CircuitBreaker` - 熔断器
- `with_retry` - 指数退避重试装饰器
- `ResilientAdapter` - 弹性适配器封装

### 2.7 管理器 (manager.py)

```python
class LLMManager:
    """Provider 管理器，支持健康检查和自动降级"""
    def get_adapter(self, provider: str) -> LLMAdapter
    async def health_check(self, provider: str) -> ProviderHealth
    async def get_best_provider(self) -> Optional[str]
```

---

## 三、接口清单

### 3.1 核心接口

```python
# 获取适配器
from backend.services.llm import get_llm_adapter

adapter = get_llm_adapter(
    provider: str = "claude",  # claude/openai/deepseek/groq/ollama 等
    model: Optional[str] = None,  # 默认使用配置
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
) -> LLMAdapter

# 基本聊天
response = await adapter.chat(
    messages: list[dict],      # [{"role": "user", "content": "..."}]
    system_prompt: str,         # 系统提示
    user_api_key: str = None,   # 用户 API Key（优先级最高）
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    **kwargs
) -> str

# 流式聊天
async for chunk in adapter.chat_stream(messages, system_prompt):
    print(chunk, end="")

# 带工具调用（仅 OpenAICompatibleAdapter）
text, tool_calls = await adapter.chat_with_tools(
    messages: list[dict],
    tools: list[Tool],          # from backend.services.llm import Tool
    system_prompt: str = "",
    tool_choice: str = "auto"   # "auto"/"any"/"none"
) -> tuple[str, list[ToolCall]]
```

### 3.2 工具定义

```python
from backend.services.llm import Tool, ToolCall

# 定义工具
tool = Tool(
    name="get_weather",
    description="获取指定城市的天气",
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名"}
        },
        "required": ["city"]
    }
)

# 处理工具调用
for tc in tool_calls:
    print(f"Tool: {tc.name}, Args: {tc.arguments}")
```

### 3.3 错误处理

```python
from backend.services.llm import LLMError, RateLimitError, AuthError

try:
    response = await adapter.chat(messages, system_prompt)
except RateLimitError as e:
    print(f"限流: {e.message}")
except AuthError as e:
    print(f"认证失败: {e.message}")
except LLMError as e:
    print(f"LLM 错误: {e.code} - {e.message}")
```

### 3.4 预算控制

```python
from backend.services.llm import get_user_budget

budget = get_user_budget(user_id=1)

# 检查预算
allowed, reason = budget.check_budget(
    estimated_input_tokens=1000,
    estimated_output_tokens=2000,
    model="gpt-4"
)

# 记录使用
budget.record_usage(
    input_tokens=1000,
    output_tokens=2000,
    provider="openai",
    model="gpt-4"
)

# 获取状态
status = budget.get_status()
print(f"今日已用: {status.daily_used_tokens}/{status.daily_limit}")
```

### 3.5 Provider 管理

```python
from backend.services.llm import LLMManager, get_llm_manager

manager = get_llm_manager()

# 获取最佳 Provider
provider = await manager.get_best_provider()

# 健康检查
health = await manager.health_check("claude")
print(f"健康: {health.healthy}, 延迟: {health.latency_ms}ms")

# 获取适配器
adapter = manager.get_adapter("deepseek")
```

---

## 四、调用示例

### 4.1 基础调用

```python
from backend.services.llm import get_llm_adapter

adapter = get_llm_adapter("claude")
response = await adapter.chat(
    messages=[{"role": "user", "content": "你好"}],
    system_prompt="你是一个有帮助的助手"
)
```

### 4.2 带工具调用

```python
from backend.services.llm import get_llm_adapter, Tool

tools = [
    Tool(
        name="calculator",
        description="计算数学表达式",
        parameters={
            "type": "object",
            "properties": {
                "expression": {"type": "string"}
            },
            "required": ["expression"]
        }
    )
]

adapter = get_llm_adapter("deepseek")
text, tool_calls = await adapter.chat_with_tools(
    messages=[{"role": "user", "content": "计算 2+2"}],
    tools=tools
)
```

### 4.3 流式输出

```python
adapter = get_llm_adapter("openai")
async for chunk in adapter.chat_stream(
    messages=[{"role": "user", "content": "写一首诗"}],
    system_prompt="你是一个诗人"
):
    print(chunk, end="", flush=True)
```

---

## 五、待办事项

| 优先级 | 问题 | 状态 |
|--------|------|------|
| P3 | 官方 SDK 迁移（anthropic/openai） | ❌ 未实现 |
| P3 | 响应缓存 | ❌ 未实现 |
| P3 | 流式输出完善（Claude SSE） | ❌ 未实现 |

---

## 六、详细文档（附录）

详细的问题分析、改进方案、Cline 对比等内容已移至：

- 内部文档（Claude.md）
- 原始分析文档备份

---

*最后更新：2026-04-06*
