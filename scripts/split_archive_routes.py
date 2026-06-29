#!/usr/bin/env python3
"""One-shot helper: split archive.py into slug-aligned route modules (Seam B)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "backend" / "api" / "routes" / "archive.py"
ROUTES = ROOT / "backend" / "api" / "routes"


def lines(start: int, end: int) -> str:
    text = ARCHIVE.read_text(encoding="utf-8").splitlines()
    return "\n".join(text[start - 1 : end]) + "\n"


def write(name: str, header: str, body: str) -> None:
    path = ROUTES / name
    path.write_text(header + body, encoding="utf-8")
    line_count = len((header + body).splitlines())
    print(f"wrote {path.name}: {line_count} lines")


COMMON_HEADER = '''\
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from backend.api.routes.auth import get_current_user
from backend.db.database import get_db
from backend.models import models as models_module
from backend.models.models import User

router = APIRouter()

'''

CHARACTERS_HEADER = COMMON_HEADER.replace(
    "from backend.models.models import User\n",
    """from backend.models.models import Character, User, World, WorldCharacter

from backend.services.character_llm_settings import normalize_character_llm_settings
from backend.services.user_llm_settings import get_effective_llm_config

""",
)

WORLDS_HEADER = COMMON_HEADER.replace(
    "from backend.models.models import User\n",
    """from backend.models.models import Character, Course, ProgressTracking, User, World, WorldCharacter

from backend.api.routes.courses import CourseResponse
from backend.services.user_llm_settings import get_effective_llm_config

""",
)

LEARNER_HEADER = COMMON_HEADER.replace(
    "from backend.models.models import User\n",
    "from backend.models.models import LearnerProfile, User, World\n\n",
)

COURSES_HEADER = COMMON_HEADER.replace(
    "from backend.models.models import User\n",
    """from backend.models.models import (
    Character,
    ChatMessage,
    Course,
    MemoryFact,
    User,
    World,
    WorldCharacter,
)

""",
)

SETTINGS_HEADER = COMMON_HEADER.replace(
    "from backend.models.models import User\n",
    """from backend.models.models import User

from backend.core.conflicts.user_llm_settings import raise_settings_conflict_http
from backend.services.user_llm_settings import (
    get_effective_llm_config,
    lock_user_for_update,
    normalize_base_url,
    serialize_provider_settings,
    update_generation_params,
    update_provider_settings,
)

""",
)

DIARY_HEADER = COMMON_HEADER.replace(
    "from backend.models.models import User\n",
    "from backend.models.models import Course, LearningDiary, User, World\n\n",
)

ARCHIVE_SHELL_HEADER = '''\
"""Archive compat shell — aggregates slug routes + progress compat surface (v1.0.5 Seam B)."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.api.routes import characters, courses, learner_profiles, learning_diary, settings, worlds
from backend.api.routes.auth import get_current_user
from backend.db.database import get_db
from backend.models.models import Course, User, World

router = APIRouter()
router.include_router(characters.router)
router.include_router(worlds.router)
router.include_router(learner_profiles.router)
router.include_router(courses.router)
router.include_router(settings.router)
router.include_router(learning_diary.router)

# Re-exports for tests / legacy imports
from backend.api.routes.characters import (  # noqa: E402, F401
    PERSONA_GENERATE_PROMPT,
    PERSONA_TEMPLATES,
    PersonaGenerateRequest,
    PersonaGenerateResponse,
)

'''


def main() -> None:
    # characters: naming comment, persona templates, char schemas, char endpoints, sprites, persona
    write(
        "characters.py",
        CHARACTERS_HEADER,
        lines(39, 51)
        + "\n"
        + lines(86, 165)
        + "\n"
        + lines(399, 635)
        + lines(1210, 1277)
        + lines(2206, 2361),
    )

    # worlds: cooldown, world generate schemas, world schemas+helpers, world endpoints
    write(
        "worlds.py",
        WORLDS_HEADER,
        lines(53, 84)
        + "\n"
        + lines(167, 315)
        + "\n"
        + lines(637, 1208),
    )

    write(
        "learner_profiles.py",
        LEARNER_HEADER,
        lines(319, 328) + "\n" + lines(1280, 1375),
    )

    write(
        "courses.py",
        COURSES_HEADER,
        lines(331, 357)
        + "\n"
        + lines(1378, 1741),
    )

    write(
        "learning_diary.py",
        DIARY_HEADER,
        lines(370, 381) + "\n" + lines(1744, 1782),
    )

    write(
        "settings.py",
        SETTINGS_HEADER,
        lines(1937, 2203),
    )

    # archive shell: progress schemas + endpoints only
    write(
        "archive.py",
        ARCHIVE_SHELL_HEADER,
        lines(384, 396)
        + "\n"
        + lines(1785, 1934),
    )


if __name__ == "__main__":
    main()
