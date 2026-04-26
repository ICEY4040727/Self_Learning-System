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

        # [TODO-3] One observe_recent per fact_type, not per prereq.
        # [R1-01] world_id filter prevents cross-world memory leakage.
        struggle_facts = memory_manager.observe_recent(
            db, character_id,
            world_id=world_id,
            fact_types=["concept_struggle"],
            limit=50,
        )
        mastered_facts = memory_manager.observe_recent(
            db, character_id,
            world_id=world_id,
            fact_types=["concept_mastered"],
            limit=50,
        )

        # Build tag-only sets for exact membership checks.
        # [TODO-3] Dropped `prereq_id in content` substring match —
        # `"abs" in "absolutely confused"` was a false-positive trap.
        # concept_tags is the structured field; content is freeform prose.
        struggle_tags = {
            tag for f in struggle_facts for tag in (f.concept_tags or [])
        }
        mastered_tags = {
            tag for f in mastered_facts for tag in (f.concept_tags or [])
        }

        hints: list[str] = []
        for prereq_id in prerequisites:
            # Find node label
            label = prereq_id
            for n in nodes:
                if n["id"] == prereq_id:
                    label = n.get("label", prereq_id)
                    break

            has_struggle = prereq_id in struggle_tags
            has_mastered = prereq_id in mastered_tags

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