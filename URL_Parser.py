# URL_Parser.py
import streamlit as st
import pandas as pd
import os
from pathlib import Path

# Import refactored processing logic
from batch_website_scraper import process_urls
from utils.llm_utils import ArticleInfo
from utils.scraping_utils import fix_mojibake

# --- Page Configuration ---
st.set_page_config(
    "URL Parser",
    page_icon=":material/precision_manufacturing:",
    layout="wide",
)
st.title("🔗 URL Parser")
st.markdown(
    "Enter URLs or upload a CSV to extract metadata and article text using web scraping and AI."
)

# --- Functions ---


@st.cache_resource
def install_playwright_and_browsers():
    """
    Installs Playwright browsers and their system dependencies.
    This is cached and will only run once per application startup.
    """
    with st.spinner("⏳ Setting up environment (this happens once)..."):
        # Using st.progress to give better feedback
        # progress_bar = st.progress(0, "Installing Playwright browsers...")
        os.system("playwright install --with-deps > playwright_install.log")
        # progress_bar.progress(100, "Setup complete!")
        # st.success("Environment is ready!")
        # Clean up log file
        if os.path.exists("playwright_install.log"):
            os.remove("playwright_install.log")


def initialize_session_state():
    """Initializes session state variables."""
    if "scraping_result" not in st.session_state:
        st.session_state.scraping_result = None
    if "urls_to_process" not in st.session_state:
        st.session_state.urls_to_process = []
    if "processed_file_id" not in st.session_state:
        st.session_state.processed_file_id = None
    # Add this new state variable
    if "processing_triggered" not in st.session_state:
        st.session_state.processing_triggered = False


def handle_user_input():
    """Manages UI for URL input and file uploads."""
    st.header("Provide URLs")
    col1, col2 = st.columns([1, 1])

    with col1:
        input_urls_text = st.text_area(
            "Enter URLs (one per line or comma-separated)",
            height=150,
            placeholder="https://www.example.com/article1\nhttps://www.example.com/article2",
        )
        if input_urls_text:
            # Split by comma or newline, strip whitespace, and filter empty strings
            urls = [
                url.strip()
                for line in input_urls_text.split("\n")
                for url in line.split(",")
                if url.strip()
            ]
            if urls:
                st.session_state.urls_to_process = urls

    with col2:
        uploaded_file = st.file_uploader(
            "Or upload a CSV/TXT file of URLs", type=["csv", "txt"]
        )
        if uploaded_file:
            # Create a unique identifier for the file to prevent reprocessing on rerun
            file_id = f"{uploaded_file.name}-{uploaded_file.size}"
            if st.session_state.processed_file_id != file_id:
                try:
                    if uploaded_file.type == "text/csv":
                        df = pd.read_csv(uploaded_file, header=None)
                        urls = df.iloc[:, 0].dropna().astype(str).tolist()
                    else:  # txt file
                        urls = [
                            line.decode("utf-8").strip()
                            for line in uploaded_file
                            if line.strip()
                        ]

                    st.session_state.urls_to_process = urls
                    st.session_state.processed_file_id = file_id
                except Exception as e:
                    st.error(f"Error reading file: {e}")

    return st.session_state.urls_to_process


def display_results():
    """Renders the scraping results in the UI."""
    if not st.session_state.scraping_result:
        return

    results = st.session_state.scraping_result
    articles = results.get("articles", [])
    file_path = results.get("file_path")

    if not articles:
        st.warning(
            "Scraping did not return any articles. Please check the URLs and try again."
        )
        return

    st.header("📄 Processing Results")
    st.success(f"Successfully processed {len(articles)} URL(s).")

    if file_path and Path(file_path).exists():
        with open(file_path, "rb") as fp:
            st.download_button(
                label="Download Results as CSV",
                data=fp,
                file_name=Path(file_path).name,
                mime="text/csv",
            )

    for idx, entry in enumerate(articles, 1):
        article_info = entry.get("article_info")
        url = entry.get("url", "Unknown URL")
        llm_used = entry.get("llm_used", "N/A")
        status = entry.get("status", "Unknown")

        if isinstance(article_info, ArticleInfo):
            # --- MOJIBAKE FIX ---
            # Apply `fix_mojibake` to all text fields before displaying
            title = fix_mojibake(article_info.title or "Untitled Article")
            authors = fix_mojibake(article_info.authors or "N/A")
            text_preview = fix_mojibake(article_info.article_text or "")
            source = fix_mojibake(article_info.source or "N/A")
            published_date = fix_mojibake(article_info.published_date or "N/A")
            updated_date = fix_mojibake(article_info.updated_date or "N/A")

            expander_title = f"✅ Success: {title}"
            is_expanded = False
        else:
            expander_title = f"⚠️ Failed: {url} ({status})"
            is_expanded = True

        with st.expander(expander_title, expanded=is_expanded):
            if isinstance(article_info, ArticleInfo):
                st.markdown(f"**URL:** [{url}]({url})")
                st.markdown(f"**Source:** {source}")
                st.markdown(f"**Author(s):** {authors}")
                st.markdown(f"**Published Date:** {published_date}")
                st.markdown(f"**LLM Used:** `{llm_used}`")
                st.write(f"**Article Text Preview:** {text_preview[:1500]}...")
            else:
                st.error(f"Could not parse article data. Status: {status}")


# --- Main Application Flow ---
install_playwright_and_browsers()
initialize_session_state()

# This part just gathers the URLs from user input
urls_from_input = handle_user_input()

# Add an explicit button to start the processing
st.divider()
if st.button(
    "🚀 Process URLs",
    type="primary",
    disabled=not urls_from_input,
    use_container_width=True,
):
    st.session_state.processing_triggered = True

# This block only runs if the button was clicked
if st.session_state.processing_triggered:
    with st.spinner(
        "Scraping websites and analyzing content... This may take a little while."
    ):
        output_filename = "user_facing_csvs/Enriched_URL_Data.csv"
        # Use the URLs stored in the session state
        results = process_urls(
            st.session_state.urls_to_process, output_filename, for_streamlit=True
        )
        st.session_state.scraping_result = results

    # Reset the trigger and the URL list to prevent re-running on the next interaction
    st.session_state.processing_triggered = False
    st.session_state.urls_to_process = []
    st.rerun()  # Force a rerun to update the UI cleanly after processing

# This will now display results without re-triggering the processing
# because `processing_triggered` will be False.
display_results()
