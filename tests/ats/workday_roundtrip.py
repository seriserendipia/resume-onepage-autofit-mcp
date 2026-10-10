"""Upload a resume PDF to a Workday application draft and read back what Workday parsed.

This is the ground-truth half of the ATS parse check (see tests/test_pdf_stream_order.py).
It drives a Chrome you already logged into, over CDP, and NEVER clicks Submit.

Setup (once per run):
  1. Start Chrome with --remote-debugging-port=9222 and log into a Workday
     career site you do not intend to apply to.
  2. Open a draft application and stop on step 1 "Autofill with Resume".
  3. Fill "My Information" once by hand and save it. Workday keeps those values
     across uploads, so the script only has to click through that page.

Usage:
  python tests/ats/workday_roundtrip.py resume.pdf [--out parsed.json] [--cdp http://127.0.0.1:9222]

Known behaviour of the draft (measured 2026-10-02 on one tenant):
  - parsing is deterministic and a re-upload overwrites My Experience;
  - a parse can flip the Country on My Information; this script stops rather
    than guess, because leaving that page unsaved raises "Discard Application?";
  - the tenant decides which fields exist (some have no location/description).
"""
import argparse
import json
import sys

from playwright.sync_api import sync_playwright

READ_EXPERIENCE = """() => {
  const out = [];
  for (const g of document.querySelectorAll('[role=group][aria-labelledby]')) {
    const title = document.getElementById(g.getAttribute('aria-labelledby'))?.innerText || '';
    if (!/^(Work Experience|Education) \\d+$/.test(title)) continue;
    const entry = {_: title};
    for (const ff of g.querySelectorAll('[data-automation-id^=formField-]')) {
      const key = ff.getAttribute('data-automation-id').replace('formField-', '');
      const inputs = [...ff.querySelectorAll('input:not([type=hidden]),textarea')];
      const dateParts = [...ff.querySelectorAll('[data-automation-id^=dateSection][data-automation-id$=input]')];
      if (inputs.length && inputs[0].type === 'checkbox') entry[key] = inputs[0].checked;
      else if (dateParts.length) entry[key] = dateParts.map(e => e.value).filter(Boolean).join('/');
      else if (inputs.length) entry[key] = inputs.map(e => e.value).join(' | ');
      else entry[key] = ff.querySelector('button')?.innerText || '';
    }
    out.push(entry);
  }
  return out;
}"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pdf")
    ap.add_argument("--out")
    ap.add_argument("--cdp", default="http://127.0.0.1:9222")
    args = ap.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(args.cdp)
        pages = [pg for ctx in browser.contexts for pg in ctx.pages if "myworkdayjobs" in pg.url]
        if not pages:
            sys.exit("No Workday tab found. Open the draft on 'Autofill with Resume' first.")
        page = pages[0]

        def step():
            return page.locator("[data-automation-id=progressBarActiveStep]").inner_text().replace("\n", " ")

        def click_footer(which):
            page.locator(f"[data-automation-id=pageFooter{which}Button]").click()
            page.wait_for_timeout(7000)

        if "step 1" not in step():
            sys.exit(f"Start on step 1 (Autofill with Resume); the draft is on: {step()}")

        page.locator("input[type=file]").set_input_files(args.pdf)
        page.get_by_text("Successfully Uploaded!").wait_for(timeout=30000)
        click_footer("Next")

        country = page.locator("[data-automation-id='formField-country'] button").inner_text()
        click_footer("Next")
        if "step 3" not in step():
            errors = page.locator("[data-automation-id=errorMessage]").all_inner_texts()
            sys.exit(f"Could not leave My Information (country now {country!r}): {errors}. "
                     "Fix and save that page by hand, then go Back to step 1.")

        result = {"pdf": args.pdf, "tenant": page.url.split("/")[2], "experience": page.evaluate(READ_EXPERIENCE)}

        click_footer("Back")
        click_footer("Back")

    for entry in result["experience"]:
        fields = {k: v for k, v in entry.items() if k != "_"}
        print(f"{entry['_']:18}", " | ".join(f"{k}={v}" for k, v in fields.items()))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
