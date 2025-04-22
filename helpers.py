import requests
from bs4 import BeautifulSoup
from groq import Groq
import json
from config import CHAR_LIMIT
from scraper_utils import parse_html_for_llm

TOTAL_TOKENS = 0

sys = """
You are a structured web article parser. Your task is to extract only the following fields from the provided article text or URL and return them in strict JSON format:

- "title": The main title of the article.
- "author": The full name of the article’s author (leave blank if unknown).
- "source": The publisher or website name.
- "url": The full URL of the article.
- "published": The original date and time the article was published.
- "updated": The most recent date and time the article was updated.

If only one date is available, use it for both "published" and "updated".

⚠️ IMPORTANT:
- DO NOT make up or hallucinate any data.
- Leave fields blank if the information is not explicitly available.
- Use the format *exactly*: MM/DD/YYYY HH:MM (24-hour time).
- If multiple dates are present, always use the earliest one as "published" and the latest one as "updated".

✅ Return only a JSON object. Do not include any commentary, explanation, or extra text.

Example Output:
{
  "title": "Example Headline",
  "author": "Jane Doe",
  "source": "Example News",
  "url": "https://www.example.com/example-article",
  "published": "04/16/2025 09:28",
  "updated": "04/17/2025 04:40"
}
"""

cleanup_sys = """You are a content cleaner for online articles. Your task is to isolate and return only the main article body from a web page.

Instructions:
- Remove any unrelated content at the beginning or end, such as:
  - Navigation bars
  - Promotional sections
  - Author bios
  - Related articles
  - Newsletter prompts
  - Footers or comment sections
- Do NOT edit or rewrite the article content.
- Only return the main body of the article, focused on a single topic or story.
- The main body will usually be the longest continuous block of coherent text.

Return the article body as plain text with no additional commentary.
"""
    
ap_url = "https://apnews.com/live/trump-presidency-day-8-updates"
fox_url = "https://www.foxnews.com/politics/one-bill-two-bills-i-dont-care-trump-promises-get-large-reconciliation-bill-passed-either-way"
reuters_url = "https://www.reuters.com/technology/chinas-deepseek-sets-off-ai-market-rout-2025-01-27/"
cnn_url = "https://www.cnn.com/2025/01/27/politics/trump-special-project-january-6-prosecutors/index.html"

client = Groq()

def call_llm(input_soup: str, model_name="llama-3.1-8b-instant") -> str:
    stream = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": sys,
            },
            {
                "role": "user",
                "content": input_soup
            }
        ],
        model=model_name,
        response_format={"type": "json_object"},
    )
    # TOTAL_TOKENS += stream.usage.completion_tokens + stream.usage.prompt_tokens
    # print("Prompt Tokens:", stream.usage.prompt_tokens)
    # print("Completion Tokens:", stream.usage.completion_tokens)
    return stream.choices[0].message.content
    
    
    
def clean_article(input_article: str, model_name="gemma2-9b-it"):
    print('cleaning article')
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": cleanup_sys,
            },
            {
                "role": "user",
                "content": input_article
            }
        ],
        model=model_name,
    )
    # TOTAL_TOKENS += response.usage.completion_tokens + response.usage.prompt_tokens

    # print("Prompt Tokens:", response.usage.prompt_tokens)
    # print("Completion Tokens:", response.usage.completion_tokens)
    return response.choices[0].message.content
    