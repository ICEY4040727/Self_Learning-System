## Overview
[本 PR 的目的、背景与核心收益]

## Change List
- [模块/文件 1]：[改动说明]
- [模块/文件 2]：[改动说明]

## Self-Check
- [ ] 已运行相关测试（单测/集成/手测）
- [ ] 已评估回归风险
- [ ] 已检查兼容性（接口/配置/数据）
- [ ] 无无关改动混入
- [ ] 未在业务层/脚本中直接赋值 User LLM 字段（须走 `user_llm_settings.update_*`；可运行 `python scripts/check_user_llm_direct_writes.py`）

## Reviewer Focus
- [ ] User LLM 字段是否存在绕过 write gateway 的直接 ORM 赋值（出现即 request changes）

### 自查项 - LLM 用户配置写入规范
- [ ] 未直接赋值 user.default_provider / model / encrypted_api_key / llm_provider_settings / temperature / max_tokens
- [ ] 所有LLM配置更新统一使用 update_provider_settings / update_generation_params
- [ ] 仅 tests 目录 fixture 允许裸写，业务代码、scripts 不允许直接ORM赋值

## Linked Issues
Closes #N

> 必须使用自动闭合关键字：`Closes #N` / `Fixes #N` / `Resolves #N`。
> 仅写 `Related to #N` 不会自动闭合 issue。
