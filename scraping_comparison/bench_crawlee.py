import asyncio
import json
import time
from pathlib import Path

from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

URLS = [
    'https://docs.haproxy.org/3.2/intro.html',
    'https://docs.haproxy.org/3.2/configuration.html',
    'https://docs.haproxy.org/3.2/management.html',
]

OUTPUT_DIR = Path('scraping_comparison/data')
OUTPUT_FILE = OUTPUT_DIR / 'results_crawlee.json'


async def main():
    print('--- Starting Crawlee Benchmark ---')
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    crawler = PlaywrightCrawler(
        max_requests_per_crawl=10,
        headless=True,
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext):
        url = context.request.url
        print(f'Scraping {url}...')

        page_start = time.time()
        # Wait for content to load
        await context.page.wait_for_load_state('networkidle')

        # Extract content
        content_html = await context.page.content()
        text_only = await context.page.evaluate('() => document.body.innerText')

        page_end = time.time()

        results.append(
            {
                'url': url,
                'success': True,
                'time_seconds': page_end - page_start,
                'html_length': len(content_html),
                'text_length': len(text_only),
                'content': content_html,
                'text': text_only,
            }
        )
        print(f'Successfully scraped {url} in {page_end - page_start:.2f}s')

    start_time = time.time()
    await crawler.run(URLS)
    total_time = time.time() - start_time

    output_data = {'tool': 'crawlee', 'total_time_seconds': total_time, 'results': results}

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f'--- Crawlee Benchmark Finished in {total_time:.2f}s ---')


if __name__ == '__main__':
    asyncio.run(main())
