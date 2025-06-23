# utils/text_scrubber.py
import re
import codecs


def scrub_text(raw_text: str | None) -> str:
    """
    Cleans a raw string by un-escaping characters and normalizing whitespace.

    Args:
        raw_text: The input string, possibly with escaped chars and messy whitespace.

    Returns:
        A cleaned, single-line string.
    """
    if not raw_text:
        return ""

    # Step 1: Decode standard escape sequences like \n, \t, \'
    try:
        # More robust way to handle escapes
        text = codecs.decode(raw_text, "unicode_escape")
    except (TypeError, ValueError):
        text = raw_text  # Fallback if decoding fails

    # Step 2: Normalize all whitespace (newlines, tabs, multiple spaces) to a single space
    text = re.sub(r"\s+", " ", text).strip()

    return text
