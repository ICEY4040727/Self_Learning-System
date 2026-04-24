"""Profile Aggregator - Dimension-based learner profile computation

Triggered at end of learning_engine.process_message.
Aggregates MemoryFact data into LearnerProfile.dimension_scores.
No LLM calls — zero API cost.

Hallucination guard: requires >= N same-type MemoryFacts before updating.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.models.models import LearnerProfile, MemoryFact, ProfileDimensionDef
from backend.services.memory_manager import memory_manager

logger = logging.getLogger(__name__)


def _cfg() -> dict:
    return get_settings().learning_system


class ProfileAggregator:
    """Compute dimension_scores, learning_stats, strengths/weaknesses."""

    def aggregate(
        self,
        db: Session,
        *,
        character_id: int,
        world_id: int,
        user_id: int,
    ) -> dict | None:
        """Run aggregation and write to LearnerProfile. Returns updated profile or None."""
        profile_row = db.query(LearnerProfile).filter(
            LearnerProfile.user_id == user_id,
            LearnerProfile.world_id == world_id,
        ).first()
        if not profile_row:
            return None

        # Load enabled dimension definitions
        dim_defs = db.query(ProfileDimensionDef).filter(
            ProfileDimensionDef.enabled == True,
        ).all()
        if not dim_defs:
            return None

        profile = dict(profile_row.profile if isinstance(profile_row.profile, dict) else {})

        # Save previous dimension_scores as snapshot
        prev_scores = dict(profile.get("dimension_scores") or {})
        snapshots = dict(profile.get("dimension_snapshots") or {})
        now_iso = datetime.now(UTC).isoformat()

        # Compute each dimension
        new_scores: dict[str, float] = {}
        for dim_def in dim_defs:
            score = self._compute_dimension(db, dim_def, character_id, world_id, profile)
            if score is not None:
                new_scores[dim_def.key] = score

                # Record snapshot if score changed
                prev_val = prev_scores.get(dim_def.key)
                if prev_val is not None and prev_val != score:
                    snapshots[dim_def.key] = {"prev": prev_val, "updated_at": now_iso}

        # Compute learning_stats from MemoryFact counts
        learning_stats = self._compute_learning_stats(db, character_id, world_id)

        # Compute strengths / weaknesses
        profile_cfg = _cfg()["profile"]
        strengths = [k for k, v in new_scores.items() if v >= profile_cfg["strength_threshold"]]
        weaknesses = [k for k, v in new_scores.items() if v <= profile_cfg["weakness_threshold"]]

        # Merge write — preserve other fields
        profile["dimension_scores"] = new_scores
        if snapshots:
            profile["dimension_snapshots"] = snapshots
        profile["learning_stats"] = learning_stats
        profile["strengths"] = strengths
        profile["weaknesses"] = weaknesses

        profile_row.profile = profile
        db.flush()
        return profile

    # ---------------------------------------------------------------
    # Dimension computation dispatch
    # ---------------------------------------------------------------

    def _compute_dimension(
        self,
        db: Session,
        dim_def: ProfileDimensionDef,
        character_id: int,
        world_id: int,
        profile: dict,
    ) -> float | None:
        method = dim_def.aggregation_method
        params = dim_def.aggregation_params or {}
        source_types = dim_def.source_fact_types or []
        min_facts = _cfg()["profile"]["hallucination_guard_min_facts"]

        if method == "ratio":
            return self._ratio(db, character_id, world_id, source_types, params, min_facts)
        elif method == "conversion_rate":
            return self._conversion_rate(db, character_id, world_id, params, min_facts)
        elif method == "count":
            return self._count(db, character_id, world_id, source_types, params, min_facts)
        elif method == "keyword_extract":
            return self._keyword_extract(db, character_id, world_id, source_types, params, min_facts)
        elif method == "emotion_balance":
            return self._emotion_balance(profile, params, min_facts)
        else:
            logger.warning(f"Unknown aggregation method: {method}")
            return None

    # ---------------------------------------------------------------
    # Aggregation methods
    # ---------------------------------------------------------------

    def _ratio(
        self, db: Session, cid: int, wid: int,
        source_types: list, params: dict, min_facts: int,
    ) -> float | None:
        """positive_types count / total_types count"""
        positive_types = params.get("positive_types", [])
        total_types = params.get("total_types", source_types)

        total_q = db.query(func.count(MemoryFact.id)).filter(
            MemoryFact.character_id == cid,
            MemoryFact.fact_type.in_(total_types),
        )
        if wid:
            total_q = total_q.filter(
                (MemoryFact.world_id == wid) | (MemoryFact.world_id.is_(None))
            )
        total = total_q.scalar() or 0

        if total < min_facts:
            return None

        pos_q = db.query(func.count(MemoryFact.id)).filter(
            MemoryFact.character_id == cid,
            MemoryFact.fact_type.in_(positive_types),
        )
        if wid:
            pos_q = pos_q.filter(
                (MemoryFact.world_id == wid) | (MemoryFact.world_id.is_(None))
            )
        positive = pos_q.scalar() or 0

        return round(positive / total, 3) if total > 0 else None

    def _conversion_rate(
        self, db: Session, cid: int, wid: int,
        params: dict, min_facts: int,
    ) -> float | None:
        """struggle→mastered conversion: mastered / (struggle + mastered)"""
        from_type = params.get("from_type", "concept_struggle")
        to_type = params.get("to_type", "concept_mastered")

        from_q = db.query(func.count(MemoryFact.id)).filter(
            MemoryFact.character_id == cid,
            MemoryFact.fact_type == from_type,
        )
        to_q = db.query(func.count(MemoryFact.id)).filter(
            MemoryFact.character_id == cid,
            MemoryFact.fact_type == to_type,
        )
        if wid:
            from_q = from_q.filter(
                (MemoryFact.world_id == wid) | (MemoryFact.world_id.is_(None))
            )
            to_q = to_q.filter(
                (MemoryFact.world_id == wid) | (MemoryFact.world_id.is_(None))
            )

        from_count = from_q.scalar() or 0
        to_count = to_q.scalar() or 0
        total = from_count + to_count

        if total < min_facts:
            return None

        return round(to_count / total, 3) if total > 0 else None

    def _count(
        self, db: Session, cid: int, wid: int,
        source_types: list, params: dict, min_facts: int,
    ) -> float | None:
        """Normalized count: count / max_expected"""
        q = db.query(func.count(MemoryFact.id)).filter(
            MemoryFact.character_id == cid,
            MemoryFact.fact_type.in_(source_types),
        )
        if wid:
            q = q.filter(
                (MemoryFact.world_id == wid) | (MemoryFact.world_id.is_(None))
            )
        count = q.scalar() or 0

        if count < min_facts:
            return None

        max_expected = params.get("max_expected", 20)
        return round(min(count / max_expected, 1.0), 3)

    def _keyword_extract(
        self, db: Session, cid: int, wid: int,
        source_types: list, params: dict, min_facts: int,
    ) -> float | None:
        """Keyword frequency in MemoryFact content"""
        keywords = params.get("keywords", [])
        if not keywords:
            return None

        facts = memory_manager.observe_recent(
            db, cid, fact_types=source_types, limit=50,
        )
        if len(facts) < min_facts:
            return None

        total_keywords = 0
        total_content_len = 0
        for f in facts:
            content = f.content or ""
            total_content_len += len(content)
            for kw in keywords:
                total_keywords += content.count(kw)

        if total_content_len == 0:
            return None

        # Normalize: ratio of keyword chars to total content
        ratio = total_keywords / (total_content_len * len(keywords)) if keywords else 0
        return round(min(ratio * 10, 1.0), 3)  # scale up

    def _emotion_balance(
        self, profile: dict, params: dict, min_facts: int,
    ) -> float | None:
        """Positive emotion counts / total emotion counts from LearnerProfile.affect"""
        affect = profile.get("affect") or {}
        positive_emotions = params.get("positive_emotions", [])
        total_emotions = params.get("total_emotions", [])

        pos_count = 0
        total_count = 0
        for emo in total_emotions:
            cnt = affect.get(f"count_{emo}", 0)
            total_count += cnt
            if emo in positive_emotions:
                pos_count += cnt

        if total_count < min_facts:
            return None

        return round(pos_count / total_count, 3) if total_count > 0 else None

    # ---------------------------------------------------------------
    # Learning stats
    # ---------------------------------------------------------------

    def _compute_learning_stats(
        self, db: Session, character_id: int, world_id: int,
    ) -> dict[str, Any]:
        """Compute concept mastery/struggle counts."""
        mastered = db.query(func.count(MemoryFact.id)).filter(
            MemoryFact.character_id == character_id,
            MemoryFact.fact_type == "concept_mastered",
        )
        struggling = db.query(func.count(MemoryFact.id)).filter(
            MemoryFact.character_id == character_id,
            MemoryFact.fact_type == "concept_struggle",
        )
        if world_id:
            mastered = mastered.filter(
                (MemoryFact.world_id == world_id) | (MemoryFact.world_id.is_(None))
            )
            struggling = struggling.filter(
                (MemoryFact.world_id == world_id) | (MemoryFact.world_id.is_(None))
            )

        return {
            "concepts_mastered": mastered.scalar() or 0,
            "concepts_struggling": struggling.scalar() or 0,
        }


# Global instance
profile_aggregator = ProfileAggregator()