"""Shared AI client for AKW framework.

Supports OpenAI, Anthropic, Gemini. Used by relevance.py and categorization.py.

Usage:
    from ai_client import get_ai_client, call_ai, detect_provider, SUPPORTED_MODELS
"""

import json
import logging
import os
import re
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SUPPORTED_MODELS = {
    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1-nano"],
    "anthropic": ["claude-sonnet-4-5-20241022", "claude-haiku-4-5-20251001"],
    "gemini": ["gemini-2.0-flash", "gemini-2.5-flash-preview-05-20", "gemini-2.5-pro-preview-05-06"],
}


def detect_provider(model: str) -> str:
    """Detect provider from model name."""
    if model.startswith("claude"):
        return "anthropic"
    elif model.startswith("gemini"):
        return "gemini"
    else:
        return "openai"


def get_ai_client(model: str) -> tuple[object, str]:
    """Initialize AI client. Returns (client, provider)."""
    provider = detect_provider(model)

    if provider == "anthropic":
        import anthropic
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            log.error("ANTHROPIC_API_KEY not set in .env")
            sys.exit(1)
        return anthropic.Anthropic(api_key=key), provider

    elif provider == "gemini":
        import google.generativeai as genai
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            log.error("GEMINI_API_KEY not set in .env")
            sys.exit(1)
        genai.configure(api_key=key)
        return genai, provider

    else:
        import openai
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            log.error("OPENAI_API_KEY not set in .env")
            sys.exit(1)
        return openai.OpenAI(api_key=key), provider


def call_ai(
    prompt: str, client: object, provider: str, model: str
) -> str:
    """Call AI API and return raw text response."""
    if provider == "openai":
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4000,
        )
        return response.choices[0].message.content

    elif provider == "anthropic":
        response = client.messages.create(
            model=model, max_tokens=4000, temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    elif provider == "gemini":
        import google.generativeai as genai
        gen_model = genai.GenerativeModel(model)
        response = gen_model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1, max_output_tokens=4000
            ),
        )
        return response.text

    else:
        raise ValueError(f"Unknown provider: {provider}")


def call_ai_json(
    prompt: str, client: object, provider: str, model: str,
    max_retries: int = 3,
) -> list[dict]:
    """Call AI and parse JSON response. Retries with exponential backoff.

    Returns list of dicts on success, or fallback dicts on failure.
    """
    for attempt in range(max_retries):
        try:
            content = call_ai(prompt, client, provider, model)
            content = content.strip()
            # Strip markdown code blocks
            if content.startswith("```"):
                content = re.sub(r"^```\w*\n?", "", content)
                content = re.sub(r"\n?```$", "", content)
            return json.loads(content)

        except json.JSONDecodeError as e:
            log.warning("JSON parse error (attempt %d/%d): %s", attempt + 1, max_retries, e)
        except Exception as e:
            delay = 2 ** attempt
            log.warning("API error (attempt %d/%d, retry in %ds): %s", attempt + 1, max_retries, delay, e)
            time.sleep(delay)

    return []


def load_env(project_root) -> None:
    """Load .env from project root or data/ subfolder."""
    from pathlib import Path
    from dotenv import load_dotenv

    root = Path(project_root)
    for env_path in [root / ".env", root / "data" / ".env"]:
        if env_path.exists():
            load_dotenv(env_path)
            log.info("Loaded API keys from %s", env_path)
            return
    log.warning("No .env file found in %s or %s", root, root / "data")
