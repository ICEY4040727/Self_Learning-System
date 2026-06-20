# v1.0.4 收束发布检查清单

> 状态：收束发布中
> 目标：冻结已完成主线，补齐验证，不继续扩大功能范围。

## 1. 发布范围冻结

本轮 v1.0.4 只收束以下主线：

- 世界壳契约：`World.name`、`World.description`、`World.background_picture`。
- 世界壳创建向导：4+1 步采集，AI 只生成世界壳建议。
- 学习启动背景：前端只消费顶层 `background_picture`。
- 教材生命周期最小修复：书架教材和课程教材使用真实关联，不再用 `file_path` 当隐式外键。
- LLM 设置链路：用户级 provider 设置和角色级覆盖设置进入验证，不继续扩展新 provider。

本轮不做：

- 不实现课程叙事事件池执行器。
- 不删除 `World.scenes` 数据库列。
- 不把 `LearningPlanDraft -> commit_learning_plan_draft()` 扩展为主产品路径。
- 不做教材异步解析任务系统。

## 2. 世界壳完成标准

- `POST /world/generate` 只返回 `name_suggestion`、`description`、`background_picture`。
- `POST /worlds` 只接收 `name`、`description`、`background_picture`，拒绝 legacy `scenes`。
- `PUT /worlds/{id}` 是局部更新，未传字段保持原值。
- `GET /worlds` 和 `GET /worlds/{id}` 不返回 `scenes`。
- 学习启动响应不返回 `scenes`，只返回顶层 `background_picture`。
- 前端世界创建最终 payload 只包含 `name`、`description`、`background_picture`。
- 前端学习态只从 `background_picture` 读取背景。

## 3. 教材与 LLM 收束标准

- 书架教材关联课程时写入真实关联键，而不是只复制文件路径。
- 删除课程教材时，如果教材来自书架，只删除课程关联，不删除共享文件。
- 删除仍被课程引用的书架教材时，应阻断并返回明确错误。
- 解析失败的教材不能被当作普通可用教材继续生成课程。
- 用户级 LLM 设置必须能按 provider 独立保存和读取。
- 角色级 LLM 设置优先级必须高于用户默认设置。

## 4. 验证命令

后端世界壳、学习启动、draft 命名：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_archive.py backend/tests/test_learning_sessions.py backend/tests/test_learning_plan_drafts.py -q
```

后端教材和 LLM 链路：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_textbook_bookshelf_flow.py backend/tests/test_llm_call_chain.py -q
```

前端构建：

```powershell
npm.cmd run build
```

## 5. 当前已验证结果

- `backend/tests/test_archive.py backend/tests/test_learning_sessions.py backend/tests/test_learning_plan_drafts.py`：通过，`22 passed, 5 skipped`。
- `backend/tests/test_textbook_bookshelf_flow.py backend/tests/test_llm_call_chain.py`：通过，`15 passed`。
- `frontend` build：通过。

## 6. 已知非阻塞风险

- `backend/.pytest_cache` 当前存在权限拒绝警告，不影响测试结果，但建议后续清理目录权限。
- pytest 配置中 `asyncio_mode` 当前被提示为未知配置项，需要后续确认 pytest-asyncio 版本或配置位置。
- `checkpoints / sessions` 仍有外键循环警告，这是历史技术债，不应混入本轮 v1.0.4 收束。
- 工作区同时包含多条主线改动，最终提交前必须按功能拆分，避免一个大提交混入世界壳、教材、LLM 和文档清理。

## 7. 推荐提交分组

1. `feat: finalize minimal world shell contract`
2. `fix: stabilize textbook bookshelf linking lifecycle`
3. `feat: add provider-scoped llm settings`
4. `docs: add v1.0.4 release checklist`

每组提交前至少跑对应后端目标测试；最终提交前跑完整收束验证命令。
