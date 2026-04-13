"""
UserProfile 测试 - 跨世界特征聚合

测试根据 learning_memory_theory.md 第五部分的设计实现。
"""

from unittest.mock import MagicMock

import pytest

from backend.services.user_profile import (
    MSKT_DIMENSIONS,
    compute_learning_stats,
    compute_metacognition_trend,
    compute_preference_stability,
    normalize_mskt_value,
)


class TestNormalizeMSKTValue:
    """测试 MSKT 值归一化"""

    def test_weak_maps_to_1(self):
        assert normalize_mskt_value("weak") == 1

    def test_moderate_maps_to_2(self):
        assert normalize_mskt_value("moderate") == 2

    def test_strong_maps_to_3(self):
        assert normalize_mskt_value("strong") == 3

    def test_unknown_maps_to_0(self):
        assert normalize_mskt_value("unknown") == 0
        assert normalize_mskt_value(None) == 0


class TestComputeMetacognitionTrend:
    """测试元认知趋势计算"""

    def test_empty_profiles(self):
        result = compute_metacognition_trend([])
        assert result == {}

    def test_single_profile_unknown_trend(self):
        """单个世界无法计算趋势"""
        profiles = [
            {
                "world_id": 1,
                "metacognition": {
                    "planning": {
                        "value": "moderate",
                        "t_updated": "2026-04-01T10:00:00Z"
                    }
                }
            }
        ]
        result = compute_metacognition_trend(profiles)

        assert "planning" in result
        assert result["planning"]["current"] == "moderate"
        assert result["planning"]["trend"] == "unknown"
        assert result["planning"]["evidence_count"] == 1

    def test_two_profiles_improving_trend(self):
        """两个世界，后一个比前一个好"""
        profiles = [
            {
                "world_id": 1,
                "metacognition": {
                    "planning": {
                        "value": "weak",
                        "t_updated": "2026-04-01T10:00:00Z"
                    }
                }
            },
            {
                "world_id": 2,
                "metacognition": {
                    "planning": {
                        "value": "moderate",
                        "t_updated": "2026-04-05T10:00:00Z"
                    }
                }
            }
        ]
        result = compute_metacognition_trend(profiles)

        assert result["planning"]["current"] == "moderate"
        assert result["planning"]["trend"] == "improving"
        assert result["planning"]["evidence_count"] == 2

    def test_two_profiles_stable_trend(self):
        """两个世界，值相同"""
        profiles = [
            {
                "world_id": 1,
                "metacognition": {
                    "planning": {
                        "value": "moderate",
                        "t_updated": "2026-04-01T10:00:00Z"
                    }
                }
            },
            {
                "world_id": 2,
                "metacognition": {
                    "planning": {
                        "value": "moderate",
                        "t_updated": "2026-04-05T10:00:00Z"
                    }
                }
            }
        ]
        result = compute_metacognition_trend(profiles)

        assert result["planning"]["current"] == "moderate"
        assert result["planning"]["trend"] == "stable"

    def test_multiple_dimensions(self):
        """测试多个维度"""
        profiles = [
            {
                "world_id": 1,
                "metacognition": {
                    "planning": {"value": "weak", "t_updated": "2026-04-01T10:00:00Z"},
                    "monitoring": {"value": "moderate", "t_updated": "2026-04-01T10:00:00Z"},
                    "regulating": {"value": "strong", "t_updated": "2026-04-01T10:00:00Z"},
                    "reflecting": {"value": "moderate", "t_updated": "2026-04-01T10:00:00Z"},
                }
            },
            {
                "world_id": 2,
                "metacognition": {
                    "planning": {"value": "moderate", "t_updated": "2026-04-05T10:00:00Z"},
                    "monitoring": {"value": "moderate", "t_updated": "2026-04-05T10:00:00Z"},
                    "regulating": {"value": "weak", "t_updated": "2026-04-05T10:00:00Z"},
                    "reflecting": {"value": "strong", "t_updated": "2026-04-05T10:00:00Z"},
                }
            }
        ]
        result = compute_metacognition_trend(profiles)

        # 4个维度都应该存在
        for dim in MSKT_DIMENSIONS:
            assert dim in result
            assert "current" in result[dim]
            assert "trend" in result[dim]


