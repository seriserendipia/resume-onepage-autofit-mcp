"""
把 render_resume_pdf 的结果字典排成给 LLM 读的 Markdown 文本。

读者是模型，不是程序：列名只写一次、写清楚，每行只放数值，比 JSON 每项重复键名省一半以上 token。
顺序即阅读顺序：status → pdf_path → explanation → Page fit → 按板块/条目的占用表 → 警告。
"""
import re
from typing import Any, Dict, List, Optional

from resume_structured import strip_markdown

_TRAILING_ITALIC = re.compile(r"\s*\*[^*]+\*\s*$")


def entry_name(source_line_text: str) -> str:
    """条目头的第一段：项目名、公司名或学校名（去掉行尾斜体日期/地点和 Markdown 标记）。"""
    text = _TRAILING_ITALIC.sub("", source_line_text)
    return strip_markdown(text).split(" · ")[0].strip()


def group_entries(items: List[dict], lines: List[str]) -> List[dict]:
    """把板块里的块按条目分组。条目从一个条目头开始；紧跟在条目头后面的条目头
    （例如 Education 的学位行）属于同一个条目。条目头之前的块不归入任何条目。"""
    entries, current, prev_kind = [], None, None
    for item in items:
        if item["kind"] == "entry_header" and prev_kind != "entry_header":
            current = {"name": entry_name(lines[item["source_line"] - 1]), "items": []}
            entries.append(current)
        if current is not None:
            current["items"].append(item)
        prev_kind = item["kind"]
    return entries


def _line_range(items: List[dict]) -> str:
    if not items:
        return "-"
    first, last = items[0]["source_line"], items[-1]["source_line"]
    return str(first) if first == last else f"{first}–{last}"


def _wrapped(items: List[dict]) -> str:
    return ", ".join(f"{i['source_line']}: {i['characters_on_last_line']}" for i in items if i["rendered_lines"] > 1)


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def format_result(result: Dict[str, Any], markdown: str) -> str:
    """渲染结果 → Markdown 文本。markdown 是用户的源文件内容，用来取条目名。"""
    lines = markdown.splitlines()
    out = [f"status: {result['status']}", f"pdf_path: {result['pdf_path']}", "", result["explanation"], "", "## Page fit"]
    out += [f"- {key}: {value}" for key, value in result["page_fit"].items()]

    sections = result.get("space_by_section", [])
    total = sum(s["rendered_lines"] for s in sections) or 1
    out += ["", "## Space by section and entry", "",
            "| section / entry | source lines | rendered lines | % of all rendered lines "
            "| wrapped items (source line: characters on last line) |",
            "|---|---|---|---|---|"]

    def row(name: str, items: List[dict], rendered: int, wrapped: str) -> None:
        out.append(f"| {_cell(name)} | {_line_range(items)} | {rendered} | {round(rendered / total * 100)}% | {wrapped} |")

    for section in sections:
        entries = group_entries(section["items"], lines)
        # 有条目的板块，折行信息只写在条目行上，避免重复
        row(f"**{section['section_title']}**", section["items"], section["rendered_lines"],
            "" if entries else _wrapped(section["items"]))
        for entry in entries:
            row(f"↳ {entry['name']}", entry["items"], sum(i["rendered_lines"] for i in entry["items"]),
                _wrapped(entry["items"]))

    if result.get("layout_warnings"):
        out += ["", "## Layout warnings (entry headers that wrapped)", "",
                "| source line | rendered lines | cause | text |", "|---|---|---|---|"]
        out += [f"| {w['source_line']} | {w['rendered_lines']} | {w['cause']} | {_cell(w['text'])} |"
                for w in result["layout_warnings"]]
    if result.get("format_warnings"):
        out += ["", "## Format warnings (lines not in the canonical form)", "",
                "| source line | rule | found | expected |", "|---|---|---|---|"]
        out += [f"| {w['source_line']} | {w['rule']} | {_cell(w['found'])} | {_cell(w['expected'])} |"
                for w in result["format_warnings"]]
    return "\n".join(out)


def format_error(error: Dict[str, Any]) -> str:
    """错误结果 → 文本：status、error_code，然后是原因与下一步。"""
    out = [f"status: {error.get('status', 'error')}", f"error_code: {error.get('error_code')}", "", error.get("message", "")]
    for key in ("suggestion", "next_action"):
        if error.get(key):
            out.append(error[key])
    return "\n".join(out)
