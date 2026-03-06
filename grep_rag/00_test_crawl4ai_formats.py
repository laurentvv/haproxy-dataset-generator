import asyncio
import os

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

TEST_URL = "https://docs.haproxy.org/3.2/configuration.html"

async def test_formats():
    print(f"Testing formats for: {TEST_URL}")

    # Configuration basic
    browser_config = BrowserConfig(headless=True)

    # Test 1: Default Markdown
    run_config_default = CrawlerRunConfig(
        cache_mode="bypass",
        exclude_external_links=True,
        remove_overlay_elements=True,
    )

    # Test 2: Filtered Markdown (PruningContentFilter)
    run_config_filtered = CrawlerRunConfig(
        cache_mode="bypass",
        exclude_external_links=True,
        remove_overlay_elements=True,
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=0.48, min_word_threshold=5),
            options={"ignore_links": False}
        )
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        print("\n--- Running Default Crawl ---")
        result_default = await crawler.arun(url=TEST_URL, config=run_config_default)

        print("\n--- Running Filtered Crawl ---")
        result_filtered = await crawler.arun(url=TEST_URL, config=run_config_filtered)

    formats = {}

    if result_default.success:
        formats["raw_markdown"] = result_default.markdown
        # result.markdown might be an object or string depending on version
        if hasattr(result_default.markdown, 'raw_markdown'):
             formats["raw_markdown"] = result_default.markdown.raw_markdown

    if result_filtered.success:
        if hasattr(result_filtered.markdown, 'fit_markdown'):
            formats["fit_markdown"] = result_filtered.markdown.fit_markdown
        else:
            formats["fit_markdown"] = result_filtered.markdown # fallback

    for name, content in formats.items():
        if content:
            print(f"\n{'='*60}")
            print(f"FORMAT : {name} ({len(content)} chars)")
            print(f"{'='*60}")
            # Print a snippet that likely contains a configuration parameter
            print(content[:2000])
            print("\n...")

            # Save samples for manual inspection if needed
            os.makedirs("grep_rag/samples", exist_ok=True)
            with open(f"grep_rag/samples/sample_{name}.md", "w", encoding="utf-8") as f:
                f.write(content)

if __name__ == "__main__":
    asyncio.run(test_formats())
