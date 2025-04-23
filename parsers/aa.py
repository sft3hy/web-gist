import re
from bs4 import BeautifulSoup
from text_scrubber import scrub_text

def parse_aa_article(html_string):
    """
    Parses an AA.com article HTML string and extracts the following information:
        - Authors
        - Published Time
        - Last Updated Time
        - Title
        - URL
        - Article Text
        - Source
    Args:
        html_string (str): The HTML content of the AA.com article.
    Returns:
        dict: A dictionary containing the extracted information.  Returns None if parsing fails.
    """
    try:
        soup = BeautifulSoup(html_string, 'html.parser')

        # Title
        title = soup.find('title').text.strip() if soup.find('title') else None

        # URL
        url = soup.find('link', {'rel': 'canonical'})['href'] if soup.find('link', {'rel': 'canonical'}) else None

        # Authors
        author_span = soup.find('span', style=re.compile(r'float:left;.*padding-right: 15px;'))
        authors_text = scrub_text(author_span.text.strip()) if author_span else None
        authors = [author.strip() for author in authors_text.replace("|", "").split(",")] if authors_text else []


        # Published and Updated Time
        time_span = soup.find('span', class_='tarih')
        time_text = time_span.text.strip() if time_span else None
        published_time = time_text.split(" - Update : ")[0].strip() if time_text else None
        last_updated_time = time_text.split(" - Update : ")[1].strip() if time_text and " - Update : " in time_text else None

        # Article Text
        article_content_div = soup.find('div', class_='detay-icerik')
        article_text_paragraphs = article_content_div.find_all('p') if article_content_div else []
        article_text = '\n'.join(p.text.strip() for p in article_text_paragraphs) if article_text_paragraphs else None

        # Source
        source = "aa.com.tr"

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
        print(f"Error parsing article: {e}")
        return None
    
with open('html_dumps/aa_com_tr_20250423_145140.html', 'r') as file:
    html_content = file.read()
article_data = parse_aa_article(html_content)
print(article_data)