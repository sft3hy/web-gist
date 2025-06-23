import os
from pathlib import Path
import pprint  # Used for pretty-printing the output dictionary


def get_file_contents_recursively(directory_path: str) -> dict:
    """
    Recursively goes through each file in a directory and its subdirectories
    and gets its text content.

    Rules:
    - For files named 'Links.csv' or 'temp.txt', it reads only the first 3 lines.
    - For all other files, it reads the entire content.
    - It ignores any files or directories that start with a dot (e.g., '.git', '.DS_Store').
    - It ignores specific folders like '__pycache__' and '.vscode'.
    - It skips files that cannot be decoded as text (like images or binaries).

    Args:
        directory_path: The path to the root directory to scan.

    Returns:
        A dictionary where keys are the relative file paths (e.g.,
        'src/main.py') and values are the text contents.
    """
    path = Path(directory_path)

    if not path.is_dir():
        print(f"Error: The path '{directory_path}' is not a valid directory.")
        return {}

    file_contents = {}
    special_files = {
        "Links.csv",
        "temp.txt",
        "Enriched_Links_Updated.csv",
        "proxies_list.txt",
    }
    lines_to_read = 3

    # --- NEW: Set of directory names to completely ignore ---
    # Using a set provides fast lookups.
    ignored_dirs = {"__pycache__", ".vscode", ".git", "node_modules"}

    # Use path.rglob('*') to recursively find all items
    for item in path.rglob("*"):
        # Get the path relative to the starting directory
        relative_item_path = item.relative_to(path)

        # --- UPDATED LOGIC TO IGNORE HIDDEN AND SPECIFIC FOLDERS ---
        # Check if any part of the path is in the ignored_dirs set or starts with a '.'
        is_ignored = any(
            part in ignored_dirs or part.startswith(".")
            for part in relative_item_path.parts
        )

        if is_ignored:
            continue  # Skip to the next item in the loop

        # Ensure we are only processing files from here on
        if item.is_file():
            # Use forward slashes for cross-platform consistency in keys
            relative_path_key = str(relative_item_path).replace("\\", "/")

            try:
                with open(item, "r", encoding="utf-8", errors="ignore") as f:
                    if item.name in special_files:
                        lines = [next(f) for _ in range(lines_to_read)]
                        content = "".join(lines)
                        print(
                            f"-> Reading first {lines_to_read} lines from '{relative_path_key}'..."
                        )
                    else:
                        content = f.read()

                    file_contents[relative_path_key] = content

            except StopIteration:
                file_contents[relative_path_key] = content
            except Exception as e:
                print(
                    f"Warning: Could not read '{relative_path_key}' due to an error: {e}. Skipping."
                )

    return file_contents


# --- Main execution block ---
if __name__ == "__main__":
    target_directory = "."

    import sys

    if len(sys.argv) > 1:
        target_directory = sys.argv[1]

    print(
        f"Recursively scanning for text files in: '{os.path.abspath(target_directory)}'\n"
    )

    all_contents = get_file_contents_recursively(target_directory)

    if all_contents:
        print("\n--- File Contents Found ---")
        pprint.pprint(all_contents)
    else:
        print(
            "No readable text files or directories were found after applying ignore rules."
        )
