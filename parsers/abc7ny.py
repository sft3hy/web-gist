from bs4 import BeautifulSoup
import json
from text_scrubber import scrub_text


def parse_abc7ny_article(html_string):
    """
    Parses an ABC7 New York article HTML string and extracts the following information:
        - Authors (Not reliably available, attempting to extract from ld+json if present)
        - Published Time
        - Last Updated Time
        - Title
        - URL
        - Article Text
        - Source
    Args:
        html_string (str): The HTML content of the ABC7 article.

    Returns:
        dict: A dictionary containing the extracted information. Returns None if parsing fails.
    """
    try:
        soup = BeautifulSoup(html_string, 'html.parser')

        # Title
        title = soup.find('title', {'data-react-helmet': 'true'}).text.strip() if soup.find('title', {'data-react-helmet': 'true'}) else None

        # URL
        url = soup.find('link', {'rel': 'canonical'})['href'] if soup.find('link', {'rel': 'canonical'}) else None

        # Published Time and Last Updated Time.  Pull from ld+json
        published_time = None
        last_updated_time = None

        ld_json_script = soup.find('script', {'type': 'application/ld+json'})
        if ld_json_script:
            try:
                ld_json = json.loads(ld_json_script.string)
                published_time = ld_json.get('datePublished')
                last_updated_time = ld_json.get('dateModified')
            except json.JSONDecodeError:
                print("Error decoding ld+json")
        if last_updated_time is None:
            last_updated_time = published_time

        # Authors - Attempt to extract from ld+json
        authors = []
        if ld_json_script:
            try:
                ld_json = json.loads(ld_json_script.string)
                author_data = ld_json.get('author')
                if isinstance(author_data, list):
                    authors = [author.get('name', '') for author in author_data if isinstance(author, dict)]
                elif isinstance(author_data, dict):
                    authors = [author_data.get('name', '')]
            except json.JSONDecodeError:
                print("Error decoding ld+json for authors.")
        cleaned_authors = [scrub_text(author) for author in authors]
        # Article Text
        article_body_div = soup.find('div', class_='xvlfx ZRifP TKoO eaKKC EcdEg bOdfO qXhdi NFNeu UyHES')
        article_paragraphs = article_body_div.find_all('p') if article_body_div else []

        # Extract text from span tags if available
        article_text = '\n'.join(
            [p.find('span', class_="oyrPY qlwaB AGxeB").text.strip() if p.find('span', class_="oyrPY qlwaB AGxeB") else p.text.strip()
             for p in article_paragraphs]) if article_paragraphs else None
        # Source
        source = "abc7ny.com"

        article_data = {
            'authors': cleaned_authors,
            'published_time': published_time,
            'last_updated_time': last_updated_time,
            'title': scrub_text(title),
            'url': url,
            'article_text': scrub_text(article_text),
            'source': source
        }

        return article_data

    except Exception as e:
        print(f"Error parsing ABC7 article: {e}")
        return None



with open('html_dumps/abc7ny_com_20250422_203729.html', 'r') as file:
    html_content = file.read()
article_data = parse_abc7ny_article(html_content)
print(article_data)