from google import genai
from pydantic import BaseModel
from groq import Groq
import json
import os
from config import HTML_MODEL, JSONLD_MODEL

gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

html_parser_sys_prompt = """You are a highly accurate and detail-oriented extraction engine. You will be given the full raw HTML of a news article page from an online publication. Your job is to extract and return only the essential structured content in the following JSON format:
Use this JSON schema:

{
  "title": "...",
  "authors": "...",
  "source": "...",
  "article_text": "...",
  "published_date": "...",
  "updated_date": "..."
}
Field Descriptions:
title (str): The headline or main title of the article, as shown on the page. This should match what a reader would consider the article's title.

authors (str): The full name(s) of the journalist(s) or author(s) who wrote the article. If multiple names are listed, include them as a comma-separated string.

source (str): The name of the publication or website (e.g., "The New York Times", "BBC", "Reuters").

article_text (str): The full readable body of the article. This includes all meaningful paragraphs that make up the story content. Do not include navigation links, ads, sidebars, or captions. Return this as a single plain string with whitespace cleaned up.

published_date (str): The original publication date and time of the article, as shown on the page or in embedded metadata. Use the ISO 8601 format in eastern time when possible (e.g., "2025-04-23T14:52:05").

updated_date (str): The last modified or updated date and time of the article, if present. If there is no update time, return the same value as published_date.

Instructions:
Look first in structured data (OpenGraph tags and meta tags).

If structured data is missing or incomplete, fall back to text in visible headers, bylines, or timestamp areas.

If a field is truly not present, return an empty string "" for that field.

Your output must be a single, well-formed JSON object with only the specified keys.

Respond only with the final JSON — do not include explanations or notes.
           """

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


def gemini_parse_html(input_html: str):
    print("no json+ld info, passing whole html to gemini 2.0 flash lite")
    response = gemini_client.models.generate_content(
        model=HTML_MODEL,
        contents=input_html,
        config={
            "response_mime_type": "application/json",
            "response_schema": ArticleInfo,
            "system_instruction": html_parser_sys_prompt,
        },
    )
    # Use the response as a JSON string.
    return ArticleInfo.model_validate_json(response.text)


# html_string = open("html_dumps/chosun_com_20250423_145233.html", "r").read()
# info = gemini_parse_html(str(html_string))
# print(info)


groq_cleaner_sys_prompt = f"""
You are a precise and context-aware data extractor. You will be given a JSON object that contains:
- A list of `ld_json_list`: all `application/ld+json` blocks extracted from a news article HTML.
- Optionally, `article_text`: unstructured plain text from the HTML's <p> tags.

Your task is to parse the input and return a single, clean, and complete `ArticleInfo` object as JSON.
The JSON object must use the schema:
{json.dumps(ArticleInfo.model_json_schema(), indent=2)}"

Field Descriptions:
title (str): The article's main title or headline. Prefer the value of "headline" or "name" from the most relevant NewsArticle object.

authors (str): Full name(s) of the article's author(s). Extract from "author", "creator", or related fields. Return a comma-separated string if multiple authors are present.

source (str): The name of the news organization or website, e.g., "BBC News", "The Guardian", "Il Messaggero". Typically found in the "publisher" or "copyrightHolder" fields.

article_text (str): Use the "articleBody" field from JSON-LD if available. If not, fall back to the raw article_text provided in the input. Clean up excessive whitespace and line breaks.

published_date (str): The article's original publication date and time. Use "datePublished" if available. Convert it to Eastern Time (ET) and format using ISO 8601, e.g., "2025-04-05T13:10:15-04:00".

updated_date (str): The most recent modification time of the article. Use "dateModified" or similar. If missing, use the same value as published_date. Convert to Eastern Time in ISO 8601 format.

Rules and Instructions:
Parse and evaluate all items in ld_json_list. Choose the one that represents the main news article (usually where @type is "NewsArticle").

If multiple valid options exist for a field, use the one with the most complete or specific value.

Always convert published_date and updated_date to Eastern Time. Assume source timestamps are in the local time of the publication if a time zone is provided; otherwise, default to UTC.

If any required field is truly missing, return an empty string "".

Your response must be only the final JSON output — no explanation or comments.

Input will always be a single dictionary with keys:

"ld_json_list": a list of dictionaries (parsed JSON-LD blocks)

"article_text": a string (optional)

Respond with a valid, fully populated JSON object with the exact 6 keys defined above.

"""


groq_client = Groq()


def groq_parse_dict(article_info: dict):
    print("received json+ld info, calling gemma via groq")
    chat_completion = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": groq_cleaner_sys_prompt},
            {
                "role": "user",
                "content": str(article_info),
            },
        ],
        model=JSONLD_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
    )
    return ArticleInfo.model_validate_json(chat_completion.choices[0].message.content)
