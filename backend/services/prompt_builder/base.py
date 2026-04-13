"""Prompt Builder Base Classes
模块化提示词注入器的抽象基类
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class MemoryModule(ABC):
    """记忆模块基类

    所有记忆模块需要实现以下方法：
    - get_section_name(): 返回模块名称
    - get_priority(): 返回组装顺序（越小越靠前）
    - should_include(): 判断是否包含此模块
    - assemble(): 组装模块内容
    """

    @abstractmethod
    def get_section_name(self) -> str:
        """模块名称，如【当前知识状态】"""
        pass

    @abstractmethod
    def get_priority(self) -> int:
        """组装顺序（越小越靠前）"""
        pass

    @abstractmethod
    def should_include(self, context: dict[str, Any]) -> bool:
        """是否包含此模块

        Args:
            context: 上下文字典，包含 db, world_id 等

        Returns:
            True 表示包含此模块
        """
        pass

    @abstractmethod
    def assemble(self, context: dict[str, Any]) -> str | None:
        """组装模块内容

        Args:
            context: 包含以下键的字典:
                - db: Session
                - world_id: int
                - session_id: int
                - learner_profile: LearnerProfile | None
                - user_message: str
                - prev_emotion: dict | None
                - checkpoint_time: str | None
                - ... 其他上下文

        Returns:
            组装后的字符串，或 None 表示跳过此模块
        """
        pass


class ContextProvider(ABC):
    """上下文提供者基类（关系阶段、脚手架等）

    与 MemoryModule 类似，但上下文提供者更基础，
    通常在 MemoryModules 之前组装。
    """

    @abstractmethod
    def get_priority(self) -> int:
        """组装顺序（越小越靠前）"""
        pass

    @abstractmethod
    def should_include(self, context: dict[str, Any]) -> bool:
        """是否包含此上下文"""
        pass

    @abstractmethod
    def assemble(self, context: dict[str, Any]) -> str | None:
        """组装上下文内容

        Args:
            context: 上下文字典

        Returns:
            组装后的字符串，或 None 表示跳过
        """
        pass
