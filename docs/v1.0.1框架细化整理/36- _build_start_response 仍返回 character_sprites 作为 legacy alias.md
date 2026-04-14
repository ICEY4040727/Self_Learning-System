#36: _build_start_response 仍返回 character_sprites 作为 legacy alias

### 问题描述
#212 提取 `_build_start_response()` 时保留了 `character_sprites` 字段（值等于 `sage_sprites`），因为前端 `learning.ts` 有 `data.sage_sprites ?? data.character_sprites` fallback 引用。这个 legacy alias 增加了维护负担。

### 来源
#212 折中方案：避免前端 breaking change 而保留冗余字段。

### 严重程度
低

### 建议修复
1. 确认前端 `learning.ts` 是否仍使用 `character_sprites`
2. 如果前端统一使用 `sage_sprites`，从 `_build_start_response` 中删除 `character_sprites` 字段