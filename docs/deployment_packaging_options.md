# Self_Learning-System 部署与封装方案说明（单用户定位）

## 1. 背景与目标

本项目当前定位为**单用户学习应用**，核心目标是：

1. 用户可低门槛本地运行
2. 维护成本可控，问题可复现、可回滚
3. 后续可平滑演进到“一键安装”的产品形态

因此，不采用多租户/大规模分布式场景下的重型部署思路。

## 2. 当前技术现实

- 前端：Vue 3 + Vite（Web SPA）
- 后端：FastAPI（ASGI）
- 数据：SQLite（单用户默认）
- 现有主线：`scripts/setup.sh` + `docker compose up -d --build`

## 3. 方案总览

| 方案 | 内容 | 适配度（本项目） | 实施复杂度 | 建议 |
|---|---|---|---|---|
| Docker Compose 单机部署 | frontend + backend 双容器，SQLite 持久化 | 高 | 低 | **主线方案** |
| 非 Docker 本地部署 | venv + uvicorn + 前端 dev/preview | 高 | 低-中 | 备选（高级用户） |
| 云主机 Compose | 在 VPS 上按当前 compose 运行 | 中高 | 中 | 后续线上可选 |
| systemd + Nginx 完整服务化 | 进程托管 + 反向代理 + TLS | 中 | 中高 | 可选增强，不是当前必需 |
| Electron/Tauri 桌面封装 | 打包为安装包（Win/macOS/Linux） | 中高 | 中高 | 产品化阶段建议评估 |
| K8s/微服务化 | 集群编排与弹性扩缩 | 低 | 高 | 当前不建议 |
| Serverless | 函数化部署 | 低-中 | 中高 | 与当前状态/数据模式不匹配 |

## 4. 推荐决策

### 4.1 近期（当前主线）

采用 **Docker Compose 作为唯一官方支持部署路径**：

- 文档与脚本统一围绕 Compose
- CI 证据链围绕 Compose（含 health/logs/smoke）
- 故障排查与回滚统一口径

### 4.2 备选路径

保留“非 Docker 本地运行”作为开发/进阶用户备选，不承诺同等级运维支持。

### 4.3 中期封装

若目标是“普通用户下载即用”，优先评估：

1. **Tauri**（包体更小，资源占用更低）
2. **Electron**（生态成熟，跨平台经验多）

## 5. 可执行落地方案

### A. 官方主线（现在执行）

1. 初始化：`bash scripts/setup.sh`
2. 启动：`docker compose up -d --build`
3. 验证：`docker compose ps` + `curl /health`
4. 运维：日志采集、SQLite 备份与恢复

### B. 轻量备选（可选补充）

1. 后端：`uvicorn main:app --reload --port 8000`（开发）
2. 前端：`npm run dev` 或 `npm run build && npm run preview`
3. 数据：继续使用 SQLite，本地文件备份

### C. 封装方向（下一阶段）

1. 明确目标平台（Windows 优先或全平台）
2. 先做最小 PoC（登录、学习会话、存档）
3. 再决定 Tauri / Electron 正式路线

## 6. 与 Reviewer 讨论时需拍板的点

1. 官方支持边界：是否仅保证 Compose 路径
2. 非 Docker 路径是否只做“参考运行”
3. 封装优先级：先稳定部署，还是并行推进桌面打包

### 6.1 Creator 立场（用于评审对齐）

#### 1) Compose 官方边界

- 以 **Docker Compose** 作为唯一官方支持与验收边界。
- 发布质量门禁、CI 证据链、问题复现与回滚口径统一按 Compose 路径执行。
- 非 Compose 路径不作为“发布阻塞判定”依据。

#### 2) 非 Docker 支持等级

- 定义为 **Best-effort 参考支持**（提供最小运行指引）。
- 提供范围：venv + uvicorn + 前端构建/启动说明。
- 不纳入同等级 CI 保证，不作为主线可用性承诺。

#### 3) 桌面封装优先级

- 定义为 **P1.5（次于主线稳定）**。
- 先完成 Web + Compose 主线稳定与文档收敛，再启动桌面封装 PoC。
- 路线建议：**Tauri 优先，Electron 备选**；封装工作不阻塞当前主线交付。

## 7. 参考资料（官方文档）

- FastAPI Deployment: https://fastapi.tiangolo.com/deployment/
- FastAPI Docker: https://fastapi.tiangolo.com/deployment/docker/
- FastAPI Manual: https://fastapi.tiangolo.com/deployment/manually/
- Vite Static Deploy: https://vite.dev/guide/static-deploy.html
- Docker Compose: https://docs.docker.com/compose/
- Electron Distribution: https://www.electronjs.org/docs/latest/tutorial/application-distribution
- Tauri Building: https://v1.tauri.app/v1/guides/building/
- PyInstaller: https://pyinstaller.org/en/stable/operating-mode.html
- Briefcase: https://briefcase.readthedocs.io/en/stable/

## 8. Creator × Reviewer 讨论纪要（按 CONTRIBUTING 讨论格式）

### 8.1 官方支持边界（Compose 是否唯一官方路径）

| 角色 | 立场 | 主要理由 |
|---|---|---|
| Reviewer | Compose 作为唯一官方支持与验收边界 | 统一文档、CI 证据链、故障复现与回滚口径，降低单用户场景运维复杂度 |
| Creator | 同意 Compose 唯一官方边界 | 发布阻塞与质量门禁仅按 Compose 路径判定，减少分叉支持成本 |

**结论状态**：双方一致，建议按此执行。

### 8.2 非 Docker 路径支持等级（是否同等级保障）

| 角色 | 立场 | 主要理由 |
|---|---|---|
| Reviewer | 非 Docker 仅作参考运行，不承诺同等级运维支持 | 满足进阶用户需求，同时避免扩大发布保障面 |
| Creator | 定义为 Best-effort 参考支持 | 提供最小运行指引即可，不纳入同等级 CI 保证，也不作为发布阻塞项 |

**结论状态**：双方一致，建议在文档中明确“参考运行”与“非阻塞”属性。

### 8.3 桌面封装优先级（是否并行推进）

| 角色 | 立场 | 主要理由 |
|---|---|---|
| Reviewer | 先稳定 Web + Compose 主线，再推进桌面封装 | 先收敛部署与运维基线，避免并行导致主线质量门禁分散 |
| Creator | 封装优先级次于主线稳定，先做 Tauri PoC，Electron 备选 | 封装工作不应阻塞当前主线交付，先用最小 PoC 验证路线 |

**结论状态**：双方一致，建议优先级定为“主线稳定后启动封装 PoC”。

### 8.4 待 Owner 拍板

1. 是否正式写入“Compose 为唯一官方支持路径”并作为发布阻塞边界。
2. 是否明确“非 Docker 为 Best-effort 参考运行，不纳入同等级 CI 保证”。
3. 是否确认“桌面封装后置（Tauri PoC 优先）”的优先级策略。
