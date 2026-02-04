"""
长期复用测试：MCP Server 功能测试
验证 resume_renderer.py 的核心功能正常
"""
import asyncio
import sys
import io
from pathlib import Path

# 修复 Windows 控制台 Unicode 输出问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加 mcp_server 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'mcp_server'))

from resume_renderer import ResumeRenderer, get_default_output_dir


# 测试用的简单 Markdown
TEST_MARKDOWN = """
# John Doe
San Francisco, CA | john@example.com

---

## Education
**Test University** · San Francisco, CA  
*Master of Science in Computer Science*  
*2023 - Present*

---

## Experience
**Tech Company** · Software Engineer  
*2022 - Present*  
- Built awesome features

---

## Skills
- Python, JavaScript, SQL
"""


async def test_renderer_initialization():
    """测试渲染器初始化"""
    print("1. 测试渲染器初始化...")
    renderer = ResumeRenderer()
    
    assert renderer.html_path.exists(), f"HTML 路径不存在: {renderer.html_path}"
    print(f"   ✅ HTML 路径: {renderer.html_path}")
    
    assert renderer.browser is None, "浏览器应该初始化为 None"
    print("   ✅ 浏览器初始状态正确")
    
    return True


async def test_default_output_dir():
    """测试默认输出目录获取"""
    print("2. 测试默认输出目录...")
    output_dir = get_default_output_dir()
    
    assert output_dir is not None, "输出目录不应为空"
    assert Path(output_dir).exists(), f"输出目录不存在: {output_dir}"
    print(f"   ✅ 默认输出目录: {output_dir}")
    
    return True


async def test_browser_lifecycle():
    """测试浏览器启动和关闭"""
    print("3. 测试浏览器生命周期...")
    renderer = ResumeRenderer()
    
    try:
        await renderer.start()
        assert renderer.browser is not None, "浏览器应该已启动"
        print("   ✅ 浏览器启动成功")
        
        await renderer.stop()
        print("   ✅ 浏览器关闭成功")
        
        return True
    except Exception as e:
        print(f"   ❌ 浏览器测试失败: {e}")
        return False


async def test_markdown_rendering():
    """测试 Markdown 渲染为 PDF"""
    print("4. 测试 Markdown 渲染...")
    renderer = ResumeRenderer()
    
    try:
        import tempfile
        import os
        
        # 使用临时文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_pdf = f.name
        
        result = await renderer.render_resume_pdf(
            markdown_content=TEST_MARKDOWN,
            output_path=temp_pdf,
            timeout_ms=30000  # 30秒超时
        )
        
        print(f"   渲染结果状态: {result.get('status', 'unknown')}")
        
        # 检查 PDF 文件是否生成
        if os.path.exists(temp_pdf) and os.path.getsize(temp_pdf) > 0:
            file_size = os.path.getsize(temp_pdf) / 1024
            print(f"   ✅ PDF 生成成功: {file_size:.1f} KB")
            os.unlink(temp_pdf)  # 清理
            return True
        else:
            print(f"   ❌ PDF 未生成或为空")
            return False
            
    except Exception as e:
        print(f"   ❌ 渲染测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await renderer.stop()


async def main():
    print("=" * 60)
    print("MCP Server 功能测试")
    print("=" * 60)
    
    tests = [
        ("初始化", test_renderer_initialization),
        ("输出目录", test_default_output_dir),
        ("浏览器生命周期", test_browser_lifecycle),
        ("Markdown 渲染", test_markdown_rendering),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"   ❌ 测试异常: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {status} - {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✅ 所有测试通过！")
    else:
        print("❌ 部分测试失败")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
