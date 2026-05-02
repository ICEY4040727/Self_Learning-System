# v1.0.3 Review 总结

> Branch: `feat/v1.0.3`
> Date: 2026-05-02
> Range: backend 全量路由 + 服务层

## 修复清单

| Batch | 文件 | 修复 | Commit |
|-------|------|------|--------|
| B1 | save.py + 5 测试 | save-system 全面修复 | `9418c5e` |
| B2 | archive.py | A1 IDOR, A2 missing user_id, A3 delete 204, A6 top-import | `270be35` |
| B3 | learning.py | 无 P0/P1，P2/P3 deferred | `07c7daf` |
| B4 | auth/achievements/report/textbook | 审查通过，无需修复 | `07c7daf` |
| B5 | llm/* + prompt_builder/* | 安全审查通过 | — |

## 测试结果
- 312 passed, 13 skipped, 0 failed

## Deferred (下个迭代)

### archive.py
- 🟡 P2: `_get_world_sages` 向后兼容包装可删除
- 🟡 P2: `_ensure_world_knowledge` 已是空操作，可清理

### learning.py
- 🟡 P2: `start_learning` 查 Character 两次（可复用）
- 🟢 P3: `_get_session_characters` fallback 逻辑用 WorldCharacter.id 匹配 teacher_persona_id（旧数据兼容，不影响新数据）
- 🟢 P3: 多处函数内 import

### 全局
- 🟢 P3: Pydantic V1 `class Config` → V2 `model_config` 迁移（33处警告）