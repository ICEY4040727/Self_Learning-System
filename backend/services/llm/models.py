"""
LLM 模型配置模块

定义 ModelInfo 模型元信息，包含价格、能力、限制等。
参考 Cline 的 ModelInfo 设计。
"""

from typing import Optional
from pydantic import BaseModel


class ModelInfo(BaseModel):
    """
    模型元信息
    
    包含模型的所有配置和能力信息，用于：
    - Token 限制和上下文窗口
    - 能力支持（图像、思考模式、缓存等）
    - 价格信息（用于成本计算）
    """
    name: Optional[str] = None
    max_tokens: int = 1024  # 单次回复最大 token 数
    context_window: int = 128000  # 上下文窗口大小
    supports_images: bool = False  # 是否支持图像输入
    supports_reasoning: bool = False  # 是否支持思考模式（如 Claude 的 Extended Thinking）
    supports_prompt_cache: bool = False  # 是否支持提示缓存
    supports_vision: bool = False  # 是否支持视觉（图像理解）
    
    # 价格信息（每百万 token）
    input_price: Optional[float] = None
    output_price: Optional[float] = None
    cache_writes_price: Optional[float] = None  # 缓存写入价格
    cache_reads_price: Optional[float] = None  # 缓存读取价格
    
    # 生成参数默认值
    temperature: float = 0.7
    top_p: float = 1.0
    
    # 描述
    description: Optional[str] = None
    
    def get_input_cost(self, tokens: int) -> float:
        """计算输入 token 的成本"""
        if self.input_price is None:
            return 0.0
        return (tokens / 1_000_000) * self.input_price
    
    def get_output_cost(self, tokens: int) -> float:
        """计算输出 token 的成本"""
        if self.output_price is None:
            return 0.0
        return (tokens / 1_000_000) * self.output_price


# ============================================================================
# Claude Models
# ============================================================================

CLAUDE_MODELS = {
    "claude-3-5-sonnet-20241022": ModelInfo(
        name="Claude 3.5 Sonnet",
        max_tokens=8192,
        context_window=200000,
        supports_reasoning=True,
        supports_prompt_cache=True,
        input_price=3.0,
        output_price=15.0,
        cache_writes_price=3.75,
        cache_reads_price=0.3,
        description="Latest flagship model with enhanced reasoning and coding",
    ),
    "claude-3-5-haiku-20241022": ModelInfo(
        name="Claude 3.5 Haiku",
        max_tokens=8192,
        context_window=200000,
        supports_prompt_cache=True,
        input_price=0.8,
        output_price=4.0,
        cache_writes_price=1.0,
        cache_reads_price=0.08,
        description="Fast and affordable model for simple tasks",
    ),
    "claude-opus-4-20250514": ModelInfo(
        name="Claude Opus 4",
        max_tokens=8192,
        context_window=200000,
        supports_reasoning=True,
        supports_prompt_cache=True,
        input_price=15.0,
        output_price=75.0,
        cache_writes_price=18.75,
        cache_reads_price=1.5,
        description="Most capable model for complex tasks",
    ),
    "claude-sonnet-4-20250514": ModelInfo(
        name="Claude Sonnet 4",
        max_tokens=8192,
        context_window=200000,
        supports_reasoning=True,
        supports_prompt_cache=True,
        input_price=3.0,
        output_price=15.0,
        cache_writes_price=3.75,
        cache_reads_price=0.3,
        description="Balanced model for most tasks",
    ),
}


# ============================================================================
# OpenAI Models
# ============================================================================

OPENAI_MODELS = {
    "gpt-4o": ModelInfo(
        name="GPT-4o",
        max_tokens=4096,
        context_window=128000,
        supports_images=True,
        input_price=5.0,
        output_price=15.0,
        description="Fast and capable with image support",
    ),
    "gpt-4o-mini": ModelInfo(
        name="GPT-4o Mini",
        max_tokens=16384,
        context_window=128000,
        supports_images=True,
        input_price=0.15,
        output_price=0.6,
        description="Affordable and fast small model",
    ),
    "gpt-4-turbo": ModelInfo(
        name="GPT-4 Turbo",
        max_tokens=4096,
        context_window=128000,
        supports_images=True,
        input_price=10.0,
        output_price=30.0,
        description="Previous flagship with vision support",
    ),
    "gpt-4": ModelInfo(
        name="GPT-4",
        max_tokens=4096,
        context_window=8192,
        input_price=30.0,
        output_price=60.0,
        description="Original GPT-4 model",
    ),
    "gpt-3.5-turbo": ModelInfo(
        name="GPT-3.5 Turbo",
        max_tokens=4096,
        context_window=16385,
        input_price=0.5,
        output_price=1.5,
        description="Fast and affordable model",
    ),
}


# ============================================================================
# OpenAI-Compatible / Local Models
# ============================================================================

