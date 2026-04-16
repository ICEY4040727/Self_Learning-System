# 问题 10: `learning.py` 中 `tool_confirm` 是占位接口但已暴露在生产路由

## ✅ 已解决

**解决方案**: 接口已删除
**PR**: #240

## 问题类型
占位代码 / 逻辑不清

## 涉及文件
- `backend/api/routes/learning.py` 第 283-295 行

## 具体描述

```python
# Confirm tool call
@router.post("/chat/tool_confirm")
async def confirm_tool(
    tool_request: ToolConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Execute tool and return result
    # This is a placeholder - will integrate actual tool execution
    return {
        "message": "Tool execution placeholder",
        "tool": tool_request.tool,
        "query": tool_request.query
    }
```

这个接口：
1. 注释明确标注为 "placeholder"
2. 不执行任何实际逻辑，仅原样返回请求参数
3. 需要用户认证（`get_current_user`），但认证信息完全未使用
4. 已通过 `app.include_router` 注册到生产 API 路由中

## 影响分析

1. **API 接口污染**：占位接口暴露在 API 文档中（FastAPI 自动生成），误导 API 使用者
2. **安全风险**：虽然当前无害，但占位接口绕过了正常的功能审查流程
3. **债务累积**：如果长期不清理，后续开发者可能误以为此接口有实际功能

## 建议修复方向

1. 如果 tool_confirm 功能近期不计划实现，删除此接口和相关 Pydantic 模型（`ToolConfirmRequest`）
2. 如果计划实现，应创建对应的 Issue 追踪，并在注释中标注 Issue 编号和预计实现时间
3. 占位接口不应注册到生产路由中