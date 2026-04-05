# 部署说明（SQLite + Docker 双容器）

本文档提供当前主线版本的**标准部署流程**、**发布升级流程**与**回滚方案**。  
默认部署形态：`frontend (Nginx:80)` + `backend (FastAPI:8000)`，数据存储在 SQLite。

## 1. 前置要求

- Linux / macOS（Windows 建议 WSL2）
- Docker 20+
- Docker Compose v2
- 可访问外网拉取镜像

> LLM API Key 不写入 `.env`，在系统设置页配置。

## 2. 一键初始化

在仓库根目录执行：

```bash
bash scripts/setup.sh
```

脚本会自动完成：

1. 检查 Docker / Compose 可用性  
2. 生成 `.env`（含随机 `SECRET_KEY`）  
3. 初始化本地目录：`data/`、`backend/static/characters/`  
4. 可选立即启动服务

`.env` 已存在时会提示确认覆盖，并提醒 SQLite 备份方式。

## 3. 启动服务

```bash
docker compose up -d --build
docker compose ps
```

访问地址：

- 前端：`http://localhost`
- 后端：`http://localhost:8000`

## 4. 部署后验证（必须执行）

### 4.1 健康检查

```bash
curl http://localhost:8000/health
```

期望返回包含：

- `status: healthy`
- `checks.api: ok`
- `checks.database: ok`

### 4.2 关键链路冒烟

1. 注册并登录
2. 设置页填入可用 LLM Key
3. 创建世界与角色绑定
4. 创建课程并进入学习页发起对话
5. 创建 checkpoint 并尝试分叉继续学习

## 5. 运维常用命令

```bash
# 查看状态
docker compose ps

# 查看日志
docker compose logs -f backend
docker compose logs -f frontend

# 停止服务（保留数据）
docker compose down

# 停止并删除卷（清空容器卷内数据）
docker compose down -v

# 进入后端容器
docker compose exec backend sh
```

## 6. 发布升级流程（推荐）

```bash
# 1) 拉取最新代码
git pull

# 2) 重建并启动
docker compose up -d --build

# 3) 健康检查
docker compose ps
curl http://localhost:8000/health
```

## 7. 数据备份与恢复（SQLite）

### 7.1 备份

```bash
cp data/socratic_learning.db data/socratic_learning.db.bak
```

### 7.2 恢复

```bash
cp data/socratic_learning.db.bak data/socratic_learning.db
docker compose restart backend
```

## 8. 回滚流程（最小可用）

```bash
# 1) 停止当前版本
docker compose down

# 2) 回到稳定提交
git checkout <stable_commit_sha>

# 3) （可选）恢复数据库备份
cp data/socratic_learning.db.bak data/socratic_learning.db

# 4) 重启并验证
docker compose up -d --build
curl http://localhost:8000/health
```

## 9. 常见问题排查

### 9.1 backend unhealthy

```bash
docker compose logs backend --tail=200
```

重点检查：

- `.env` 中 `SECRET_KEY`、`DATABASE_URL` 是否有效
- 数据库文件权限是否可写
- 容器内迁移/启动日志是否报错

### 9.2 前端可打开但接口 401/500

```bash
docker compose logs backend --tail=200
```

确认：

- 后端是否 healthy
- 前端请求是否正确转发到 `/api`
- 登录 token 是否过期

### 9.3 端口冲突

如 80/8000 被占用，先释放端口或按需修改 `docker-compose.yml` 映射。

## 10. CI 部署证据（审查用）

仓库使用 `.github/workflows/phase4-evidence.yml` 提供可复核证据：

- `phase4-ui-e2e`：前端 Playwright 自动化
- `docker-compose-smoke`：`docker compose up -d --build` + `ps/health/logs`

当 Reviewer 要求“可复核部署闭环”时，直接引用对应 workflow run 与 artifacts。
