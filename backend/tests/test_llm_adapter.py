"""
LLM Adapter 测试脚本

测试各个 Adapter 是否正常工作。
"""

import asyncio
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.llm import (
    LLMError,
    get_llm_adapter,
    get_model_info,
    get_provider_info,
    list_providers,
)


async def test_claude_adapter():
    """测试 Claude Adapter"""
    print("\n" + "="*60)
    print("测试 Claude Adapter")
    print("="*60)

    try:
        adapter = get_llm_adapter("claude")
        print(f"✓ Adapter 创建成功: provider={adapter.provider}, model={adapter.model}")

        # 获取模型信息
        model_info = adapter.get_model_info()
        print(f"✓ 模型信息: {model_info.name}, max_tokens={model_info.max_tokens}")

        # 发送测试请求
        response = await adapter.chat(
            messages=[{"role": "user", "content": "你好，请用一句话介绍自己"}],
            system_prompt="你是一个友好的AI助手。",
            max_tokens=100
        )
        print("✓ 请求成功!")
        print(f"  响应: {response[:200]}...")
        return True

    except LLMError as e:
        print(f"✗ LLM 错误: [{e.provider}] {e.code.value}: {e.message}")
        return False
    except Exception as e:
        print(f"✗ 错误: {type(e).__name__}: {e}")
        return False


async def test_openai_adapter():
    """测试 OpenAI Adapter"""
    print("\n" + "="*60)
    print("测试 OpenAI Adapter")
    print("="*60)

    try:
        adapter = get_llm_adapter("openai")
        print(f"✓ Adapter 创建成功: provider={adapter.provider}, model={adapter.model}")

        model_info = adapter.get_model_info()
        print(f"✓ 模型信息: {model_info.name}, max_tokens={model_info.max_tokens}")

        response = await adapter.chat(
            messages=[{"role": "user", "content": "你好，请用一句话介绍自己"}],
            system_prompt="你是一个友好的AI助手。",
            max_tokens=100
        )
        print("✓ 请求成功!")
        print(f"  响应: {response[:200]}...")
        return True

    except LLMError as e:
        print(f"✗ LLM 错误: [{e.provider}] {e.code.value}: {e.message}")
        return False
    except Exception as e:
        print(f"✗ 错误: {type(e).__name__}: {e}")
        return False


async def test_local_adapter():
    """测试 Local Adapter"""
    print("\n" + "="*60)
    print("测试 Local Adapter (Ollama)")
    print("="*60)

    try:
        adapter = get_llm_adapter("local")
        print(f"✓ Adapter 创建成功: provider={adapter.provider}, model={adapter.model}")

        model_info = adapter.get_model_info()
        print(f"✓ 模型信息: {model_info.name}")

        response = await adapter.chat(
            messages=[{"role": "user", "content": "你好"}],
            system_prompt="你是一个友好的AI助手。",
            max_tokens=50
        )
        print("✓ 请求成功!")
        print(f"  响应: {response[:200]}...")
        return True

    except LLMError as e:
        print(f"✗ LLM 错误: [{e.provider}] {e.code.value}: {e.message}")
        return False
    except Exception as e:
        print(f"✗ 错误: {type(e).__name__}: {e}")
        print("  (这可能是正常的，如果 Ollama 没有运行)")
        return False


async def test_streaming():
    """测试流式输出"""
    print("\n" + "="*60)
    print("测试流式输出")
    print("="*60)

    try:
        adapter = get_llm_adapter("claude")
        print(f"✓ 使用 {adapter.provider} 进行流式测试")

        full_response = ""
        chunk_count = 0

        async for chunk in adapter.chat_stream(
            messages=[{"role": "user", "content": "数到5"}],
            system_prompt="只输出数字，用空格分隔，例如: 1 2 3 4 5",
            max_tokens=50
        ):
            full_response += chunk
            chunk_count += 1
            print(f"  Chunk {chunk_count}: {chunk[:20]}...")

        print(f"✓ 流式完成! 共 {chunk_count} 个块")
        print(f"  完整响应: {full_response[:100]}...")
        return True

    except LLMError as e:
        print(f"✗ LLM 错误: [{e.provider}] {e.code.value}: {e.message}")
        return False
    except Exception as e:
        print(f"✗ 错误: {type(e).__name__}: {e}")
        return False


def test_providers_and_models():
    """测试 Provider 和 Model 信息"""
    print("\n" + "="*60)
    print("测试 Provider 和 Model 信息")
    print("="*60)

    # 测试 Provider 列表
    providers = list_providers()
    print(f"✓ 支持的 Provider ({len(providers)} 个):")
    for p in providers[:5]:
        print(f"  - {p['value']}: {p['label']} ({p['api_format']})")
    if len(providers) > 5:
        print(f"  ... 还有 {len(providers) - 5} 个")

    # 测试获取特定 Provider
    deepseek = get_provider_info("deepseek")
    if deepseek:
        print(f"✓ DeepSeek 信息: {deepseek}")

    # 测试 Model 信息
    model = get_model_info("claude-3-5-sonnet-20241022")
    print("✓ Claude 3.5 Sonnet 信息:")
    print(f"  - 名称: {model.name}")
    print(f"  - max_tokens: {model.max_tokens}")
    print(f"  - context_window: {model.context_window}")
    print(f"  - 价格: 输入 ${model.input_price}/1M, 输出 ${model.output_price}/1M")

    return True


async def main():
    """运行所有测试"""
    print("="*60)
    print("LLM Adapter 测试套件")
    print("="*60)

    # 先测试配置和模型信息
    test_providers_and_models()

    # 测试各个 Adapter
    results = {}

    # Claude 测试（最常用）
    results["Claude"] = await test_claude_adapter()

    # OpenAI 测试（可选）
    results["OpenAI"] = await test_openai_adapter()

    # Local 测试（如果 Ollama 运行中）
    results["Local"] = await test_local_adapter()

    # 流式测试
    results["Streaming"] = await test_streaming()

    # 总结
    print("\n" + "="*60)
    print("测试结果总结")
    print("="*60)

    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\n总计: {passed}/{total} 通过")


if __name__ == "__main__":
    asyncio.run(main())
