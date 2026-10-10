"""
render_resume_pdf reports layout facts per block of the Markdown file: rendered lines,
characters on the last rendered line, and how many body lines overflow page 1.
"""
import json

import pytest
from resume_renderer import ResumeRenderer

try:
    from mcp_server.mcp_server import handle_call_tool
except ImportError:
    from mcp_server import handle_call_tool

LONG = ("Long: Built and maintained the nightly reporting pipeline that feeds every finance, "
        "sales and operations dashboard, rewrote the slowest joins, added data quality checks "
        "at each stage, and documented the on-call runbook so new hires could own it alone")

RESUME = f"""# Jane Doe
Springfield, IL | jane@example.com

## Experience

Acme · Analyst · Springfield, IL *Jan 2022 – Present*

- Short: one line
- {LONG}

## Skills

- Languages: Python, SQL
"""


async def _render(md, out):
    r = ResumeRenderer()
    try:
        return await r.render_resume_pdf(md, str(out))
    finally:
        await r.stop()


def _blocks(res):
    return {b[0]: b for s in res["sections"] for b in s["blocks"]}


async def test_blocks_carry_source_line_rendered_lines_and_last_line_chars(tmp_path):
    res = await _render(RESUME, tmp_path / "r.pdf")
    assert res["status"] == "success"
    assert [s["title"] for s in res["sections"]] == ["(header)", "Experience", "Skills"]
    assert [s["line"] for s in res["sections"]] == [None, 4, 11]

    blocks = _blocks(res)
    assert blocks[1] == [1, 1, len("Jane Doe")]
    assert blocks[8] == [8, 1, len("Short: one line")]        # the bullet marker is not counted
    _, lines, last = blocks[9]
    assert lines >= 2 and 0 < last < len(LONG)
    assert blocks[13] == [13, 1, len("Languages: Python, SQL")]
    for s in res["sections"]:
        assert s["lines"] == sum(b[1] for b in s["blocks"])


async def test_page_budget_on_one_page(tmp_path):
    res = await _render(RESUME, tmp_path / "r.pdf")
    page = res["page"]
    assert page["page_lines"] > 30 and page["body_line_px"] > 0
    assert page["used_lines"] + page["free_lines"] == pytest.approx(page["page_lines"], abs=0.2)
    assert "overflow_lines" not in page
    assert "layout_warnings" not in res and "format_warnings" not in res
    assert {"hint", "content_stats", "final_styles", "auto_fit_status", "suggestion", "next_action"}.isdisjoint(res)


async def test_overflow_reports_lines_and_where_page_two_starts(tmp_path):
    md = RESUME + "\n".join(f"- Filler {i}: a bullet with enough words to take real space" for i in range(80))
    res = await _render(md, tmp_path / "r.pdf")
    assert res["status"] == "overflow" and res["current_pages"] >= 2
    page = res["page"]
    assert page["overflow_lines"] > 0
    assert page["overflow_starts_at_line"] in _blocks(res)
    assert str(page["overflow_lines"]) in res["message"]


async def test_wrapped_entry_header_is_reported_by_line(tmp_path):
    md = RESUME.replace("Acme · Analyst", "Acme International Holdings Corporation · Principal Senior Staff Analyst · Team")
    res = await _render(md, tmp_path / "r.pdf")
    assert res["status"] == "layout_error"
    (w,) = res["layout_warnings"]
    assert w["line"] == 6 and w["rendered_lines"] >= 2


async def test_call_writes_pdf_next_to_markdown_and_returns_compact_json(tmp_path):
    md = tmp_path / "resume.md"
    md.write_text(RESUME, encoding="utf-8")
    out = await handle_call_tool("render_resume_pdf", {"markdown_path": str(md)})
    text = out[0].text
    res = json.loads(text)
    assert res["pdf_path"] == str(tmp_path / "resume.pdf") and (tmp_path / "resume.pdf").exists()
    assert "\n" not in text and ", " not in text.split('"sections"')[1][:40]


async def test_relative_output_path_is_rejected(tmp_path):
    md = tmp_path / "resume.md"
    md.write_text(RESUME, encoding="utf-8")
    out = await handle_call_tool("render_resume_pdf", {"markdown_path": str(md), "output_path": "out/resume.pdf"})
    res = json.loads(out[0].text)
    assert res["status"] == "error" and res["error_code"] == "INVALID_PATH" and "output_path" in res["message"]
