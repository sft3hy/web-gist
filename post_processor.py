import csv
from utils.llm_utils import ArticleInfo, gemini_parse_web_content
from batch_website_scraper import call_groq, get_naughty_links
from utils.json_ld_finder import extract_ld_json_and_article
from config import GEMINI_MODEL, CHAR_LIMIT
from bs4 import BeautifulSoup
from utils.scraping_utils import scrape_site, remove_paths_and_urls


def scrape_link(url: str, writer):
    naughties = get_naughty_links()
    for naughty in naughties:
        if naughty in url:
            call_groq(writer=writer, url=url)
    else:
        try:
            llm = GEMINI_MODEL
            print("link passed the vibe check")
            html = scrape_site(url)

            soup = BeautifulSoup(html, "html.parser")

            json_ld_try = extract_ld_json_and_article(soup)

            # Remove noisy elements to reduce token count
            for tag in soup(
                [
                    "script",
                    "style",
                    "nav",
                    "footer",
                    "aside",
                    "noscript",
                    "iframe",
                    "link",
                    "picture",
                    "source",
                    "img",
                ]
            ):
                tag.decompose()

            # Optionally keep only relevant top-level sections (e.g. <article>, <main>, etc.)
            main_content = soup.find("article") or soup.find("main") or soup.body

            # If found, keep only the main content; else fallback to the cleaned soup
            if main_content:
                cleaned_html = str(main_content)
            else:
                cleaned_html = str(soup)

            pass_dict = {"URL": url}
            if json_ld_try is not None:
                pass_dict["json_ld"] = json_ld_try
            pass_dict["raw_html"] = cleaned_html

            token_est = len(str(pass_dict)) / 4

            print("token estimate of pass_dict:", token_est)
            parsed_dict = gemini_parse_web_content(pass_dict)
            writer.writerow(
                [
                    url,
                    remove_paths_and_urls(parsed_dict.article_text)[:CHAR_LIMIT],
                    parsed_dict.title,
                    parsed_dict.authors,
                    parsed_dict.source,
                    parsed_dict.published_date,
                    parsed_dict.updated_date,
                    llm,
                ]
            )
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            print("calling groq")
            call_groq(writer=writer, url=url)


def process_and_enrich_csv(
    input_path="personal_batched_csvs/Enriched_Links2.csv",
    output_path="personal_batched_csvs/Enriched_Links3.csv",
):
    """
    Reads input CSV and writes a new CSV with enriched data:
    - Healthy rows are copied as-is.
    - Lonely rows are processed using `scrape_link(url)` and replaced.
    """

    def try_open(encoding):
        with open(
            input_path, newline="", encoding=encoding, errors="replace"
        ) as infile, open(output_path, "w", newline="", encoding="utf-8") as outfile:
            reader = csv.reader(infile)
            writer = csv.writer(outfile)
            for row in reader:
                # If the row is completely empty, write it as-is
                if not any(cell.strip() for cell in row):
                    writer.writerow(row)
                # Lonely row: first cell has data, rest are empty
                elif row[0].strip() and all(cell.strip() == "" for cell in row[1:]):
                    scrape_link(url=row[0].strip(), writer=writer)
                else:
                    writer.writerow(row)

    try:
        try_open("utf-8")
    except UnicodeDecodeError:
        try_open("ISO-8859-1")


process_and_enrich_csv()
