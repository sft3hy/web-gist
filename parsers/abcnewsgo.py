from bs4 import BeautifulSoup
import re
import json
from text_scrubber import scrub_text


def parse_abcnews_article(html_string):
    """
    Parses an ABC News article HTML string and extracts the following information:
        - Authors
        - Published Time (finds timestamp)
        - Last Updated Time (Not available, setting to None)
        - Title (from h1 tag)
        - URL
        - Article Text (all <p> tags)
        - Source
    Args:
        html_string (str): The HTML content of the ABC News article.

    Returns:
        dict: A dictionary containing the extracted information. Returns None if parsing fails.
    """
    try:
        soup = BeautifulSoup(html_string, 'html.parser')

        # Title - from h1 tag
        title_element = soup.find('h1')
        title = title_element.text.strip() if title_element else None

        # URL
        url = soup.find('link', {'rel': 'canonical'})['href'] if soup.find('link', {'rel': 'canonical'}) else None

        # Published Time - Look for a timestamp pattern in a div
        published_time = None
        time_div = soup.find('div', class_=re.compile(r"jTKbV.*QtiLO.*"))  # flexible class matching timestamp
        if time_div:
            published_time = time_div.text.strip()

        # Authors - Extract from byline section, attempting to split name from title
        authors = []
        byline_div = soup.find('div', {'data-testid': 'prism-byline'})
        if byline_div:
            author_span = byline_div.find('div', class_="TQPvQ fVlAg HUcap kxY REjk UamUc WxHIR HhZOB yaUf VOJBn KMpjV XSbaH Umfib ukdDD")
            author_text = author_span.text.replace("By", "").strip() if author_span else None
            authors = [scrub_text(author_text)] if author_text else []


        # Last Updated Time - Not directly available in this HTML, set to None
        last_updated_time = published_time

        # Article Text - Extract all <p> tags
        article_body_div = soup.find('div', class_='xvlfx ZRifP TKoO eaKKC EcdEg bOdfO qXhdi NFNeu UyHES')
        article_paragraphs = article_body_div.find_all('p') if article_body_div else []
        article_text = '\n'.join(p.text.strip() for p in article_paragraphs) if article_paragraphs else None

        # Source
        source = "abcnews.go.com"

        article_data = {
            'authors': authors,
            'published_time': published_time,
            'last_updated_time': last_updated_time,
            'title': scrub_text(title),
            'url': url,
            'article_text': scrub_text(article_text),
            'source': source
        }

        return article_data

    except Exception as e:
        print(f"Error parsing ABC News article: {e}")
        return None
    
# abcnews_go_com_20250422_203657
with open('html_dumps/abcnews_go_com_20250422_203657.html', 'r') as file:
    html_content = file.read()
article_data = parse_abcnews_article(html_content)
print(article_data)