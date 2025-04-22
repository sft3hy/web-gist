import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dateutil import parser
from pytz import timezone, utc
import json
from config import CHAR_LIMIT

def get_source_from_url(url):
    domain = urlparse(url).netloc.lower()
    if "reuters" in domain:
        return "reuters"
    elif "apnews" in domain:
        return "ap"
    elif "washingtonpost" in domain:
        return "washingtonpost"
    elif "afp" in domain:
        return "afp"
    elif "bbc" in domain:
        return "bbc"
    elif "bloomberg" in domain:
        return "bloomberg"
    elif "jpost" in domain:
        return "jpost"
    elif "yonhapnews" in domain:
        return "yonhap"
    elif "nikkei" in domain:
        return "nikkei"
    elif "france24" in domain:
        return "france24"
    return "generic"

def convert_utc_to_edt(date_str):
    try:
        dt = parser.parse(date_str)
        dt = dt.replace(tzinfo=utc)
        edt = dt.astimezone(timezone("US/Eastern"))
        return edt.isoformat()
    except Exception:
        return date_str

def parse_html_for_llm(url):
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive",
        }
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        result = []
        pretty_text = []
        article_paragraphs = []

        source = get_source_from_url(url)

        # ===== TITLE =====
        title = ""
        if source == "ap":
            tag = soup.select_one("h1.Page-headline")
            if tag:
                title = tag.get_text(strip=True)
        elif source == "washingtonpost":
            title = url.split("/")[-1].replace("-", " ").title()
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()

        if title:
            result.append(f"# Title: {title}\n")

        # ===== AUTHOR =====
        author = ""
        if source == "ap":
            tag = soup.select_one("div.Page-authors")
            if tag:
                author = tag.get_text(" ", strip=True).replace("By ", "")
        elif source == "bbc":
            tag = soup.select_one("[data-testid='byline-new-contributors']")
            if tag:
                author = tag.get_text(" ", strip=True)
        else:
            author_selectors = [
                'meta[name="author"]',
                'meta[property="article:author"]',
                '[class*=author]',
                '.byline',
                '[rel=author]'
            ]
            for selector in author_selectors:
                tag = soup.select_one(selector)
                if tag:
                    content = tag.get('content') or tag.get_text(strip=True)
                    if content:
                        author = content.split("/")[-1].replace("-", " ").title() if "http" in content else content
                        break

        if author:
            result.append(f"# Author: {author}\n")

        # ===== PUBLISH & UPDATE DATES =====
        published = ""
        updated = ""

        if source == "jpost":
            pub_tag = soup.select_one("section.published-date-data time")
            if pub_tag:
                published = pub_tag.get("datetime") or pub_tag.get_text(strip=True)
            upd_tag = soup.select_one("section.updated-date-data")
            if upd_tag:
                updated = upd_tag.get_text(strip=True).replace("Updated:", "").strip()
        elif source == "nikkei":
            pub_tag = soup.select_one("div.ArticleTimestamp_articleTimestamp__Oknqo span")
            if pub_tag:
                published = pub_tag.get_text(strip=True)
            upd_tag = soup.select_one("div.ArticleTimestamp_articleTimestampUpdated__3hUKK span")
            if upd_tag:
                updated = upd_tag.get_text(strip=True)
        elif source == "france24":
            pub = soup.select_one("span.m-pub-dates__date time[pubdate]")
            if pub:
                published = pub.get("datetime") or pub.get_text(strip=True)
            mod = soup.select("span.m-pub-dates__date time")
            if len(mod) > 1:
                updated = mod[1].get("datetime") or mod[1].get_text(strip=True)
        else:
            date_meta = {
                "published": [
                    "meta[property='article:published_time']",
                    "meta[name='pubdate']",
                    "meta[name='publish-date']",
                    "meta[name='date']",
                    "meta[itemprop='datePublished']",
                    "time[datetime]",
                    "time[class*=Timestamp]",
                    "span[class*=date]",
                    "span[class*=published]",
                    "span[class*='date-line__date']",
                    "span.txt"
                ],
                "updated": [
                    "meta[property='article:modified_time']",
                    "meta[name='lastmod']",
                    "meta[itemprop='dateModified']",
                    "meta[name='updated']",
                    "meta[name='last-modified']",
                    "time[datetime]",
                    "time[class*=Timestamp]",
                    "span[class*=updated]",
                    "span[class*=date]",
                    "span[class*='date-line__date']"
                ]
            }

            for key, selectors in date_meta.items():
                for selector in selectors:
                    tag = soup.select_one(selector)
                    if tag:
                        val = tag.get("content") or tag.get("datetime") or tag.get_text(strip=True)
                        if key == "published" and val and not published:
                            published = val
                        elif key == "updated" and val and not updated:
                            updated = val

            for tag in soup.find_all("time"):
                val = tag.get("datetime") or tag.get_text(strip=True)
                if not published:
                    published = val
                elif not updated:
                    updated = val

            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        if "datePublished" in data and not published:
                            published = data["datePublished"]
                        if "dateModified" in data and not updated:
                            updated = data["dateModified"]
                except:
                    continue

        if published and not updated:
            updated = published
        elif updated and not published:
            published = updated

        if source == "reuters":
            with open('sample.html', 'w') as f:
                f.write(str(soup))
            if published:
                published = convert_utc_to_edt(published)
            if updated:
                updated = convert_utc_to_edt(updated)

        if source == "bloomberg":
            published = updated = ""

        if published:
            result.append(f"# Published: {published}\n")
        if updated:
            result.append(f"# Updated: {updated}\n")

        # ===== ARTICLE TEXT =====
        if source == "ap":
            article_paragraphs = [p.get_text(strip=True) for p in soup.select("div.RichTextStoryBody.RichTextBody p")]
        elif source == "france24":
            div = soup.select_one("div.t-content__body")
            if div:
                article_paragraphs = [p.get_text(strip=True) for p in div.find_all("p")]
        elif source == "washingtonpost" or source == "bloomberg":
            article_paragraphs = []
        else:
            known_selectors = [
                'div[data-testid^="paragraph"]',
                'div[class*="article-body__paragraph"]',
                'div[class*="text__text__"]',
                'div.article-body__content__17Yit',
                'div.ArticleBody__content___2gQno'
            ]
            for selector in known_selectors:
                for tag in soup.select(selector):
                    text = tag.get_text(strip=True)
                    if text:
                        article_paragraphs.append(text)

            if not article_paragraphs:
                for tag in soup.find_all('p'):
                    text = tag.get_text(strip=True)
                    if text:
                        article_paragraphs.append(text)

        for para in article_paragraphs:
            result.append(f"{para}\n")
            pretty_text.append(f"{para}\n")

        to_return = '\n'.join(result)[:CHAR_LIMIT]
        prettier_text = '\n'.join(pretty_text)

        return [to_return, prettier_text]

    except Exception as e:
        print("Error parsing HTML:", e)
        return ["", ""]
