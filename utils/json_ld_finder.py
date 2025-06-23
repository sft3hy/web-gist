# utils/json_ld_finder.py
import json
import logging
from bs4 import BeautifulSoup, Tag
from typing import Any, Dict, List

from utils.text_scrubber import scrub_text


def extract_ld_json_and_article(soup: BeautifulSoup) -> Dict[str, Any] | None:
    """
    Extracts JSON-LD scripts and article text from a BeautifulSoup object.

    Args:
        soup: The BeautifulSoup object of the parsed HTML page.

    Returns:
        A dictionary containing the list of parsed JSON-LD objects and the
        scrubbed article text, or None if no JSON-LD is found.
    """
    script_tags = soup.find_all("script", type="application/ld+json")
    ld_datas: List[Dict[str, Any]] = []

    for script_tag in script_tags:
        # Ensure the tag has content
        if not script_tag.string:
            continue
        try:
            ld_datas.append(json.loads(script_tag.string))
        except json.JSONDecodeError:
            logging.warning("Failed to decode a JSON-LD script tag.")
            continue

    if not ld_datas:
        return None

    # Extract all text in <p> tags and clean it
    article_text = " ".join(p.get_text(strip=True) for p in soup.find_all("p"))
    cleaned_article_text = scrub_text(article_text)

    return {"ld_json_list": ld_datas, "article_text": cleaned_article_text}
