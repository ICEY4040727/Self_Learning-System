"""
MiniMax Adapter 测试脚本
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.llm import (
    OpenAICompatibleAdapter,
    get_provider_endpoint,
)

MINIMAX_API_KEY = "sk-cp-VFnpiXDLGPueu-2iE_PV8CDFiZtsuurAecZgULpws0UIBY1gFdR8TFWz6yiWSb6TvTgkq5l-3shphDZmXKw6bHXhFzqw-iSeKsBgzTrJ08xkUx8x0vr_SuM"


async def test_minimax():
    """测试 MiniMax API"""
    print("="*60)
    print("测试 MiniMax API")
    print("="*60)
    
    # MiniMax API 端点
    base_url = "https://api.minimax.chat/v1"
    
    # MiniMax 使用的模型
    model = "MiniMax-M2.7-highspeed"
    
    adapter = OpenAICompatibleAdapter(
        model=model,
        api_key=MINIMAX_API_KEY,
        base_url=base_url
    )
    
    print(f"Adapter: provider={adapter.provider}, model={adapter.model}")
    print(f"Endpoint: {base_url}")
    
    try:
        print("\n发送测试请求...")
        response = await adapter.chat(
            messages=[{"role": "user", "content": "你好，请用一句话介绍自己"}],
            system_prompt="你是一个友好的AI助手。",
            max_tokens=100
        )
        print(f"✓ 请求成功!")
        print(f"响应: {response}")
        return True
        
    except Exception as e:
        print(f"✗ 错误: {type(e).__name__}: {e}")
        return False


async def main():
    success = await test_minimax()
    print("\n" + "="*60)
    print(f"结果: {'✓ 通过' if success else '✗ 失败'}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
