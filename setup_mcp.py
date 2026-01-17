"""
Setup script for MCP Server
Creates directory structure and initial files
"""

import os
from pathlib import Path

# 创建 mcp_server 目录
mcp_dir = Path("mcp_server")
mcp_dir.mkdir(exist_ok=True)
print(f"✓ Created directory: {mcp_dir}")

# 创建 __init__.py
init_content = '''"""
MCP Server for Resume Auto-Fitting
Provides tools for AI agents to render and validate resume PDF generation
"""

__version__ = "0.1.0"
'''

with open(mcp_dir / "__init__.py", "w", encoding="utf-8") as f:
    f.write(init_content)
print("✓ Created: mcp_server/__init__.py")

# 创建 resume_renderer.py
renderer_content = '''"""
Resume PDF Renderer using Playwright
Provides headless browser rendering with overflow detection
"""

import asyncio
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Page, Browser


class ResumeRenderer:
    """使用 Playwright 渲染简历并检测页面溢出"""
    
    def __init__(self, html_path: str = "generated_resume.html"):
        self.html_path = Path(html_path).resolve()
        self.browser: Optional[Browser] = None
        self.A4_HEIGHT_PX = 1120  # 297mm @ 96dpi
        
    async def start(self):
        """启动浏览器实例"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        
    async def stop(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            
    async def render_resume_pdf(
        self, 
        markdown_content: str, 
        output_path: str = "output_resume.pdf",
        timeout_ms: int = 10000
    ) -> Dict[str, Any]:
        """
        渲染简历为 PDF 并检测溢出
        
        Args:
            markdown_content: Markdown 格式的简历内容
            output_path: PDF 输出路径
            timeout_ms: 渲染超时时间（毫秒）
            
        Returns:
            字典包含:
            - status: "success" 或 "failed"
            - pdf_path: PDF 文件路径（成功时）
            - reason: 失败原因（失败时）
            - current_pages: 当前页数
            - overflow_amount: 溢出百分比
            - hint: 削减建议
        """
        if not self.browser:
            await self.start()
            
        page = await self.browser.new_page()
        
        try:
            # 加载本地 HTML 文件
            html_url = f"file:///{self.html_path.as_posix()}"
            await page.goto(html_url, wait_until="networkidle")
            
            # 注入 Markdown 内容
            escaped_markdown = markdown_content.replace('`', '\\\\`').replace('${', '\\\\${')
            inject_script = f"""
                if (window.simpleViewer && window.simpleViewer.renderContent) {{
                    window.simpleViewer.renderContent(`{escaped_markdown}`);
                }} else {{
                    console.error('SimpleViewer not available');
                }}
            """
            await page.evaluate(inject_script)
            
            # 等待渲染完成信号
            await page.wait_for_selector('body.render-complete', timeout=timeout_ms)
            
            # 额外等待确保自动适配完成（如果启用）
            try:
                await page.wait_for_selector('body.autofit-complete', timeout=3000)
            except:
                pass  # 可能未启用自动适配
            
            # 检测页面高度和溢出
            metrics = await self._check_overflow(page)
            
            if metrics['current_pages'] <= 1:
                # 成功：生成 PDF
                output_full_path = Path(output_path).resolve()
                await page.pdf(
                    path=str(output_full_path),
                    format='A4',
                    print_background=True,
                    margin={
                        'top': '0mm',
                        'bottom': '0mm',
                        'left': '0mm',
                        'right': '0mm'
                    }
                )
                
                return {
                    "status": "success",
                    "pdf_path": str(output_full_path),
                    "current_pages": metrics['current_pages'],
                    "message": "简历已成功渲染为单页 PDF"
                }
            else:
                # 失败：内容溢出
                return {
                    "status": "failed",
                    "reason": "overflow",
                    "current_pages": metrics['current_pages'],
                    "overflow_amount": metrics['overflow_percentage'],
                    "overflow_px": metrics['overflow_px'],
                    "hint": self._generate_hint(metrics)
                }
                
        finally:
            await page.close()
            
    async def _check_overflow(self, page: Page) -> Dict[str, Any]:
        """检测页面溢出情况"""
        result = await page.evaluate("""
            () => {
                const contentEl = document.querySelector('#content') || document.querySelector('.page');
                if (!contentEl) {
                    return { error: 'Content element not found' };
                }
                
                const A4_HEIGHT_PX = 1120;
                const totalHeight = contentEl.scrollHeight;
                const pageCount = Math.ceil(totalHeight / A4_HEIGHT_PX);
                const overflowPx = Math.max(0, totalHeight - A4_HEIGHT_PX);
                const overflowPercentage = (overflowPx / A4_HEIGHT_PX) * 100;
                
                return {
                    total_height: totalHeight,
                    current_pages: pageCount,
                    overflow_px: overflowPx,
                    overflow_percentage: Math.round(overflowPercentage)
                };
            }
        """)
        
        return result
    
    def _generate_hint(self, metrics: Dict[str, Any]) -> str:
        """根据溢出量生成削减建议"""
        overflow_pct = metrics.get('overflow_percentage', 0)
        
        if overflow_pct < 5:
            return "轻微溢出（<5%）。建议：应用 Level 1 削减（合并孤行、压缩技能列表）"
        elif overflow_pct < 15:
            return f"中等溢出（{overflow_pct}%）。建议：应用 Level 2 削减（简化描述、移除软技能表述）"
        else:
            return f"严重溢出（{overflow_pct}%）。建议：应用 Level 3 削减（移除不相关经历或项目）"


# 单独的工具函数用于 MCP 集成
async def render_resume_tool(markdown: str, output: str = "resume.pdf") -> Dict[str, Any]:
    """MCP 工具：渲染简历 PDF"""
    renderer = ResumeRenderer()
    try:
        result = await renderer.render_resume_pdf(markdown, output)
        return result
    finally:
        await renderer.stop()


if __name__ == "__main__":
    # 测试示例
    async def test():
        renderer = ResumeRenderer()
        await renderer.start()
        
        # 读取示例 Markdown
        with open("myexperience.md", "r", encoding="utf-8") as f:
            markdown = f.read()
        
        result = await renderer.render_resume_pdf(markdown, "test_output.pdf")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        await renderer.stop()
    
    asyncio.run(test())
'''

