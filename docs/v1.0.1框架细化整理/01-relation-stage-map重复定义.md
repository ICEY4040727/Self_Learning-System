# 问题 01: `stage_map`（关系阶段中英文映射）在两处重复定义

## 问题类型
重复定义

## 涉及文件
- `backend/api/routes/save.py` 第 223-228 行
- `backend/api/routes/archive.py` 第 589-594 行（`_build_world_response` 内）

## 重复内容

两处定义了完全相同的字典：

```python
stage_map = {
    "stranger": "初识",
    "acquaintance": "相识",
    "friend": "朋友",
    "mentor": "导师",
    "partner": "伙伴",
}
```

- `save.py` 用于 `_build_checkpoint_response` 函数，将 relationship stage 翻译为中文显示
- `archive.py` 用于 `_build_world_response` 函数，同样将 relationship stage 翻译为中文

## 影响分析

1. **维护风险**：如果新增或修改关系阶段（例如新增 "rival" 阶段），需要同时修改两处，容易遗漏
2. **违反 DRY 原则**：相同的业务映射散落在不同路由文件中

## ✅ 已确认修复方案

### 方案：在 `RelationshipService` 类上定义为类属性

选择放在 `RelationshipService` 类上作为类属性（与 `derive_stage` 同源，职责内聚）：

```python
# backend/services/relationship.py
class RelationshipService:
    STAGE_LABELS = {
        "stranger": "初识",
        "acquaintance": "相识",
        "friend": "朋友",
        "mentor": "导师",
        "partner": "伙伴",
    }

    def derive_stage(self, dimensions) -> str:
        ...
```

### 步骤

1. 在 `RelationshipService` 类上添加 `STAGE_LABELS` 类属性
2. `save.py` 第 223 行：改为 `from backend.services.relationship import relationship_service` → `stage = relationship_service.STAGE_LABELS.get(...)`
3. `archive.py` 第 589 行：同上
4. 删除两处 `stage_map = {...}` 局部变量定义

### 为什么不选 `backend/core/constants.py`

- `stage_map` 与 `derive_stage` 强绑定（阶段值来源于同一个类）
- 放在 `relationship.py` 上可确保阶段值和标签一起维护
- 避免 `constants.py` 变成无差别的大杂烩

### 联动

- #08（前端 `STAGE_LABELS` 和 `RELATIONSHIP_STAGE_LABELS`）保持前端独立定义（类型安全），但需确保 key 与后端一致
- #03（`_default_relationship`）同理考虑移到 `relationship.py`