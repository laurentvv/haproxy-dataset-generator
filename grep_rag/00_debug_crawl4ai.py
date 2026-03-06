import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig

async def debug_crawl():
    url = "https://docs.haproxy.org/3.2/intro.html"
    print(f"DEBUG: Crawling {url}...")

    browser_cfg = BrowserConfig(headless=True)
    run_cfg = CrawlerRunConfig(cache_mode="bypass")

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=run_cfg)

        if result.success:
            md = result.markdown
            if hasattr(md, 'raw_markdown'):
                md = md.raw_markdown

            print(f"\n--- SUCCESS ---")
            print(f"Content Length: {len(md)} chars")
            print("\n--- FIRST 1000 CHARS ---")
            print(md[:1000])

            # Search for a known technical sentence in intro.html
            # Example: "HAProxy is a free, very fast and reliable solution"
            search_term = "HAProxy is a"
            if search_term in md:
                idx = md.find(search_term)
                print(f"\n--- SNIPPET AROUND '{search_term}' ---")
                print(md[idx:idx+500])
            else:
                print(f"\n--- '{search_term}' NOT FOUND IN MARKDOWN ---")
        else:
            print(f"ERROR: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(debug_crawl())
