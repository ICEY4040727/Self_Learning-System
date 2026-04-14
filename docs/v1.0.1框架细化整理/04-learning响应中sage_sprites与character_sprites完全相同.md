# 问题 04: `start_learning` 响应中 `sage_sprites` 与 `character_sprites` 完全相同

## 问题类型
冗余字段 / 逻辑不清

## 涉及文件
- `backend/api/routes/learning.py` 第 122、124 行（existing session 路径）
- `backend/api/routes/learning.py` 第 195、196 行（new session 路径）

## 重复内容

```python
# existing session 路径 (行 114-125)
return {
    ...
    "sage_sprites": sage_character.sprites if sage_character else None,
    "traveler_sprites": traveler_character.sprites if traveler_character else None,
    "character_sprites": sage_character.sprites if sage_character else None,  # 与 sage_sprites 完全相同
}

# new session 路径 (行 186-197)
return {
    ...
    "sage_sprites": sage_character.sprites if sage_character else None,
    "traveler_sprites": traveler_character.sprites if traveler_character else None,
    "character_sprites": sage_character.sprites if sage_character else None,  # 与 sage_sprites 完全相同
}
```

`character_sprites` 的值始终等于 `sage_sprites`，没有提供任何额外信息。

## 影响分析

1. **前端困惑**：前端开发者不清楚应该使用 `character_sprites` 还是 `sage_sprites`，可能导致不一致的使用方式
2. **维护冗余**：两处返回逻辑需要保持同步
3. **语义不清**：`character_sprites` 这个名字过于泛化，不明确指的是哪个角色

## 建议修复方向

1. **确认前端使用情况**：检查前端是否使用了 `character_sprites`
   - 如果前端仅使用 `sage_sprites`，直接删除 `character_sprites`
   - 如果前端使用了 `character_sprites`，将其改为使用 `sage_sprites`，然后删除
2. 统一两处返回的字典构造，确保字段一致且无冗余