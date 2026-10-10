import json, re, shutil, subprocess
from pathlib import Path
import pytest
from resume_renderer import ResumeRenderer

FIX = Path(__file__).parent / "fixtures"

async def _render(md, out):
    r = ResumeRenderer()
    try:
        return await r.render_resume_pdf(md, str(out))
    finally:
        await r.stop()

@pytest.mark.asyncio
async def test_sidecar_written_next_to_pdf(tmp_path):
    out = tmp_path / "resume.pdf"
    res = await _render((FIX / "structured_canonical.md").read_text(encoding="utf-8"), out)
    side = tmp_path / "resume.structured.json"
    assert res["structured_path"] == str(side) and side.exists()
    assert "format_warnings" not in res   # empty lists are left out
    doc = json.loads(side.read_text(encoding="utf-8"))
    assert list(doc)[:6] == ["schema_version", "generator", "generated_at", "pdf_file", "warnings", "sections"]
    assert doc["pdf_file"] == "resume.pdf"
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", doc["generated_at"])

@pytest.mark.asyncio
async def test_sidecar_written_on_overflow_too(tmp_path):
    md = (FIX / "structured_canonical.md").read_text(encoding="utf-8")
    md += "\n" + "\n".join(f"- Filler: line number {i} with enough words to take real space on the page" for i in range(120))
    res = await _render(md, tmp_path / "long.pdf")
    assert res["status"] == "overflow"
    assert (tmp_path / "long.structured.json").exists()

@pytest.mark.asyncio
async def test_format_warnings_do_not_change_status(tmp_path):
    md = (FIX / "structured_canonical.md").read_text(encoding="utf-8")
    assert " – " in md
    res = await _render(md.replace(" – ", " - "), tmp_path / "r.pdf")
    assert res["status"] == "success"
    assert res["format_warnings"] and all(w["rule"] == "date" for w in res["format_warnings"])


# --- pin the parser to the rendered page and the PDF -------------------------

from playwright.async_api import async_playwright
from resume_structured import scan_blocks, strip_markdown, parse_resume_structured
from test_inline_formatting import _render_markdown

squash = lambda t: "".join(t.split()).lower()   # headings may be upper-cased by CSS

@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["structured_canonical.md", "structured_variants.md"])
async def test_trailing_italic_lines_match_dom_entry_headers(name):
    md = (FIX / name).read_text(encoding="utf-8")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await _render_markdown(page, md)
            dom = await page.evaluate("""() =>
                [...document.querySelectorAll('.pagedjs_page p.entry-header')].map(p => [
                    p.querySelector('.entry-main').textContent,
                    p.lastElementChild.textContent])""")
        finally:
            await browser.close()
    py = [(strip_markdown(b["text"]), strip_markdown(b["trailing"]))
          for b in scan_blocks(md) if b["type"] == "para" and b["trailing"] is not None]
    assert [(squash(a), squash(b)) for a, b in dom] == [(squash(a), squash(b)) for a, b in py]

def _strings(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("raw", "text", "date_raw", "trailing", "title") and isinstance(v, str):
                yield v
            else:
                yield from _strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)

@pytest.mark.asyncio
@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="needs poppler pdftotext")
async def test_every_string_appears_in_the_pdf(tmp_path):
    md = (FIX / "structured_canonical.md").read_text(encoding="utf-8")
    out = tmp_path / "r.pdf"
    await _render(md, out)
    pdf = squash(subprocess.run(["pdftotext", "-raw", str(out), "-"], capture_output=True, text=True, check=True).stdout)
    doc = json.loads((tmp_path / "r.structured.json").read_text(encoding="utf-8"))
    missing = [s for s in _strings(doc["sections"]) if squash(s) not in pdf]
    assert missing == []


# --- tool description, examples and docs -------------------------------------

# `mcp_server` is the package when run alone, but the module once test_mcp_server.py
# has put mcp_server/ first on sys.path during collection.
try:
    from mcp_server.mcp_server import handle_list_tools, EXAMPLE_RESUME
except ImportError:
    from mcp_server import handle_list_tools, EXAMPLE_RESUME

ROOT = Path(__file__).parent.parent

@pytest.mark.asyncio
async def test_tool_examples_and_example_resume_are_canonical():
    tool = (await handle_list_tools())[0]
    assert EXAMPLE_RESUME in tool.inputSchema["properties"]["markdown_path"]["description"]
    samples = [EXAMPLE_RESUME]
    samples.append((ROOT / "example_resume.md").read_text(encoding="utf-8"))
    for md in samples:
        doc, fw = parse_resume_structured(md)
        assert fw == [], fw
        kinds = [s["kind"] for s in doc["sections"]]
        assert {"experience", "skills"} <= set(kinds)

@pytest.mark.asyncio
async def test_tool_description_mentions_new_outputs():
    tool = (await handle_list_tools())[0]
    assert ".structured.json" in tool.description and "## Format warnings" in tool.description
    assert "## Space by section and entry" in tool.description and "characters on its last line" in tool.description
    assert "never says which content to cut" in tool.description
    d = tool.inputSchema["properties"]["markdown_path"]["description"]
    for needle in ("Mon YYYY – Mon YYYY", "Never invent", "City, ST", "Company · Job Title · Location"):
        assert needle in d
    assert ".structured.json" in tool.inputSchema["properties"]["output_path"]["description"]


# --- a failed sidecar leaves no stale file -------------------------------------

@pytest.mark.asyncio
async def test_failed_sidecar_removes_stale_file(tmp_path, monkeypatch):
    import resume_renderer
    def boom(_md):
        raise RuntimeError("parser failed")
    monkeypatch.setattr(resume_renderer, "parse_resume_structured", boom)
    stale = tmp_path / "r.structured.json"
    stale.write_text("{}", encoding="utf-8")
    res = await _render((FIX / "structured_canonical.md").read_text(encoding="utf-8"), tmp_path / "r.pdf")
    assert res["status"] == "success"
    assert res["structured_path"] is None and "format_warnings" not in res
    assert not stale.exists()
