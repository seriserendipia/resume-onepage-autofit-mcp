"""
One-off visual check (not picked up by pytest — underscore-prefixed).

Renders example_resume.md via the real resume_preview.html pipeline and:
  1. Captures CSS variables actually applied (--body-font-size etc.)
  2. Captures localStorage keys (defaultFontSize, __configRef)
  3. Saves a full-page screenshot + A4 PDF for visual inspection

Run:
  python tests/_visual_check.py
"""
import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright

PROJECT_ROOT = Path(__file__).parent.parent
PREVIEW_HTML = PROJECT_ROOT / "resume_preview.html"
CONTROL_HTML = PROJECT_ROOT / "control_panel.html"
EXAMPLE_MD = PROJECT_ROOT / "example_resume.md"
OUT_DIR = PROJECT_ROOT / "tests" / "screenshots"


async def render_and_capture(
    label: str,
    pre_localstorage: dict | None = None,
    html_path: Path = PREVIEW_HTML,
    inject_markdown: bool = True,
):
    OUT_DIR.mkdir(exist_ok=True)
    markdown = EXAMPLE_MD.read_text(encoding="utf-8")
    html_url = f"file:///{html_path.resolve().as_posix()}"

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 900, "height": 1300})
        page = await context.new_page()

        # If we want to simulate stale localStorage from prior usage, seed it
        # before any script runs.
        if pre_localstorage:
            await page.add_init_script(
                "Object.entries(%s).forEach(([k,v]) => localStorage.setItem(k, v));"
                % json.dumps(pre_localstorage)
            )

        await page.goto(html_url, wait_until="networkidle")
        if inject_markdown:
            try:
                await page.wait_for_function("() => window.isRendererReady", timeout=5000)
            except Exception:
                pass

            # ACK + inject content (same handshake the renderer expects)
            await page.evaluate("window.postMessage({ type: 'ACK' }, '*')")
            await page.evaluate(
                """(md) => {
                    window.postMessage({ type: 'SET_CONTENT', payload: { markdown: md } }, '*');
                }""",
                markdown,
            )

            try:
                await page.wait_for_selector("body.render-complete", timeout=20000)
            except Exception as e:
                print(f"[{label}] warning: render-complete not observed: {e}", file=sys.stderr)

        await page.wait_for_timeout(1200)  # let autofit / slider init settle

        diag = await page.evaluate(
            """() => {
                const root = document.documentElement;
                const cs = getComputedStyle(root);
                const ls = {};
                for (const k of [
                  'defaultFontSize', 'defaultFontSize__configRef',
                  'defaultHeadingScale', 'defaultLineHeight',
                  'defaultMargin', 'defaultBodyMargin'
                ]) {
                  ls[k] = localStorage.getItem(k);
                }
                return {
                    cssVars: {
                        bodyFontSize: cs.getPropertyValue('--body-font-size').trim(),
                        headingScale: cs.getPropertyValue('--heading-scale').trim(),
                        lineHeight:   cs.getPropertyValue('--line-height').trim(),
                        pageMargin:   cs.getPropertyValue('--page-margin').trim(),
                    },
                    configDefault: window.ResumeConfig?.defaultStyles ?? null,
                    localStorage: ls,
                    pageCount: document.querySelectorAll('.pagedjs_page').length,
                };
            }"""
        )

        png = OUT_DIR / f"visual_{label}.png"
        pdf = OUT_DIR / f"visual_{label}.pdf"

        await page.screenshot(path=str(png), full_page=True)
        await page.pdf(
            path=str(pdf),
            format="A4",
            print_background=True,
            margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"},
        )

        await context.close()
        await browser.close()

        return diag, png, pdf


async def main():
    print("=" * 70)
    print("Scenario A: fresh browser (no prior localStorage)")
    print("=" * 70)
    diag_a, png_a, pdf_a = await render_and_capture("fresh")
    print(json.dumps(diag_a, indent=2, ensure_ascii=False))
    print(f"  PNG: {png_a}")
    print(f"  PDF: {pdf_a}")

    print()
    print("=" * 70)
    print("Scenario B: control_panel.html, stale localStorage (defaultFontSize=9,")
    print("            __configRef=9). sliderController.syncWithConfigDefault should")
    print("            overwrite both to 9.5 because config default has changed.")
    print("=" * 70)
    stale = {"defaultFontSize": "9", "defaultFontSize__configRef": "9"}
    diag_b, png_b, pdf_b = await render_and_capture(
        "control_panel_stale",
        pre_localstorage=stale,
        html_path=CONTROL_HTML,
        inject_markdown=False,  # control panel doesn't take SET_CONTENT directly
    )
    print(json.dumps(diag_b, indent=2, ensure_ascii=False))
    print(f"  PNG: {png_b}")

    # Summary check
    print()
    print("=" * 70)
    print("EXPECTATIONS")
    print("=" * 70)
    fs_a = diag_a["cssVars"]["bodyFontSize"]
    fs_b = diag_b["cssVars"]["bodyFontSize"]
    ls_a = diag_a["localStorage"]["defaultFontSize"]
    ls_b = diag_b["localStorage"]["defaultFontSize"]
    cr_a = diag_a["localStorage"]["defaultFontSize__configRef"]
    cr_b = diag_b["localStorage"]["defaultFontSize__configRef"]
    print(f"  MCP preview (fresh)        --body-font-size = {fs_a:<8} (expect 9.5pt)")
    print(f"  Control panel (stale LS)   --body-font-size = {fs_b:<8} (expect 9.5pt)")
    print(f"  MCP preview     localStorage defaultFontSize = {ls_a}        (expect null — no slider runs)")
    print(f"  Control panel   localStorage defaultFontSize = {ls_b}        (expect '9.5' — sync overwrites stale '9')")
    print(f"  MCP preview     __configRef                  = {cr_a}        (expect null)")
    print(f"  Control panel   __configRef                  = {cr_b}        (expect '9.5' — was '9')")


if __name__ == "__main__":
    asyncio.run(main())
