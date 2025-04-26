from google import genai
from pydantic import BaseModel
from groq import Groq
import json
import os
from config import GEMINI_MODEL, GROQ_PARSER_MODEL, URL_MODEL, VISIBLE_TEXT_MODEL
from google.genai import types


gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
html_sample = str(open("html_dumps/africanews_com_20250423_145035.html", "r").read())

html_parser_sys_prompt = f"""You are a highly accurate and detail-oriented extraction engine. You will be given a URL, optional json+ld data, and the full raw HTML from a news article page from an online publication. Your job is to extract and return only the essential structured content in the following JSON format:
Use this JSON schema:

{{
  "title": "...",
  "authors": "...",
  "source": "...",
  "article_text": "...",
  "published_date": "...",
  "updated_date": "..."
}}
Field Descriptions:
title (str): The headline or main title of the article, as shown on the page. This should match what a reader would consider the article's title.

authors (str): The full name(s) of the journalist(s) or author(s) who wrote the article. If multiple names are listed, include them as a comma-separated string.

source (str): The name of the publication or website (e.g., "The New York Times", "BBC", "Reuters").

article_text (str): The full readable body of the article. This includes all meaningful paragraphs that make up the story content. Do not include navigation links, ads, sidebars, or captions. Return this as a single plain string with whitespace cleaned up. Do not edit or summarize any of the article text.

published_date (str): The original publication date and time of the article, as shown on the page or in embedded metadata. If you are given a time zone, convert it to Eastern Time (ET). If you are not given a time zone, leave as is. Use this format: "2025-04-23T14:52:05"

updated_date (str): The last modified or updated date and time of the article, if present. If there is no update time, return the same value as published_date.

Instructions:
Look first in structured data (json ld, OpenGraph tags, and meta tags).

If structured data is missing or incomplete, fall back to text in visible headers, bylines, or timestamp areas.

If a field is truly not present, return an empty string "" for that field.

Your output must be a single, well-formed JSON object with only the specified keys.

Respond only with the final JSON — do not include explanations or notes.

Example Input:
{{
    {{
        "URL": "https://www.africanews.com/2025/04/15/south-africa-appoints-mcebisi-jonas-as-special-us-envoy-in-bid-to-ease-tensions/",
        "json_ld": {{
          "@context" : "http://schema.org",
          "@type" : "Article",
          "name" : "South Africa appoints Mcebisi Jonas as special US envoy in bid to ease tensions",
          "datePublished" : "2025-04-15T08:13:40+02:00",
          "image" : "https://static.euronews.com/articles/stories/09/20/16/20/900x506_cmsv2_0280c47c-6fc8-50d3-b7f0-a46c45bb5592-9201620.jpg",
          "articleSection" : "World",
          "articleBody" : "",
          "url" : "http://www.africanews.com/2025/04/15/south-africa-appoints-mcebisi-jonas-as-special-us-envoy-in-bid-to-ease-tensions/",
          "publisher" : {{
                "@type" : "Organization",
                "name" : "Africanews"
          }},
          "aggregateRating" : {{
                "@type" : "AggregateRating",
                "ratingValue" : ""
                }}
        }},
        "raw_html": {html_sample}
    }}
}}
Example Output:
{{
  "title": "South Africa appoints Mcebisi Jonas as special US envoy in bid to ease tensions",
  "authors": "Rédaction Africanews",
  "source": "africanews",
  "article_text": "The South African presidency announced Monday the appointment of Mcebisi Jonas as 'Special Envoy to the United States of America, serving as the official representative of the President and the government of the Republic of South Africa.'

Mcebisi Jonas is former deputy finance minister and also served as investment envoy in 2018.

In 2016, he accused the government of Jacob Zuma, back then president of South Africa, of corruption, saying that the Gupta family had offered to bribe him for the position of finance minister.

The move to appoint him as special envoy to the US comes as relations between Washington and Pretoria are at their lowest point in years.

The situation rapidly deteriorated earlier this year when US president Donald Trump cut off US foreign assistance to South Africa.

And in late March, South African ambassador to the US Ebrahim Rasool was declared a persona non grata and expelled from American territory over critical remarks he made on the subject of the Trump administration.

In his statement announcing the appointment of the special US envoy, president Ramaphosa however noted that he remained 'committed to rebuilding and maintaining' the relationship with Washington.

'Mr Jonas is entrusted with the responsibility to advance South Africa's diplomatic, trade and bilateral priorities', noted the presidency."
  "published_date": "2025-04-15T04:34:06",
  "updated_date": "2025-04-15T04:34:12"
}}
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

    def to_dict(self, llm: str):
        data = self.model_dump()
        if llm is not None:
            data["llm"] = llm
        return data


cache_name = "Long html sys prompt"
cache_code = "cachedContents/ezuxvlqgt3p1"


def create_cache():
    # Create a cache with a 1 hour TTL
    print("creating cached system prompt")
    cache = gemini_client.caches.create(
        model=GEMINI_MODEL,
        config=types.CreateCachedContentConfig(
            display_name="Long html sys prompt",  # used to identify the cache
            system_instruction=(html_parser_sys_prompt),
            ttl="7200s",  # 1 hour
        ),
    )
    print(cache)
    print("finished")


# create_cache()


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
    print(f"received json+ld info, calling {JSONLD_MODEL} via groq")
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


url_parser_sys_prompt = f"""
You are a cautious and precise metadata extractor. You will receive a single URL to a news article. Your task is to infer as much real metadata as possible and return it in the following JSON structure:

The JSON object must use the schema:
{json.dumps(ArticleInfo.model_json_schema(), indent=2)}

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

Example input: https://www.reuters.com/world/africa/al-shabaab-captures-strategic-somalia-town-it-presses-offensive-2025-04-16/

Expected output:
{{
  "title": "Al Shabaab captures strategic Somalia town as it presses offensive",
  "authors": "",
  "source": "Reuters",
  "article_text": "",
  "published_date": "2025-04-16",
  "updated_date": "2025-04-16"
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
{json.dumps(ArticleInfo.model_json_schema(), indent=2)}

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


# print(f"{json.dumps(ArticleInfo.model_json_schema(), indent=2)}")
