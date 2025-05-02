import csv
import re
from datetime import datetime
from zoneinfo import ZoneInfo  # Requires Python 3.9+

ET_ZONE = ZoneInfo("America/New_York")


def extract_afp_datetime(url):
    match = re.search(r"\.([\d]{8}T[\d]{6})Z", url)
    if match:
        dt_str = match.group(1)
        dt_utc = datetime.strptime(dt_str, "%Y%m%dT%H%M%S").replace(
            tzinfo=ZoneInfo("UTC")
        )
        dt_et = dt_utc.astimezone(ET_ZONE)
        return dt_et.strftime("%-m/%-d/%YT%H:%M:%S")  # Example: 4/16/2025T13:03:21
    return None


with open(
    "personal_batched_csvs/Enriched_Links3.csv", "r", newline="", encoding="utf-8"
) as infile, open(
    "personal_batched_csvs/Enriched_Links4.csv", "w", newline="", encoding="utf-8"
) as outfile:

    reader = csv.reader(infile)
    writer = csv.writer(outfile)

    for row in reader:
        if not any(row):  # skip empty rows
            writer.writerow(row)
            continue

        row += [""] * (8 - len(row))  # Ensure length
        url, article_text, title, author, source, published_date, updated_date, llm = (
            row[:8]
        )

        if source.strip() == "AFP":
            new_date = extract_afp_datetime(url)
            if new_date:
                published_date = updated_date = new_date

        writer.writerow(
            [
                url,
                article_text,
                title,
                author,
                source,
                published_date,
                updated_date,
                llm,
            ]
        )
