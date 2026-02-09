"""
Tests for inline formatting rendering (bold/strong, italic/em).

Verifies that inline markup like **bold** and *italic* renders properly
within paragraphs — no unwanted line breaks, no display:block overrides.

These tests use Playwright to render actual HTML and check both:
1. CSS computed styles (unit-level)
2. Bounding rect positions (layout-level)
3. Screenshot comparison (visual-level)
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest
from playwright.async_api import async_playwright

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
HTML_PATH = PROJECT_ROOT / "resume_preview.html"

# The exact markdown that triggered the bug report
BUG_REPORT_MARKDOWN = r"""# Mary Lu
Los Angeles, CA | (213) 301-2014 | yihelu@usc.edu | [LinkedIn](https://linkedin.com/in/yihe-lu/) | [GitHub](https://github.com/seriserendipia)
**F-1 OPT (STEM eligible, Valid until 07/2029). No sponsorship required during OPT period.**

## PROFESSIONAL SUMMARY
Data Scientist with a Master's in Analytics and strong expertise in **Product Analytics, Statistical Modeling, and Experimentation**. Proven ability to translate complex data into strategic business recommendations, driving **10% cost reductions** and **20% efficiency gains** for global operations. Skilled in communicating data-driven insights to cross-functional stakeholders.
"""

# A minimal markdown that isolates the inline-bold-in-paragraph pattern
MINIMAL_INLINE_BOLD_MD = r"""# Test Resume

## Summary
This is a paragraph with **inline bold text** inside it and **more bold** here.
"""


async def _render_markdown(page, markdown: str, timeout_ms: int = 15000):
    """Load resume_preview.html and inject markdown, wait for render."""
    html_url = f"file:///{HTML_PATH.resolve().as_posix()}"
    await page.goto(html_url, wait_until="networkidle")

    # Wait for renderer
    try:
        await page.wait_for_function("() => window.isRendererReady", timeout=5000)
    except Exception:
        pass  # proceed anyway

    # ACK handshake
    await page.evaluate("window.postMessage({ type: 'ACK' }, '*')")

    # Inject content
    escaped = markdown.replace('`', '\\`').replace('${', '\\${')
    await page.evaluate(f"""
        window.postMessage({{
            type: 'SET_CONTENT',
            payload: {{ markdown: `{escaped}` }}
        }}, '*');
    """)

    # Wait for paged.js render
    try:
        await page.wait_for_selector('body.render-complete', timeout=timeout_ms)
    except Exception:
        pass


# ===========================================================================
# Test 1: CSS computed style — <strong> inside <p> must NOT be display:block
# ===========================================================================
@pytest.mark.asyncio
async def test_strong_inside_paragraph_not_display_block():
    """
    <strong> elements inside <p> must NOT have display:block.
    display:block forces a line break before and after the element,
    destroying inline flow of text.
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await _render_markdown(page, MINIMAL_INLINE_BOLD_MD)

            results = await page.evaluate("""() => {
                const strongs = document.querySelectorAll('p strong');
                return Array.from(strongs).map(el => {
                    const cs = getComputedStyle(el);
                    return {
                        text: el.textContent,
                        display: cs.display,
                        parentTag: el.parentElement.tagName
                    };
                });
            }""")

            assert len(results) > 0, "Expected at least one <strong> inside <p>"

            for item in results:
                assert item['display'] != 'block', (
                    f"<strong> containing '{item['text']}' has display:block — "
                    f"this causes unwanted line breaks inside paragraphs!"
                )
        finally:
            await page.close()
            await browser.close()


# ===========================================================================
# Test 2: Bounding rect — bold text must be on the same line as surrounding
# ===========================================================================
@pytest.mark.asyncio
async def test_bold_text_same_line_as_surrounding_text():
    """
    If we have: '...expertise in **Product Analytics** ...'
    the bold text and the text before it must share the same vertical line
    (or at least overlap vertically), proving no forced line-break occurred.
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await _render_markdown(page, BUG_REPORT_MARKDOWN)

            result = await page.evaluate("""() => {
                // Find <strong> containing 'Product Analytics'
                const allStrong = Array.from(document.querySelectorAll('strong'));
                const target = allStrong.find(el =>
                    el.textContent.includes('Product Analytics')
                );
                if (!target) return { error: 'Target <strong> not found' };

                const strongRect = target.getBoundingClientRect();

                // Get the previous text node sibling
                const parentP = target.closest('p');
                if (!parentP) return { error: 'No parent <p> found' };

                const prevNode = target.previousSibling;
                if (!prevNode || prevNode.nodeType !== 3) {
                    return { error: 'No preceding text node found' };
                }

                const range = document.createRange();
                const textLen = prevNode.textContent.length;
                range.setStart(prevNode, Math.max(0, textLen - 5));
                range.setEnd(prevNode, textLen);
                const prevRect = range.getBoundingClientRect();

                return {
                    strongTop: strongRect.top,
                    strongBottom: strongRect.bottom,
                    prevTextTop: prevRect.top,
                    prevTextBottom: prevRect.bottom,
                    strongDisplay: getComputedStyle(target).display,
                    strongText: target.textContent.substring(0, 40)
                };
            }""")

            assert 'error' not in result, f"Setup error: {result.get('error')}"

            strong_top = result['strongTop']
            prev_bottom = result['prevTextBottom']
            prev_top = result['prevTextTop']
            strong_bottom = result['strongBottom']

            # They overlap vertically = same line
            vertical_overlap = strong_top < prev_bottom and prev_top < strong_bottom

            assert vertical_overlap, (
                f"Bold text '{result['strongText']}' is NOT on the same line as preceding text! "
                f"Strong rect: top={strong_top}, bottom={strong_bottom}; "
                f"Preceding text rect: top={prev_top}, bottom={prev_bottom}. "
                f"Computed display: {result['strongDisplay']}"
            )
        finally:
            await page.close()
            await browser.close()


# ===========================================================================
# Test 3: Summary paragraph must NOT have excessive line breaks
# ===========================================================================
@pytest.mark.asyncio
async def test_summary_paragraph_no_extra_line_breaks():
    """
    The PROFESSIONAL SUMMARY paragraph has 3 bold segments.
    With display:block bug, each causes 2 extra line breaks (before+after).
    We count estimated visual lines and assert they are reasonable.
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await _render_markdown(page, BUG_REPORT_MARKDOWN)

            result = await page.evaluate("""() => {
                const paragraphs = Array.from(document.querySelectorAll('p'));
                const summaryP = paragraphs.find(p =>
                    p.textContent.includes('10% cost reductions')
                );
                if (!summaryP) return { error: 'Summary paragraph not found' };

                const pRect = summaryP.getBoundingClientRect();
                const lineHeight = parseFloat(getComputedStyle(summaryP).lineHeight);
                const estimatedLines = pRect.height / lineHeight;

                const strongs = Array.from(summaryP.querySelectorAll('strong'));
                const strongInfos = strongs.map(s => ({
                    text: s.textContent.substring(0, 30),
                    display: getComputedStyle(s).display
                }));

                return {
                    paragraphHeight: pRect.height,
                    lineHeight: lineHeight,
                    estimatedLines: estimatedLines,
                    strongCount: strongs.length,
                    strongInfos: strongInfos,
                    textLength: summaryP.textContent.length
                };
            }""")

            assert 'error' not in result, f"Setup error: {result.get('error')}"

            estimated_lines = result['estimatedLines']

            # The summary is ~250 chars. Should be 3-5 lines normally.
            # With display:block bug, it would be 8+ lines.
            assert estimated_lines < 8, (
                f"Summary paragraph has ~{estimated_lines:.1f} estimated visual lines, "
                f"expected < 8. Height={result['paragraphHeight']:.0f}px, "
                f"lineHeight={result['lineHeight']:.1f}px. "
                f"This suggests <strong> is causing unwanted line breaks. "
                f"Strong display values: {result['strongInfos']}"
            )

            for info in result['strongInfos']:
                assert info['display'] != 'block', (
                    f"<strong> '{info['text']}' is display:block in the summary paragraph!"
                )
        finally:
            await page.close()
            await browser.close()


# ===========================================================================
# Test 4: Screenshot-based visual regression test
# ===========================================================================
@pytest.mark.asyncio
async def test_screenshot_inline_bold_no_break():
    """
    Render the bug-report markdown and take a screenshot.
    Serves as a visual regression artifact + verifies summary paragraph
    bounding box height is in expected range.
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1200, "height": 1600})
        try:
            await _render_markdown(page, BUG_REPORT_MARKDOWN)

            screenshot_dir = PROJECT_ROOT / "tests" / "screenshots"
            screenshot_dir.mkdir(exist_ok=True)
            screenshot_path = screenshot_dir / "inline_bold_rendering.png"

            await page.screenshot(path=str(screenshot_path), full_page=True)
            assert screenshot_path.exists(), "Screenshot was not saved"
            assert screenshot_path.stat().st_size > 1000, "Screenshot file is suspiciously small"

            # Also crop just the summary section
            summary_rect = await page.evaluate("""() => {
                const paragraphs = Array.from(document.querySelectorAll('p'));
                const summaryP = paragraphs.find(p =>
                    p.textContent.includes('10% cost reductions')
                );
                if (!summaryP) return null;
                const r = summaryP.getBoundingClientRect();
                return { x: r.x, y: r.y, width: r.width, height: r.height };
            }""")

            if summary_rect:
                cropped_path = screenshot_dir / "summary_section_cropped.png"
                await page.screenshot(path=str(cropped_path), clip=summary_rect)
                print(f"\n  Screenshots saved:")
                print(f"    Full:    {screenshot_path}")
                print(f"    Cropped: {cropped_path}")

        finally:
            await page.close()
            await browser.close()


# ===========================================================================
# Test 5: PDF rendering — generate PDF and verify it was created
# ===========================================================================
@pytest.mark.asyncio
async def test_pdf_visual_verification():
    """
    Generate an actual PDF via Playwright page.pdf().
    The PDF is saved for manual inspection.
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await _render_markdown(page, BUG_REPORT_MARKDOWN)
            await page.wait_for_timeout(1000)

            output_dir = PROJECT_ROOT / "tests" / "screenshots"
            output_dir.mkdir(exist_ok=True)
            pdf_path = output_dir / "test_inline_bold.pdf"

            await page.pdf(
                path=str(pdf_path),
                format='A4',
                print_background=True,
                margin={'top': '0mm', 'bottom': '0mm', 'left': '0mm', 'right': '0mm'}
            )

            assert pdf_path.exists(), "PDF was not generated"
            assert pdf_path.stat().st_size > 1000, "PDF file is suspiciously small"

            metrics = await page.evaluate("""() => {
                const pages = document.querySelectorAll('.pagedjs_page');
                return { pageCount: pages.length };
            }""")

            print(f"\n  PDF saved to: {pdf_path}")
            print(f"  Page count: {metrics.get('pageCount', 'unknown')}")

        finally:
            await page.close()
            await browser.close()


# ===========================================================================
# Test 6: Standalone bold lines should still work properly
# ===========================================================================
@pytest.mark.asyncio
async def test_standalone_bold_paragraph_still_works():
    """
    Paragraphs where bold is the FIRST child (e.g., **Company** · Title)
    should still render without display:block forcing line breaks.
    This ensures the fix doesn't break job-title formatting.
    """
    job_title_md = r"""# Test Resume

## Experience
**Google** · Software Engineer
*2020 - 2023*
- Built scalable distributed systems

**Meta** · Data Scientist
*2018 - 2020*
- Led A/B testing framework development
"""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await _render_markdown(page, job_title_md)

            result = await page.evaluate("""() => {
                const strongs = Array.from(document.querySelectorAll('p > strong:first-child'));
                return strongs.map(s => {
                    const cs = getComputedStyle(s);
                    return {
                        text: s.textContent.substring(0, 30),
                        display: cs.display
                    };
                });
            }""")

            for item in result:
                assert item['display'] != 'block', (
                    f"Standalone bold '{item['text']}' should not be display:block"
                )
        finally:
            await page.close()
            await browser.close()
