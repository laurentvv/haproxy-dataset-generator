import asyncio
from playwright.async_api import async_playwright

async def verify_chatbot():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Go to the local server
        await page.goto("http://localhost:7862")

        # Wait for the page to load
        await page.wait_for_selector("h1")

        # Take a screenshot
        await page.screenshot(path="verification/agentic_chatbot.png")
        print("Screenshot saved to verification/agentic_chatbot.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_chatbot())
