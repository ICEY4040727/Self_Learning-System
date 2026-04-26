"""Memory Manager - Service Layer for memory system

Single entry point for all memory operations.
memory_facts_service and memory_extractor are internal implementation details;
external callers use MemoryManager exclusively.
"""

import logging
import math
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.models.models import ChatMessage, MemoryFact
from backend.services.memory_extractor import (
    ExtractionResult,
    extract_memories,
    strip_memory_tags,
)
from backend.services.memory_facts import memory_facts_service

logger = logging.getLogger(__name__)


def _cfg() -> dict:
    return get_settings().learning_system


class MemoryManager:
    """Memory system - sole external entry point."""

    # ---------------------------------------------------------------
    # Working memory (chat_messages)
    # ---------------------------------------------------------------

    def get_working_context(
        self,
        db: Session,
        session_id: int,
        *,
        max_messages: int | None = None,
    ) -> list[dict]:
        """Return recent chat messages for LLM context, respecting budget."""
        mem_cfg = _cfg()["memory"]
        limit = max_messages or mem_cfg["max_working_context_messages"]

        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.timestamp.desc())
            .limit(limit)
            .all()
        )
        messages.reverse()

        role_map = {"user": "user", "teacher": "assistant"}
        return [
            {"role": role_map.get(m.sender_type, "user"), "content": m.content}
            for m in messages
        ]

    # ---------------------------------------------------------------
    # Long-term memory (MemoryFact) - retrieval
    # ---------------------------------------------------------------

    def retrieve(
        self,
        db: Session,
        character_id: int,
        *,
        world_id: int | None = None,
        fact_types: list[str] | None = None,
        concept_tags: list[str] | None = None,
        limit: int | None = None,
        min_salience: float = 0.3,
    ) -> list[MemoryFact]:
        """
        Retrieve memories for PromptBuilder context injection.

        Ordered by effective_salience DESC, filtered by min_salience.
        Updates recall_count + last_recalled_at on returned facts.

        effective_salience <= base salience (decay never amplifies), so
        SQL-prefiltering by base salience >= min_salience is safe and prunes
        the candidate pool before per-row Python computation.
        """
        mem_cfg = _cfg()["memory"]
        limit = limit or mem_cfg["default_retrieve_limit"]

        q = db.query(MemoryFact).filter(
            MemoryFact.character_id == character_id,
            MemoryFact.salience >= min_salience,
            (MemoryFact.expires_at.is_(None))
            | (MemoryFact.expires_at > datetime.now(UTC)),
        )

        if world_id is not None:
            q = q.filter(
                (MemoryFact.world_id == world_id)
                | (MemoryFact.world_id.is_(None))
            )

        if fact_types:
            q = q.filter(MemoryFact.fact_type.in_(fact_types))

        if concept_tags:
            # SQLite JSON: concept_tags stored as JSON array
            for tag in concept_tags:
                q = q.filter(MemoryFact.concept_tags.contains(f'"{tag}"'))

        # Pull a buffer; effective_salience filtering may further prune.
        candidates = q.order_by(MemoryFact.salience.desc()).limit(limit * 5).all()

        scored = [(f, self.compute_effective_salience(f)) for f in candidates]
        scored = [(f, s) for f, s in scored if s >= min_salience]
        scored.sort(key=lambda x: x[1], reverse=True)
        facts = [f for f, _ in scored[:limit]]

        # Update recall metadata (M2)
        now = datetime.now(UTC)
        for f in facts:
            f.recall_count = (f.recall_count or 0) + 1
            f.last_recalled_at = now
        db.flush()

        return facts

    def observe_recent(
        self,
        db: Session,
        character_id: int,
        *,
        world_id: int | None = None,
        fact_types: list[str] | None = None,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[MemoryFact]:
        """
        Observe recent memories without affecting recall state.
        For NarrativeEngine and GamificationEngine.

        [R1-01] Added world_id filter to prevent cross-world memory leakage.
        """
        mem_cfg = _cfg()["memory"]
        limit = limit or mem_cfg["observe_recent_limit"]

        q = db.query(MemoryFact).filter(MemoryFact.character_id == character_id)

        if world_id is not None:
            q = q.filter(
                (MemoryFact.world_id == world_id) | (MemoryFact.world_id.is_(None))
            )

        if fact_types:
            q = q.filter(MemoryFact.fact_type.in_(fact_types))

        if since:
            q = q.filter(MemoryFact.created_at >= since)

        return q.order_by(MemoryFact.created_at.desc()).limit(limit).all()

    # ---------------------------------------------------------------
    # Long-term memory - write with dedup (M4)
    # ---------------------------------------------------------------

    def write_facts(
        self,
        db: Session,
        character_id: int,
        world_id: int | None,
        memories: list[dict[str, Any]],
        *,
        source_message_id: int | None = None,
    ) -> list[int]:
        """Write memories with deduplication. Same type + same tags -> merge."""
        mem_cfg = _cfg()["memory"]
        window_hours = mem_cfg["dedup_window_hours"]
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=window_hours)

        ids: list[int] = []
        for mem in memories:
            fact_type = mem.get("fact_type", "event")
            content = (mem.get("content", "") or "")[:500]
            if not content:
                continue
            tags = mem.get("concept_tags", [])
            if not isinstance(tags, list):
                tags = []
            salience = float(mem.get("salience", 0.5))
            salience = max(0.1, min(1.0, salience))

            existing = self._find_duplicate(db, character_id, fact_type, tags, cutoff)

            if existing:
                existing.content = content
                existing.salience = max(existing.salience, salience)
                db.flush()
                ids.append(existing.id)
            else:
                new_ids = memory_facts_service.write_memory_facts(
                    db=db,
                    character_id=character_id,
                    world_id=world_id,
                    memories=[mem],
                    source_message_id=source_message_id,
                )
                ids.extend(new_ids)

        return ids

    # ---------------------------------------------------------------
    # Dual-channel extraction
    # ---------------------------------------------------------------

    def extract_and_store(
        self,
        db: Session,
        llm_response: str,
        student_message: str,
        *,
        character_id: int,
        world_id: int | None,
        source_message_id: int | None = None,
    ) -> ExtractionResult:
        """Channel 1: Extract from LLM response + merge with channel 2."""
        result = extract_memories(llm_response)

        if result.memories:
            mem_data = [
                {
                    "fact_type": m.fact_type,
                    "content": m.content,
                    "concept_tags": m.concept_tags,
                    "salience": m.salience,
                    "expires_at": m.expires_at,
                }
                for m in result.memories
            ]
            self.write_facts(
                db,
                character_id,
                world_id,
                mem_data,
                source_message_id=source_message_id,
            )

        # Channel 2: rule-based extraction from student message
        ext_cfg = _cfg()["extraction"]
        if ext_cfg["channel2_enabled"] and student_message:
            self._extract_student_signals(
                db, student_message, character_id=character_id, world_id=world_id
            )

        return result

    def _extract_student_signals(
        self,
        db: Session,
        student_message: str,
        *,
        character_id: int,
        world_id: int | None,
    ) -> None:
        """Channel 2: Rule-based signal extraction from student message."""
        ext_cfg = _cfg()["extraction"]
        msg = student_message
        signals: list[dict[str, Any]] = []

        # Channel-2 signals get sentinel concept_tags so they participate in
        # dedup. Without a tag, _find_duplicate skips and every "我不懂" spawns
        # a new row.

        # Confusion
        for kw in ext_cfg["confusion_keywords"]:
            if kw in msg:
                signals.append(
                    {
                        "fact_type": "concept_struggle",
                        "content": f"学生表示困惑: {msg[:80]}",
                        "concept_tags": ["__channel2_confusion__"],
                        "salience": 0.6,
                    }
                )
                break

        # Mastery
        for kw in ext_cfg["mastery_keywords"]:
            if kw in msg:
                signals.append(
                    {
                        "fact_type": "concept_mastered",
                        "content": f"学生表示理解: {msg[:80]}",
                        "concept_tags": ["__channel2_mastery__"],
                        "salience": 0.6,
                    }
                )
                break

        # Negative emotion
        for kw in ext_cfg["emotion_negative_keywords"]:
            if kw in msg:
                signals.append(
                    {
                        "fact_type": "student_state",
                        "content": f"学生情绪低落: {msg[:80]}",
                        "concept_tags": ["__channel2_negative_emotion__"],
                        "salience": 0.5,
                    }
                )
                break

        # Preference
        pref_cfg = ext_cfg["preference_keywords"]
        for pref_key, keywords in pref_cfg.items():
            for kw in keywords:
                if kw in msg:
                    display = {"example_first": "例子优先", "step_by_step": "步骤化"}.get(
                        pref_key, pref_key
                    )
                    signals.append(
                        {
                            "fact_type": "preference",
                            "content": f"学生偏好{display}学习方式",
                            "concept_tags": [f"__channel2_preference_{pref_key}__"],
                            "salience": 0.5,
                        }
                    )
                    break

        if signals:
            self.write_facts(db, character_id, world_id, signals)

    # ---------------------------------------------------------------
    # Effective salience (M3)
    # ---------------------------------------------------------------

    def compute_effective_salience(self, fact: MemoryFact) -> float:
        """Compute dynamic salience with type-based decay and recall reinforcement."""
        cfg = _cfg()
        base_decay = cfg["memory"]["salience_base_decay"]
        recall_factor = cfg["memory"]["salience_recall_factor"]
        multipliers = cfg["salience_type_multiplier"]

        multiplier = multipliers.get(fact.fact_type, 1.0)
        if multiplier == 0.0:
            return fact.salience  # no decay

        now = datetime.now(UTC)
        created = fact.created_at
        if created is None:
            hours_elapsed = 0
        else:
            # SQLite stores DateTime without tz; coerce to UTC to subtract.
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            hours_elapsed = (now - created).total_seconds() / 3600
        recall_count = fact.recall_count or 0

        adjusted_decay = base_decay * multiplier / (1 + recall_count * recall_factor)
        retention = math.exp(-adjusted_decay * hours_elapsed / 24)
        return fact.salience * retention

    # ---------------------------------------------------------------
    # Maintenance
    # ---------------------------------------------------------------

    def cleanup_expired(self, db: Session) -> int:
        """Remove expired memories. Returns count deleted."""
        return memory_facts_service.delete_expired_memories(db)

    # ---------------------------------------------------------------
    # Internal: dedup lookup
    # ---------------------------------------------------------------

    def _find_duplicate(
        self,
        db: Session,
        character_id: int,
        fact_type: str,
        concept_tags: list[str],
        cutoff: datetime,
    ) -> MemoryFact | None:
        """Find a recent memory with same character, type, and overlapping tags."""
        q = db.query(MemoryFact).filter(
            MemoryFact.character_id == character_id,
            MemoryFact.fact_type == fact_type,
            MemoryFact.created_at >= cutoff,
        )

        if concept_tags:
            for tag in concept_tags:
                q = q.filter(MemoryFact.concept_tags.contains(f'"{tag}"'))
        else:
            # No tags: cannot do tag-based dedup, skip
            return None

        return q.first()


# Global instance
memory_manager = MemoryManager()