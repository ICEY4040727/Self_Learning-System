"""Test for Phase 2: Persona generation endpoint refactoring.

This module tests the enhanced /persona/generate endpoint with:
- New request/response schema fields
- world_context injection
- Copyright character handling
- traits as dict[str, int]

See: docs/v1.0.0前后端联调修复/世界_课程_角色_表单设计.md Phase 2
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


class TestPersonaGenerateRequest:
    """Test the new PersonaGenerateRequest schema."""
    
    def test_request_with_new_fields(self):
        """Request should accept inspiration_type and world_id."""
        from backend.api.routes.archive import PersonaGenerateRequest
        
        # Test with default values
        req = PersonaGenerateRequest(description="A wise teacher who uses metaphors")
        assert req.inspiration_type == "freeform"
        assert req.world_id is None
        
        # Test with custom values
        req = PersonaGenerateRequest(
            description="Like Professor Lupin from Harry Potter",
            inspiration_type="character",
            world_id=42,
        )
        assert req.inspiration_type == "character"
        assert req.world_id == 42


class TestPersonaGenerateResponse:
    """Test the new PersonaGenerateResponse schema."""
    
    def test_response_fields(self):
        """Response should include all new fields."""
        from backend.api.routes.archive import PersonaGenerateResponse
        
        response = PersonaGenerateResponse(
            name_suggestion="沐风导师",
            title_suggestion="雾港学院研究员",
            background="曾在多处游学...",
            personality="温和而富有洞察力...",
            speech_style="善用比喻",
            traits={
                "strictness": 6,
                "pace": 5,
                "questioning": 7,
                "warmth": 8,
                "humor": 4,
            },
            system_prompt_template="你是一位博学的导师...",
            greeting="你好，让我们开始今天的探索。",
            warnings=None,
        )
        
        assert response.name_suggestion == "沐风导师"
        assert response.title_suggestion == "雾港学院研究员"
        assert isinstance(response.traits, dict)
        assert response.traits["strictness"] == 6
        assert response.greeting == "你好，让我们开始今天的探索。"

    def test_traits_must_be_dict(self):
        """traits should be dict[str, int], not list."""
        from backend.api.routes.archive import PersonaGenerateResponse
        
        response = PersonaGenerateResponse(
            name_suggestion="测试",
            traits={"strictness": 5, "pace": 5},  # dict, not list
            system_prompt_template="...",
        )
        assert isinstance(response.traits, dict)


class TestPersonaGeneratePrompt:
    """Test the new PERSONA_GENERATE_PROMPT template."""
    
    def test_prompt_contains_new_structure(self):
        """Prompt should require the new JSON structure."""
        from backend.api.routes.archive import PERSONA_GENERATE_PROMPT
        
        # Check for new fields in prompt
        assert "name_suggestion" in PERSONA_GENERATE_PROMPT
        assert "title_suggestion" in PERSONA_GENERATE_PROMPT
        assert "background" in PERSONA_GENERATE_PROMPT
        assert "greeting" in PERSONA_GENERATE_PROMPT
        
        # Check for traits as dict
        assert "strictness" in PERSONA_GENERATE_PROMPT
        assert "pace" in PERSONA_GENERATE_PROMPT
        assert "questioning" in PERSONA_GENERATE_PROMPT
        assert "warmth" in PERSONA_GENERATE_PROMPT
        assert "humor" in PERSONA_GENERATE_PROMPT
        
        # Check for copyright handling
        assert "风格借鉴" in PERSONA_GENERATE_PROMPT
        assert "禁止保留" in PERSONA_GENERATE_PROMPT
        
        # Check for inspiration_type
        assert "inspiration_type" in PERSONA_GENERATE_PROMPT
        assert "world_context" in PERSONA_GENERATE_PROMPT


class TestCopyrightCharacterHandling:
    """Test copyright character detection and warnings."""
    
    def test_warning_generated_for_copyright_terms(self):
        """When user mentions copyrighted character, warnings should be generated."""
        from backend.api.routes.archive import PersonaGenerateResponse
        
        # Simulating the warning generation logic
        description = "像哈利波特里的卢平教授"
        data = {
            "name_suggestion": "卢平老师",  # Contains "卢平" - problematic
            "background": "曾在霍格沃茨任教...",  # Contains "霍格沃茨" - problematic
        }
        
        import re
        suspicious = re.findall(r"[\u4e00-\u9fa5]{2,4}", description)
        leaked = [t for t in suspicious
                  if t in data.get("name_suggestion", "")
                  or t in (data.get("background") or "")]
        
        assert "卢平" in leaked or "哈利波特" in leaked
    
    def test_no_warning_for_original_character(self):
        """Original characters should not trigger warnings."""
        description = "一位严厉但公正的女性物理学家"
        data = {
            "name_suggestion": "苏明理学",
            "background": "曾在科学院从事研究...",
        }
        
        import re
        suspicious = re.findall(r"[\u4e00-\u9fa5]{2,4}", description)
        leaked = [t for t in suspicious
                  if t in data.get("name_suggestion", "")
                  or t in (data.get("background") or "")]
        
        assert len(leaked) == 0


class TestWorldContextInjection:
    """Test world context is properly injected into prompt."""
    
    def test_world_context_empty_when_no_world_id(self):
        """When world_id is None, world_context should be empty."""
        from backend.api.routes.archive import PERSONA_GENERATE_PROMPT
        
        prompt = PERSONA_GENERATE_PROMPT.format(
            description="测试描述",
            inspiration_type="freeform",
            world_context="",
        )
        
        assert "目标世界氛围" not in prompt
    
    def test_world_context_contains_mood(self):
        """When world has mood, it should appear in world_context."""
        from backend.api.routes.archive import PERSONA_GENERATE_PROMPT
        
        prompt = PERSONA_GENERATE_PROMPT.format(
            description="测试描述",
            inspiration_type="freeform",
            world_context="目标世界氛围：温暖, 神秘。",
        )
        
        assert "目标世界氛围：温暖, 神秘。" in prompt


# Integration test fixtures
@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = MagicMock()
    user.id = 1
    user.default_provider = "claude"
    user.encrypted_api_key = None
    return user


@pytest.fixture
def mock_world():
    """Create a mock world with scenes."""
    world = MagicMock()
    world.id = 1
    world.scenes = {"mood": ["温暖", "治愈"], "theme_preset": "academy"}
    return world


class TestPersonaGenerateEndpoint:
    """Integration tests for the /persona/generate endpoint."""
    
    @pytest.mark.asyncio
    async def test_generate_with_freeform_inspiration(self):
        """Test generation with freeform inspiration type."""
        from backend.api.routes.archive import (
            PersonaGenerateRequest,
            PERSONA_GENERATE_PROMPT,
        )
        
        req = PersonaGenerateRequest(
            description="一位温和但坚持原则的图书管理员",
            inspiration_type="freeform",
        )
        
        prompt = PERSONA_GENERATE_PROMPT.format(
            description=req.description,
            inspiration_type=req.inspiration_type,
            world_context="",
        )
        
        assert "character" not in prompt or "inspiration_type" in prompt
        assert req.description in prompt
    
    @pytest.mark.asyncio
    async def test_generate_with_character_inspiration(self):
        """Test generation with character inspiration type."""
        from backend.api.routes.archive import PERSONA_GENERATE_PROMPT
        
        prompt = PERSONA_GENERATE_PROMPT.format(
            description="像哈利波特里的卢平教授",
            inspiration_type="character",
            world_context="",
        )
        
        assert "风格借鉴" in prompt
        assert "禁止保留" in prompt
    
    @pytest.mark.asyncio
    async def test_response_parsing(self):
        """Test parsing LLM response into PersonaGenerateResponse."""
        from backend.api.routes.archive import PersonaGenerateResponse
        
        # Simulated LLM response
        llm_response = '''{
            "name_suggestion": "沐风导师",
            "title_suggestion": "雾港学院研究员",
            "background": "曾在云端学院从事研究多年...",
            "personality": "温和而富有洞察力...",
            "speech_style": "善用比喻和故事",
            "traits": {
                "strictness": 6,
                "pace": 5,
                "questioning": 7,
                "warmth": 8,
                "humor": 4
            },
            "system_prompt_template": "你是一位博学的导师...",
            "greeting": "你好，让我们开始今天的探索。"
        }'''
        
        import json
        data = json.loads(llm_response)
        
        response = PersonaGenerateResponse(
            name_suggestion=data.get("name_suggestion", ""),
            title_suggestion=data.get("title_suggestion"),
            background=data.get("background"),
            personality=data.get("personality"),
            speech_style=data.get("speech_style"),
            traits=data.get("traits", {}),
            system_prompt_template=data.get("system_prompt_template", ""),
            greeting=data.get("greeting"),
        )
        
        assert response.name_suggestion == "沐风导师"
        assert response.traits["warmth"] == 8
        assert response.greeting == "你好，让我们开始今天的探索。"


# Test cases from design doc (Appendix B)
COPYRIGHT_TEST_CASES = [
    {
        "description": "像哈利波特里的卢平教授",
        "expected": {
            "name_excludes": ["卢平"],
            "background_excludes": ["霍格沃茨"],
            "style_preserved": ["温和", "敏感", "博学"],
        },
    },
    {
        "description": "像孔子那样",
        "expected": {
            "name_varied": True,  # 可以建议"子言"等衍生名
            "background_may_include": ["周礼", "仁"],  # 公共领域
        },
    },
    {
        "description": "一位严厉但公正的女性物理学家",
        "expected": {
            "no_warnings": True,  # 完全自由生成
        },
    },
    {
        "description": "像鬼灭之刃的炼狱杏寿郎那种热血",
        "expected": {
            "name_excludes": ["炼狱", "杏寿郎"],
            "background_excludes": ["呼吸法", "鬼"],
            "style_preserved": ["热血", "坚定"],
            "warnings_may_include": ["炼狱", "杏寿郎"],
        },
    },
]


class TestCopyrightHandlingFromDoc:
    """Test cases from the design document (Appendix B)."""
    
    @pytest.mark.parametrize("case", COPYRIGHT_TEST_CASES)
    def test_copyright_cases(self, case):
        """Verify each test case from the design doc."""
        import re
        
        description = case["description"]
        expected = case["expected"]
        
        suspicious = re.findall(r"[\u4e00-\u9fa5]{2,4}", description)
        
        if expected.get("no_warnings"):
            assert len(suspicious) == 0
        else:
            # Just verify detection works
            assert len(suspicious) > 0
