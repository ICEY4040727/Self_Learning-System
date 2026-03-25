# 部署指南

## 前置要求

- Docker 20+ 和 Docker Compose v2
- 至少 2GB 可用内存
- LLM API Key（Claude 或 OpenAI 任选一个）

## 一、配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，**必须修改**以下值：

```env
# 必须修改（安全关键）
SECRET_KEY=<随机生成 32 位字符串>
POSTGRES_PASSWORD=<强密码>
CORS_ORIGIN=http://你的域名或IP
```

> **注意**：Docker 部署时 `DATABASE_URL` 由 docker-compose.yml 从 `POSTGRES_*` 变量自动拼接，**无需手动设置**。仅本地开发（非 Docker）时才需要在 `.env` 中设置 `DATABASE_URL`。本地开发请参考 CLAUDE.md 的 Commands 部分。

生成随机 SECRET_KEY：
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## 二、Docker 一键启动

```bash
# 构建并启动所有服务
docker compose up -d

# 查看启动状态
docker compose ps

# 查看日志（持续输出）
docker compose logs -f backend
```

启动顺序（自动编排）：
```
postgres (5432) → chromadb (8001) → backend (8000) → frontend (80)
```

等待所有服务 healthy 后访问 `http://localhost`。

## 三、验证部署

### 3.1 健康检查

```bash
# API 健康状态（应返回 healthy + 各组件状态）
curl http://localhost:8000/health
```

期望输出：
```json
{
  "status": "healthy",
  "checks": {
    "api": "ok",
    "database": "ok",
    "chromadb": "ok"
  }
}
```

### 3.2 功能验证

1. 打开 `http://localhost`
2. 注册账号（用户名 3+ 字符，密码 8+ 字符）
3. 登录后进入主页
4. 创建角色 → 创建教师人格 → 创建科目
5. 进入学习页，发送消息测试对话
6. 在设置页配置 LLM API Key（Claude 或 OpenAI）

### 3.3 运行测试

测试应在部署前本地运行，不要在生产容器中安装测试依赖：

```bash
# 本地运行（推荐）
cd backend
pip install -r requirements-dev.txt
PYTHONPATH=.. pytest tests/ -v
```

## 四、服务架构

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  frontend    │    │  backend     │    │  postgres    │
│  Nginx :80   │───→│  FastAPI     │───→│  :5432       │
│  Vue 3 SPA   │    │  :8000       │    └──────────────┘
└──────────────┘    │              │    ┌──────────────┐
                    │              │───→│  chromadb    │
                    │              │    │  :8001       │
                    └──────────────┘    └──────────────┘
                           │
                    ┌──────────────┐
                    │  neo4j       │  ← 可选（需 KNOWLEDGE_GRAPH_ENABLED=true）
                    │  :7687       │
                    └──────────────┘
```

## 五、常用运维命令

```bash
# 停止所有服务
docker compose down

# 停止并删除数据卷（慎用，数据丢失）
docker compose down -v

# 重建单个服务（代码更新后）
docker compose build backend
docker compose up -d backend

# 数据库迁移
docker compose exec backend sh -c "cd /app && alembic -c backend/alembic.ini upgrade head"

# 查看 PostgreSQL 日志
docker compose logs postgres

# 进入后端容器 shell
docker compose exec backend sh
```

## 六、可选功能配置

### 6.1 知识图谱（Graphiti + Neo4j）

在 `.env` 中添加：
```env
KNOWLEDGE_GRAPH_ENABLED=true
NEO4J_PASSWORD=<强密码>
```

Neo4j 浏览器界面：`http://localhost:7474`

### 6.2 Sentry 错误监控

在 `.env` 中添加：
```env
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
```

免费额度：5K errors/月。

### 6.3 HTTPS（生产环境）

在 `frontend/nginx.conf` 中配置 SSL，或在前端加一层反向代理（如 Caddy、Traefik）处理 TLS 终止。

## 七、故障排查

| 症状 | 可能原因 | 解决方案 |
|------|---------|---------|
| 前端白屏 | backend 未启动 | `docker compose logs backend` 查错 |
| API 返回 401 | Token 过期或未登录 | 重新登录 |
| API 返回 500 | 数据库未就绪 | `docker compose ps` 检查 postgres 状态 |
| 对话无回复 | LLM API Key 未配置 | 在设置页配置 API Key |
| 健康检查 degraded | 某服务未就绪 | 查看 `/health` 返回的 checks 字段 |
| 存档为空 | session_id 未传递 | 确认是最新版本代码 |
| docker compose build 失败 | 网络或依赖问题 | 检查 Docker 网络，重试 |

## 八、数据备份

将下方 `<POSTGRES_USER>` 和 `<POSTGRES_DB>` 替换为你 `.env` 中的实际值：

```bash
# 备份 PostgreSQL
docker compose exec postgres pg_dump -U <POSTGRES_USER> <POSTGRES_DB> > backup_$(date +%Y%m%d).sql

# 恢复
cat backup_20260325.sql | docker compose exec -T postgres psql -U <POSTGRES_USER> <POSTGRES_DB>

# 备份所有卷
docker run --rm -v self_learning-system_pg_data:/data -v $(pwd):/backup alpine tar czf /backup/pg_data.tar.gz -C /data .
```
