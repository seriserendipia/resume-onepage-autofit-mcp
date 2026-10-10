"""
render_resume_pdf reports layout facts per block of the Markdown file: rendered lines,
characters on the last rendered line, and how many body lines overflow page 1.
"""

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


def _items(res):
    return {it["source_line"]: it for sec in res["space_by_section"] for it in sec["items"]}


async def test_items_carry_source_line_kind_rendered_lines_and_last_line_chars(tmp_path):
    res = await _render(RESUME, tmp_path / "r.pdf")
    assert res["status"] == "success"
    secs = res["space_by_section"]
    assert [s["section_title"] for s in secs] == ["(name and contact lines)", "Experience", "Skills"]
    assert [s["title_source_line"] for s in secs] == [None, 4, 11]

    items = _items(res)
    assert items[1] == {"source_line": 1, "kind": "heading", "rendered_lines": 1, "characters_on_last_line": len("Jane Doe")}
    assert items[6]["kind"] == "entry_header"
    assert items[8] == {"source_line": 8, "kind": "bullet", "rendered_lines": 1,
                        "characters_on_last_line": len("Short: one line")}   # the bullet marker is not counted
    assert items[9]["rendered_lines"] >= 2 and 0 < items[9]["characters_on_last_line"] < len(LONG)
    for s in secs:
        assert s["rendered_lines"] == sum(it["rendered_lines"] for it in s["items"])
    assert sum(s["percent_of_all_rendered_lines"] for s in secs) == pytest.approx(100, abs=2)


async def test_result_order_and_fields_on_success(tmp_path):
    res = await _render(RESUME, tmp_path / "r.pdf")
    assert list(res)[:5] == ["status", "pdf_path", "explanation", "page_fit", "space_by_section"]
    assert res["explanation"].startswith("Success:")
    fit = res["page_fit"]
    assert fit["page_count"] == 1 and 0 <= fit["empty_space_percent"] <= 100
    assert fit["auto_fit_direction"] in ("shrink", "expand", "none")
    assert "overflow_percent" not in fit
    assert "layout_warnings" not in res and "format_warnings" not in res
    assert {"hint", "content_stats", "final_styles", "auto_fit", "auto_fit_status", "fill_ratio", "page"}.isdisjoint(res)


async def test_overflow_reports_percent_lines_and_where_page_two_starts(tmp_path):
    md = RESUME + "\n".join(f"- Filler {i}: a bullet with enough words to take real space" for i in range(80))
    res = await _render(md, tmp_path / "r.pdf")
    assert res["status"] == "overflow" and res["explanation"].startswith("Failed:")
    fit = res["page_fit"]
    assert fit["page_count"] >= 2 and fit["overflow_percent"] > 0 and fit["overflow_body_lines"] > 0
    first = fit["first_source_line_on_page_2"]
    assert first in _items(res)
    assert f"source line {first}" in res["explanation"]
    assert "empty_space_percent" not in fit


async def test_wrapped_entry_header_is_reported_by_source_line(tmp_path):
    md = RESUME.replace("Acme · Analyst", "Acme International Holdings Corporation · Principal Senior Staff Analyst · Team")
    res = await _render(md, tmp_path / "r.pdf")
    assert res["status"] == "layout_error" and res["explanation"].startswith("Failed:")
    (w,) = res["layout_warnings"]
    assert w["source_line"] == 6 and w["rendered_lines"] >= 2


async def test_call_writes_pdf_next_to_markdown_and_returns_text(tmp_path):
    md = tmp_path / "resume.md"
    md.write_text(RESUME, encoding="utf-8")
    out = await handle_call_tool("render_resume_pdf", {"markdown_path": str(md)})
    lines = out[0].text.splitlines()
    assert lines[0] == "status: success"
    assert lines[1] == f"pdf_path: {tmp_path / 'resume.pdf'}" and (tmp_path / "resume.pdf").exists()
    assert lines[3].startswith("Success:")
    assert "## Page fit" in lines and "## Space by section and entry" in lines
    assert "| ↳ Acme | 6–9 |" in out[0].text          # the entry is named by the first part of its entry line
    assert "structured_path" not in out[0].text


async def test_relative_output_path_is_rejected(tmp_path):
    md = tmp_path / "resume.md"
    md.write_text(RESUME, encoding="utf-8")
    out = await handle_call_tool("render_resume_pdf", {"markdown_path": str(md), "output_path": "out/resume.pdf"})
    text = out[0].text
    assert text.startswith("status: error\nerror_code: INVALID_PATH\n") and "output_path" in text
