# Modules subpackage
# 记忆模块实现
# P1 #183: 移除 KnowledgeModule, MemoryRetrievalModule
# P1 #183: 添加 MemoryFactsModule

from backend.services.prompt_builder.modules.preference import PreferenceModule
from backend.services.prompt_builder.modules.metacognition import MetacognitionModule
from backend.services.prompt_builder.modules.affect import AffectModule
from backend.services.prompt_builder.modules.misconception import MisconceptionModule
from backend.services.prompt_builder.modules.episode import EpisodeModule
from backend.services.prompt_builder.modules.memory_facts import MemoryFactsModule
from backend.services.prompt_builder.modules.world_setting import WorldSettingModule
from backend.services.prompt_builder.modules.course_intent import CourseIntentModule

__all__ = [
    "PreferenceModule",
    "MetacognitionModule",
    "AffectModule",
    "MisconceptionModule",
    "EpisodeModule",
    "MemoryFactsModule",
    "WorldSettingModule",
    "CourseIntentModule",
]
