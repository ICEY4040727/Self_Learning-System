"""Spaced repetition service based on FSRS (Free Spaced Repetition Scheduler).

Wraps py-fsrs to provide topic-level review scheduling for the learning system.
Each ProgressTracking record stores an FSRS Card state in its `fsrs_state` JSON column.
"""

from datetime import datetime, timezone
from typing import Optional

from fsrs import Card, Rating, Scheduler, State


# Shared scheduler instance with sensible defaults for educational context
_scheduler = Scheduler(
    desired_retention=0.85,          # target 85% recall
    enable_fuzzing=True,             # add slight randomness to intervals
)

# Rating helpers – map integer (1-4) to fsrs.Rating
RATING_MAP = {
    1: Rating.Again,
    2: Rating.Hard,
    3: Rating.Good,
    4: Rating.Easy,
}


def new_card() -> dict:
    """Create a fresh FSRS card state (serialised to dict)."""
    return Card().to_dict()


def review(fsrs_state: Optional[dict], rating_int: int) -> dict:
    """
    Review a topic and return updated state.

    Args:
        fsrs_state: existing Card dict from DB (or None for first review)
        rating_int: 1=Again, 2=Hard, 3=Good, 4=Easy

    Returns:
        dict with keys: fsrs_state, due, last_review, mastery_level, retrievability
    """
    if rating_int not in RATING_MAP:
        raise ValueError(f"rating must be 1-4, got {rating_int}")

    rating = RATING_MAP[rating_int]
    now = datetime.now(timezone.utc)

    # Restore or create card
    if fsrs_state:
        card = Card.from_dict(fsrs_state)
    else:
        card = Card()

    # Perform the review
    card, _review_log = _scheduler.review_card(card, rating, review_datetime=now)

    # Compute retrievability (0.0 – 1.0)
    retrievability = _scheduler.get_card_retrievability(card, now)

    # Map to mastery_level 0-100
    mastery_level = _compute_mastery(card, retrievability)

    return {
        "fsrs_state": card.to_dict(),
        "due": card.due,
        "last_review": now,
        "mastery_level": mastery_level,
        "retrievability": round(retrievability, 3),
    }


def get_retrievability(fsrs_state: dict) -> float:
    """Get current recall probability for a card."""
    card = Card.from_dict(fsrs_state)
    return _scheduler.get_card_retrievability(card, datetime.now(timezone.utc))


def _compute_mastery(card: Card, retrievability: float) -> int:
    """
    Compute a 0-100 mastery level from FSRS card state.

    Combines card state (learning/review) with retrievability:
    - Learning state: 0-30
    - Review state with low stability: 30-60
    - Review state with high stability: 60-100
    """
    if card.state == State.Learning:
        return int(retrievability * 30)
    elif card.state == State.Relearning:
        return int(20 + retrievability * 20)
    else:  # Review
        stability = card.stability or 1.0
        # stability grows with successful reviews; cap contribution at ~90 days
        stability_factor = min(1.0, stability / 90.0)
        base = 40 + stability_factor * 40   # 40-80
        return int(base + retrievability * 20)  # up to 100
