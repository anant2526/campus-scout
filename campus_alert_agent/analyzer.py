"""Analysis module using Gemini AI for campus_alert_agent."""
import json
import logging
from google import genai
from google.genai import types
import config

client = genai.Client(api_key=config.GEMINI_API_KEY)

def analyze_content(url: str, text: str) -> dict:
    """Analyze text content from a URL using Gemini to check for campus program mentions."""
    try:
        text = text[:config.MAX_TEXT_CHARS]
        prompt = f"""You are a precise web content analyzer. Your only job is to detect whether a webpage mentions the Anthropic Claude Campus Program, a student program, university partnership, academic fellowship, or any student or intern opportunity related to Claude or Anthropic.

Analyze this webpage content from {url}.

Content:
{text}

Reply ONLY with a valid JSON object. No explanation. No markdown. No code fences. Just the raw JSON.
Use exactly this structure:
{{
  "detected": true or false,
  "confidence": "high" or "medium" or "low",
  "summary": "one sentence summary if detected, otherwise null",
  "relevant_excerpt": "the most relevant quote from the text if detected, otherwise null"
}}"""

        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=400,
            )
        )

        raw = response.text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)

        if "detected" not in parsed:
            raise ValueError("Missing detected key")

        return parsed

    except Exception as e:
        logging.error(f"Error analyzing content for {url}: {e}")
        return {
            "detected": False,
            "confidence": "low",
            "summary": None,
            "relevant_excerpt": None
        }