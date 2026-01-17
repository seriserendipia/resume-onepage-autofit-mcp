"""
简单测试：生成一个肯定能适配单页的简历
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mcp_server'))
from resume_renderer import ResumeRenderer

# 简短的简历（肯定能放进一页）
SHORT_RESUME = """
# 张三

**邮箱**: zhangsan@example.com | **电话**: 138-0013-8000

---

## 工作经历

### Python 开发工程师 | ABC 公司 | 2021-2023

- 开发并维护后端 API 服务
- 优化数据库查询性能，响应时间降低 40%
- 使用 Docker 实现服务容器化部署

---

## 技能

**语言**: Python | JavaScript | SQL  
**框架**: Django | FastAPI  
**工具**: Docker | Git

---

## 教育

**清华大学** 计算机科学 本科 (2015-2019)
"""


async def main():
    print("🧪 测试生成简短简历 PDF...\n")
    
    renderer = ResumeRenderer()
    await renderer.start()
    
    result = await renderer.render_resume_pdf(
        SHORT_RESUME, 
        output_path="success_test.pdf"
    )
    
    print("=" * 60)
    print("📊 渲染结果：")
    print(f"状态: {result['status']}")
    print(f"当前页数: {result['current_pages']}")
    
    if result['status'] == 'success':
        print(f"✅ PDF 已生成: {result['pdf_path']}")
        print(f"消息: {result['message']}")
    else:
        print(f"❌ 生成失败")
        print(f"原因: {result.get('hint', result.get('reason'))}")
    
    print("=" * 60)
    
    await renderer.stop()


if __name__ == "__main__":
    asyncio.run(main())
