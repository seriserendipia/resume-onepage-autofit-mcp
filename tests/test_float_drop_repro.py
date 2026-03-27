"""Test: Float Drop Layout Validation

Verifies that the MCP renderer detects when long titles cause
right-floated dates to wrap to the next line (Float Drop).
"""
import asyncio
import os
import pytest
from pathlib import Path
from playwright.async_api import async_playwright
from resume_renderer import ResumeRenderer


@pytest.mark.asyncio
async def test_float_drop_detected_by_renderer():
    """Long title should trigger layout_warning from ResumeRenderer."""
    renderer = ResumeRenderer()
    test_md = (Path(__file__).parent / "float_drop_test.md").read_text(encoding="utf-8")
    result = await renderer.render_resume_pdf(test_md)
    await renderer.stop()

    assert "layout_warnings" in result, "Result should contain layout_warnings key"
    assert len(result["layout_warnings"]) > 0, "Should detect at least one float drop"
    assert result["status"] == "layout_warning", f"Status should be layout_warning, got {result['status']}"


@pytest.mark.asyncio
async def test_no_float_drop_on_short_title():
    """Normal-length title should NOT trigger layout warnings."""
    short_md = """# John Doe
San Francisco, CA | john@email.com | [LinkedIn](https://linkedin.com/in/johndoe)

## Experience

**Google** · SWE *2022 – Present*

- Built scalable backend services serving 10M+ users
- Reduced API latency by 40% through caching optimization

**Meta** · Software Engineer *2020 – 2022*

- Developed real-time data pipeline processing 1TB daily
- Mentored 3 junior engineers on system design best practices

## Education

**Stanford University** · M.S. Computer Science *2018 – 2020*

## Skills
- Python, Java, Go, SQL, Kubernetes, AWS
"""
    renderer = ResumeRenderer()
    result = await renderer.render_resume_pdf(short_md)
    await renderer.stop()

    warnings = result.get("layout_warnings", [])
    assert len(warnings) == 0, f"Short title should not trigger warnings, got: {warnings}"


async def run_reproduction():
    """Standalone reproduction script (run directly with python)."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Load the preview HTML
        base_dir = Path(__file__).parent.parent
        html_path = base_dir / "resume_preview.html"
        await page.goto(f"file:///{html_path.as_posix()}", wait_until="networkidle")
        
        # Wait for Renderer
        try:
            await page.wait_for_function("() => window.isRendererReady", timeout=5000)
        except:
            print("Renderer not ready, proceeding anyway")
            
        await page.evaluate("window.postMessage({ type: 'ACK' }, '*')")
        
        # Read the test markdown
        with open(Path(__file__).parent / "float_drop_test.md", "r", encoding="utf-8") as f:
            md_content = f.read()
            
        # Inject markdown
        await page.evaluate(f'''(md) => {{
            window.postMessage({{
                type: 'SET_CONTENT',
                payload: {{ markdown: md }}
            }}, '*');
        }}''', md_content)
        
        print("Waiting for page render-complete...")
        await page.wait_for_selector('body.render-complete', timeout=15000)
        
        # Wait a bit just in case
        await page.wait_for_timeout(1000)
        
        # Take a screenshot to visually confirm
        screenshot_path = Path(__file__).parent / "screenshots" / "float_drop_repro.png"
        os.makedirs(screenshot_path.parent, exist_ok=True)
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"Screenshot saved to {screenshot_path}")
        
        # Now run the detection logic
        print("Executing layout validation check...")
        warnings = await page.evaluate('''() => {
            const warnings = [];
            const titleParagraphs = document.querySelectorAll('.pagedjs_page p');
            
            titleParagraphs.forEach(p => {
                const strongItem = p.querySelector('strong:first-of-type');
                const emItem = p.querySelector('em:last-of-type');
                
                if (strongItem && emItem) {
                    const strongBottom = strongItem.getBoundingClientRect().bottom;
                    const emBottom = emItem.getBoundingClientRect().bottom;
                    
                    const diff = Math.abs(strongBottom - emBottom);
                    if (diff > 5) {
                        const badText = p.innerText.replace(/\\n/g, ' ').substring(0, 50);
                        warnings.push(`Float drop detected (Diff: ${diff}px): "${badText}..."`);
                    }
                }
            });
            return warnings;
        }''')
        
        if warnings:
            print("\\n[TEST SUCCESS] Issue successfully reproduced and caught by evaluation!")
            for w in warnings:
                print(f" - {w}")
        else:
            print("\\n[TEST FAILED] No float drop detected.")
            
        await browser.close()
        
if __name__ == "__main__":
    asyncio.run(run_reproduction())
