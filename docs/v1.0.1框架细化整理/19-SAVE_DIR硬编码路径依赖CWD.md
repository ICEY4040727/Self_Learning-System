# 问题 19: `SAVE_DIR` 硬编码相对路径依赖工作目录 (CWD)

## ✅ 已解决

**解决方案**: `save_directory` 在 `backend/core/config.py` 配置，改为绝对路径
**PR**: #214 → #221

## 问题类型

## 问题类型
硬编码 / 配置不当

## 涉及文件
- `backend/services/save_file_manager.py` 第 18 行

## 具体描述

```python
SAVE_DIR = Path("data/saves")
```

`SAVE_DIR` 使用相对路径 `"data/saves"`，其绝对位置完全取决于进程启动时的工作目录（CWD）。

- 通过 `alembic` 或 `python -m backend.main` 启动时，CWD 可能是项目根目录，`data/saves` 解析为 `{project_root}/data/saves`
- 通过 `uvicorn backend.main:app` 从不同目录启动时，路径可能解析到错误位置
- Docker 部署时，CWD 由 Dockerfile 的 `WORKDIR` 决定，需额外确认一致性

## 影响分析

1. **部署风险**：不同启动方式可能导致存档文件写入不同目录，已有存档"丢失"
2. **与 `config.py` 脱节**：项目已有 `backend/core/config.py` 管理配置（如 `DATABASE_URL`），但存档路径未纳入配置体系
3. **测试困难**：单元测试需要手动 patch `SAVE_DIR`（当前测试已通过 `sfm.SAVE_DIR = tmp_path` 绕过）

## 建议修复方向

1. **首选方案**：在 `backend/core/config.py` 的 `Settings` 类中添加 `save_dir: str = "data/saves"`，`SaveFileManager` 改为 `SAVE_DIR = Path(get_settings().save_dir)`
2. **次选方案**：使用 `__file__` 相对定位：`SAVE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "saves"`
3. Docker 部署时通过环境变量 `SAVE_DIR` 覆盖