with open(mcp_dir / "resume_renderer.py", "w", encoding="utf-8") as f:
    f.write(renderer_content)
print("✓ Created: mcp_server/resume_renderer.py")

# 创建 mcp_server.py (MCP Server 主文件)
mcp_server_content = '''"""
MCP Server Implementation for Resume Auto-Fitting
Exposes render_resume_pdf tool to AI agents via MCP protocol
"""

import asyncio
import json
from typing import Any
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from resume_renderer import ResumeRenderer

# 创建 MCP Server 实例
server = Server("resume-autofit-server")

# 全局 Renderer 实例
renderer: ResumeRenderer = None


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """列出可用的工具"""
    return [
        types.Tool(
            name="render_resume_pdf",
            description="渲染简历 Markdown 为 PDF，检测是否溢出一页，并返回详细反馈",
            inputSchema={
                "type": "object",
                "properties": {
                    "markdown": {
                        "type": "string",
                        "description": "Markdown 格式的简历内容"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "PDF 输出路径（可选，默认为 resume.pdf）",
                        "default": "resume.pdf"
                    }
                },
                "required": ["markdown"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, 
    arguments: dict[str, Any]
) -> list[types.TextContent]:
    """处理工具调用"""
    
    global renderer
    
    if name != "render_resume_pdf":
        raise ValueError(f"Unknown tool: {name}")
    
    # 提取参数
    markdown = arguments.get("markdown", "")
    output_path = arguments.get("output_path", "resume.pdf")
    
    if not markdown:
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "status": "error",
                "message": "Markdown 内容不能为空"
            }, ensure_ascii=False)
        )]
    
    # 初始化 Renderer（如果尚未初始化）
    if not renderer:
        renderer = ResumeRenderer()
        await renderer.start()
    
    # 执行渲染
    try:
        result = await renderer.render_resume_pdf(markdown, output_path)
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2, ensure_ascii=False)
        )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "status": "error",
                "message": f"渲染失败: {str(e)}"
            }, ensure_ascii=False)
        )]


async def main():
    """启动 MCP Server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="resume-autofit-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
'''

