import asyncio
from playwright.async_api import async_playwright
import json

async def verify_config():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        url = "http://localhost:5500/myresumebuilder/outer_resume_display.html"
        print(f"Navigating to {url}...")
        try:
            await page.goto(url, wait_until="networkidle")
        except Exception:
             url = "http://localhost:5500/outer_resume_display.html" # fallback
             await page.goto(url, wait_until="networkidle")
        
        # 1. Check Window.ResumeConfig
        print("Checking ResumeConfig...")
        config = await page.evaluate("() => window.ResumeConfig")
        defaults = config['defaultStyles']
        
        expected_defaults = {
            'fontSize': 9,
            'margin': 7,
            'headingScale': 1.7,
            'lineHeight': 1.45,
            'titleHrMargin': 0,
            'bodyMargin': 0.5,
            'ulMargin': 0,
            'strongParagraphMargin': 0.2
        }

        all_passed = True
        for key, expected in expected_defaults.items():
            actual = defaults.get(key)
            if actual != expected:
                print(f"❌ Default Mismatch: {key} - Expected {expected}, Got {actual}")
                all_passed = False
            else:
                print(f"✅ Default Verified: {key} = {expected}")

        # 2. Check Sliders Min/Max in DOM
        print("\nChecking Slider Attributes in DOM...")
        sliders_to_check = [
            {'id': 'fontSlider', 'max': '13'},
            {'id': 'headingSlider', 'max': '1.7'},
            {'id': 'marginSlider', 'max': '21', 'min': '7'},
            {'id': 'titleHrMarginSlider', 'max': '0.7'},
        ]
        
        for item in sliders_to_check:
            el_id = item['id']
            el = await page.query_selector(f"#{el_id}")
            if not el:
                print(f"❌ Slider not found: {el_id}")
                all_passed = False
                continue
            
            for attr, val in item.items():
                if attr == 'id': continue
                actual_val = await page.evaluate(f"el => el.getAttribute('{attr}')", el)
                if str(actual_val) != str(val):
                    print(f"❌ Slider {el_id} {attr} Mismatch: Expected {val}, Got {actual_val}")
                    all_passed = False
                else:
                    print(f"✅ Slider {el_id} {attr} Verified: {val}")

        if all_passed:
            print("\n🎉 All Configuration Verifications Passed!")
        else:
            print("\n⚠️ Some configurations did not match.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_config())
