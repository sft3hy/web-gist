# Web-Gist: AI-Powered Batch URL Parser & Metadata Extractor

`web-gist` is a professional-grade web scraping and content analysis tool that leverages advanced Large Language Models (LLMs) to extract structured metadata and core article content from any given URL. Designed for high throughput and precision, it transforms raw web pages into clean, actionable data.

---

## 🚀 High-Level Overview

At its core, **web-gist** acts as a bridge between the unstructured web and structured data. It takes a list of URLs and automatically performs the following:

1.  **Smart Scraping**: Uses Playwright and BeautifulSoup to navigate and extract raw HTML content, effectively bypassing common bot detection mechanisms.
2.  **Metadata Extraction**: Intelligently identifies and extracts critical article information including:
    *   **Title**
    *   **Authors**
    *   **Source/Publisher**
    *   **Published & Modified Dates**
    *   **Full Article Text** (cleaned and formatted)
3.  **LLM-Driven Analysis**: Employs **Google Gemini 2.5 Flash** for sophisticated content parsing and **Ollama (link-parser)** for specialized local processing.
4.  **Batch Processing**: Handles multiple URLs concurrently, significantly reducing the time required for large-scale data collection.
5.  **Interactive Dashboard**: Provides a sleek **Streamlit** interface for manual URL input, file uploads (CSV/TXT), real-time progress tracking, and easy results download.

---

## 🛠 Detailed Technical Explanation

### 🏗 Architecture & Core Components

#### 1. Frontend: Streamlit (`URL_Parser.py`)
The primary entry point is a Streamlit application designed for user-friendliness and efficiency.
*   **Input Flexibility**: Users can paste URLs directly or upload `.csv` and `.txt` files containing batches of links.
*   **Real-time Feedback**: As URLs are processed, the UI updates with success/failure metrics and interactive result cards.
*   **Result Persistence**: Automatically saves processing output to partitioned CSV files in the `user_facing_csvs/` directory.

#### 2. Orchestration: Batch Scraper (`batch_website_scraper.py`)
Handles the lifecycle of a URL parsing job:
*   **Concurrency Control**: Utilizes `ThreadPoolExecutor` (defaulting to 3 workers) to parallelize scraping and LLM calls.
*   **Naughty List Redirection**: Specifically identifies problematic or restricted domains and reroutes them to a local LLM parser (`link-parser`) to ensure continuous operation.
*   **Content Sanitization**: Implements `BeautifulSoup` to strip non-essential HTML tags (scripts, styles, navs, etc.) before handing content to the LLM.

#### 3. Intelligence Layer: LLM Integration (`utils/llm_utils.py`)
This layer handles all interactions with AI models:
*   **Gemini 2.0/1.5/2.5 Flash**: The primary workforce. It processes truncated HTML and JSON-LD data to return a structured `ArticleInfo` object.
*   **Ollama (Link-Parser)**: A localized fallback for high-security or complex sites where raw HTML scraping is less effective than direct URL string inference.

#### 4. Scraping Engine (`utils/scraping_utils.py`)
*   **Playwright Stealth**: Uses headless browser technology with stealth plugins to mimic human browsing behavior, defeating anti-scraping measures.
*   **JSON-LD Finder**: Specifically targets structured data embedded in the page to ensure date and authorship accuracy.

### 📁 File Structure

```text
web-gist/
├── URL_Parser.py           # Main Streamlit application
├── batch_website_scraper.py # Core processing and batch logic
├── config.py               # Central configuration (models, limits, paths)
├── utils/                  # Implementation helpers
│   ├── llm_utils.py        # Gemini & Ollama API wrappers
│   ├── scraping_utils.py   # Playwright & BeautifulSoup logic
│   └── json_ld_finder.py   # Specialized structured data extractor
├── prompts/                # System instructions for LLM extraction
├── user_facing_csvs/       # Output directory for processed results
└── requirements.txt        # Python dependency list
```

---

## ⚡ Quick Start

### 1. Prerequisites
*   Python 3.10+
*   Google Gemini API Key
*   Ollama (optional, for localized parsing)

### 2. Installation
```bash
# Clone the repository
git clone <repository-url>
cd web-gist

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 3. Configuration
Create a `.env` file or export your environment variables:
```bash
export GEMINI_API_KEY='your_api_key_here'
```

### 4. Running the App
```bash
streamlit run URL_Parser.py
```

---

## 🛡 Security & Best Practices
*   **Rate Limiting**: Integrated `backoff` logic handles API rate limits gracefully.
*   **Content Sanitization**: Automatic character limits (`CHAR_LIMIT`) and text scrubbing prevent token overflow in LLM requests.
*   **Proxy Support**: Configurable proxy lists for enhanced scraping reliability in restrictive environments.
