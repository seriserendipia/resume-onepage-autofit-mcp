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
            description="Render resume Markdown to single-page A4 PDF with auto-fit, and write a structured JSON copy next to the PDF. "
                "Returns: status ('success'|'overflow'|'layout_error'|'error'), pdf_path, current_pages, "
                "fill_ratio (0-1), overflow_amount, hint (reduction suggestions), layout_warnings, "
                "structured_path, format_warnings (lines that do not follow the canonical forms in the "
                "markdown parameter, each with the expected form).",
            inputSchema={
                "type": "object",
                "properties": {
                    "markdown": {
                        "type": "string",
                        "description": (
                            "Resume in Markdown. Write every line in the canonical form below. The renderer reads\n"
                            "structure from these forms and reports deviations in format_warnings.\n"
                            "\n"
                            "SYNTAX\n"
                            "  # Name              centered title\n"
                            "  ## Section          underlined heading\n"
                            "  - text              bullet\n"
                            "  [text](url)         link\n"
                            "  **bold**            optional, visual only. Bold never changes structure.\n"
                            "  *italic*            when it ends a paragraph line, it is right-aligned.\n"
                            "\n"
                            "HEADER\n"
                            "  Line 1: # Full Name\n"
                            "  Line 2: contact items separated by \" | \".\n"
                            "  Example: San Francisco, CA | (555) 123-4567 | jane@email.com | [LinkedIn](https://linkedin.com/in/jane)\n"
                            "\n"
                            "SECTION TITLES\n"
                            "  Use exactly: Summary, Skills, Experience, Projects, Education (any letter case).\n"
                            "  Other titles are allowed. In them you may use paragraphs, bullets, and entry lines.\n"
                            "\n"
                            "DATES (the italic at the end of an entry line)\n"
                            "  Mon YYYY \u2013 Mon YYYY     three-letter month, four-digit year, en dash (\u2013) with one space each side\n"
                            "  Mon YYYY \u2013 Present      ongoing\n"
                            "  Mon YYYY                happened within a single month\n"
                            "  Months: Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec\n"
                            "  Do not write full month names, hyphens, or a year without a month.\n"
                            "  If you do not know the month, ask the user. Never invent one.\n"
                            "  Dates inside bullet text are free-form.\n"
                            "\n"
                            "LOCATIONS\n"
                            "  City, ST         US places, two-letter state code\n"
                            "  City, Country    everywhere else\n"
                            "  Remote\n"
                            "\n"
                            "ENTRY LINE\n"
                            "  An entry line is the first line of an entry. Its parts are separated by \" \u00b7 \"\n"
                            "  (space, middle dot, space) and it ends with an italic date range.\n"
                            "  Put the date directly after the last part, with no \" \u00b7 \" before it.\n"
                            "    Experience:  Company \u00b7 Job Title \u00b7 Location *Mon YYYY \u2013 Mon YYYY*\n"
                            "    Project:     Project Name \u00b7 Your Role *Mon YYYY \u2013 Mon YYYY*\n"
                            "                 Project Name \u00b7 Your Role \u00b7 Location *Mon YYYY \u2013 Mon YYYY*   (location optional)\n"
                            "  Leave one blank line after the entry line, then write its bullets.\n"
                            "\n"
                            "EDUCATION\n"
                            "  Each school is two lines with one blank line between them:\n"
                            "    School Name *Mon YYYY \u2013 Mon YYYY*\n"
                            "\n"
                            "    Degree in Field (GPA: x/y) *Location*\n"
                            "  Write the degree in full: \"Master of Science in Statistics\", not \"M.S. Statistics\".\n"
                            "  The GPA part is optional. If you bold the degree, bold the whole \"Degree in Field\" text.\n"
                            "\n"
                            "BULLETS\n"
                            "  - Label: sentence\n"
                            "  The label is a 1-3 word topic. No period at the end.\n"
                            "  Example: - Churn Modeling: Built an ML pipeline that cut churn by **12%**\n"
                            "\n"
                            "SKILLS\n"
                            "  One bullet per category:  - Category: item, item, item\n"
                            "  Put details of one item in parentheses:  SQL (PostgreSQL, MySQL)\n"
                            "\n"
                            "SUMMARY\n"
                            "  One paragraph of prose (bold allowed), no bullets."
                        ),
                        "examples": [
                            "# Jane Doe\n"
                            "San Francisco, CA | jane@email.com | [LinkedIn](https://linkedin.com/in/jane)\n"
                            "\n"
                            "## Summary\n"
                            "\n"
                            "Data Scientist with expertise in **ML** and **Experimentation**, driving **15% revenue growth**.\n"
                            "\n"
                            "## Experience\n"
                            "\n"
                            "Google \u00b7 Senior Data Scientist \u00b7 Mountain View, CA *Jan 2022 \u2013 Present*\n"
                            "\n"
                            "- A/B Testing: Led an experimentation framework serving **100M+ users**\n"
                            "- Churn Modeling: Built an ML pipeline that cut churn by **12%**\n"
                            "\n"
                            "## Projects\n"
                            "\n"
                            "tinyqueue \u00b7 Maintainer *Mar 2021 \u2013 Present*\n"
                            "\n"
                            "- Job Scheduling: Wrote an open-source Python task queue used by **40+ teams**\n"
                            "\n"
                            "## Education\n"
                            "\n"
                            "Stanford University *Sep 2017 \u2013 Jun 2019*\n"
                            "\n"
                            "Master of Science in Statistics (GPA: 3.9/4.0) *Stanford, CA*\n"
                            "\n"
                            "## Skills\n"
                            "\n"
                            "- Languages: Python, R, SQL (PostgreSQL, BigQuery)\n"
                            "- Tools: Spark, Airflow, Tableau"
                        ]
                    },
                    "output_path": {
                        "type": "string",
                        "description": "PDF save path (e.g., JohnDoe_Google_SWE.pdf). Default: ./generated_resume/output_resume.pdf. "
                            "The structured JSON is written next to it with the suffix .structured.json."
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
                "example": "## Experience\\n\\nCompany Name · **Job Title** *2023 – Present*\\n- Achievement 1\\n- Achievement 2"
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
