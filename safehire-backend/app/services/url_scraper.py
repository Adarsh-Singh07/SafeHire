import httpx
from bs4 import BeautifulSoup

async def scrape_job_description(url: str) -> str:
    """
    Fetches raw HTML from a job board URL and extracts clean readable text 
    representing the job description.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0, follow_redirects=True)
            if response.status_code != 200:
                raise Exception(f"HTTP request returned status code {response.status_code}")
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Decompose common structural blocks that don't contain description text
            for element in soup(["script", "style", "header", "footer", "nav", "aside", "form"]):
                element.decompose()
                
            # Extract plain text
            text = soup.get_text(separator=" ")
            
            # Clean and join white space
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = " ".join(chunk for chunk in chunks if chunk)
            
            # Bound input size to fit LLM window sizes cleanly
            return clean_text[:4000].strip()
            
    except Exception as e:
        raise Exception(f"Failed to scrape webpage: {str(e)}")
