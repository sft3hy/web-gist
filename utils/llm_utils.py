from google import genai
from pydantic import BaseModel
from groq import Groq
import json
import os
from utils.gemini_cache import html_parser_sys_prompt, create_cache
from config import GEMINI_MODEL, GROQ_PARSER_MODEL, URL_MODEL, VISIBLE_TEXT_MODEL
from google.genai import types


gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


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
    llm: str

    def to_dict(self):
        data = self.model_dump()
        return data


json_schema = json.dumps(ArticleInfo.model_json_schema(), indent=2)
print(json_schema)


# cache_code = create_cache().name


def gemini_parse_web_content(input_dict: str):
    print(f"parsing web content with {GEMINI_MODEL}")
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=input_dict,
        config={
            "response_mime_type": "application/json",
            "response_schema": ArticleInfo,
            # "system_instruction": html_parser_sys_prompt,
            "cached_content": cache_code,
        },
    )
    # Use the response as a JSON string.
    return ArticleInfo.model_validate_json(response.text)


# html_string = open("html_dumps/chosun_com_20250423_145233.html", "r").read()
# info = gemini_parse_html(str(html_string))
# print(info)


groq_client = Groq()


def groq_parse_dict(article_info: dict):
    print(f"calling {GROQ_PARSER_MODEL} via groq")
    chat_completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": html_parser_sys_prompt},
            {
                "role": "user",
                "content": str(article_info),
            },
        ],
        model=GROQ_PARSER_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
    )
    return ArticleInfo.model_validate_json(chat_completion.choices[0].message.content)


url_parser_sys_prompt = f"""
You are a cautious and precise metadata extractor. You will receive a single URL to a news article. Your task is to infer as much real metadata as possible and return it in the following JSON structure:

The JSON object must use the schema:
{json_schema}

Descriptions of each field:

- title: Do not guess or fabricate a title. If the URL contains readable words or a slug that appears to be a title, use it (e.g., from the last part of the path). Otherwise, return "".
- authors: Leave this as "" unless a specific person's name appears clearly in the URL (e.g., /by/john-smith/).
- source: Use the domain name from the URL (e.g., “bbc.com”, “nytimes.com”, “reuters.com”). Normalize it to a clean readable form when possible, such as “BBC” or “Reuters”.
- article_text: Always return "" (you do not have the article body).
- published_date: Only extract a date if an explicit, clearly formatted date string appears in the URL path (e.g., /2024/12/15/, /15-apr-2023/, or similar). If no such date is visible in the URL, **do not guess** — return "".
- updated_date: Return the same value as published_date if available, or "".

Strict rules:
- Never infer or hallucinate any data. You must only use what is **explicitly** and **visibly** present in the URL string.
- Especially for dates: if the URL does not visibly contain a date, you must return an empty string for both `published_date` and `updated_date`.
- Your response must be only the final JSON object, with no explanation or comments.
- Always return all 6 fields exactly as specified, even if most values are empty.

You will receive only one input: a string containing the article URL.

Example input: https://www.governor.virginia.gov/newsroom/news-releases/2025/february/name-1041143-en.html

Expected output:
{{
  "title": "",
  "authors": "",
  "source": "Governer of Virginia",
  "article_text": "",
  "published_date": "2025-02",
  "updated_date": "2025-02"
}}
"""


def groq_parse_url(url: str):
    print(f"received no html, calling {URL_MODEL} on url")
    chat_completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": url_parser_sys_prompt},
            {
                "role": "user",
                "content": str(url),
            },
        ],
        model=URL_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
    )
    return ArticleInfo.model_validate_json(chat_completion.choices[0].message.content)


visible_text_sys_prompt = f"""
You are a web content parser. Given a URL and all visible text from a news or article webpage, extract a dictionary with:
JSON SCHEMA:
{json_schema}

Guidelines:
- article_text: The main body—usually the longest coherent text block.
- title: Usually first, short, and stands alone.
- author: Names (often after "By") near article start or end.
- source: Publication name near title or author (e.g., "CNN", "Reuters").
- published_date / updated_date: Near author or start of text. Use phrases like “Published”, “Updated”, etc. Format as ISO 8601 if possible.
- If any fields are missing, use "".

Ignore unrelated nav, ads, or comments. Prioritize info near the article. If the page is a paywall or lacks details, return only what you can (e.g., title).
"""


def groq_parse_visible_text(text: str):
    print(f"received visible text, calling {VISIBLE_TEXT_MODEL}")
    chat_completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": visible_text_sys_prompt},
            {
                "role": "user",
                "content": text,
            },
        ],
        model=VISIBLE_TEXT_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
    )
    return ArticleInfo.model_validate_json(chat_completion.choices[0].message.content)


# print(f"{json_schema}")
