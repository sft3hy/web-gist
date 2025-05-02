import csv
from urllib.parse import urlparse


def get_lonely_first_column_entries(csv_path):
    """
    Reads a CSV file and returns a list of values from the first column
    of rows where all other columns are empty.
    """

    def try_open(encoding):
        results = []
        with open(csv_path, newline="", encoding=encoding, errors="replace") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if (
                    row
                    and row[0].strip()
                    and all(cell.strip() == "" for cell in row[1:])
                ):
                    netloc = urlparse(row[0].strip()).netloc
                    base_domain = ".".join(netloc.split(".")[-2:])
                    final = "https://" + base_domain
                    # results.append(row[0].strip())
                    results.append(final)
        return results

    try:
        return try_open("utf-8")  # <-- Add `return` here
    except Exception as e:
        print(e)
        return try_open("ISO-8859-1")  # <-- And here


print(set(get_lonely_first_column_entries("personal_batched_csvs/Enriched_Links3.csv")))
print(len(get_lonely_first_column_entries("personal_batched_csvs/Enriched_Links3.csv")))
