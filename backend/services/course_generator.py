"""课程生成服务 — 基于教材文本 AI 生成课程结构

Phase 3 Step 2 核心服务:
- 接收提取的教材文本
- 调用 LLM 分析内容
- 输出结构化的课程大纲（lessons + concept_map）
"""

import json
import logging
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ── 数据模型 ──────────────────────────────────────────────────────────


class GeneratedLesson(BaseModel):
    """生成的单节课"""
    title: str
    description: str
    order: int
    concepts: list[str]
    prerequisites: list[str] = []


# ── Prompt 模板 ───────────────────────────────────────────────────────

COURSE_GENERATION_SYSTEM_PROMPT = """你是一位专业的课程设计师，擅长从教材内容中提取知识点并设计教学路径。

你的任务是根据提供的教材文本，设计一个结构化的课程大纲。

## 输出要求

请输出 **严格的 JSON 格式**（不要包含 markdown 代码块标记），结构如下：

```json
{
  "overview": "课程概览（100-200字，概括课程内容和目标）",
  "lessons": [
    {
      "title": "章节标题",
      "description": "章节描述（50-100字，说明学习目标和内容）",
      "order": 1,
      "concepts": ["核心概念1", "核心概念2"],
      "prerequisites": []
    }
  ],
  "concept_map": {
    "nodes": [
      {"id": "concept_1", "label": "概念名称", "category": "category_name"}
    ],
    "edges": [
      {"source": "concept_1", "target": "concept_2", "relation": "prerequisite"}
    ]
  }
}
```

## 设计原则

1. **循序渐进**: 从基础概念开始，逐步深入
2. **概念拆分**: 每节课 2-5 个核心概念，不要过于密集
3. **先决条件**: 明确标注章节间的依赖关系
4. **概念图**: 构建概念间的关系网络（prerequisite/related/contains）
5. **适应性**: 章节数量根据教材内容量合理分配（通常 5-15 节）
"""

COURSE_GENERATION_USER_TEMPLATE = """## 课程信息
- 课程名称: {course_name}
- 课程描述: {course_description}
- 目标水平: {target_level}
{custom_instructions}{target_days}

## 教材内容

{text}

---

请根据以上教材内容，设计课程大纲。只输出 JSON，不要其他内容。"""


# ── CourseGenerator 服务 ──────────────────────────────────────────────


class CourseGenerator:
    """AI 课程生成器

    工作流程:
    1. 拼装 prompt（教材文本 + 课程元信息）
    2. 调用 LLM 获取 JSON 结果
    3. 解析并验证结果
    """

    def __init__(self):
        self.system_prompt = COURSE_GENERATION_SYSTEM_PROMPT

    async def generate(
        self,
        text: str,
        course_name: str = "未命名课程",
        course_description: str | None = None,
        target_level: str | None = None,
        custom_instructions: str | None = None,
        target_days: int | None = None,
        user_api_key: str | None = None,
        default_provider: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """生成课程结构

        Returns:
            {"overview": str, "lessons": list[GeneratedLesson], "concept_map": dict|None}
        """
        # 拼装 user prompt
        custom_section = ""
        if custom_instructions:
            custom_section = f"\n- 自定义指令: {custom_instructions}"

        days_section = ""
        if target_days:
            days_section = f"\n- 目标学习天数: {target_days}天"

        user_prompt = COURSE_GENERATION_USER_TEMPLATE.format(
            course_name=course_name,
            course_description=course_description or "无",
            target_level=target_level or "未指定",
            custom_instructions=custom_section,
            target_days=days_section,
            text=text,
        )

        # 调用 LLM
        llm_response = await self._call_llm(
            user_prompt=user_prompt,
            user_api_key=user_api_key,
            default_provider=default_provider,
            model=model,
        )

        # 解析 JSON 结果
        result = self._parse_response(llm_response)

        # 验证并标准化
        return self._validate_result(result)

    async def _call_llm(
        self,
        user_prompt: str,
        user_api_key: str | None = None,
        default_provider: str | None = None,
        model: str | None = None,
    ) -> str:
        """调用 LLM 获取生成结果"""
        from backend.services.llm.manager import get_llm_manager

        adapter = get_llm_manager().get_adapter(
            provider=default_provider, model=model, api_key=user_api_key,
        )
        messages = [{"role": "user", "content": user_prompt}]

        response = await adapter.chat(
            messages=messages,
            system_prompt=self.system_prompt,
            user_api_key=user_api_key,
            temperature=0.3,  # 低温度保证结构化输出
            max_tokens=4096,
        )
        return response

    def _parse_response(self, raw: str) -> dict:
        """解析 LLM 返回的 JSON"""
        # 尝试直接解析
        text = raw.strip()

        # 去除可能的 markdown 代码块标记
        if text.startswith("```"):
            # 找到第一个换行
            first_newline = text.index("\n") if "\n" in text else 3
            text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试找到 JSON 对象的边界
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass

            logger.error("无法解析 LLM 返回的 JSON: %s...", raw[:200])
            raise ValueError(f"LLM 返回的 JSON 格式无效: {raw[:100]}")

    def _validate_result(self, data: dict) -> dict[str, Any]:
        """验证并标准化生成结果"""
        result = {
            "overview": data.get("overview", ""),
            "lessons": [],
            "concept_map": data.get("concept_map"),
        }

        # 验证 lessons
        raw_lessons = data.get("lessons", [])
        if isinstance(raw_lessons, list):
            for i, lesson_data in enumerate(raw_lessons):
                if not isinstance(lesson_data, dict):
                    continue
                lesson = GeneratedLesson(
                    title=lesson_data.get("title", f"第{i+1}课"),
                    description=lesson_data.get("description", ""),
                    order=lesson_data.get("order", i + 1),
                    concepts=lesson_data.get("concepts", []),
                    prerequisites=lesson_data.get("prerequisites", []),
                )
                result["lessons"].append(lesson)

        # [TODO-T4] No silent fallback. Empty lessons means LLM failed to
        # produce a usable course; the caller should surface that to the
        # user (retry / report / let them author lessons manually) rather
        # than receive a fake "入门" placeholder that pretends success.
        if not result["lessons"]:
            raise ValueError(
                "LLM 未生成有效章节 — 请检查教材内容或重试课程生成"
            )

        return result

