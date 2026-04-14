#34: save.py 的 stage_map 仍未统一到 RELATIONSHIP_STAGE_LABELS

### 问题描述
#211 (PR #218) 统一了 `archive.py` 和 `save.py` 的关系阶段标签，但 `save.py` 中仍保留独立的 `stage_map` 局部变量定义，未改为从 `models.RELATIONSHIP_STAGE_LABELS` 引用。

### 来源
#211 修复时仅处理了 `archive.py`，`save.py` 的 `stage_map` 因遗留接口（#06）纠缠暂未处理。

### 严重程度
中

### 建议修复
- 随 #06（save.py 遗留接口删除）一并清理
- 或单独将 `save.py` 的 `stage_map` 替换为 `from backend.models.models import RELATIONSHIP_STAGE_LABELS`
