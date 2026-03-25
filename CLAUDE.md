# Self_Learning-System

基于苏格拉底教学法的 AI 个性化学习平台，Galgame 风格沉浸式交互界面。

## Design Vision (see idea/idea.md)

核心理念：用户自定义 AI 教师人设，通过"角色系统 + 学习档案"增进知识掌握。

- **教学方法**: 苏格拉底式提问引导，非直接灌输
- **情感系统**: 关系阶段演进（stranger → acquaintance → friend → mentor → partner），动态影响教师回应风格
- **动态 Prompt**: 系统提示词由 教师人格模板 + 关系阶段 + 当前情感 + ChromaDB 记忆检索 动态组装
- **工具调用**: LLM 可返回工具请求（JSON/XML 标签），前端弹窗确认后执行
- **存档机制**: 会话状态 + 聊天记录 + ChromaDB 记忆 ID 打包为 JSON，读档时恢复
- **多租户**: 数据库设计兼容多租户，初期单用户模式
- **未来规划**: 语音交互、WebGAL 集成、Docker 部署、Electron 客户端

## Roadmap (from idea/idea.md)

| Phase | Content | Status |
|-------|---------|--------|
| 1 | 基础框架 (Vue3 + FastAPI + JWT + DB models) | Done |
| 2 | 档案系统 (角色/人格/画像/科目/日记/进度 CRUD) | Done |
| 3 | 学习引擎 + 动态分析 (LLM adapter + ChromaDB + emotion + relationship) | Done |
| 4 | 前端 UI (Galgame 组件 + 各页面) | Mostly done |
| 5 | 完善与部署 (存档联调 + Docker + 语音预留 + 性能优化) | In progress |

## Tech Stack

- **Frontend**: Vue 3 + Vite + TypeScript + Pinia + Axios (port 5173)
- **Backend**: FastAPI + SQLAlchemy + Pydantic (port 8000)
- **Database**: PostgreSQL + ChromaDB (vector memory)
- **LLM**: Multi-provider adapter (Claude / OpenAI / Local via Ollama)

## Project Structure

```
frontend/          # Vue 3 SPA
  src/views/       # Login, Home, Learning, Archive, Character, Settings
  src/components/  # galgame/ (CharacterDisplay, DialogBox, ChoicePanel, EmotionIndicator, SaveLoad)
  src/stores/      # Pinia stores (auth)
  src/router/      # Vue Router

backend/           # FastAPI app
  api/routes/      # auth, learning, archive, save
  services/        # learning_engine, memory (ChromaDB), dynamic_analyzer, llm/adapter
  models/          # SQLAlchemy models (13 tables)
  core/            # config, security
  db/              # database session

idea/              # Design docs (idea.md)
WebGAL/            # Reserved for WebGAL integration (empty)
```

## Commands

```bash
# Frontend
cd frontend && npm install && npm run dev    # Dev server on :5173
cd frontend && npm run build                 # Production build

# Backend
cd backend && pip install -r requirements.txt                   # Production deps
cd backend && pip install -r requirements-dev.txt               # Dev + test deps
cd backend && uvicorn main:app --reload --port 8000

# Tests (requires requirements-dev.txt)
cd backend && pytest                                            # Run all tests
cd backend && pytest tests/test_scaffold.py -v                  # Run specific file
cd backend && pytest -k "test_login"                            # Run by name pattern

# Database migrations (Alembic)
cd backend && alembic revision --autogenerate -m "description"  # Generate migration
cd backend && alembic upgrade head                              # Apply migrations
cd backend && alembic downgrade -1                              # Rollback one step

# Docker (Neo4j + PostgreSQL)
docker-compose up -d                                            # Start services
```

## Conventions

- Git branch workflow: `feat/xxx`, `fix/xxx`, `docs/xxx` from `main`
- Commit messages: `feat:`, `fix:`, `docs:`, `refactor:`, `test:` prefixes
- Frontend API calls proxy through Vite → `/api` → `localhost:8000`
- Backend config via `.env` file (pydantic-settings), never commit secrets
- License: GPL-3.0

## Team & Communication

三角色协作（详见 CONTRIBUTING.md）：Owner（人类决策）、Creator（写代码）、Reviewer（审查+调研）。

**tmux 实时通知**：Creator 和 Reviewer 在独立 tmux session 中运行，通过 `tmux send-keys` 互相通知。

```bash
# Creator 通知 Reviewer（如：PR 修复完成）
tmux send-keys -t SelfLearn-reviewer "[Creator 通知] 消息内容" Enter

# Reviewer 通知 Creator（如：审查完成）
tmux send-keys -t SelfLearning-creator "[Reviewer 通知] 消息内容" Enter

# 发送前检查对方是否空闲（末尾含 ❯ 表示空闲）
tmux capture-pane -t <session> -p | grep -v '^$' | tail -1
```

自动守护脚本：`tmux new-session -d -s gh-notify "bash scripts/gh-notify-daemon.sh"`
