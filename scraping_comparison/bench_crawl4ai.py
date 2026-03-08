import asyncio
import json
import time
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

URLS = [
    'https://docs.haproxy.org/3.2/intro.html',
    'https://docs.haproxy.org/3.2/configuration.html',
    'https://docs.haproxy.org/3.2/management.html',
]

OUTPUT_DIR = Path('scraping_comparison/data')
OUTPUT_FILE = OUTPUT_DIR / 'results_crawl4ai.json'


async def main():
    print('--- Starting Crawl4AI Benchmark ---')
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS, excluded_tags=['nav', 'footer', 'header']
    )

    results = []
    start_time = time.time()

    async with AsyncWebCrawler(config=browser_config) as crawler:
        for url in URLS:
            print(f'Scraping {url}...')
            page_start = time.time()
            result = await crawler.arun(url=url, config=run_config)
            page_end = time.time()

            if result.success:
                results.append(
                    {
                        'url': url,
                        'success': True,
                        'time_seconds': page_end - page_start,
                        'markdown_length': len(result.markdown),
                        'markdown_preview': result.markdown[:500],
                        'content': result.markdown,
                    }
                )
                print(f'Successfully scraped {url} in {page_end - page_start:.2f}s')
            else:
                results.append({'url': url, 'success': False, 'error': result.error_message})
                print(f'Failed to scrape {url}: {result.error_message}')

    total_time = time.time() - start_time

    output_data = {'tool': 'crawl4ai', 'total_time_seconds': total_time, 'results': results}

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f'--- Crawl4AI Benchmark Finished in {total_time:.2f}s ---')


if __name__ == '__main__':
    asyncio.run(main())
