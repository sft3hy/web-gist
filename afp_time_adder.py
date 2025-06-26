# afp_time_adder.py
import csv
import re
import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Define constants for clarity
ET_ZONE = ZoneInfo("America/New_York")
UTC_ZONE = ZoneInfo("UTC")


def extract_afp_datetime(url: str) -> str | None:
    """
    Extracts a datetime string from an AFP URL and converts it to Eastern Time.

    Example URL part: .20250416T170321Z
    Returns: 4/16/2025T13:03:21
    """
    match = re.search(r"\.([\d]{8}T[\d]{6})Z", url)
    if not match:
        return None

    dt_str = match.group(1)
    try:
        dt_utc = datetime.strptime(dt_str, "%Y%m%dT%H%M%S").replace(tzinfo=UTC_ZONE)
        dt_et = dt_utc.astimezone(ET_ZONE)
        # Format: 4/16/2025T13:03:21
        return dt_et.strftime("%-m/%-d/%YT%H:%M:%S")
    except (ValueError, TypeError):
        return None


def main(input_file: Path, output_file: Path):
    """
    Reads a CSV, finds rows with 'AFP' as the source, and attempts to
    add a more precise timestamp based on the URL.
    """
    if not input_file.exists():
        print(f"Error: Input file not found at {input_file}")
        return

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with input_file.open("r", newline="", encoding="utf-8") as infile, output_file.open(
        "w", newline="", encoding="utf-8"
    ) as outfile:

        # Using DictReader and DictWriter for robust column handling
        # This assumes the input CSV has a header.
        reader = csv.DictReader(infile)
        if not reader.fieldnames:
            print("Error: Could not read header from input CSV.")
            return

        # Ensure all expected fields are in the writer
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            # Check if source is AFP
            if row.get("source", "").strip().upper() == "AFP":
                new_date = extract_afp_datetime(row.get("URL", ""))
                if new_date:
                    row["published_date"] = new_date
                    row["modified_date"] = new_date

            writer.writerow(row)

    print(f"Processing complete. Output saved to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Enrich a CSV file by extracting precise datetimes from AFP URLs."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=Path("personal_batched_csvs/Enriched_Links_Updated.csv"),
        help="Path to the input CSV file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("personal_batched_csvs/Enriched_Links_AFP_Updated.csv"),
        help="Path to the output CSV file.",
    )
    args = parser.parse_args()

    main(args.input, args.output)
