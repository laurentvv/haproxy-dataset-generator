import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig

async def debug_crawl():
    url = "https://docs.haproxy.org/3.2/configuration.html"
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

            # Look for a specific technical definition
            # The definition of maxconn usually starts with "**[maxconn]..."
            search_term = "**[maxconn]"
            if search_term in md:
                print(f"\n--- FOUND '{search_term}' ---")
                # Find all occurrences and print the one that looks like a definition (followed by <number>)
                start = 0
                while True:
                    idx = md.find(search_term, start)
                    if idx == -1: break
                    snippet = md[idx:idx+300]
                    if "<number>" in snippet or "<conns>" in snippet:
                        print(f"\nDEFINITION FOUND at index {idx}:")
                        print(snippet)
                    start = idx + 1
            else:
                print(f"\n--- '{search_term}' NOT FOUND IN MARKDOWN ---")
                # Print some characters from the middle to see what's there
                print("\n--- SAMPLE FROM MIDDLE (index 500,000) ---")
                print(md[500000:501000])
        else:
            print(f"ERROR: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(debug_crawl())
