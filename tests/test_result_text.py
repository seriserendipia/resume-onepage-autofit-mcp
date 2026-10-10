"""
The MCP returns the render result as Markdown text, grouped by section and entry.
These tests build the result dict by hand, so no browser is needed.
"""
from result_text import entry_name, format_error, format_result, group_entries

MARKDOWN = """# Jane Doe
Springfield, IL | jane@example.com

## Education

**Example University** *Sep 2019 – Jun 2023*

Bachelor of Science in Computer Science *Boston, MA*

## Projects

Open Source Contributor · pandas *Jan 2022 – Aug 2022*

- Documentation: Rewrote the user guide
- Fixes: Fixed 12 issues

## Skills
- Languages: Python | SQL
"""


def _item(line, kind, rendered=1, last=40):
    return {"source_line": line, "kind": kind, "rendered_lines": rendered, "characters_on_last_line": last}


RESULT = {
    "status": "overflow",
    "pdf_path": "/home/jane/resume.pdf",
    "explanation": "Failed: it does not fit. Next step: shorten it.",
    "page_fit": {"page_count": 2, "overflow_percent": 6, "overflow_body_lines": 4,
                 "first_source_line_on_page_2": 15, "auto_fit_direction": "shrink"},
    "space_by_section": [
        {"section_title": "(name and contact lines)", "title_source_line": None, "rendered_lines": 2,
         "items": [_item(1, "heading", last=8), _item(2, "paragraph")]},
        {"section_title": "Education", "title_source_line": 4, "rendered_lines": 2,
         "items": [_item(6, "entry_header"), _item(8, "entry_header")]},
        {"section_title": "Projects", "title_source_line": 10, "rendered_lines": 4,
         "items": [_item(12, "entry_header"), _item(14, "bullet", rendered=2, last=6), _item(15, "bullet")]},
        {"section_title": "Skills", "title_source_line": 17, "rendered_lines": 2,
         "items": [_item(18, "bullet", rendered=2, last=3)]},
    ],
    "format_warnings": [{"source_line": 18, "rule": "skills", "found": "Languages: Python | SQL",
                         "expected": "Category: item, item"}],
}


def test_entry_name_is_the_first_part_of_the_entry_line():
    assert entry_name("Open Source Contributor · pandas *Jan 2022 – Aug 2022*") == "Open Source Contributor"
    assert entry_name("**Example University** *Sep 2019 – Jun 2023*") == "Example University"
    assert entry_name("Tech Company Inc. · Software Engineer Intern · San Francisco, CA *Jun 2024 – Present*") == "Tech Company Inc."


def test_degree_line_belongs_to_its_school():
    lines = MARKDOWN.splitlines()
    (school,) = group_entries(RESULT["space_by_section"][1]["items"], lines)
    assert school["name"] == "Example University" and [i["source_line"] for i in school["items"]] == [6, 8]


def test_text_order_and_rows():
    text = format_result(RESULT, MARKDOWN)
    lines = text.splitlines()
    assert lines[:4] == ["status: overflow", "pdf_path: /home/jane/resume.pdf", "", "Failed: it does not fit. Next step: shorten it."]
    assert "- overflow_percent: 6" in lines and "- first_source_line_on_page_2: 15" in lines
    assert "| **(name and contact lines)** | 1–2 | 2 | 20% |  |" in lines
    assert "| ↳ Example University | 6–8 | 2 | 20% |  |" in lines
    # wrapped items appear on the entry row only, not again on its section row
    assert "| **Projects** | 12–15 | 4 | 40% |  |" in lines
    assert "| ↳ Open Source Contributor | 12–15 | 4 | 40% | 14: 6 |" in lines
    # a section without entries carries its own wrapped items; a single line is not shown as a range
    assert "| **Skills** | 18 | 2 | 20% | 18: 3 |" in lines


def test_pipes_in_cells_are_escaped_and_warnings_are_tables():
    text = format_result(RESULT, MARKDOWN)
    assert "## Format warnings (lines not in the canonical form)" in text
    assert "| 18 | skills | Languages: Python \\| SQL | Category: item, item |" in text
    assert "Layout warnings" not in text


def test_error_text():
    text = format_error({"status": "error", "error_code": "FILE_NOT_FOUND",
                         "message": "No file at /x.md.", "next_action": "Write the resume first."})
    assert text == "status: error\nerror_code: FILE_NOT_FOUND\n\nNo file at /x.md.\nWrite the resume first."
