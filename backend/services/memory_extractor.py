"""Memory Extractor
记忆提取拦截器 - 从 LLM 回复中提取 <memory> 标签内容

根据草案设计:
- 触发条件: 用户发言后且 AI 产生实质内容 (>20 字)
- 格式: <memory>{"memories": [...]}</memory>
- 容错策略: 解析失败时丢弃，不影响主对话
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class MemoryParseError(Exception):
    """记忆解析错误"""
    pass


@dataclass
class ExtractedMemory:
    """提取的单条记忆"""
    fact_type: str
    content: str
    concept_tags: list[str]
    salience: float
    expires_at: str | None


@dataclass
class ExtractionResult:
    """提取结果"""
    memories: list[ExtractedMemory]
    raw_json: str | None = None
    error: str | None = None


def extract_memory_tags(text: str) -> str | None:
    """
    从 LLM 回复中提取 <memory>...</memory> 标签内容
    
    Args:
        text: LLM 回复文本
    
    Returns:
        标签内的 JSON 字符串，或 None（如果没有标签）
    """
    match = re.search(r'<memory>(.*?)</memory>', text, re.DOTALL)
    return match.group(1).strip() if match else None


def strip_memory_tags(text: str) -> str:
    """
    移除 <memory> 标签，保留主对话内容
    
    Args:
        text: LLM 回复文本
    
    Returns:
        清理后的文本
    """
    return re.sub(r'<memory>.*?</memory>', '', text, flags=re.DOTALL).strip()


def parse_memory_json(json_str: str) -> list[dict[str, Any]]:
    """
    解析记忆 JSON
    
    Args:
        json_str: JSON 字符串
    
    Returns:
        memories 列表
    
    Raises:
        MemoryParseError: 解析失败
    """
    try:
        data = json.loads(json_str)
        if not isinstance(data, dict):
            raise MemoryParseError("JSON 根对象必须是字典")
        
        memories = data.get("memories", [])
        if not isinstance(memories, list):
            raise MemoryParseError("memories 必须是数组")
        
        # 验证每条记忆
        for i, mem in enumerate(memories):
            if not isinstance(mem, dict):
                raise MemoryParseError(f"memories[{i}] 必须是对象")
            if "fact_type" not in mem:
                raise MemoryParseError(f"memories[{i}] 缺少 fact_type")
            if "content" not in mem:
                raise MemoryParseError(f"memories[{i}] 缺少 content")
        
        return memories
        
    except json.JSONDecodeError as e:
        raise MemoryParseError(f"JSON 解析失败: {e}")


def extract_memories(text: str) -> ExtractionResult:
    """
    从文本中提取记忆
    
    Args:
        text: LLM 回复文本
    
    Returns:
        ExtractionResult: 提取结果
    """
    # 提取标签内容
    raw_json = extract_memory_tags(text)
    if not raw_json:
        return ExtractionResult(memories=[])
    
    try:
        memories_data = parse_memory_json(raw_json)
    except MemoryParseError as e:
        logger.warning(f"记忆解析失败，丢弃: {e}")
        return ExtractionResult(memories=[], raw_json=raw_json, error=str(e))
    
    # 转换并验证每条记忆
    memories = []
    for mem in memories_data:
        try:
            # 验证 fact_type
            valid_types = {"student_state", "concept_struggle", "concept_mastered", "preference", "event", "commitment"}
            fact_type = mem.get("fact_type", "event")
            if fact_type not in valid_types:
                logger.warning(f"未知的 fact_type: {fact_type}，使用默认 event")
                fact_type = "event"
            
            # 验证 content
            content = mem.get("content", "")
            if not content:
                continue
            # 截断至 500 字
            content = content[:500]
            
            # 验证 salience
            salience = mem.get("salience")
            if not isinstance(salience, (int, float)):
                salience = 0.5
            salience = max(0.1, min(1.0, float(salience)))
            
            # 验证 concept_tags
            concept_tags = mem.get("concept_tags", [])
            if not isinstance(concept_tags, list):
                concept_tags = []
            concept_tags = concept_tags[:5]  # 最多 5 个标签
            
            # 验证 expires_at
            expires_at = mem.get("expires_at")
            if expires_at is not None and not isinstance(expires_at, str):
                expires_at = None
            
            memories.append(ExtractedMemory(
                fact_type=fact_type,
                content=content,
                concept_tags=concept_tags,
                salience=salience,
                expires_at=expires_at,
            ))
        except Exception as e:
            # 单条记忆解析失败，跳过
            logger.warning(f"单条记忆解析失败，跳过: {e}")
            continue
    
    return ExtractionResult(memories=memories, raw_json=raw_json)


def should_extract_memory(llm_response: str) -> bool:
    """
    判断是否应该提取记忆
    
    条件: AI 回复有实质内容 (>20 字) 且包含 <memory> 标签
    
    Args:
        llm_response: LLM 回复文本
    
    Returns:
        True 如果应该提取
    """
    # 移除 <memory> 标签后检查长度
    clean_text = strip_memory_tags(llm_response)
    return len(clean_text.strip()) > 20


class MemoryExtractor:
    """
    记忆提取器
    
    用法:
    ```python
    extractor = MemoryExtractor()
    
    # 在 LLM 回复后调用
    if should_extract_memory(llm_response):
        result = extractor.extract(llm_response)
        if result.memories:
            await memory_facts_service.write_memory_facts(
                db=db,
                character_id=teacher_character_id,
                world_id=session.world_id,
                memories=[{
                    "fact_type": m.fact_type,
                    "content": m.content,
                    "concept_tags": m.concept_tags,
                    "salience": m.salience,
                    "expires_at": m.expires_at,
                } for m in result.memories],
                source_message_id=ai_message.id,
            )
    
    # 返回清理后的回复（不含 <memory> 标签）
    clean_response = extractor.strip_tags(llm_response)
    ```
    """
    
    def extract(self, text: str) -> ExtractionResult:
        """提取记忆"""
        return extract_memories(text)
    
    def strip_tags(self, text: str) -> str:
        """移除标签"""
        return strip_memory_tags(text)


# 全局实例
memory_extractor = MemoryExtractor()
