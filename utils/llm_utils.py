from google import genai
from pydantic import BaseModel
from groq import Groq
import json
import os
import time
import requests
from utils.gemini_cache import html_parser_sys_prompt, create_cache
from config import GEMINI_MODEL, GROQ_PARSER_MODEL, URL_MODEL, VISIBLE_TEXT_MODEL


gemini_client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"], http_options={"timeout": 30000}
)


from google import genai
from pydantic import BaseModel
import os


class ArticleInfo(BaseModel):
    title: str
    authors: str
    source: str
    article_text: str
    published_date: str
    updated_date: str

    def to_dict(self):
        data = self.model_dump()
        return data


json_schema = json.dumps(ArticleInfo.model_json_schema(), indent=2)
cache_code = "cachedContents/d680dzpf4gu1"


def gemini_parse_web_content(input_dict: dict, for_streamlit=False):
    max_attempts = 3
    max_html_length = 28000

    # Truncate the raw_html field if it's too long
    if "raw_html" in input_dict and isinstance(input_dict["raw_html"], str):
        input_dict["raw_html"] = input_dict["raw_html"][:max_html_length]

    gemini_config = {
        "response_mime_type": "application/json",
        "response_schema": ArticleInfo,
        # "system_instruction": html_parser_sys_prompt,
    }
    if not for_streamlit:
        gemini_config["cached_content"] = cache_code
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"Attempt {attempt}: parsing web content with {GEMINI_MODEL}")
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=str(input_dict),
                config=gemini_config,
            )
            return ArticleInfo.model_validate_json(response.text)

        except Exception as e:
            print(f"Attempt {attempt} failed with error: {e}")
            if attempt == max_attempts:
                raise
            time.sleep(0.5)  # optional: brief pause before retrying


groq_client = Groq()

url_parser_sys_prompt = f"""
You are a cautious and precise metadata extractor. You will receive a single URL to a news article. Your task is to infer as much real metadata as possible and return it in the following JSON structure:

Respond only with JSON using this format:
{{
    \"title\": \"the title of the article\"
    \"authors\": \"author(s) of the article\"
    \"source\": \"news source\"
    \"article_text\": \"unknown\"
    \"published_date\": \"date from url\"
    \"updated_date\": \"date from url\"
}}

Descriptions of each field:

- title: Do not guess or fabricate a title. If the URL contains readable words or a slug that appears to be a title, use it (e.g., from the last part of the path). Otherwise, return "".
- authors: Leave this as "" unless a specific person's name appears clearly in the URL (e.g., /by/john-smith/).
- source: Use the domain name from the URL (e.g., “bbc.com”, “nytimes.com”, “reuters.com”). Normalize it to a clean readable form when possible, such as “BBC” or “Reuters”.
- article_text: Always return "" (you do not have the article body).
- published_date: Only extract a date if an explicit, clearly formatted date string appears in the URL path (e.g., /2024/12/15/, /15-apr-2023/, or similar). If no such date is visible in the URL, **do not guess** — return "".
- updated_date: Return the same value as published_date if available, or "".

Strict rules:
- Never infer or hallucinate any data. You must only use what is **explicitly** and **visibly** present in the URL string.
- Especially for dates: if the URL does not visibly contain a date, you must return "unkown"for both `published_date` and `updated_date`.
- Your response must be only the final JSON object, with no explanation or comments.
- Always return all 6 fields exactly as specified. If you cannot extract a value, use "unknown" instead of an empty string..

You will receive only one input: a string containing the article URL.

Example input: https://www.governor.virginia.gov/newsroom/news-releases/2025/february/name-1041143-en.html

Expected output:
{{
  "title": "unknown",
  "authors": "unknown",
  "source": "Governer of Virginia",
  "article_text": "unknown",
  "published_date": "2025-02",
  "updated_date": "2025-02"
}}
"""


# def groq_parse_url(url: str):
#     print(f"received no html, calling {URL_MODEL} on url")
#     try:
#         chat_completion = groq_client.chat.completions.create(
#             messages=[
#                 {"role": "system", "content": url_parser_sys_prompt},
#                 {
#                     "role": "user",
#                     "content": str(url),
#                 },
#             ],
#             model=URL_MODEL,
#             temperature=0,
#             response_format={"type": "json_object"},
#         )
#         return ArticleInfo.model_validate_json(
#             chat_completion.choices[0].message.content
#         )
#     except Exception as e:
#         print(e)
#         return None


import json


def groq_parse_url(url: str):
    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "link-parser",
                "stream": False,
                "messages": [
                    {"role": "user", "content": url},
                ],
            },
        )

        # The content may be a double-encoded JSON string, so decode it
        raw_content = response.json()["message"]["content"]
        cleaned_json = json.loads(raw_content)  # unescape it

        return ArticleInfo.model_validate(cleaned_json)

    except Exception as e:
        print(f"Error calling Groq parser: {e}")
        return None  # Return a neutral failure value instead of the class itself


# print(url_parser_sys_prompt)
