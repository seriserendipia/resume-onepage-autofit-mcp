import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# Add the parent directory to Python path so we can import mcp_server's pieces if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Or better yet, just write a standalone quick playwright script to reproduce it
async def run_reproduction():
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
