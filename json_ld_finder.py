import json
from bs4 import BeautifulSoup
from utils.text_scrubber import scrub_text


def extract_ld_json_and_article(soup):
    """
    Extracts the first JSON-LD (application/ld+json) script and the full article text from <p> tags.

    Args:
        html (str): The input HTML string.

    Returns:
        dict: A dictionary with keys:
              - 'ld_json': Parsed JSON-LD data or None
              - 'article_text': Concatenated text from all <p> tags
    """

    # Extract the first ld+json script
    script_tags = soup.find_all("script", type="application/ld+json")
    ld_datas = []
    if script_tags:
        for script_tag in script_tags:
            try:
                ld_datas.append(json.loads(script_tag.string))
            except json.JSONDecodeError:
                continue

    if ld_datas == []:
        return None

    # Extract all text in <p> tags
    article_text = " ".join(p.get_text(strip=True) for p in soup.find_all("p"))
    cleaned_article_text = scrub_text(article_text)
    return {"ld_json_list": ld_datas, "article_text": cleaned_article_text}


# html_string = open("html_dumps/ilmessaggero_it_20250423_145118.html", "r").read()
# info = extract_ld_json_and_article(html_string)
# print(info)
