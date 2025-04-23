from bs4 import BeautifulSoup
import json
from text_scrubber import scrub_text


def parse_abc7_article(html_string):
    """
    Parses an ABC7 Los Angeles article HTML string and extracts the following information:
        - Authors (as a single string)
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

        # Authors - Attempt to extract from ld+json and concatenate into a single string
        author_string = None
        if ld_json_script:
            try:
                ld_json = json.loads(ld_json_script.string)
                author_data = ld_json.get('author')
                if isinstance(author_data, list):
                    author_names = [author.get('name', '') for author in author_data if isinstance(author, dict)]
                    author_string = ', '.join(author_names)  # Join names with a comma
                elif isinstance(author_data, dict):
                    author_string = author_data.get('name', '')
                else:
                    author_string = None  # Handle cases where 'author' is not a list or dict

            except json.JSONDecodeError:
                print("Error decoding ld+json for authors.")
        author_string = scrub_text(author_string) if author_string else None #scrub the text

        # Article Text
        article_body_div = soup.find('div', class_='xvlfx ZRifP TKoO eaKKC EcdEg bOdfO qXhdi NFNeu UyHES')
        article_paragraphs = article_body_div.find_all('p') if article_body_div else []

        # Extract text from span tags if available
        article_text = '\n'.join(
            [p.find('span', class_="oyrPY qlwaB AGxeB").text.strip() if p.find('span', class_="oyrPY qlwaB AGxeB") else p.text.strip()
             for p in article_paragraphs]) if article_paragraphs else None
        # Source
        source = "abc7.com"

        article_data = {
            'authors': author_string,  # Store the combined author string
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

# abc7_com_20250423_145157
with open('html_dumps/abc7test.html', 'r') as file:
    html_content = file.read()
article_data = parse_abc7_article(html_content)
print(article_data)