# 问题 06: `save.py` 中遗留 save 接口与 checkpoints 接口并存，代码严重膨胀

## ✅ 已解决

**解决方案**: 遗留接口已删除，仅保留新接口
**PR**: #210 → #217


## 问题类型
遗留代码 / 结构冗余

## 涉及文件
- `backend/api/routes/save.py`（710 行）

## 问题描述

`save.py` 中存在两套功能完全重叠的 API 接口：

### 新接口（checkpoints，第 96-442 行）
- `POST /checkpoints` — 创建存档
- `GET /checkpoints` — 列出存档
- `GET /worlds/{world_id}/checkpoints` — 按世界列出存档
- `POST /checkpoints/{id}/branch` — 从存档分支
- `GET /worlds/{world_id}/timelines` — 获取世界时间线
- `GET /checkpoints/{id}` — 获取单个存档
- `DELETE /checkpoints/{id}` — 删除存档
- `GET /checkpoints/{id}/export` — 导出存档
- `POST /checkpoints/import` — 导入存档

### 遗留接口（save，第 461-605 行）
- `POST /save` — 已标记 `DEPRECATED`，内部调用 `create_checkpoint`
- `GET /save` — 已标记 `DEPRECATED`，内部重新实现了一套过滤逻辑
- `GET /save/{id}` — 已标记 `DEPRECATED`，内部重新实现了一套详情获取逻辑
- `DELETE /save/{id}` — 已标记 `DEPRECATED`，直接委托给 `delete_checkpoint`

代码注释明确标注：
```python
# Legacy save endpoints - DEPRECATED
# Use /checkpoints/* endpoints instead. See Issue #204.
```

## 影响分析

1. **文件过长**：710 行，其中约 150 行是遗留代码
2. **维护负担**：修改 checkpoint 逻辑时需要确认遗留接口的行为是否受影响
3. **`GET /save` 有独立的过滤逻辑**（第 500-523 行），没有复用 `_build_checkpoint_response`，与 checkpoint 列表的行为可能不一致
4. **增加新开发者理解成本**：需要弄清楚两套接口的关系和区别

## 建议修复方向

1. 确认前端已完全迁移到 `/checkpoints` 接口
2. 如果前端不再调用 `/save` 接口，直接删除遗留代码（约 150 行）
3. 如果仍有调用方，设置明确的移除时间表（如 v1.1.0 完全删除）