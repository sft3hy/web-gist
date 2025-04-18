import requests
import requests
from bs4 import BeautifulSoup
from groq import Groq
from config import CHAR_LIMIT

TOTAL_TOKENS = 0

sys = """You are a web article reader. Extract and output the following information in JSON format from the provided text or URL:

- Title
- Author
- Source/Publisher
- URL
- Date/Time of Publishing

If the article text is unavailable or a 401 error occurs, infer details from the URL (e.g., extract the date). Output only this JSON format:

{
    "title": "Example Title",
    "author": "Example Name",
    "source": "Example Source",
    "url": "https://www.example.com/example-article",
    "published": "01/27/2025 10:03"
}

⚠️ DO NOT MAKE UP ANY DATA FOR THE JSON.  
🗓 For the "published" field, use the exact format: MM/DD/YYYY HH:MM (e.g., 04/17/2025 14:30).  
This format ensures compatibility with Excel date parsing.

"""

cleanup_sys = """You are a website text editor. You will remove extra content at the bottom and top of
an article that does not have to do with the article, and just return the one main article body without editing its content. The main article will be the longest text about one topic."""

def parse_html_for_llm(url):
    print('parsing html')
    try:
        # Define headers to mimic a browser request
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
            )
        }

        # Fetch the webpage content with a timeout
        response = requests.get(url, headers=headers, timeout=3)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the HTML using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract and clean text, keeping it structured
        result = []

        # Add the title of the page if available
        if soup.title and soup.title.string:
            result.append(f"# Title: {soup.title.string.strip()}\n")

        # Process headers and paragraphs
        pretty_text = []
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
            if tag.name.startswith('h'):
                level = int(tag.name[1])
                result.append(f"{'#' * level} {tag.get_text(strip=True)}\n")
                pretty_text.append(f"{'#' * level} {tag.get_text(strip=True)}\n")
            elif tag.name == 'p':
                text = tag.get_text(strip=True)
                if text:
                    result.append(f"{text}\n")
                    pretty_text.append(f"{text}\n")

        # Join and limit content
        to_return = '\n'.join(result)[:CHAR_LIMIT]
        prettier_text = '\n'.join(pretty_text)
        # print('ARITCLE:')
        # print(to_return)
        # print([to_return, prettier_text])
        return [to_return, prettier_text]

    except requests.exceptions.Timeout:
        print("Request timed out after 3 seconds.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
ap_url = "https://apnews.com/live/trump-presidency-day-8-updates"
fox_url = "https://www.foxnews.com/politics/one-bill-two-bills-i-dont-care-trump-promises-get-large-reconciliation-bill-passed-either-way"
reuters_url = "https://www.reuters.com/technology/chinas-deepseek-sets-off-ai-market-rout-2025-01-27/"
cnn_url = "https://www.cnn.com/2025/01/27/politics/trump-special-project-january-6-prosecutors/index.html"

client = Groq()

def call_llm(input_soup: str, model_name="llama-3.1-8b-instant") -> str:
    print('getting article info from url')
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
    