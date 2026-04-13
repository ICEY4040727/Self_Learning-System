"""World Setting Module

读取 world.scenes 中的 mood/theme_preset 等信息，注入到静态层。
这是世界级常量，属于静态层（缓存友好）。

See: docs/v1.0.0前后端联调修复/世界_课程_角色_表单设计.md Phase 3
"""

from backend.services.prompt_builder.base import MemoryModule


class WorldSettingModule(MemoryModule):
    """世界氛围设置模块

    从 World.scenes 中读取 mood/theme_preset/background 等信息，
    生成世界氛围描述，注入静态层影响 AI 行为。
    """

    def get_section_name(self) -> str:
        return "【当前世界】"

    def is_applicable(self, context: dict) -> bool:
        """需要有 world_id 才能获取世界信息"""
        return context.get("world_id") is not None

    def assemble(self, context: dict) -> str:
        """从 world.scenes 读取信息并渲染"""
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

        # 从 scenes 读取氛围信息
        scenes = world.scenes or {}

        # mood（氛围标签）
        mood = scenes.get("mood", [])
        if mood:
            mood_str = "、".join(mood) if isinstance(mood, list) else mood
            parts.append(f"氛围基调：{mood_str}")

        # theme_preset（主题预设）
        theme_preset = scenes.get("theme_preset")
        if theme_preset:
            theme_names = {
                "academy": "学院",
                "library": "图书馆",
                "laboratory": "实验室",
                "mountain_academy": "山林书院",
                "cyberspace": "赛博空间",
                "blank": "空白画布",
            }
            theme_name = theme_names.get(theme_preset, theme_preset)
            parts.append(f"世界风格：{theme_name}")

        # bgm（背景音乐）
        bgm = scenes.get("bgm")
        if bgm:
            bgm_names = {
                "white_noise": "自习室白噪",
                "rainy_piano": "雨夜钢琴",
                "morning_guitar": "晨光木吉他",
                "silent": "静音",
            }
            bgm_name = bgm_names.get(bgm, bgm)
            parts.append(f"背景氛围：{bgm_name}")

        # 综合引导
        if mood or theme_preset:
            parts.append("请让你的对话风格与此氛围契合。")

        return " ".join(parts)
