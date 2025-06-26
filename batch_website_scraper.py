# batch_website_scraper.py
import csv
import logging
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Optional
from functools import lru_cache
import time

from bs4 import BeautifulSoup

from config import CHAR_LIMIT, GEMINI_MODEL, BEGIN_ROW, END_ROW
from utils.llm_utils import (
    ArticleInfo,
    gemini_extract_article_info,
    ollama_parse_url_metadata,
    process_urls_sync,  # Import the new batch processing function
)
from utils.scraping_utils import scrape_site, fix_mojibake
from utils.json_ld_finder import extract_ld_json_and_article

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Helper Functions (OPTIMIZED) ---


@lru_cache(maxsize=1)
def load_urls_from_file(file_path: Path) -> list[str]:
    """Cached URL loading to avoid repeated file reads."""
    if not file_path.exists():
        logging.warning(f"URL file not found: {file_path}")
        return []
    with file_path.open("r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


@lru_cache(maxsize=1)
def get_naughty_link_bases() -> set[str]:
    """Cached naughty links to avoid repeated file reads."""
    naughty_links_path = Path("txt_files/new_naughty_links.txt")
    urls = load_urls_from_file(naughty_links_path)
    return {"/".join(link.split("/")[:3]) for link in urls}


def has_good_json_ld_dates(json_ld_data: dict) -> bool:
    """Check if JSON-LD has good date information."""
    if not json_ld_data:
        return False

    # Check for common date fields in JSON-LD
    date_fields = [
        "datePublished",
        "dateModified",
        "dateCreated",
        "publishedDate",
        "modifiedDate",
    ]
    return any(json_ld_data.get(field) for field in date_fields)


def clean_content_fast(soup: BeautifulSoup) -> str:
    """Faster content cleaning with targeted removal."""
    # Remove unwanted elements in one pass
    unwanted_tags = ["script", "style", "nav", "footer", "aside", "form", "header"]

    for tag_name in unwanted_tags:
        for element in soup.find_all(tag_name):
            element.decompose()

    # Get main content with priority order
    content_candidates = [
        soup.find("article"),
        soup.find("main"),
        soup.body,
    ]

    main_content = next((c for c in content_candidates if c), soup)
    if not main_content:
        return ""

    # Extract text more efficiently
    content_text = main_content.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", content_text).strip()


def write_csv_header(writer):
    """CSV header writing."""
    writer.writerow(
        [
            "url",
            "title",
            "authors",
            "source",
            "published_date",
            "modified_date",
            "llm_used",
            "status",
            "error_message",
            "article_text",
        ]
    )


def write_csv_row(writer, result: dict):
    """Optimized CSV row writing."""
    info = result.get("article_info")
    if isinstance(info, ArticleInfo):
        writer.writerow(
            [
                result.get("url"),
                info.title,
                info.authors,
                info.source,
                info.published_date,
                info.modified_date,
                result.get("llm_used"),
                result.get("status"),
                "",
                fix_mojibake(info.article_text[:CHAR_LIMIT]),
            ]
        )
    else:
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


# --- Core Processing Logic (HEAVILY OPTIMIZED) ---


def process_single_url_fast(
    url: str,
    naughty_link_bases: set,
    status_callback: Callable[[str], None] = lambda msg: None,
) -> dict:
    """
    Optimized single URL processing with better error handling and speed.
    """
    start_time = time.time()

    # Quick validation
    if not url or not url.startswith(("http://", "https://")):
        return {
            "url": url,
            "article_info": None,
            "status": "error_invalid_url",
            "error_message": "Invalid or empty URL",
            "llm_used": "N/A",
        }

    base_url = "/".join(url.split("/")[:3])

    # Handle naughty list
    if base_url in naughty_link_bases:
        status_callback(f"Using local parser for naughty site: {url}")
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

    try:
        # Step 1: Scraping (with timeout handling)
        status_callback(f"🌐 Scraping: {url}")
        logging.info(f"Scraping: {url}")

        html_bytes = scrape_site(url)
        soup = BeautifulSoup(html_bytes, "html.parser")

        # Step 2: Extract JSON-LD data
        status_callback("📊 Extracting JSON-LD metadata...")
        json_ld_data = extract_ld_json_and_article(soup)

        # Step 3: Fast content cleaning
        status_callback("🧹 Cleaning content...")
        content_text = clean_content_fast(soup)

        # Truncate very long content for speed
        if len(content_text) > 50000:
            content_text = content_text[:50000] + "... [truncated for processing speed]"
            logging.info(f"Content truncated for {url}")

        # Step 4: Prepare data for LLM
        pass_dict = {
            "url": url,
            "website_content": fix_mojibake(content_text) if content_text else "",
        }

        # Add JSON-LD if available
        if json_ld_data:
            pass_dict["json_ld"] = json_ld_data

        # If JSON-LD doesn't have good date info, pass raw HTML for date extraction
        if not has_good_json_ld_dates(json_ld_data):
            status_callback("📅 No good dates in JSON-LD, including raw HTML...")
            # Get raw HTML (truncated for LLM efficiency)
            raw_html = str(soup)[:20000]  # Limit to first 20k chars
            pass_dict["raw_html_for_dates"] = raw_html
            logging.info(f"Including raw HTML for date extraction: {url}")

        # Step 5: LLM extraction
        status_callback("🤖 Analyzing URL content...")
        logging.info(f"Extracting metadata with Gemini for: {url}")

        article_info = gemini_extract_article_info(pass_dict)

        processing_time = time.time() - start_time
        logging.info(f"✅ Processed {url} in {processing_time:.2f}s")

        return {
            "url": url,
            "article_info": article_info,
            "status": "success",
            "llm_used": GEMINI_MODEL,
        }

    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"Failed after {processing_time:.2f}s: {str(e)}"
        status_callback(f"❌ Error: {str(e)}")
        logging.error(f"Full scraping/parsing failed for {url}: {e}")
        return {
            "url": url,
            "article_info": None,
            "status": "error_scraping",
            "error_message": error_msg,
            "llm_used": "N/A",
        }


# --- Batch Processing Functions (NEW) ---


def process_urls_batch_concurrent(
    url_list: list[str],
    output_filename: str,
    status_callback: Optional[Callable[[str], None]] = None,
    max_workers: int = 3,
    use_batch_llm: bool = True,
) -> dict:
    """
    Process URLs with concurrent scraping and batch LLM processing.
    """
    _status_callback = status_callback or (lambda msg: None)

    output_path = Path(output_filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    naughty_link_bases = get_naughty_link_bases()

    start_time = time.time()
    total_urls = len(url_list)
    all_results = []

    _status_callback(f"🚀 Starting batch processing of {total_urls} URLs...")

    # Phase 1: Concurrent scraping and data preparation
    scraping_results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all scraping tasks
        future_to_url = {
            executor.submit(
                process_single_url_fast,
                url,
                naughty_link_bases,
                lambda msg, u=url: _status_callback(
                    f"[{url_list.index(u)+1}/{total_urls}] {msg}"
                ),
            ): url
            for url in url_list
        }

        # Collect results as they complete
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                scraping_results.append(result)

                success_count = len(
                    [r for r in scraping_results if r.get("status") == "success"]
                )
                _status_callback(
                    f"✅ Completed {len(scraping_results)}/{total_urls} URLs ({success_count} successful)"
                )

            except Exception as e:
                logging.error(f"Future failed for {url}: {e}")
                scraping_results.append(
                    {
                        "url": url,
                        "article_info": None,
                        "status": "error_future",
                        "error_message": str(e),
                        "llm_used": "N/A",
                    }
                )

    # Phase 2: Batch LLM processing for failed items (if enabled)
    if use_batch_llm:
        failed_items = [
            r
            for r in scraping_results
            if r.get("status") != "success" and "pass_dict" in r
        ]
        if failed_items:
            _status_callback(
                f"🔄 Retrying {len(failed_items)} failed items with batch processing..."
            )
            # This would use the batch processing from llm_utils
            # Implementation depends on your specific needs

    all_results = scraping_results

    # Write results to CSV
    _status_callback("💾 Saving results to CSV...")
    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        write_csv_header(writer)

        for result in all_results:
            write_csv_row(writer, result)

    total_time = time.time() - start_time
    success_count = len([r for r in all_results if r.get("status") == "success"])

    _status_callback(
        f"🎉 Complete! Processed {success_count}/{total_urls} URLs in {total_time:.1f}s"
    )
    logging.info(
        f"Batch processing complete. {success_count}/{total_urls} successful in {total_time:.1f}s"
    )

    return {
        "articles": all_results,
        "file_path": str(output_path),
        "stats": {
            "total": total_urls,
            "successful": success_count,
            "failed": total_urls - success_count,
            "processing_time": total_time,
        },
    }


# --- Legacy Function (MODIFIED for backwards compatibility) ---


def process_urls(
    url_list: list[str],
    output_filename: str,
    status_callback: Optional[Callable[[str], None]] = None,
    use_concurrent: bool = True,
) -> dict:
    """
    Main processing function with option for concurrent or sequential processing.
    """
    if use_concurrent and len(url_list) > 1:
        return process_urls_batch_concurrent(
            url_list, output_filename, status_callback, max_workers=3
        )
    else:
        # Fallback to sequential processing for single URLs or when requested
        return process_urls_sequential(url_list, output_filename, status_callback)


def process_urls_sequential(
    url_list: list[str],
    output_filename: str,
    status_callback: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    Original sequential processing (kept for compatibility).
    """
    _status_callback = status_callback or (lambda msg: None)

    output_path = Path(output_filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    naughty_link_bases = get_naughty_link_bases()
    all_results = []

    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        write_csv_header(writer)

        total_urls = len(url_list)
        for i, url in enumerate(url_list, 1):
            _status_callback(f"Starting URL {i}/{total_urls}: {url}")
            logging.info(f"--- Processing URL {i}/{total_urls}: {url} ---")

            result = process_single_url_fast(url, naughty_link_bases, _status_callback)
            all_results.append(result)
            write_csv_row(writer, result)

    logging.info(f"Processing complete. Results saved to {output_path}")
    return {"articles": all_results, "file_path": str(output_path)}


# --- Main Execution ---

if __name__ == "__main__":
    logging.info("Starting batch scraping process...")
    links_path = Path("txt_files/Links.txt")
    urls_to_process = load_urls_from_file(links_path)

    if not urls_to_process:
        logging.error("No URLs found to process. Exiting.")
    else:
        urls_subset = urls_to_process[BEGIN_ROW:END_ROW]
        logging.info(
            f"Loaded {len(urls_to_process)} URLs, processing slice [{BEGIN_ROW}:{END_ROW}] ({len(urls_subset)} URLs)."
        )
        output_file = f"personal_batched_csvs/Parsed_links_{BEGIN_ROW+1}-{END_ROW}.csv"

        # Use concurrent processing by default
        result = process_urls(urls_subset, output_file, use_concurrent=True)

        if result.get("stats"):
            stats = result["stats"]
            logging.info(
                f"Final stats: {stats['successful']}/{stats['total']} successful in {stats['processing_time']:.1f}s"
            )

    logging.info("🎉 Batch scraping done!")
