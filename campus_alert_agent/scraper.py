"""Web scraping module for campus_alert_agent."""
import re
import hashlib
import logging
import requests
from bs4 import BeautifulSoup

def scrape_url(url: str) -> dict:
    """Scrape the provided URL and return cleaned text and its SHA-256 hash."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code} for {url}")
            
        soup = BeautifulSoup(response.text, "html.parser")
        
        for tag_name in ['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript']:
            for tag in soup.find_all(tag_name):
                tag.decompose()
        
        text = soup.get_text(separator=" ", strip=True)
        cleaned_text = re.sub(r'\s+', ' ', text).strip()
        content_hash = hashlib.sha256(cleaned_text.encode()).hexdigest()
        
        return {
            "url": url, 
            "text": cleaned_text, 
            "content_hash": content_hash, 
            "success": True, 
            "error": None
        }
        
    except Exception as e:
        logging.error(f"Error scraping {url}: {e}")
        return {
            "url": url, 
            "text": "", 
            "content_hash": "", 
            "success": False, 
            "error": str(e)
        }