class TestComputePreferenceStability:
    """测试偏好稳定性计算"""

    def test_empty_profiles(self):
        result = compute_preference_stability([])
        assert result == {}

    def test_single_profile_insufficient_data(self):
        """单个世界无法计算稳定性"""
        profiles = [
            {
                "world_id": 1,
                "preferences": {
                    "visual_examples": {"value": True, "confidence": 0.8}
                }
            }
        ]
        result = compute_preference_stability(profiles)

        assert result["visual_examples"]["status"] == "insufficient_data"

    def test_boolean_consistent(self):
        """布尔值偏好高度一致"""
        profiles = [
            {
                "world_id": 1,
                "preferences": {
                    "visual_examples": {"value": True, "confidence": 0.8}
                }
            },
            {
                "world_id": 2,
                "preferences": {
                    "visual_examples": {"value": True, "confidence": 0.9}
                }
            },
            {
                "world_id": 3,
                "preferences": {
                    "visual_examples": {"value": True, "confidence": 0.7}
                }
            }
        ]
        result = compute_preference_stability(profiles)

        assert result["visual_examples"]["stable"] == True
        assert result["visual_examples"]["consistency"] == 1.0
        assert result["visual_examples"]["display"] == "稳定"

    def test_boolean_inconsistent(self):
        """布尔值偏好不一致"""
        profiles = [
            {
                "world_id": 1,
                "preferences": {
                    "visual_examples": {"value": True, "confidence": 0.8}
                }
            },
            {
                "world_id": 2,
                "preferences": {
                    "visual_examples": {"value": False, "confidence": 0.9}
                }
            },
            {
                "world_id": 3,
                "preferences": {
                    "visual_examples": {"value": False, "confidence": 0.7}
                }
            }
        ]
        result = compute_preference_stability(profiles)

        assert result["visual_examples"]["stable"] == False
        assert result["visual_examples"]["consistency"] == pytest.approx(1/3)
        assert result["visual_examples"]["display"] == "变化中"

    def test_string_enum_most_common(self):
        """字符串枚举值取最常见的"""
        profiles = [
            {
                "world_id": 1,
                "preferences": {
                    "pace": {"value": "slow", "confidence": 0.8}
                }
            },
            {
                "world_id": 2,
                "preferences": {
                    "pace": {"value": "slow", "confidence": 0.9}
                }
            },
            {
                "world_id": 3,
                "preferences": {
                    "pace": {"value": "fast", "confidence": 0.7}
                }
            }
        ]
        result = compute_preference_stability(profiles)

        assert result["pace"]["stable"] == True
        assert result["pace"]["most_common"] == "slow"
        assert result["pace"]["display"] == "slow"


class TestComputeLearningStats:
    """测试学习统计计算"""

    def test_empty_profiles(self):
        """空profile"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = compute_learning_stats(mock_db, [])

        assert result["total_concepts_learned"] == 0
        assert result["total_sessions"] == 0
        assert result["average_mastery"] == 0
        assert result["worlds_explored"] == 0

    def test_single_world_with_knowledge(self):
        """单个世界有知识图谱"""
        mock_db = MagicMock()

        # Mock Knowledge
        mock_knowledge = MagicMock()
        mock_knowledge.graph = {
            "concepts": {
                "concept1": {"mastery": 0.8},
                "concept2": {"mastery": 0.6},
                "concept3": {"mastery": 0.9}
            }
        }
        mock_db.query.return_value.filter.return_value.first.return_value = mock_knowledge

        profiles = [
            {
                "world_id": 1,
                "session_count": 5
            }
        ]

        result = compute_learning_stats(mock_db, profiles)

        assert result["total_concepts_learned"] == 3
        assert result["total_sessions"] == 5
        assert result["average_mastery"] == pytest.approx(0.767, rel=0.01)
        assert result["worlds_explored"] == 1

    def test_multiple_worlds(self):
        """多个世界"""
        mock_db = MagicMock()

        # Mock for world 1
        mock_knowledge1 = MagicMock()
        mock_knowledge1.graph = {
            "concepts": {
                "concept1": {"mastery": 0.8}
            }
        }

        # Mock for world 2
        mock_knowledge2 = MagicMock()
        mock_knowledge2.graph = {
            "concepts": {
                "concept2": {"mastery": 0.6},
                "concept3": {"mastery": 0.9}
            }
        }

        def mock_filter(*args):
            mock_result = MagicMock()
            world_id = args[1].right.value if hasattr(args[1], 'right') else None
            if world_id == 1:
                mock_result.first.return_value = mock_knowledge1
            elif world_id == 2:
                mock_result.first.return_value = mock_knowledge2
            else:
                mock_result.first.return_value = None
            return mock_result

        mock_db.query.return_value.filter.side_effect = mock_filter

        profiles = [
            {"world_id": 1, "session_count": 3},
            {"world_id": 2, "session_count": 7}
        ]

        result = compute_learning_stats(mock_db, profiles)

        assert result["total_concepts_learned"] == 3
        assert result["total_sessions"] == 10
        assert result["worlds_explored"] == 2
        # Average of (0.8) and (0.75) = 0.775
        assert result["average_mastery"] == pytest.approx(0.775, rel=0.01)
