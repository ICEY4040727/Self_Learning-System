# 问题 03: 版本号 `"1.0.0"` 在 `main.py` 中硬编码重复出现

## ✅ 已解决

**解决方案**: 版本号在 `backend/core/config.py` 统一定义为 `app_version`
**PR**: #214 → #221

## 问题类型
硬编码重复

## 涉及文件
- `backend/main.py` 第 34、53 行

## 重复内容

```python
# 第 34 行
app = FastAPI(
    title="Socratic Learning System",
    description="基于苏格拉底教学法的个性化学习系统",
    version="1.0.0",  # ← 硬编码
    lifespan=lifespan,
)

# 第 53 行
@app.get("/")
async def root():
    return {"message": "Socratic Learning System API", "version": "1.0.0"}  # ← 再次硬编码
```

## 影响分析

1. **版本号更新容易遗漏**：发版时必须同时修改两处，如果忘记修改 `root()` 端点的返回值，API 用户看到的版本信息就不准确
2. **与 `config.py` 脱节**：`Settings` 类没有版本号字段，无法通过环境变量或配置文件统一管理

## 建议修复方向

1. 在 `backend/core/config.py` 的 `Settings` 类中添加 `app_version: str = "1.0.0"`
2. 两处都改为 `settings.app_version`
3. 或者从 `pyproject.toml` 动态读取版本号（推荐）