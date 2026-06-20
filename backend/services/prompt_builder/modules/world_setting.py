"""World Setting Module

读取最小世界壳信息，注入到静态层。
这是世界级常量，属于静态层（缓存友好）。
"""

from backend.services.prompt_builder.base import MemoryModule


class WorldSettingModule(MemoryModule):
    """世界壳静态模块

    从 World.name / World.description 读取最小世界壳信息，
    生成稳定的世界舞台描述，注入静态层影响 AI 行为。
    固定层：始终注入，优先级 5（最高）。
    """

    always_include = True

    def get_section_name(self) -> str:
        return "【当前世界】"

    def get_priority(self) -> int:
        return 5

    def is_applicable(self, context: dict) -> bool:
        """需要有 world_id 才能获取世界信息"""
        return context.get("world_id") is not None

    def should_include(self, context: dict) -> bool:
        return context.get("world_id") is not None

    def assemble(self, context: dict) -> str:
        """从最小世界壳读取信息并渲染"""
        db = context.get("db")
        world_id = context.get("world_id")

        if not db or not world_id:
            return ""

        from backend.models.models import World

        world = db.query(World).filter(World.id == world_id).first()
        if not world:
            return ""

        parts = []

        # 世界名称和描述
        parts.append(f"《{world.name}》")
        if world.description:
            parts.append(world.description)

        parts.append("请将对话稳定地放在这个长期学习世界中展开。")

        return " ".join(parts)
