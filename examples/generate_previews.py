"""Generate preview screenshots of all example HTML resumes using Playwright."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

EXAMPLES_DIR = Path(__file__).parent
EXAMPLES = [
    "software-engineer",
    "executive",
    "creative-designer",
    "academic-researcher",
    "new-graduate",
    "data-scientist",
]

async def capture_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for name in EXAMPLES:
            html_path = EXAMPLES_DIR / name / "output" / "html" / "index.html"
            if not html_path.exists():
                print(f"  SKIP {name} (no HTML output)")
                continue
            page = await browser.new_page(viewport={"width": 1200, "height": 900})
            await page.goto(html_path.as_uri())
            # Wait for rendering
            await page.wait_for_timeout(500)
            screenshot_path = EXAMPLES_DIR / "previews" / f"{name}.png"
            screenshot_path.parent.mkdir(exist_ok=True)
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"  OK {name} -> {screenshot_path.name}")
            await page.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_screenshots())