OPENAI_COMPATIBLE_MODELS = {
    "deepseek-chat": ModelInfo(
        name="DeepSeek Chat",
        max_tokens=4096,
        context_window=128000,
        input_price=0.14,
        output_price=0.28,
        description="DeepSeek's chat model",
    ),
    "deepseek-coder": ModelInfo(
        name="DeepSeek Coder",
        max_tokens=4096,
        context_window=128000,
        input_price=0.14,
        output_price=0.28,
        description="DeepSeek's code model",
    ),
    "qwen-plus": ModelInfo(
        name="Qwen Plus",
        max_tokens=4096,
        context_window=131072,
        input_price=0.8,
        output_price=2.4,
        description="Alibaba Qwen Plus",
    ),
    "qwen-turbo": ModelInfo(
        name="Qwen Turbo",
        max_tokens=4096,
        context_window=131072,
        input_price=0.3,
        output_price=0.6,
        description="Alibaba Qwen Turbo",
    ),
    "moonshot-v1-8k": ModelInfo(
        name="Moonshot V1 8K",
        max_tokens=4096,
        context_window=8192,
        input_price=0.6,
        output_price=0.6,
        description="Moonshot AI's model",
    ),
    "moonshot-v1-32k": ModelInfo(
        name="Moonshot V1 32K",
        max_tokens=8192,
        context_window=32768,
        input_price=1.2,
        output_price=1.2,
        description="Moonshot AI's 32K context model",
    ),
}


# ============================================================================
# MiniMax Models
# ============================================================================

MINIMAX_MODELS = {
    "MiniMax-M2.7-highspeed": ModelInfo(
        name="MiniMax M2.7 Highspeed",
        max_tokens=128000,
        context_window=192000,
        supports_reasoning=True,
        input_price=0.6,
        output_price=2.4,
        description="MiniMax M2.7 high-speed version for low-latency scenarios",
    ),
    "MiniMax-M2.7": ModelInfo(
        name="MiniMax M2.7",
        max_tokens=128000,
        context_window=192000,
        supports_reasoning=True,
        input_price=0.3,
        output_price=1.2,
        description="MiniMax M2.7 flagship model",
    ),
    "MiniMax-M2.5-highspeed": ModelInfo(
        name="MiniMax M2.5 Highspeed",
        max_tokens=128000,
        context_window=192000,
        supports_reasoning=True,
        input_price=0.6,
        output_price=2.4,
        description="MiniMax M2.5 high-speed version",
    ),
    "MiniMax-M2.5": ModelInfo(
        name="MiniMax M2.5",
        max_tokens=128000,
        context_window=192000,
        supports_reasoning=True,
        input_price=0.3,
        output_price=1.2,
        description="MiniMax M2.5 model",
    ),
    "MiniMax-M2.1": ModelInfo(
        name="MiniMax M2.1",
        max_tokens=128000,
        context_window=192000,
        input_price=0.3,
        output_price=1.2,
        description="MiniMax M2.1 model",
    ),
}


# ============================================================================
# Ollama / Local Models (默认配置)
# ============================================================================

OLLAMA_MODELS = {
    "llama3": ModelInfo(
        name="Llama 3",
        max_tokens=2048,
        context_window=8192,
        description="Meta's Llama 3 8B",
    ),
    "llama3.1": ModelInfo(
        name="Llama 3.1",
        max_tokens=2048,
        context_window=128000,
        description="Meta's Llama 3.1 8B",
    ),
    "llama3.2": ModelInfo(
        name="Llama 3.2",
        max_tokens=2048,
        context_window=128000,
        supports_vision=True,
        description="Meta's Llama 3.2 with vision",
    ),
    "mistral": ModelInfo(
        name="Mistral",
        max_tokens=2048,
        context_window=8192,
        description="Mistral AI's model",
    ),
    "mixtral": ModelInfo(
        name="Mixtral",
        max_tokens=2048,
        context_window=32768,
        description="Mistral AI's Mixtral mixture of experts",
    ),
    "codellama": ModelInfo(
        name="Code Llama",
        max_tokens=2048,
        context_window=16384,
        description="Meta's Code Llama",
    ),
}


# ============================================================================
# All Models Registry
# ============================================================================

# 合并所有模型
ALL_MODELS: dict[str, ModelInfo] = {}
ALL_MODELS.update(CLAUDE_MODELS)
ALL_MODELS.update(OPENAI_MODELS)
ALL_MODELS.update(OPENAI_COMPATIBLE_MODELS)
ALL_MODELS.update(OLLAMA_MODELS)
ALL_MODELS.update(MINIMAX_MODELS)


def get_model_info(model_id: str) -> ModelInfo:
    """
    获取模型信息
    
    Args:
        model_id: 模型 ID
    
    Returns:
        ModelInfo 实例，如果模型未知则返回默认值
    """
    if model_id in ALL_MODELS:
        return ALL_MODELS[model_id]
    
    # 尝试模糊匹配（如带版本号的模型）
    for known_id, info in ALL_MODELS.items():
        if known_id.split("-")[0] == model_id.split("-")[0]:
            return info
    
    # 返回默认配置
    return ModelInfo(
        name=model_id,
        description=f"Unknown model: {model_id}"
    )
