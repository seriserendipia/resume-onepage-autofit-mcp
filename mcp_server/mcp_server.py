"""
MCP Server Implementation for Resume Auto-Fitting
Exposes render_resume_pdf tool to AI agents via MCP protocol
"""

import asyncio
import json
import sys
import os
from typing import Any
from pathlib import Path

# Add the current directory to sys.path to ensure absolute imports work regardless of CWD
current_dir = Path(__file__).parent.resolve()
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from resume_renderer import ResumeRenderer

# 创建 MCP Server 实例
server = Server("resume-onepage-autofit-mcp")

# 全局 Renderer 实例
renderer: ResumeRenderer = None


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """列出可用的工具"""
    return [
        types.Tool(
            name="render_resume_pdf",
            description="Render resume Markdown to single-page A4 PDF with auto-fit. "
                "Returns: status ('success'|'layout_warning'|'overflow'|'error'), pdf_path, current_pages, "
                "fill_ratio (0-1), overflow_amount, hint (reduction suggestions), layout_warnings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "markdown": {
                        "type": "string",
                        "description": (
                            "Resume in Markdown. Supported: "
                            "# Name (centered), ## Section (underlined, no --- needed), "
                            "**bold** (company/title/key metrics like **15%**), "
                            "*italic at end of line* (dates, auto right-aligned in PDF), "
                            "- bullets, [text](url). "
                            "Entry format: **Company** · Role · Location *Date range* "
                            "(all one line, NO dot before italic date), blank line, then - bullets. "
                            "Bullet format: - **Label:** description with **key metric** "
                            "(e.g., - **Churn Modeling:** Built ML pipeline, reducing churn by **12%**)."
                        ),
                        "examples": [
                            "# Jane Doe\n"
                            "SF, CA | jane@email.com | [LinkedIn](https://linkedin.com/in/jane)\n"
                            "\n"
                            "## Summary\n"
                            "Data Scientist with expertise in **ML** and **Experimentation**, "
                            "driving **15% revenue growth**.\n"
                            "\n"
                            "## Experience\n"
                            "\n"
                            "**Google** · Senior Data Scientist · Mountain View, CA *Jan 2022 – Present*\n"
                            "\n"
                            "- **A/B Testing:** Led experimentation framework serving **100M+ users**\n"
                            "- **Churn Modeling:** Built ML pipeline, reducing churn by **12%**\n"
                            "\n"
                            "## Education\n"
                            "\n"
                            "**Stanford University** · M.S. Statistics · Stanford, CA *2017 – 2019*\n"
                            "\n"
                            "## Skills\n"
                            "- **Languages**: Python, R, SQL\n"
                            "- **Tools**: Spark, Airflow, Tableau"
                        ]
                    },
                    "output_path": {
                        "type": "string",
                        "description": "PDF save path (e.g., JohnDoe_Google_SWE.pdf). Default: ./generated_resume/output_resume.pdf"
                    }
                },
                "required": ["markdown"]
            },
            annotations={
                "title": "Resume PDF Renderer",
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False
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
                "error_code": "EMPTY_CONTENT",
                "message": "Markdown content cannot be empty.",
                "suggestion": "Provide resume content in Markdown format with sections like ## Experience, ## Education, ## Skills",
                "next_action": "Generate resume content first using user's experience data, then call render_resume_pdf again",
                "example": "## Experience\\n\\n**Company Name** · Job Title\\n- Achievement 1\\n- Achievement 2"
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
        error_msg = str(e)
        suggestion = "Check that the Markdown content is valid and properly formatted."
        next_action = "Review the Markdown syntax and try again."
        
        # Provide specific suggestions based on error type
        if "timeout" in error_msg.lower():
            suggestion = "The rendering took too long. Try with shorter content first."
            next_action = "Reduce content length and retry, or check if Chromium browser is properly installed."
        elif "chromium" in error_msg.lower() or "browser" in error_msg.lower():
            suggestion = "Browser initialization failed. Ensure Playwright Chromium is installed."
            next_action = "Run 'playwright install chromium' to install the browser."
        elif "file" in error_msg.lower() or "path" in error_msg.lower():
            suggestion = "File system error. Check the output path is valid and writable."
            next_action = "Verify the output directory exists and has write permissions."
        
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "status": "error",
                "error_code": "RENDER_FAILED",
                "message": f"Rendering failed: {error_msg}",
                "suggestion": suggestion,
                "next_action": next_action
            }, ensure_ascii=False)
        )]


async def main():
    """启动 MCP Server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="resume-onepage-autofit-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
