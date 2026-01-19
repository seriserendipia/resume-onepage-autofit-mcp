import asyncio
from playwright.async_api import async_playwright

async def verify_config_updates():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Create a new context to ensure no previous state, but we also want to explicitly clear storage
        context = await browser.new_context()
        page = await context.new_page()

        # Subscribe to console
        page.on("console", lambda msg: print(f"[Console] {msg.type}: {msg.text}"))

        # Navigate
        url = "http://localhost:5500/myresumebuilder/outer_resume_display.html"
        print(f"Navigating to {url}...")
        try:
            # We might need to handle the case where it redirects or similar
            response = await page.goto(url, wait_until="networkidle")
            if not response.ok:
                print(f"Failed to load page: {response.status}")
        except Exception as e:
             # Fallback
            url_alt = "http://localhost:5500/outer_resume_display.html"
            print(f"Retrying with {url_alt}...")
            await page.goto(url_alt, wait_until="networkidle")

        # Clear localStorage and reload to ensure defaults are applied
        print("Clearing localStorage and reloading...")
        await page.evaluate("localStorage.clear()")
        await page.reload(wait_until="networkidle")

        print("--- Verifying Config Values ---")
        
        # 1. Verify ResumeConfig.defaultStyles object
        default_styles = await page.evaluate("window.ResumeConfig.defaultStyles")
        print(f"Default Styles: {default_styles}")
        
        expected_styles = {
            "fontSize": 9,
            "headingScale": 1.7,
            "lineHeight": 1.45,
            "margin": 7,
            "titleHrMargin": 0,
            "bodyMargin": 0.5,
            "ulMargin": 0,
            "strongParagraphMargin": 0.2
        }

        all_styles_match = True
        for key, expected_val in expected_styles.items():
            actual_val = default_styles.get(key)
            if actual_val != expected_val:
                print(f"❌ Mismatch for {key}: Expected {expected_val}, got {actual_val}")
                all_styles_match = False
            else:
                print(f"✅ {key} matches {expected_val}")

        if all_styles_match:
            print("✅ All default styles match configuration.")
        else:
            print("❌ Some default styles do not match.")

        # 2. Verify Slider Elements (attributes and current value)
        print("\n--- Verifying Slider Elements ---")
        slider_checks = [
            {"id": "fontSlider", "min": "9", "max": "13", "val": "9"},
            {"id": "headingSlider", "min": "1", "max": "1.7", "val": "1.7"},
            {"id": "lineHeightSlider", "min": "1", "max": "1.7", "val": "1.45"},
            {"id": "marginSlider", "min": "7", "max": "21", "val": "7"},
            {"id": "titleHrMarginSlider", "min": "0", "max": "0.7", "val": "0"},
            {"id": "bodyMarginSlider", "min": "0", "max": "0.5", "val": "0.5"},
            {"id": "ulMarginSlider", "min": "0", "max": "0.5", "val": "0"},
            {"id": "strongParagraphMarginSlider", "min": "0", "max": "0.2", "val": "0.2"},
        ]

        all_sliders_match = True
        for check in slider_checks:
            sid = check["id"]
            # Wait for element to exist (it's inside sidebar iframe usually, or directly in outer? 
            # Looking at file structure, `sidebar.html` is likely loaded into `outer_resume_display.html` via iframe or fetch?
            # Wait, `outer_resume_display.html` has `sidebar-container`. `sidebar.html` might be fetched and injected.
            # Let's check where the sliders are.
            # Based on previous context, `outer_resume_display.html` includes `sidebar.html` content or `sidebar.js` creates them?
            # `sidebar.html` seems to be in `frontend/` but `myresumebuilder` has `outer_resume_display.html`.
            # Let's assume they are in the DOM of the main page or an iframe.
            
            # Let's try to find them in main page first
            slider = page.locator(f"#{sid}")
            count = await slider.count()
            
            if count == 0:
                print(f"⚠️ Slider {sid} not found in main page. Checking frames...")
                found_in_frame = False
                for frame in page.frames:
                    f_slider = frame.locator(f"#{sid}")
                    if await f_slider.count() > 0:
                        slider = f_slider
                        found_in_frame = True
                        break
                if not found_in_frame:
                    print(f"❌ Slider {sid} not found anywhere.")
                    all_sliders_match = False
                    continue

            # Check attributes
            # Try getting property first, as it reflects the current effective value
            min_val = await slider.evaluate("el => el.min")
            max_val = await slider.evaluate("el => el.max")
            # For value, input_value() is good
            curr_val = await slider.input_value()
            
            # Debug if missing
            if not min_val or not max_val:
                html = await slider.evaluate("el => el.outerHTML")
                print(f"DEBUG: Slider {sid} HTML: {html}")

            # Normalize for float comparison strings
            def is_close(a, b):
                try:
                    return abs(float(a) - float(b)) < 0.001
                except:
                    return str(a) == str(b)

            if is_close(min_val, check["min"]) and is_close(max_val, check["max"]) and is_close(curr_val, check["val"]):
                print(f"✅ Slider {sid}: min={min_val}, max={max_val}, value={curr_val}")
            else:
                print(f"❌ Slider {sid} Mismatch:")
                print(f"   Expected: min={check['min']}, max={check['max']}, value={check['val']}")
                print(f"   Got:      min={min_val}, max={max_val}, value={curr_val}")
                all_sliders_match = False

        if all_sliders_match:
            print("✅ All sliders match configuration.")
        else:
            print("❌ Some sliders do not match.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_config_updates())
