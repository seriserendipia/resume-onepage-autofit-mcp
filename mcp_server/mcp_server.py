"""
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
