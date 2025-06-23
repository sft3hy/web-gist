# utils/llm_utils.py
import os
import json
import logging
import requests
from pathlib import Path
from pydantic import BaseModel, ValidationError
from google import genai

from config import GEMINI_MODEL, OLLAMA_URL_PARSER_MODEL, OLLAMA_API_BASE_URL

# --- Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

try:
    gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
except ImportError:
    # Allow the app to run without genai if not used
    gemini_client = None
    logging.warning(
        "Google GenAI SDK not found. Gemini functions will not be available."
    )


# --- Data Models ---
class ArticleInfo(BaseModel):
    title: str | None = ""
    authors: str | None = ""
    source: str | None = ""
    article_text: str | None = ""
    published_date: str | None = ""
    updated_date: str | None = ""


# --- Prompt Loading ---
def load_prompt(file_name: str) -> str:
    """Loads a prompt from the prompts directory."""
    prompt_path = Path(__file__).parent.parent / "prompts" / file_name
    if not prompt_path.exists():
        logging.error(f"Prompt file not found: {prompt_path}")
        return ""
    return prompt_path.read_text(encoding="utf-8")


HTML_EXTRACTOR_SYSTEM_PROMPT = load_prompt("html_extractor_system.md")

# --- LLM Functions ---


def gemini_extract_article_info(
    input_dict: dict, max_retries: int = 3
) -> ArticleInfo | None:
    """
    Parses web content using the Gemini API with a defined JSON schema.
    """
    if not gemini_client:
        logging.error("Gemini client is not initialized.")
        return None

    # Truncate content to avoid excessive token usage
    max_content_length = 30000
    if "website_content" in input_dict and isinstance(
        input_dict["website_content"], str
    ):
        input_dict["website_content"] = input_dict["website_content"][
            :max_content_length
        ]

    generation_config = {}

    for attempt in range(max_retries):
        try:
            logging.info(
                f"Attempt {attempt + 1}: Calling Gemini to extract article info."
            )
            gemini_config = {
                "response_mime_type": "application/json",
                "system_instruction": HTML_EXTRACTOR_SYSTEM_PROMPT,
            }
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[str(input_dict)],
                config=gemini_config,
            )
            return ArticleInfo.model_validate_json(response.text)
        except (ValidationError, json.JSONDecodeError) as e:
            logging.error(
                f"Gemini response validation failed on attempt {attempt + 1}: {e}"
            )
            logging.debug(
                f"Invalid response text: {response.text if 'response' in locals() else 'N/A'}"
            )
        except Exception as e:
            logging.error(f"Gemini API call failed on attempt {attempt + 1}: {e}")

        if attempt < max_retries - 1:
            logging.info("Retrying...")

    logging.error("All Gemini attempts failed.")
    return None


def ollama_parse_url_metadata(url: str, max_retries: int = 3) -> ArticleInfo | None:
    """
    Infers metadata from a URL using a local Ollama model.
    """
    for attempt in range(max_retries):
        try:
            logging.info(
                f"Attempt {attempt + 1}: Calling local Ollama model '{OLLAMA_URL_PARSER_MODEL}' for URL."
            )
            response = requests.post(
                OLLAMA_API_BASE_URL,
                json={
                    "model": OLLAMA_URL_PARSER_MODEL,
                    "stream": False,
                    "messages": [{"role": "user", "content": url}],
                },
                timeout=30,  # 30-second timeout
            )
            response.raise_for_status()

            raw_content = response.json()["message"]["content"]

            # The model might return a string containing JSON, so we parse it.
            try:
                # First, try to load it directly
                json_data = json.loads(raw_content)
            except json.JSONDecodeError:
                # If that fails, it might be a markdown-style code block
                cleaned_str = (
                    raw_content.strip()
                    .replace("```json", "")
                    .replace("```", "")
                    .strip()
                )
                json_data = json.loads(cleaned_str)

            # Validate with Pydantic model
            return ArticleInfo.model_validate(json_data)

        except requests.exceptions.RequestException as e:
            logging.error(f"Ollama API request failed on attempt {attempt + 1}: {e}")
        except (json.JSONDecodeError, KeyError, ValidationError) as e:
            logging.error(
                f"Failed to parse or validate Ollama response on attempt {attempt + 1}: {e}"
            )
            logging.debug(
                f"Invalid response content: {raw_content if 'raw_content' in locals() else 'N/A'}"
            )

    logging.error(f"All Ollama attempts failed for URL: {url}")
    return None
