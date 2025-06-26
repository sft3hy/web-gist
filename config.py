# config.py
"""
Configuration constants for the web scraper and parser application.
"""
import os

# --- Scraping Parameters ---
CHAR_LIMIT = 32750  # Character limit for article text in CSV output.

# For batch processing from a large list of URLs.
# Defines the slice of URLs to process from the input file.
BEGIN_ROW = 3154
END_ROW = 3865


# --- LLM Models ---

# Model for extracting metadata from full HTML content.
# Using a modern, cost-effective, and powerful model is recommended.
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Local Ollama model for inferring metadata from a URL string only.
# This model name MUST match the one defined in your `Modelfile`.
OLLAMA_URL_PARSER_MODEL = "link-parser"
OLLAMA_API_BASE_URL = os.environ.get(
    "OLLAMA_API_BASE_URL", "http://localhost:11434/api/chat"
)


# --- Logging ---
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
