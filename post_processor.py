# post_processor.py
import csv
import logging
from pathlib import Path

# Reuse the core processing logic
from batch_website_scraper import (
    process_single_url,
    get_naughty_link_bases,
    write_csv_header,
    write_csv_row,
)

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def is_row_lonely(row: list[str]) -> bool:
    """Checks if a row has a URL in the first cell and is empty otherwise."""
    if not row or not row[0].strip():
        return False
    return all(not cell.strip() for cell in row[1:])


def process_and_enrich_csv(input_path: str, output_path: str):
    """
    Reads an input CSV, re-processes "lonely" rows (URL only), and writes to a new CSV.
    """
    in_path = Path(input_path)
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not in_path.exists():
        logging.error(f"Input file not found: {in_path}")
        return

    naughty_link_bases = get_naughty_link_bases()
    logging.info("Starting CSV enrichment process...")

    try:
        # ~line 31
        with in_path.open(
            "r", newline="", encoding="utf-8", errors="replace"
        ) as infile, out_path.open("w", newline="", encoding="utf-8-sig") as outfile:

            reader = csv.reader(infile)
            writer = csv.writer(outfile)

            # Assuming the header might be missing or different, so we write a standard one
            # and skip the original header if present.
            header = next(reader)  # Skip header
            write_csv_header(writer)

            for i, row in enumerate(reader, 1):
                if is_row_lonely(row):
                    url = row[0].strip()
                    logging.info(f"[Row {i}] Lonely row found. Reprocessing URL: {url}")
                    result = process_single_url(url, naughty_link_bases)
                    write_csv_row(writer, result)
                else:
                    # Healthy rows are written as-is, assuming they match the new format.
                    # This part might need adjustment if the input format is very different.
                    # For now, we write it, but it might not align perfectly.
                    writer.writerow(row)

        logging.info(f"Enrichment complete. Output saved to {out_path}")

    except Exception as e:
        logging.error(f"An error occurred during CSV processing: {e}", exc_info=True)


if __name__ == "__main__":
    INPUT_CSV = "personal_batched_csvs/Enriched_Links_Updated.csv"
    OUTPUT_CSV = "personal_batched_csvs/Enriched_Links_Re-processed.csv"

    process_and_enrich_csv(INPUT_CSV, OUTPUT_CSV)