with open(mcp_dir / "mcp_server.py", "w", encoding="utf-8") as f:
    f.write(mcp_server_content)
print("✓ Created: mcp_server/mcp_server.py")

# 创建 requirements.txt
requirements_content = '''playwright>=1.40.0
mcp>=0.1.0
'''

with open(mcp_dir / "requirements.txt", "w", encoding="utf-8") as f:
    f.write(requirements_content)
print("✓ Created: mcp_server/requirements.txt")

# 创建 README.md
readme_content = '''# MCP Server for Resume Auto-Fitting

## 功能说明

这是一个 MCP (Model Context Protocol) 服务器，为 AI Agent 提供简历自动适配工具。

### 主要功能

1. **render_resume_pdf**: 渲染 Markdown 简历为 PDF
   - 检测内容是否超过一页
   - 返回详细的溢出指标和削减建议

## 安装

### 1. 安装 Python 依赖

```bash
conda activate agent_env
cd mcp_server
pip install -r requirements.txt
```

### 2. 安装 Playwright 浏览器

```bash
playwright install chromium
```

## 使用方式

### 方式一：作为 MCP Server 运行

在 Claude Desktop 或其他 MCP 客户端配置中添加：

```json
{
  "mcpServers": {
    "resume-autofit": {
      "command": "python",
      "args": ["path/to/mcp_server/mcp_server.py"],
      "cwd": "path/to/myresumebuilder"
    }
  }
}
```

### 方式二：直接测试

```bash
cd mcp_server
python resume_renderer.py
```

## 工具接口

### render_resume_pdf

**输入参数：**
- `markdown` (string, required): Markdown 格式的简历内容
- `output_path` (string, optional): PDF 输出路径，默认 "resume.pdf"

**返回格式（成功）：**
```json
{
  "status": "success",
  "pdf_path": "/absolute/path/to/resume.pdf",
  "current_pages": 1,
  "message": "简历已成功渲染为单页 PDF"
}
```

**返回格式（失败 - 溢出）：**
```json
{
  "status": "failed",
  "reason": "overflow",
  "current_pages": 2,
  "overflow_amount": 15,
  "overflow_px": 168,
  "hint": "中等溢出（15%）。建议：应用 Level 2 削减（简化描述、移除软技能表述）"
}
```

## AI Agent 削减策略

当收到溢出错误时，Agent 应按以下层级削减内容：

### Level 1 - 低损失削减（溢出 < 5%）
- 合并孤立单词（1-2 个单词单独成行的情况）
- 将"技能"或"教育"部分格式化为单行管道分隔列表

### Level 2 - 中等削减（溢出 5-15%）
- 移除软技能描述（如"优秀的沟通能力"）
- 简化 STAR 描述（仅保留 Action + Result）
- 移除 5 年以上的非关键经历

### Level 3 - 高损失削减（溢出 > 15%）
- 根据职位描述分析相关性
- 移除整个最不相关的项目或经历块

## 技术架构

```
AI Agent (Reasoning)
    ↓ 生成 Markdown V1
    ↓
MCP Server (Acting)
    - Playwright Headless Browser
    - 加载 generated_resume.html
    - 注入 Markdown
    - 等待 simple_viewer.js 完成渲染
    - 检测页面高度
    ↓
返回结果
    - 成功 → PDF 路径
    - 失败 → 溢出指标 + 削减建议
    ↓
AI Agent 分析并削减内容
    ↓
重试渲染
```

## 依赖项

- Python 3.8+
- Playwright (Chromium)
- MCP Python SDK

## 注意事项

1. 确保 `generated_resume.html` 在项目根目录
2. 确保 `js/simple_viewer.js` 已添加 `render-complete` 类标记
3. 首次运行需要下载 Chromium 浏览器（约 150MB）
'''

with open(mcp_dir / "README.md", "w", encoding="utf-8") as f:
    f.write(readme_content)
print("✓ Created: mcp_server/README.md")

print("\n✅ MCP Server 结构创建完成!")
print("\n下一步:")
print("1. cd mcp_server")
print("2. pip install -r requirements.txt")
print("3. playwright install chromium")
