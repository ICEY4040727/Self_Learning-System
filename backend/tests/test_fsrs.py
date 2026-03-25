"""Tests for FSRS spaced repetition service."""

import pytest

from backend.services.spaced_repetition import get_retrievability, new_card, review


class TestNewCard:
    def test_returns_dict(self):
        card = new_card()
        assert isinstance(card, dict)


class TestReview:
    def test_first_review_good(self):
        result = review(None, 3)
        assert result["mastery_level"] >= 0
        assert result["due"] is not None
        assert result["last_review"] is not None
        assert result["fsrs_state"] is not None
        assert 0.0 <= result["retrievability"] <= 1.0

    def test_first_review_again(self):
        result = review(None, 1)
        assert result["mastery_level"] >= 0

    def test_first_review_easy(self):
        result = review(None, 4)
        assert result["mastery_level"] >= 0

    def test_sequential_reviews_increase_mastery(self):
        state = None
        prev_mastery = -1
        for _ in range(5):
            result = review(state, 3)  # Good rating each time
            state = result["fsrs_state"]
            assert result["mastery_level"] >= prev_mastery
            prev_mastery = result["mastery_level"]

    def test_invalid_rating_raises(self):
        with pytest.raises(ValueError):
            review(None, 0)
        with pytest.raises(ValueError):
            review(None, 5)

    def test_review_with_existing_state(self):
        first = review(None, 3)
        second = review(first["fsrs_state"], 3)
        assert second["fsrs_state"] is not None
        assert second["due"] is not None


class TestGetRetrievability:
    def test_new_card_retrievability(self):
        result = review(None, 3)
        r = get_retrievability(result["fsrs_state"])
        assert 0.0 <= r <= 1.0
