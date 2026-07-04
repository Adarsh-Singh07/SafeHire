import httpx
from bs4 import BeautifulSoup
from typing import Optional, List
from app.models.schemas import ScrapeResult

class ScraperError(Exception):
    pass

async def scrape_job_url(url: str) -> ScrapeResult:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract title
            title = soup.title.string.strip() if soup.title and soup.title.string else "Unknown Title"
            
            # Extract description from meta tags or default
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and "content" in meta_desc.attrs:
                company_hint = meta_desc["content"][:100]
            else:
                company_hint = None
                
            # Clean paragraph text
            paragraphs = soup.find_all("p")
            raw_description = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            
            # Extract links
            links_found = []
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if href.startswith("http"):
                    links_found.append(href)
            
            # Deduplicate links
            links_found = list(set(links_found))
            
            return ScrapeResult(
                title=title,
                company=company_hint,
                raw_description=raw_description,
                links_found=links_found
            )
            
    except httpx.HTTPStatusError as e:
        raise ScraperError(f"HTTP error occurred: {e}")
    except httpx.RequestError as e:
        raise ScraperError(f"Request error occurred: {e}")
    except Exception as e:
        raise ScraperError(f"An unexpected error occurred: {e}")
