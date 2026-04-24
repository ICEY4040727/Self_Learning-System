"""Recall Service - Contextual memory recall for teaching

Uses concept_map (Course.metadata) for prerequisite-aware recall.
No fuzzy matching — only uses ground truth concept_map edges.
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from backend.services.memory_manager import memory_manager

logger = logging.getLogger(__name__)


class RecallService:
    """Contextual memory recall based on concept graph."""

    def get_recall_hints(
        self,
        db: Session,
        *,
        character_id: int,
        world_id: int,
        current_topic: str | None = None,
        course_id: int | None = None,
    ) -> list[str]:
        """Get contextual teaching hints based on prerequisite concepts.

        Returns list of hint strings, empty if no hints applicable.
        """
        if not current_topic or not course_id:
            return []

        # Load concept_map from Course
        concept_map = self._get_concept_map(db, course_id)
        if not concept_map:
            return []

        nodes = concept_map.get("nodes") or []
        edges = concept_map.get("edges") or []

        # Check current topic exists in nodes
        node_ids = {n["id"] for n in nodes}
        if current_topic not in node_ids:
            return []

        # Find prerequisites (edges where source=current_topic, type=requires)
        prerequisites = []
        for edge in edges:
            if edge.get("source") == current_topic and edge.get("type") == "requires":
                target = edge.get("target")
                if target:
                    prerequisites.append(target)

        if not prerequisites:
            return []

        # For each prerequisite, check struggle/mastered status
        hints: list[str] = []
        for prereq_id in prerequisites:
            # Find node label
            label = prereq_id
            for n in nodes:
                if n["id"] == prereq_id:
                    label = n.get("label", prereq_id)
                    break

            # Check memory facts for this prerequisite concept
            struggle_facts = memory_manager.observe_recent(
                db, character_id,
                fact_types=["concept_struggle"],
                limit=10,
            )
            mastered_facts = memory_manager.observe_recent(
                db, character_id,
                fact_types=["concept_mastered"],
                limit=10,
            )

            # Check if prereq concept appears in struggle/mastered facts
            has_struggle = any(
                prereq_id in (f.concept_tags or []) or prereq_id in (f.content or "")
                for f in struggle_facts
            )
            has_mastered = any(
                prereq_id in (f.concept_tags or []) or prereq_id in (f.content or "")
                for f in mastered_facts
            )

            if has_struggle and not has_mastered:
                hints.append(
                    f"学生在学习前置概念「{label}」时曾遇到困难，"
                    f"教「{current_topic}」时建议先复习相关内容。"
                )
            elif has_struggle:
                hints.append(
                    f"学生之前学「{label}」时遇到过困难，"
                    f"教「{current_topic}」时注意关联。"
                )

        return hints

    def _get_concept_map(self, db: Session, course_id: int) -> dict | None:
        """Load concept_map from Course.meta."""
        from backend.models.models import Course

        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return None

        meta = course.meta if isinstance(course.meta, dict) else {}
        return meta.get("concept_map")


# Global instance
recall_service = RecallService()