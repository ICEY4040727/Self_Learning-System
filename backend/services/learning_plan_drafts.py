"""Helpers for textbook-first learning plan drafts.

The goal is to keep the early layers persistent without inventing mock
content:
- material analysis comes from the uploaded textbook text
- blueprints are derived from the material and goal
- course/world payloads are staged but not committed until the user
  explicitly confirms
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from backend.models.models import LearningPlanDraft, TextbookLibrary


_HEADING_PATTERNS = [
    re.compile(r"^#{1,3}\s+(.+)$"),
    re.compile(r"^(?:Chapter|Section)\s+\d+[:.，、]?\s*(.+)$", re.IGNORECASE),
    re.compile(r"^第\s*[一二三四五六七八九十百千0-9]+\s*[章节回].*$"),
]

_EXERCISE_HINTS = ("练习", "习题", "题目", "例题", "example", "exercise", "quiz", "test", "小测", "思考题")
_MISCONCEPTION_HINTS = ("易错", "误区", "注意", "混淆", "常见错误", "提醒")


@dataclass(slots=True)
class MaterialChunk:
    title: str
    excerpt: str
    index: int


def _clean_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _chapter_title(line: str) -> str | None:
    for pattern in _HEADING_PATTERNS:
        match = pattern.match(line)
        if match:
            group = match.group(1).strip() if match.lastindex else line.strip()
            return group or line.strip()
    return None


def _material_title(library_items: list[TextbookLibrary]) -> str:
    if not library_items:
        return "未命名教材"
    first = library_items[0]
    return first.title or first.filename or "未命名教材"


def _material_source_type(item: TextbookLibrary) -> str:
    filename = (item.filename or "").lower()
    if filename.endswith(".pdf"):
        return "pdf"
    if filename.endswith(".epub"):
        return "epub"
    if filename.endswith(".md") or filename.endswith(".markdown"):
        return "markdown"
    if filename.endswith(".txt"):
        return "text"
    return "manual"


def _merge_texts(library_items: list[TextbookLibrary]) -> str:
    texts = [item.extracted_text.strip() for item in library_items if item.extracted_text and item.extracted_text.strip()]
    return "\n\n".join(texts)


def _extract_chunks(text: str) -> list[MaterialChunk]:
    lines = _clean_lines(text)
    chunks: list[MaterialChunk] = []
    current_title = "导言"
    current_lines: list[str] = []

    def flush(index: int) -> None:
        nonlocal current_lines
        excerpt = " ".join(current_lines).strip()
        if excerpt:
            chunks.append(MaterialChunk(title=current_title, excerpt=excerpt[:280], index=index))
        current_lines = []

    for line in lines:
        title = _chapter_title(line)
        if title:
            flush(len(chunks))
            current_title = title
            continue
        current_lines.append(line)

    flush(len(chunks))
    if not chunks and lines:
        chunks.append(MaterialChunk(title="导言", excerpt=" ".join(lines[:12])[:280], index=0))
    return chunks


def _top_keywords(text: str, limit: int = 12) -> list[str]:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,6}|[A-Za-z]{3,}", text)
    if not tokens:
        return []
    counts: dict[str, int] = {}
    for token in tokens:
        if token.isdigit():
            continue
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], len(item[0]), item[0]))
    seen: set[str] = set()
    result: list[str] = []
    for token, _count in ranked:
        if token in seen:
            continue
        seen.add(token)
        result.append(token)
        if len(result) >= limit:
            break
    return result


def _extract_exercise_lines(text: str) -> list[str]:
    lines = _clean_lines(text)
    result = [line[:160] for line in lines if any(hint.lower() in line.lower() for hint in _EXERCISE_HINTS)]
    return result[:20]


def _extract_misconceptions(text: str) -> list[str]:
    lines = _clean_lines(text)
    result = [line[:180] for line in lines if any(hint in line for hint in _MISCONCEPTION_HINTS)]
    return result[:20]


def build_learning_plan_blueprint(
    *,
    draft: LearningPlanDraft | None,
    library_items: list[TextbookLibrary],
    goal: str,
    course_form: dict[str, Any] | None = None,
) -> dict[str, Any]:
    course_form = course_form or {}
    merged_text = _merge_texts(library_items)
    chunks = _extract_chunks(merged_text)
    keywords = _top_keywords(merged_text)
    exercises = _extract_exercise_lines(merged_text)
    misconceptions = _extract_misconceptions(merged_text)

    title = _material_title(library_items)
    route_type = _route_type_from_goal(goal, course_form)

    material_analysis = {
        "title": title,
        "source_type": _material_source_type(library_items[0]) if library_items else "manual",
        "chapter_tree": [
            {
                "id": f"chapter_{chunk.index + 1}",
                "title": chunk.title,
                "summary": chunk.excerpt[:160],
                "source_excerpt": chunk.excerpt,
            }
            for chunk in chunks
        ],
        "extracted_topics": keywords,
        "difficulty_estimate": _difficulty_estimate(merged_text),
        "mathematical_density": _density_estimate(merged_text, ("=", "∑", "∫", "公式", "定理", "证明")),
        "exercise_density": _density_estimate(merged_text, _EXERCISE_HINTS),
        "missing_structure_warnings": _missing_structure_warnings(chunks, exercises),
    }

    knowledge_blueprint = {
        "concepts": [
            {
                "id": f"concept_{idx + 1}",
                "title": keyword,
                "source_chapter_id": f"chapter_{min(idx, max(len(chunks) - 1, 0)) + 1}",
                "source_excerpt": chunks[min(idx, max(len(chunks) - 1, 0))].excerpt if chunks else "",
                "check_method": "recall_and_apply",
            }
            for idx, keyword in enumerate(keywords)
        ],
        "prerequisites": [
            {
                "from": f"concept_{idx}",
                "to": f"concept_{idx + 1}",
                "relation": "prerequisite",
            }
            for idx in range(1, max(len(keywords), 1))
            if idx < len(keywords)
        ],
        "skills": [
            {
                "id": f"skill_{idx + 1}",
                "title": exercise[:60],
                "source_type": "exercise",
            }
            for idx, exercise in enumerate(exercises[:8])
        ],
        "common_misconceptions": misconceptions,
        "exercises": exercises,
        "checkpoints": [
            {
                "id": f"checkpoint_{chunk.index + 1}",
                "title": f"检查点：{chunk.title}",
                "criteria": chunk.excerpt[:120],
            }
            for chunk in chunks
        ],
    }

    course_blueprint = {
        "course_title": course_form.get("name") or title,
        "learning_goal": goal,
        "route_type": route_type,
        "units": [
            {
                "title": chunk.title,
                "description": chunk.excerpt[:180],
                "order_index": chunk.index + 1,
                "concepts": keywords[max(0, chunk.index - 1): max(0, chunk.index - 1) + 3] or keywords[:3],
                "prerequisites": [chunks[chunk.index - 1].title] if chunk.index > 0 and chunk.index - 1 < len(chunks) else [],
                "exercise_anchor": exercises[chunk.index: chunk.index + 2],
            }
            for chunk in chunks
        ],
        "mastery_policy": {
            "auto_advance_threshold": 0.8,
            "review_threshold": 0.6,
            "misconception_requires_repair": True,
        },
        "assessment_plan": {
            "quick_checks": [f"能否复述 {k}" for k in keywords[:5]],
            "milestone_tests": [f"完成 {chunk.title} 检查点" for chunk in chunks[:3]],
        },
    }

    course_narrative_plan = {
        "world": {
            "name": course_form.get("world_name") or f"{course_blueprint['course_title']}学习世界",
            "premise": f"围绕《{title}》构建的学习容器",
            "long_term_goal": goal,
            "tone": course_form.get("tone") or "focused",
            "scenes": [
                {
                    "name": chunk.title,
                    "narrative_input": chunk.excerpt[:220],
                    "trigger": f"unit_{chunk.index + 1}",
                }
                for chunk in chunks
            ],
        },
        "route_bible": {
            "main_arc": f"从教材导言走向 {course_blueprint['course_title']} 的完整掌握",
            "recurring_motifs": keywords[:5],
            "relationship_rules": [
                "剧情只包裹教材，不替代教材",
                "每个事件都要能回指到章节或知识点",
            ],
            "boundaries": [
                "不得凭空生成与教材无关的主线",
                "不得用情绪戏替代知识检查",
            ],
        },
        "event_pool": [
            {
                "type": "lesson_opening",
                "lesson": unit["title"],
                "trigger": unit["title"],
            }
            for unit in course_blueprint["units"]
        ],
    }

    character_plan = {
        "traits": {
            "strictness": 5,
            "pace": 5,
            "questioning": 7,
            "warmth": 6,
            "humor": 3,
        },
        "system_prompt_template": "你是课程中的导师角色，必须以教材蓝图和世界设定为依据进行教学。",
        "greeting": "我们先从教材蓝图开始，再把世界搭起来。",
    }

    return {
        "material_analysis": material_analysis,
        "knowledge_blueprint": knowledge_blueprint,
        "course_blueprint": course_blueprint,
        "course_narrative_plan": course_narrative_plan,
        "character_plan": character_plan,
    }


def _route_type_from_goal(goal: str, course_form: dict[str, Any]) -> str:
    text = f"{goal} {course_form.get('pace', '')} {course_form.get('motivation', '')}".lower()
    if any(keyword in text for keyword in ("考试", "面试", "冲刺", "exam", "sprint")):
        return "exam_sprint"
    if any(keyword in text for keyword in ("项目", "project", "作品", "实践")):
        return "project_based"
    if any(keyword in text for keyword in ("综述", "survey", "overview", "广泛")):
        return "survey"
    return "deep_understanding"


def _difficulty_estimate(text: str) -> str:
    length = len(text)
    if length < 5000:
        return "intro"
    if length < 20000:
        return "intermediate"
    return "advanced"


def _density_estimate(text: str, hints: tuple[str, ...]) -> str:
    if not text:
        return "low"
    count = sum(text.lower().count(hint.lower()) for hint in hints)
    if count >= 18:
        return "high"
    if count >= 6:
        return "medium"
    return "low"


def _missing_structure_warnings(chunks: list[MaterialChunk], exercises: list[str]) -> list[str]:
    warnings: list[str] = []
    if not chunks:
        warnings.append("未识别到章节结构，建议补充目录或标题标记。")
    if not exercises:
        warnings.append("未识别到练习或例题线索，建议补充练习段落。")
    return warnings


def persist_draft(
    draft: LearningPlanDraft,
    *,
    user_id: int,
    goal: str,
    course_form: dict[str, Any] | None,
    library_items: list[TextbookLibrary],
) -> LearningPlanDraft:
    payload = build_learning_plan_blueprint(
        draft=draft,
        library_items=library_items,
        goal=goal,
        course_form=course_form,
    )
    draft.user_id = user_id
    draft.goal = goal
    draft.course_form = course_form or {}
    draft.material_ids = [item.id for item in library_items]
    draft.material_analysis = payload["material_analysis"]
    draft.knowledge_blueprint = payload["knowledge_blueprint"]
    draft.course_blueprint = payload["course_blueprint"]
    draft.world_plan = payload["course_narrative_plan"]
    draft.character_plan = payload["character_plan"]
    draft.stage = "blueprint"
    return draft
