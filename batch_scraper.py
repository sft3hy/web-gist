import csv
import re
import json
import time
from collections import deque
from helpers import call_llm, clean_article
from scraper_utils import parse_html_for_llm
from config import CHAR_LIMIT, BEGIN_ROW, END_ROW

# naughty = ['news.afp.com', 'reuters.com']

# LLM Limits
LLAMA_REQ_PER_MIN = 30
LLAMA_TOK_PER_MIN = 6000

GEMMA_REQ_PER_MIN = 30
GEMMA_TOK_PER_MIN = 15000

# Token estimator (roughly 4 chars/token)
def estimate_tokens(text):
    return max(1, len(text) // 4)

# Deques to hold (timestamp, token count)
llama_requests = deque()
llama_tokens = deque()

gemma_requests = deque()
gemma_tokens = deque()

def throttle_model(requests_deque, tokens_deque, max_req, max_tok, new_tok):
    now = time.time()

    # Purge requests older than 60 seconds
    while requests_deque and now - requests_deque[0] > 60:
        requests_deque.popleft()
    while tokens_deque and now - tokens_deque[0][0] > 60:
        tokens_deque.popleft()

    # Wait if we exceed limits
    while len(requests_deque) >= max_req or sum(tok for _, tok in tokens_deque) + new_tok > max_tok:
        time.sleep(1)
        now = time.time()
        while requests_deque and now - requests_deque[0] > 60:
            requests_deque.popleft()
        while tokens_deque and now - tokens_deque[0][0] > 60:
            tokens_deque.popleft()

    requests_deque.append(now)
    tokens_deque.append((now, new_tok))

# Read and filter URLs
urls = []
rows = open('Links.txt', 'r').read().split('\n')[1:]
for row in rows:
    if row == "":
        urls.append("")
    elif re.match(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', row):
        urls.append(row)

count = 1
with open(f'Parsed_links{BEGIN_ROW}-{END_ROW}.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['URL', 'article_text', 'title', 'author', 'source', 'published_date', 'updated_date'])

    for url in urls[BEGIN_ROW:END_ROW]:
        print('processing article', count)
        count += 1

        if url == "":
            print('writing blank row')
            writer.writerow(['', '', '', '', '', ''])
            continue

        parsed = f'URL: {url}\n'
        article_text = ''
        title = ''
        author = ''
        source = ''
        published_date = ''

        whole_parsed = parse_html_for_llm(url)
        # for item in whole_parsed:
        #     print(item)
        #     print()
        if whole_parsed is not None and whole_parsed[1] != '':
            parsed += f"URL: {url}\nWebsite text:{whole_parsed[0]}"
            raw_text = whole_parsed[1][:CHAR_LIMIT]

            # Throttle for GEMMA (used in clean_article)
            gemma_tok = estimate_tokens(raw_text)
            throttle_model(gemma_requests, gemma_tokens, GEMMA_REQ_PER_MIN, GEMMA_TOK_PER_MIN, gemma_tok)
            article_text = clean_article(raw_text)

        # Throttle for LLAMA (used in call_llm)
        llama_tok = estimate_tokens(parsed)
        throttle_model(llama_requests, llama_tokens, LLAMA_REQ_PER_MIN, LLAMA_TOK_PER_MIN, llama_tok)

        try:
            article_json = json.loads(call_llm(parsed))
            for key, value in article_json.items():
                if key == 'title':
                    title = value
                elif key == 'author':
                    author = value
                elif key == 'source':
                    source = value
                elif key == 'published':
                    published_date = value
                elif key == 'updated':
                    updated_date = value

        except (json.JSONDecodeError, TypeError) as e:
            print(f"Error decoding JSON or processing data for URL: {url} - {e}")
        except Exception as e:
            print(f"General error processing URL: {url} - {e}")

        writer.writerow([url, article_text, title, author, source, published_date, updated_date])

print("Processing complete.")
