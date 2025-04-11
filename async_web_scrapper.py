import asyncio
import aiohttp
import time
from bs4 import BeautifulSoup
import argparse
from urllib.parse import urlparse
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# Rich console for prettier output
console = Console()

async def fetch_url(session, url, timeout=30):
    """Fetch a URL asynchronously and return the HTML content."""
    try:
        async with session.get(url, timeout=timeout) as response:
            if response.status == 200:
                return await response.text()
            else:
                console.print(f"[bold red]Error fetching {url}:[/bold red] Status {response.status}")
                return None
    except Exception as e:
        console.print(f"[bold red]Error fetching {url}:[/bold red] {str(e)}")
        return None

async def extract_page_info(session, url, progress=None, task_id=None):
    """Extract title, description, and links from a webpage."""
    html = await fetch_url(session, url)
    if not html:
        if progress and task_id:
            progress.update(task_id, advance=1)
        return {
            'url': url,
            'title': None,
            'description': None,
            'links': []
        }
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract title
    title = soup.title.text.strip() if soup.title else 'No title'
    
    # Extract meta description
    description_tag = soup.find('meta', attrs={'name': 'description'})
    description = description_tag.get('content', '').strip() if description_tag else 'No description'
    
    # Extract links
    links = []
    base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        # Handle relative URLs
        if href.startswith('/'):
            href = base_url + href
        if href.startswith(('http://', 'https://')):
            links.append(href)
    
    if progress and task_id:
        progress.update(task_id, advance=1)
    
    return {
        'url': url,
        'title': title,
        'description': description,
        'links': links[:5]  # Limit to 5 links for brevity
    }

async def process_urls(urls, max_concurrent=5):
    """Process multiple URLs concurrently with a limit."""
    connector = aiohttp.TCPConnector(limit=max_concurrent)
    async with aiohttp.ClientSession(connector=connector) as session:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task_id = progress.add_task("[green]Scraping websites...", total=len(urls))
            
            tasks = [extract_page_info(session, url, progress, task_id) for url in urls]
            results = await asyncio.gather(*tasks)
            
            return results

def display_results(results):
    """Display the results in a nice format."""
    for result in results:
        if result['title']:
            console.print(f"\n[bold cyan]URL:[/bold cyan] {result['url']}")
            console.print(f"[bold green]Title:[/bold green] {result['title']}")
            console.print(f"[bold yellow]Description:[/bold yellow] {result['description'][:100]}...")
            
            if result['links']:
                console.print("[bold magenta]Top Links:[/bold magenta]")
                for i, link in enumerate(result['links'], 1):
                    console.print(f"  {i}. {link}")
            console.print("---")

async def main():
    parser = argparse.ArgumentParser(description='Async Web Scraper')
    parser.add_argument('urls', nargs='*', help='URLs to scrape (space-separated)')
    parser.add_argument('--file', '-f', help='File containing URLs (one per line)')
    parser.add_argument('--concurrent', '-c', type=int, default=5, help='Maximum concurrent requests')
    
    args = parser.parse_args()
    
    urls = args.urls
    if args.file:
        try:
            with open(args.file, 'r') as f:
                file_urls = [line.strip() for line in f if line.strip()]
                urls.extend(file_urls)
        except Exception as e:
            console.print(f"[bold red]Error reading file:[/bold red] {str(e)}")
    
    if not urls:
        # Default URLs if none provided
        urls = [
            'https://python.org',
            'https://docs.python.org/3/library/asyncio.html',
            'https://realpython.com/async-io-python/',
            'https://en.wikipedia.org/wiki/Python_(programming_language)',
            'https://github.com/python/cpython'
        ]
    
    console.print(f"[bold blue]Starting async web scraper with {len(urls)} URLs[/bold blue]")
    console.print(f"[bold blue]Maximum concurrent requests: {args.concurrent}[/bold blue]")
    
    start_time = time.time()
    results = await process_urls(urls, max_concurrent=args.concurrent)
    end_time = time.time()
    
    console.print(f"\n[bold green]Completed in {end_time - start_time:.2f} seconds[/bold green]")
    display_results(results)

if __name__ == "__main__":
    asyncio.run(main())