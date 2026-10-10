"""Test: entry dates stay next to their header in the PDF content stream.

Workday's resume autofill reads the PDF in content-stream order. When the date
is painted away from its header line (as a CSS float is), every job loses its
dates and the dates turn into empty phantom entries. `pdftotext -raw` dumps text
in content-stream order, so it is used here as a local stand-in. It is a guard
against regressions, not proof that Workday parses the file.
"""
import shutil
import subprocess
from pathlib import Path

import pytest
from resume_renderer import ResumeRenderer

pytestmark = pytest.mark.skipif(shutil.which("pdftotext") is None, reason="needs poppler pdftotext")


@pytest.mark.asyncio
async def test_dates_follow_their_header_in_content_stream(tmp_path):
    md = (Path(__file__).parent.parent / "example_resume.md").read_text(encoding="utf-8")
    out = tmp_path / "resume.pdf"
    renderer = ResumeRenderer()
    result = await renderer.render_resume_pdf(md, str(out))
    await renderer.stop()
    assert out.exists(), f"PDF not written: {result.get('message')}"

    headers = await _entry_headers(md)
    assert headers, "example_resume.md should contain entry headers"

    raw = subprocess.run(["pdftotext", "-raw", str(out), "-"], capture_output=True, text=True, check=True).stdout
    # -raw drops some inter-word spaces, so compare with all whitespace removed
    squash = lambda t: "".join(t.split())
    lines = [squash(line) for line in raw.splitlines()]
    for main, date in headers:
        hits = [line for line in lines if line.startswith(squash(main))]
        assert hits, f"header not found in PDF text: {main!r}"
        assert squash(main + date) in hits, (
            f"date {date!r} is not on the same content-stream line as {main!r}; got {hits}"
        )


async def _entry_headers(md):
    """(text before the date, date) for every entry header, as the renderer tags them."""
    from playwright.async_api import async_playwright
    from test_inline_formatting import _render_markdown

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await _render_markdown(page, md)
            pairs = await page.evaluate("""() =>
                [...document.querySelectorAll('.pagedjs_page p.entry-header')].map(p => [
                    p.querySelector('.entry-main').textContent.replace(/\\s+/g, ' ').trim(),
                    p.lastElementChild.textContent.replace(/\\s+/g, ' ').trim(),
                ])""")
        finally:
            await page.close()
            await browser.close()
    return [tuple(p) for p in pairs]
