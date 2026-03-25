"""Tests for ZPD scaffold level computation."""

from backend.services.learning_engine import LearningEngine


class TestComputeScaffoldLevel:
    """Test all branches of compute_scaffold_level(emotion, mastery)."""

    def test_frustration_low_mastery(self):
        assert LearningEngine.compute_scaffold_level("frustration", 20) == 5

    def test_frustration_high_mastery(self):
        assert LearningEngine.compute_scaffold_level("frustration", 60) == 4

    def test_confusion_low_mastery(self):
        assert LearningEngine.compute_scaffold_level("confusion", 30) == 4

    def test_confusion_high_mastery(self):
        assert LearningEngine.compute_scaffold_level("confusion", 60) == 3

    def test_anxiety_low_mastery(self):
        assert LearningEngine.compute_scaffold_level("anxiety", 40) == 4

    def test_anxiety_high_mastery(self):
        assert LearningEngine.compute_scaffold_level("anxiety", 70) == 3

    def test_curiosity_high_mastery(self):
        assert LearningEngine.compute_scaffold_level("curiosity", 70) == 2

    def test_curiosity_low_mastery(self):
        assert LearningEngine.compute_scaffold_level("curiosity", 40) == 3

    def test_excitement_high_mastery(self):
        assert LearningEngine.compute_scaffold_level("excitement", 80) == 1

    def test_excitement_low_mastery(self):
        assert LearningEngine.compute_scaffold_level("excitement", 50) == 2

    def test_satisfaction_high_mastery(self):
        assert LearningEngine.compute_scaffold_level("satisfaction", 80) == 1

    def test_satisfaction_low_mastery(self):
        assert LearningEngine.compute_scaffold_level("satisfaction", 50) == 2

    def test_boredom_high_mastery(self):
        assert LearningEngine.compute_scaffold_level("boredom", 70) == 2

    def test_boredom_low_mastery(self):
        assert LearningEngine.compute_scaffold_level("boredom", 40) == 3

    def test_neutral_high_mastery(self):
        assert LearningEngine.compute_scaffold_level("neutral", 80) == 2

    def test_neutral_low_mastery(self):
        assert LearningEngine.compute_scaffold_level("neutral", 20) == 4

    def test_neutral_mid_mastery(self):
        assert LearningEngine.compute_scaffold_level("neutral", 50) == 3

    def test_unknown_emotion(self):
        assert LearningEngine.compute_scaffold_level("unknown", 50) == 3
