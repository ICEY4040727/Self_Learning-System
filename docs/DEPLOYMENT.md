# 部署指南（SQLite + 双容器）

## 前置要求

- Docker 20+
- Docker Compose v2
- LLM API Key（在设置页配置）

## 一、初始化

```bash
bash scripts/setup.sh
```

脚本会完成：
- 生成 `SECRET_KEY`
- 写入 `.env`（`DATABASE_URL=sqlite:///./data/socratic_learning.db`）
- 初始化 `data/` 与 `backend/static/characters/`

## 二、启动服务

```bash
docker compose up -d --build
docker compose ps
```

访问：
- 前端：`http://localhost`
- 后端：`http://localhost:8000`

## 三、部署验证

### 3.1 健康检查

```bash
curl http://localhost:8000/health
```

### 3.2 端到端最小验证

1. 注册并登录。
2. 在设置页填入 API Key。
3. 创建世界 → 绑定角色（知者/旅者）→ 创建课程。
4. 进入学习页对话，确认消息与情感/关系状态更新。
5. 创建 checkpoint，并从档案页分叉读档后继续学习。

## 四、架构说明

```
┌──────────────┐    ┌──────────────┐
│  frontend    │───→│  backend     │
│  Nginx :80   │    │  FastAPI :8000
└──────────────┘    │  SQLite (/app/data/socratic_learning.db)
                    └──────────────┘
```

## 五、常用运维命令

```bash
# 停止服务
docker compose down

# 停止并删除卷（会清空数据库）
docker compose down -v

# 查看日志
docker compose logs -f backend
docker compose logs -f frontend

# 进入后端容器
docker compose exec backend sh
```

## 六、失败场景与回滚

### 6.1 常见失败场景

1. `docker compose up -d --build` 失败：优先查看 `docker compose logs backend frontend`。
2. `/health` 返回非 healthy：通常是数据库文件权限或容器未就绪。
3. 前端可打开但 API 401/500：检查 `.env` 的 `SECRET_KEY` 与 `DATABASE_URL`，确认后端容器已重启。

### 6.2 最小回滚流程

```bash
# 1) 停止当前栈
docker compose down

# 2) 回滚代码到上一个稳定 commit（示例）
git checkout <stable_commit_sha>

# 3) 恢复 SQLite 数据（如需）
cp data/socratic_learning.db.bak data/socratic_learning.db

# 4) 重启
docker compose up -d --build
curl http://localhost:8000/health
```
