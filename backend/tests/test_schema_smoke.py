"""
Schema Smoke Test - 验证模型导入和 API 可用性

确保 P1 #183 迁移后所有模型可以正确导入。
"""

from backend.main import app  # noqa: F401


def test_app_import():
    """验证 main.py 可以正确导入（无 Knowledge 模型）"""
    assert app is not None


def test_models_import():
    """验证所有模型可以正确导入"""
    from backend.models.models import (
        MemoryFact,
    )

    # 确保 MemoryFact 存在
    assert MemoryFact is not None


def test_services_import():
    """验证 services 可以正确导入"""
    # 确保没有 Knowledge 引用
    import inspect

    from backend.services.report import (
        build_world_comparison,
    )
    source = inspect.getsource(build_world_comparison)
    assert "Knowledge" not in source
