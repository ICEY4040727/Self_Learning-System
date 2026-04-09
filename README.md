# Self_Learning-System

基于苏格拉底教学法的 AI 个性化学习平台，提供 Galgame 风格沉浸式交互与可持续学习档案。

## 项目定位

- **教学方式**：以提问引导（Socratic Method）替代直接灌输  
- **交互体验**：角色关系阶段 + 情绪状态驱动教师回应风格  
- **学习连续性**：会话、checkpoint、分叉学习、知识图谱时态可见性  
- **工程目标**：可本地部署、可 Docker 一键运行、可回归验证

## 当前能力（Phase 4）

- 角色 / 人格 / 世界 / 课程 / 档案 CRUD
- 学习会话与关系系统（维度变化、阶段跃迁、事件记录）
- 知识图谱可视化（节点详情、checkpoint_time 过滤）
- Docker 双容器部署（frontend + backend，SQLite 持久化）
- 前后端自动化回归（pytest + Playwright + CI smoke）

## 技术栈

- **Frontend**: Vue 3 + Vite + TypeScript + Pinia
- **Backend**: FastAPI + SQLAlchemy + Alembic
- **Database**: SQLite（当前部署默认）/ PostgreSQL（可扩展）
- **LLM Adapter**: Claude / OpenAI / Ollama（通过设置页配置密钥）

## 快速开始（开发环境）

### 1) 后端

```bash
cd backend
uv pip install -r requirements-dev.txt --system
uvicorn main:app --reload --port 8000
```

### 2) 前端

```bash
cd frontend
npm ci
npm run dev
```

- 前端默认地址：`http://localhost:5173`
- 前端代理 API 到后端：`http://localhost:8000`

## 快速开始（Docker 部署）

```bash
bash scripts/setup.sh
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health
```

- 前端：`http://localhost`
- 后端：`http://localhost:8000`

完整部署与回滚说明见：[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)

## 测试命令

```bash
# Backend
cd backend && .venv/bin/pytest

# Frontend build
cd frontend && npm run build

# Frontend E2E
cd frontend && npx playwright test e2e/*.spec.mjs
```

## 目录结构

```text
frontend/          Vue 3 SPA
backend/           FastAPI 服务
docs/              设计与部署文档
scripts/           初始化与工具脚本
data/              运行时数据目录（本地）
```

## 环境变量

参考 `.env.example`：

- `SECRET_KEY`（必填）
- `DATABASE_URL`（默认 SQLite）
- `CORS_ORIGIN`
- `SENTRY_DSN`（可选）

## 协作流程

项目采用 Owner / Creator / Reviewer 三角色协作，详见 `CONTRIBUTING.md`。

## License

GPL-3.0
