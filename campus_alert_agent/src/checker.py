"""
Checker module — scrapes URLs and analyzes content via Gemini.

DESIGN: This module combines the original scraper.py and analyzer.py
logic into a single coherent pipeline. The scraping is done with
requests + BeautifulSoup (no browser needed). The analysis uses
Google's Gemini 1.5 Flash via the new google-genai SDK.

Retries are added for transient network/API failures with exponential
backoff. Max 3 attempts per operation.
"""
import re
import json
import time
import hashlib
import logging

import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

import config

# ── Initialize Gemini client ─────────────────────────────────────────────
_client = genai.Client(api_key=config.GEMINI_API_KEY)

# ── Constants ─────────────────────────────────────────────────────────────
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds, doubles each retry


def _retry(func, *args, retries=MAX_RETRIES, **kwargs):
    """
    Generic retry wrapper with exponential backoff.
    Retries on any exception up to `retries` times.
    """
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            wait = BACKOFF_BASE ** attempt
            logging.warning(
                f"Attempt {attempt}/{retries} failed: {e}. "
                f"Retrying in {wait}s..."
            )
            time.sleep(wait)
    raise last_error


# ══════════════════════════════════════════════════════════════════════════
# SCRAPING — preserved from original scraper.py
# ══════════════════════════════════════════════════════════════════════════

def scrape_url(url: str) -> dict:
    """
    Scrape the provided URL and return cleaned text + SHA-256 hash.
    Retries up to 3 times on network failure.
    """
    def _do_scrape():
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code} for {url}")

        soup = BeautifulSoup(response.text, "html.parser")

        # Strip non-content tags
        for tag_name in [
            "script", "style", "nav", "footer",
            "header", "aside", "noscript"
        ]:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        cleaned_text = re.sub(r"\s+", " ", text).strip()
        content_hash = hashlib.sha256(cleaned_text.encode()).hexdigest()

        return {
            "url": url,
            "text": cleaned_text,
            "content_hash": content_hash,
            "success": True,
            "error": None,
        }

    try:
        return _retry(_do_scrape)
    except Exception as e:
        logging.error(f"Error scraping {url} after {MAX_RETRIES} retries: {e}")
        return {
            "url": url,
            "text": "",
            "content_hash": "",
            "success": False,
            "error": str(e),
        }


# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS — preserved from original analyzer.py
# ══════════════════════════════════════════════════════════════════════════

def analyze_content(url: str, text: str) -> dict:
    """
    Analyze text content from a URL using Gemini to check for
    campus program / student opportunity mentions.
    Retries up to 3 times on API failure.
    """
    def _do_analyze():
        truncated = text[: config.MAX_TEXT_CHARS]
        prompt = f"""You are a precise web content analyzer. Your only job is to detect whether a webpage mentions the Anthropic Claude Campus Program, a student program, university partnership, academic fellowship, or any student or intern opportunity related to Claude or Anthropic.

Analyze this webpage content from {url}.

Content:
{truncated}

Reply ONLY with a valid JSON object. No explanation. No markdown. No code fences. Just the raw JSON.
Use exactly this structure:
{{
  "detected": true or false,
  "confidence": "high" or "medium" or "low",
  "summary": "one sentence summary if detected, otherwise null",
  "relevant_excerpt": "the most relevant quote from the text if detected, otherwise null"
}}"""

        response = _client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=400,
            ),
        )

        raw = response.text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)

        if "detected" not in parsed:
            raise ValueError("Missing 'detected' key in Gemini response")

        return parsed

    try:
        return _retry(_do_analyze)
    except Exception as e:
        logging.error(f"Error analyzing content for {url}: {e}")
        return {
            "detected": False,
            "confidence": "low",
            "summary": None,
            "relevant_excerpt": None,
        }
