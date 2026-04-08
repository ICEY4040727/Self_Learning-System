"""Course Intent Module

读取 Course.meta 中的学习意图信息（current_level/target_level/motivation/pace），
生成学习目标描述，注入静态层。

See: docs/v1.0.0前后端联调修复/世界_课程_角色_表单设计.md Phase 3
      附录 A - Course.meta JSON 结构与枚举值
"""

from backend.services.prompt_builder.base import MemoryModule


# 字段枚举值标签映射（附录 A 定义）
CURRENT_LEVEL_LABELS = {
    "none": "完全陌生",
    "heard": "听说过",
    "tried": "用过一点",
    "basic": "已有基础",
}

TARGET_LEVEL_LABELS = {
    "understand": "看懂入门",
    "applier": "能独立应用",
    "teacher": "能教别人",
    "expert": "达到专业水准",
}

MOTIVATION_LABELS = {
    "interest": "出于个人兴趣",
    "exam": "为了通过考试",
    "work": "工作所需",
    "problem": "为了解决具体问题",
    "companion": "陪伴孩子学习",
}

PACE_LABELS = {
    "chill": "慢节奏，重消化",
    "normal": "稳步推进",
    "sprint": "高强度冲刺",
}


class CourseIntentModule(MemoryModule):
    """课程学习意图模块
    
    从 Course.meta 读取学习目标信息：
    - current_level: 学生当前水平
    - target_level: 学习目标
    - motivation: 学习动机
    - motivation_detail: 动机详细说明
    - pace: 学习节奏
    
    这是会话级静态层，每个 session 的课程不变。
    """
    
    def get_section_name(self) -> str:
        return "【学习目标】"
    
    def is_applicable(self, context: dict) -> bool:
        """需要有 course_id 才能获取课程信息"""
        return context.get("course_id") is not None
    
    def assemble(self, context: dict) -> str:
        """从 Course.meta 读取信息并渲染"""
        db = context.get("db")
        course_id = context.get("course_id")
        
        if not db or not course_id:
            return ""
        
        from backend.models.models import Course
        
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return ""
        
        meta = course.meta or {}
        parts = []
        
        # 课程名称
        if course.name:
            parts.append(f"当前课程：{course.name}")
        
        # 当前水平
        current_level = meta.get("current_level")
        if current_level:
            label = CURRENT_LEVEL_LABELS.get(current_level, current_level)
            parts.append(f"学生当前水平：**{label}**")
        
        # 目标水平
        target_level = meta.get("target_level") or course.target_level
        if target_level:
            label = TARGET_LEVEL_LABELS.get(target_level, target_level)
            parts.append(f"目标水平：**{label}**")
        
        # 学习动机
        motivation = meta.get("motivation")
        motivation_detail = meta.get("motivation_detail")
        if motivation:
            label = MOTIVATION_LABELS.get(motivation, motivation)
            if motivation_detail:
                parts.append(f"学习动机：**{label}**（{motivation_detail}）")
            else:
                parts.append(f"学习动机：**{label}**")
        
        # 学习节奏
        pace = meta.get("pace")
        if pace:
            label = PACE_LABELS.get(pace, pace)
            parts.append(f"学习节奏：**{label}**")
        
        # 综合指导
        if current_level or target_level or motivation:
            parts.append(
                "请按上述目标推进，避免超出/低于当前水平的内容。"
            )
        
        return " ".join(parts)
