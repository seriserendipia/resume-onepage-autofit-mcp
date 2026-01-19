import asyncio
from playwright.async_api import async_playwright

async def debug_frontend():
    async with async_playwright() as p:
        # Launch browser (headless=True by default, set False if you want to see it)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 1. Subscribe to console logs
        page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda exc: print(f"[Browser Error] {exc}"))

        # 2. Navigate to the local server
        url = "http://localhost:5500/myresumebuilder/outer_resume_display.html"
        print(f"Navigating to {url}...")
        
        try:
            await page.goto(url, wait_until="networkidle")
        except Exception as e:
            print(f"Error navigating: {e}")
            # Fallback for path check
            url_alt = "http://localhost:5500/outer_resume_display.html"
            print(f"Retrying with {url_alt}...")
            await page.goto(url_alt, wait_until="networkidle")

        print("--- Page Loaded ---")

        # 3. Wait to capture async logs (handshake, auto-fit)
        await asyncio.sleep(5)

        # 4. Check specific state in the page
        # Check if controller thinks iframe is ready
        is_ready = await page.evaluate("() => window.resumeController && window.resumeController.isIframeReady")
        print(f"Controller isIframeReady: {is_ready}")

        # Check message queue length
        queue_len = await page.evaluate("() => window.resumeController && window.resumeController.messageQueue.length")
        print(f"Controller Message Queue Length: {queue_len}")
        
        # 5. Access the iframe and check its state
        # Note: Accessing cross-frame content might be restricted if protocols differ, 
        # but here both are localhost.
        frames = page.frames
        print(f"Total frames: {len(frames)}")
        
        if len(frames) > 1:
            resume_frame = frames[1] # Assuming 2nd frame is the iframe
            # Verify simple viewer state
            try:
                sv_exists = await resume_frame.evaluate("() => !!window.simpleViewer")
                print(f"Iframe SimpleViewer Exists: {sv_exists}")
                
                if sv_exists:
                    auto_fit_res = await resume_frame.evaluate("() => window.autoFitResult")
                    print(f"AutoFit Result: {auto_fit_res}")
            except Exception as e:
                print(f"Error accessing iframe context: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_frontend())
