# utils/llm_utils.py
import os
import re
import logging
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel, Field, ValidationError
from google import genai
from google.genai import types
import backoff
from config import GEMINI_MODEL

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Configuration ---
# Get the API key from environment variables for security
# Ensure you have GOOGLE_API_KEY set in your environment
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

GEMINI_MODEL_NAME = os.environ.get(
    "GEMINI_MODEL", GEMINI_MODEL  # Use experimental model for speed
)


# --- Pydantic Model for Structured Output ---
class ArticleInfo(BaseModel):
    title: str = Field(description="The main title of the article.")
    authors: str = Field(
        description="Comma-separated list of author names, or 'N/A' if none are found."
    )
    source: str = Field(
        description="The name of the publication or website (e.g., 'CNN', 'The New York Times')."
    )
    published_date: str = Field(
        description="The publication date in ISO 8601 format (YYYY-MM-DD), or 'N/A'."
    )
    updated_date: str = Field(
        description="The last updated date in ISO 8601 format (YYYY-MM-DD), or 'N/A'."
    )
    article_text: str = Field(
        description="The full, cleaned text content of the article."
    )


# --- Optimized System Prompt ---
SYSTEM_PROMPT = f"""Extract article information as JSON. Schema: {ArticleInfo.model_json_schema()}
Rules:
1. Output ONLY valid JSON, no markdown or comments
2. Use "N/A" for missing fields
3. Escape all quotes and special characters properly
4. Be concise but accurate"""


# --- Improved Helper Function to Clean LLM Output ---
def _clean_llm_json_output(raw_string: str) -> str:
    """Cleans the raw output from an LLM to extract a valid JSON object string."""
    if not raw_string or not raw_string.strip():
        raise json.JSONDecodeError("Empty response", "", 0)

    # Remove markdown fences and extra whitespace
    cleaned = re.sub(r"```(?:json)?\s*", "", raw_string.strip())
    cleaned = re.sub(r"\s*```", "", cleaned)
    cleaned = cleaned.strip()

    # Find JSON object boundaries
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1

    if start == -1 or end <= start:
        # Try to find array boundaries as fallback
        start = cleaned.find("[")
        end = cleaned.rfind("]") + 1
        if start == -1 or end <= start:
            raise json.JSONDecodeError("No valid JSON structure found", cleaned, 0)

    json_str = cleaned[start:end]

    # Fix common JSON formatting issues
    try:
        # First attempt: try parsing as-is
        json.loads(json_str)
        return json_str
    except json.JSONDecodeError:
        # Second attempt: fix common escape issues
        try:
            # Fix unescaped quotes in strings
            fixed_str = re.sub(r'(?<!\\)"(?=.*".*:)', r'\\"', json_str)
            # Fix newlines in strings
            fixed_str = re.sub(
                r'(?<=: ")(.*?)(?="[,}])',
                lambda m: m.group(1).replace("\n", "\\n").replace("\r", "\\r"),
                fixed_str,
            )
            # Test if it's valid now
            json.loads(fixed_str)
            return fixed_str
        except json.JSONDecodeError:
            # Third attempt: more aggressive cleaning
            try:
                # Remove problematic characters and fix structure
                fixed_str = (
                    json_str.replace("\n", "\\n")
                    .replace("\r", "\\r")
                    .replace("\t", "\\t")
                )
                # Fix unterminated strings by adding closing quotes before commas/braces
                fixed_str = re.sub(r'("[^"]*[^\\])(\s*[,}])', r'\1"\2', fixed_str)
                json.loads(fixed_str)
                return fixed_str
            except json.JSONDecodeError:
                # Final attempt: create a minimal valid structure
                logging.warning(
                    "Creating fallback JSON structure due to parsing errors"
                )
                return json.dumps(
                    {
                        "title": "N/A",
                        "authors": "N/A",
                        "source": "N/A",
                        "published_date": "N/A",
                        "updated_date": "N/A",
                        "article_text": "Parsing failed - invalid JSON response",
                    }
                )


