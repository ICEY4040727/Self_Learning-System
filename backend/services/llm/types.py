"""
LLM 类型定义模块

定义统一的请求/响应类型，隐藏不同 Provider 的差异。
"""

from typing import Optional, Any, Literal
from pydantic import BaseModel, Field


# ============================================================================
# Message Types
# ============================================================================

class Message(BaseModel):
    """
    对话消息
    
    Attributes:
        role: 角色 (system/user/assistant/tool)
        content: 消息内容
        name: 可选的名字（用于 tool 消息）
    """
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: Optional[str] = None


class ImageContent(BaseModel):
    """图片内容（用于多模态模型）"""
    type: Literal["image"] = "image"
    source: str  # URL 或 base64
    media_type: Optional[str] = None  # image/png, image/jpeg, etc.


# ============================================================================
# Tool Types
# ============================================================================

class ToolParameterProperty(BaseModel):
    """工具参数属性定义"""
    type: str
    description: Optional[str] = None
    enum: Optional[list[str]] = None


class ToolParameters(BaseModel):
    """工具参数定义（JSON Schema 格式）"""
    type: Literal["object"] = "object"
    properties: dict[str, ToolParameterProperty] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class Tool(BaseModel):
    """
    工具定义
    
    用于 Function Calling / Tool Use。
    """
    name: str
    description: str
    parameters: ToolParameters


class ToolCall(BaseModel):
    """
    工具调用请求
    
    由 LLM 生成，表示需要调用某个工具。
    """
    id: str
    name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    """
    工具执行结果
    
    返回给 LLM 用于生成最终回复。
    """
    tool_call_id: str
    output: str
    is_error: bool = False


# ============================================================================
# Request / Response Types
# ============================================================================

class LLMRequest(BaseModel):
    """
    LLM 请求参数
    
    统一的请求格式，Adapter 负责转换为各 Provider 的格式。
    """
    model: str
    messages: list[Message]
    system: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1024
    top_p: float = 1.0
    stop: Optional[list[str]] = None
    
    # 工具相关
    tools: Optional[list[Tool]] = None
    tool_choice: Optional[str] = None  # "auto", "any", "none"
    
    # 扩展参数
    extra: dict[str, Any] = Field(default_factory=dict)
    
    def get_combined_messages(self) -> list[Message]:
        """
        获取合并了 system 消息的 messages
        
        某些 Provider 需要 system 作为消息列表的一部分。
        """
        messages = list(self.messages)
        if self.system:
            messages.insert(0, Message(role="system", content=self.system))
        return messages


class Usage(BaseModel):
    """Token 使用量统计"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    
    # 缓存相关（Claude 特有）
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    
    def __str__(self) -> str:
        return f"input={self.input_tokens}, output={self.output_tokens}, total={self.total_tokens}"


class LLMResponse(BaseModel):
    """
    LLM 响应
    
    统一的响应格式。
    """
    content: str
    usage: Usage = Field(default_factory=Usage)
    finish_reason: str = "stop"  # "stop", "length", "tool_calls", "content_filter"
    
    # 工具调用（如果 LLM 请求调用工具）
    tool_calls: list[ToolCall] = Field(default_factory=list)
    
    # 模型信息
    model: Optional[str] = None
    latency_ms: Optional[float] = None
    
    # 原始响应（用于调试）
    raw_response: Optional[dict] = None
    
    def has_tool_calls(self) -> bool:
        """是否有工具调用"""
        return len(self.tool_calls) > 0
    
    def get_cost(self, model_info: "ModelInfo") -> float:
        """计算本次请求的成本"""
        input_cost = model_info.get_input_cost(self.usage.input_tokens)
        output_cost = model_info.get_output_cost(self.usage.output_tokens)
        
        # 缓存成本
        cache_cost = 0.0
        if model_info.cache_writes_price and self.usage.cache_creation_tokens > 0:
            cache_cost += (self.usage.cache_creation_tokens / 1_000_000) * model_info.cache_writes_price
        if model_info.cache_reads_price and self.usage.cache_read_tokens > 0:
            cache_cost += (self.usage.cache_read_tokens / 1_000_000) * model_info.cache_reads_price
        
        return input_cost + output_cost + cache_cost


# ============================================================================
# Streaming Types
# ============================================================================

class StreamChunk(BaseModel):
    """
    流式响应块
    
    用于 SSE 流式输出。
    """
    delta: str  # 增量内容
    index: int = 0  # 块的序号
    finish_reason: Optional[str] = None
    
    # 工具调用
    tool_call: Optional[ToolCall] = None
    
    # Usage（最后一个块可能包含）
    usage: Optional[Usage] = None
    
    def is_finish(self) -> bool:
        """是否是最后一个块"""
        return self.finish_reason is not None
