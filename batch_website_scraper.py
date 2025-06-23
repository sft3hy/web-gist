# batch_website_scraper.py
import csv
import logging
import re
from pathlib import Path

from bs4 import BeautifulSoup

from config import CHAR_LIMIT, GEMINI_MODEL, BEGIN_ROW, END_ROW
from utils.llm_utils import (
    ArticleInfo,
    gemini_extract_article_info,
    ollama_parse_url_metadata,
)
from utils.scraping_utils import scrape_site, fix_mojibake
from utils.json_ld_finder import extract_ld_json_and_article

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Helper Functions ---


def load_urls_from_file(file_path: Path) -> list[str]:
    """Loads non-empty, stripped URLs from a text file."""
    if not file_path.exists():
        logging.warning(f"URL file not found: {file_path}")
        return []
    with file_path.open("r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def get_naughty_link_bases() -> set[str]:
    """Loads and processes 'naughty links' to get a set of base URLs for quick checking."""
    naughty_links_path = Path("txt_files/new_naughty_links.txt")
    urls = load_urls_from_file(naughty_links_path)
    # Return a set of base URLs (e.g., 'https://www.example.com') for faster matching
    return {"/".join(link.split("/")[:3]) for link in urls}


def write_csv_header(writer):
    """Writes the standard header to the CSV file."""
    writer.writerow(
        [
            "url",
            "title",
            "authors",
            "source",
            "published_date",
            "updated_date",
            "llm_used",
            "status",
            "error_message",
            "article_text",
        ]
    )


def write_csv_row(writer, result: dict):
    """Writes a result dictionary to the CSV file."""
    info = result.get("article_info")
    if isinstance(info, ArticleInfo):
        writer.writerow(
            [
                result.get("url"),
                info.title,
                info.authors,
                info.source,
                info.published_date,
                info.updated_date,
                result.get("llm_used"),
                result.get("status"),
                "",  # No error message
                fix_mojibake(info.article_text[:CHAR_LIMIT]),
            ]
        )
    else:  # Failure case
        writer.writerow(
            [
                result.get("url"),
                "",
                "",
                "",
                "",
                "",
                result.get("llm_used", "N/A"),
                result.get("status"),
                result.get("error_message", "Unknown error"),
                "",
            ]
        )


# --- Core Processing Logic ---


def process_single_url(url: str, naughty_link_bases: set) -> dict:
    """
    Processes a single URL from scraping to LLM extraction.
    Returns a dictionary with the processing result.
    """
    # 1. Check if URL is on the naughty list
    base_url = "/".join(url.split("/")[:3])
    if base_url in naughty_link_bases:
        logging.info(f"URL on naughty list, parsing with Ollama: {url}")
        try:
            article_info = ollama_parse_url_metadata(url)
            if article_info:
                return {
                    "url": url,
                    "article_info": article_info,
                    "status": "success_url_parser",
                    "llm_used": "ollama-url-parser",
                }
            else:
                raise ValueError("Ollama parser returned None")
        except Exception as e:
            logging.error(f"Ollama URL parser failed for {url}: {e}")
            return {
                "url": url,
                "article_info": None,
                "status": "error_url_parser",
                "error_message": str(e),
                "llm_used": "ollama-url-parser",
            }

    # 2. Scrape the site if it's not a naughty link
    try:
        logging.info(f"Scraping: {url}")
        html_bytes = scrape_site(url)
        soup = BeautifulSoup(html_bytes, "html.parser")

        # 3. Extract content for LLM
        # Remove noisy tags to reduce tokens and improve focus
        for tag in soup(["script", "style", "nav", "footer", "aside", "form"]):
            tag.decompose()

        main_content = soup.find("article") or soup.find("main") or soup.body
        content_text = (
            main_content.get_text(separator=" ", strip=True) if main_content else ""
        )
        content_text = re.sub(r"\s+", " ", content_text).strip()

        # Find JSON-LD data
        json_ld_data = extract_ld_json_and_article(soup)

        # 4. Prepare data and call Gemini
        pass_dict = {"url": url}
        if json_ld_data:
            pass_dict["json_ld"] = json_ld_data
        if content_text:
            # Fix potential mojibake before sending to LLM
            pass_dict["website_content"] = fix_mojibake(content_text)

        logging.info(f"Extracting metadata with Gemini for: {url}")
        article_info = gemini_extract_article_info(pass_dict)

        return {
            "url": url,
            "article_info": article_info,
            "status": "success",
            "llm_used": GEMINI_MODEL,
        }

    except Exception as e:
        logging.error(f"Full scraping/parsing failed for {url}: {e}")
        return {
            "url": url,
            "article_info": None,
            "status": "error_scraping",
            "error_message": str(e),
            "llm_used": "N/A",
        }


# --- Main Orchestration Function ---


def process_urls(
    url_list: list[str], output_filename: str, for_streamlit: bool = False
) -> dict:
    """
    Takes a list of URLs, processes them, writes to a CSV, and returns results.
    """
    output_path = Path(output_filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    naughty_link_bases = get_naughty_link_bases()
    all_results = []

    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        write_csv_header(writer)

        total_urls = len(url_list)
        for i, url in enumerate(url_list, 1):
            logging.info(f"--- Processing URL {i}/{total_urls}: {url} ---")

            if not url or not url.startswith(("http://", "https://")):
                logging.warning(f"Skipping invalid URL: {url}")
                result = {
                    "url": url,
                    "article_info": None,
                    "status": "error_invalid_url",
                    "error_message": "Invalid or empty URL",
                    "llm_used": "N/A",
                }
            else:
                result = process_single_url(url, naughty_link_bases)

            all_results.append(result)
            write_csv_row(writer, result)

            if for_streamlit:
                # In Streamlit, we can provide real-time feedback
                # but for now, we'll just log.
                pass

    logging.info(f"Processing complete. Results saved to {output_path}")
    return {"articles": all_results, "file_path": str(output_path)}


if __name__ == "__main__":
    # This block allows running the script directly for batch processing.
    logging.info("Starting batch scraping process...")

    links_path = Path("txt_files/Links.txt")
    urls_to_process = load_urls_from_file(links_path)

    if not urls_to_process:
        logging.error("No URLs found to process. Exiting.")
    else:
        # Slice the URLs based on config for batching
        urls_subset = urls_to_process[BEGIN_ROW:END_ROW]
        logging.info(
            f"Loaded {len(urls_to_process)} URLs, processing slice [{BEGIN_ROW}:{END_ROW}] ({len(urls_subset)} URLs)."
        )

        output_file = f"personal_batched_csvs/Parsed_links_{BEGIN_ROW+1}-{END_ROW}.csv"
        process_urls(urls_subset, output_file)

    logging.info("🎉 Batch scraping done!")
