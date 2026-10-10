"""
MCP Server Implementation for Resume Auto-Fitting
Exposes render_resume_pdf tool to AI agents via MCP protocol
"""

import asyncio
import json
import sys
import os
from typing import Any, Optional, Tuple
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


# A complete resume in the canonical forms, shown to the model in the tool description.
EXAMPLE_RESUME = (
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
)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """列出可用的工具"""
    return [
        types.Tool(
            name="render_resume_pdf",
            description="Render a resume Markdown file to a single-page A4 PDF and write <name>.structured.json next to the PDF. "
                "Auto-fit first adjusts font size, line height and margins within fixed limits. "
                "Pass the file by absolute path in markdown_path; never put resume text in the call. "
                "Write the file once, then edit it in place and call again with the same path. "
                "The result reports layout facts and never suggests what to change: "
                "page.overflow_lines and page.free_lines are in body lines; "
                "sections[].blocks lists every rendered block as [source line, rendered lines, characters on its last rendered line]. "
                "layout_warnings and format_warnings appear only when non-empty.",
            inputSchema={
                "type": "object",
                "properties": {
                    "markdown_path": {
                        "type": "string",
                        "description": (
                            "Absolute path to the resume Markdown file (UTF-8), on the machine running this server.\n"
                            "  Linux/macOS:  /home/jane/resumes/resume.md\n"
                            "  Windows:      C:\\Users\\Jane\\resumes\\resume.md   (C:/Users/Jane/... also works)\n"
                            "Relative paths are rejected: they would resolve against the server's working directory,\n"
                            "not yours. format_warnings line numbers are line numbers in this file.\n"
                            "\n"
                            "Write every line of the file in the canonical form below. The renderer reads\n"
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
                            "  One paragraph of prose (bold allowed), no bullets.\n"
                            "\n"
                            "EXAMPLE FILE\n"
                            + EXAMPLE_RESUME
                        )
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Absolute path for the PDF. Default: next to the Markdown file with the same name "
                            "(resume.md -> resume.pdf). The structured JSON is written next to the PDF as <name>.structured.json."
                    }
                },
                "required": ["markdown_path"]
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


def _path_error(code: str, message: str, next_action: str) -> dict:
    return {"status": "error", "error_code": code, "message": message, "next_action": next_action}


def _absolute_path(raw: str, field: str, filename: str) -> Tuple[Optional[Path], Optional[dict]]:
    """去掉首尾空白和引号、展开 ~，只接受绝对路径。"""
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    path = Path(text).expanduser()
    if not path.is_absolute():
        example = f"C:\\Users\\you\\{filename}" if os.name == "nt" else f"/home/you/{filename}"
        return None, _path_error(
            "INVALID_PATH",
            f"{field} must be an absolute path, got {raw!r}. Relative paths resolve against the "
            f"server's working directory ({os.getcwd()}), not yours.",
            f"Call again with the full path, e.g. {example}.",
        )
    return path, None


def resolve_output_path(raw: Any, markdown_path: str) -> Tuple[Optional[Path], Optional[dict]]:
    """output_path 省略时放在 Markdown 文件旁边、同名 .pdf；给了就必须是绝对路径。"""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        md, _ = _absolute_path(markdown_path, "markdown_path", "resume.md")
        return md.with_suffix(".pdf"), None
    if not isinstance(raw, str):
        return None, _path_error("INVALID_PATH", "output_path must be a string.", "Pass an absolute .pdf path or omit output_path.")
    return _absolute_path(raw, "output_path", "resume.pdf")


def read_markdown_file(raw: Any) -> Tuple[Optional[str], Optional[dict]]:
    """读取 markdown_path 指向的简历文件，返回 (内容, None) 或 (None, 错误)。

    兼容 Linux 与 Windows：去掉首尾空白和引号（资源管理器"复制为路径"会加双引号），
    展开 ~，只接受绝对路径（相对路径会落到 MCP 服务器进程的工作目录，而不是调用方的工作区）。
    以 utf-8-sig 读取并统一换行，所以带 BOM、CRLF 的文件与 format_warnings 的行号一致。
    """
    write_file = "Write the resume to a .md file, then call render_resume_pdf with its absolute path in markdown_path."
    if not isinstance(raw, str) or not raw.strip():
        return None, _path_error("INVALID_PATH", "markdown_path is required: the absolute path to the resume Markdown file.", write_file)

    path, error = _absolute_path(raw, "markdown_path", "resume.md")
    if error:
        return None, error
    if not path.exists():
        return None, _path_error("FILE_NOT_FOUND", f"No file at {path}.", write_file)
    if not path.is_file():
        return None, _path_error("INVALID_PATH", f"{path} is not a file.", "Pass the path of the .md file itself, not its folder.")

    try:
        markdown = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return None, _path_error("FILE_READ_FAILED", f"{path} is not valid UTF-8 text.", "Save the file as UTF-8 and call again.")
    except OSError as e:
        return None, _path_error("FILE_READ_FAILED", f"Could not read {path}: {e}", "Check the file permissions and call again.")

    if not markdown.strip():
        return None, {
            **_path_error("EMPTY_CONTENT", f"{path} is empty.",
                          "Write the resume into the file using the user's experience data, then call render_resume_pdf again."),
            "suggestion": "Provide resume content in Markdown format with sections like ## Experience, ## Education, ## Skills",
        }
    return markdown, None


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
    markdown, error = read_markdown_file(arguments.get("markdown_path"))
    output_path = None
    if not error:
        output_path, error = resolve_output_path(arguments.get("output_path"), arguments["markdown_path"])
    if error:
        return [types.TextContent(type="text", text=json.dumps(error, ensure_ascii=False))]

    # 初始化 Renderer（如果尚未初始化）
    if not renderer:
        renderer = ResumeRenderer()
        await renderer.start()
    
    # 执行渲染
    try:
        result = await renderer.render_resume_pdf(markdown, str(output_path))
        return [types.TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, separators=(",", ":"))
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