# --- Logging handler for the backoff decorator ---
def log_backoff(details):
    """Logs a warning when a retry attempt is triggered."""
    exc = details.get("exception") or details.get("value")
    logging.warning(
        f"Backing off {details['target'].__name__} "
        f"for {details['wait']:.1f}s after attempt #{details['tries']}. "
        f"Error: {exc}"
    )


# --- Optimized LLM Interaction Logic ---
@backoff.on_exception(
    backoff.expo,
    (ValidationError, json.JSONDecodeError, Exception),
    max_tries=3,  # Increased back to 3 for better reliability
    max_time=90,  # Increased timeout for more attempts
    on_backoff=log_backoff,
)
def gemini_extract_article_info(pass_dict: dict) -> ArticleInfo | None:
    """
    Uses Gemini to extract article information with optimizations for speed.
    """
    url = pass_dict.get("url", "unknown")
    logging.info(f"Calling Gemini for: {url}")

    # Truncate very long content to speed up processing
    content = str(pass_dict)
    if len(content) > 50000:  # Limit to ~50k chars
        content = content[:50000] + "... [truncated]"
        logging.info(f"Content truncated for speed: {url}")

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=f"Extract info from: {content}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=ArticleInfo.model_json_schema(),  # Enforce schema
            ),
        )

        if not response or not response.text:
            raise ValueError("Empty response from Gemini API")

        # Clean and parse response with improved error handling
        try:
            cleaned_json = _clean_llm_json_output(response.text)
            json_data = json.loads(cleaned_json)
            article_info = ArticleInfo.model_validate(json_data)

            logging.info(f"✓ Extracted info for: {url}")
            return article_info

        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error for {url}: {e}")
            logging.debug(f"Raw response: {response.text[:1000]}...")
            # Log the problematic part of the JSON
            if hasattr(e, "pos"):
                start = max(0, e.pos - 50)
                end = min(len(response.text), e.pos + 50)
                logging.debug(f"Problem area: {response.text[start:end]}")
            raise

    except ValidationError as e:
        logging.error(f"Validation error for {url}: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error for {url}: {e}")
        raise


# --- Async batch processing for multiple URLs ---
async def process_urls_batch(
    url_data_list: list[dict], max_concurrent: int = 3
) -> list[ArticleInfo]:
    """
    Process multiple URLs concurrently for better performance.
    """

    def process_single(data):
        try:
            return gemini_extract_article_info(data)
        except Exception as e:
            logging.error(f"Failed to process {data.get('url', 'unknown')}: {e}")
            return None

    # Use ThreadPoolExecutor for concurrent API calls
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(executor, process_single, data)
            for data in url_data_list
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out None results and exceptions
    valid_results = [r for r in results if isinstance(r, ArticleInfo)]
    logging.info(
        f"Processed {len(valid_results)}/{len(url_data_list)} URLs successfully"
    )
    return valid_results


# --- Synchronous wrapper for backwards compatibility ---
def process_urls_sync(
    url_data_list: list[dict], max_concurrent: int = 3
) -> list[ArticleInfo]:
    """Synchronous wrapper for batch processing."""
    return asyncio.run(process_urls_batch(url_data_list, max_concurrent))


# --- Fallback function with timeout ---
def gemini_extract_with_timeout(
    pass_dict: dict, timeout_seconds: int = 30
) -> ArticleInfo | None:
    """
    Extract with a timeout to prevent hanging.
    """
    import signal

    def timeout_handler(signum, frame):
        raise TimeoutError("Gemini call timed out")

    # Set up timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)

    try:
        result = gemini_extract_article_info(pass_dict)
        signal.alarm(0)  # Cancel timeout
        return result
    except TimeoutError:
        logging.error(f"Timeout processing {pass_dict.get('url', 'unknown')}")
        signal.alarm(0)
        return None
    except Exception as e:
        signal.alarm(0)
        logging.error(f"Error processing {pass_dict.get('url', 'unknown')}: {e}")
        return None


def ollama_parse_url_metadata(url: str) -> ArticleInfo | None:
    """(This function is a placeholder for your existing Ollama logic)"""
    logging.info(f"Parsing with Ollama (placeholder): {url}")
    return None
