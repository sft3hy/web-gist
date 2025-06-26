# URL_Parser.py
import streamlit as st
import pandas as pd
import os
from pathlib import Path
import time
import logging
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import hashlib
import html
from datetime import datetime
import subprocess
import sys

# Import refactored processing logic
from batch_website_scraper import process_urls
from utils.llm_utils import ArticleInfo
from utils.scraping_utils import fix_mojibake


# --- Configuration ---
class Config:
    MAX_URLS = 100
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    SUPPORTED_FILE_TYPES = ["csv", "txt"]
    OUTPUT_DIR = Path("user_facing_csvs")
    CACHE_DIR = Path(".streamlit_cache")

    @classmethod
    def ensure_directories(cls):
        cls.OUTPUT_DIR.mkdir(exist_ok=True)
        cls.CACHE_DIR.mkdir(exist_ok=True)


# --- Page Configuration ---
st.set_page_config(
    page_title="URL Parser",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Styling ---
st.markdown(
    """
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    .success-card {
        background: #d4edda;
        border-left-color: #28a745;
    }
    .error-card {
        background: #f8d7da;
        border-left-color: #dc3545;
    }
    .warning-card {
        background: #fff3cd;
        border-left-color: #ffc107;
    }
</style>
""",
    unsafe_allow_html=True,
)

# --- Enhanced Functions - FIXED VERSION ---

import subprocess
import sys
import os
import streamlit as st
import logging


def initialize_session_state():
    """Initialize session state with default values"""
    defaults = {
        "scraping_result": None,
        "processed_file_hash": None,
        "processing_history": [],
        "last_processed": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


@st.cache_resource(ttl=3600)  # Cache for 1 hour - NO UI ELEMENTS HERE
def _setup_environment_cached():
    """Setup environment with NO UI elements - cached version"""
    try:
        # Ensure directories exist (assuming Config.ensure_directories() doesn't use UI)
        # Config.ensure_directories()  # Uncomment if this doesn't use Streamlit UI

        # Check if playwright is already installed
        if hasattr(st.session_state, "playwright_installed"):
            return {"success": True, "message": "Already installed", "status": "cached"}

        # Try to install Playwright browsers
        success, message = _install_playwright_browsers()

        if success:
            return {
                "success": True,
                "message": "Installation successful",
                "status": "installed",
            }
        else:
            return {"success": False, "message": message, "status": "failed"}

    except Exception as e:
        logging.error(f"Environment setup error: {e}")
        return {"success": False, "message": str(e), "status": "error"}


def _install_playwright_browsers():
    """Install Playwright browsers silently with proper error handling - NO UI"""
    try:
        # First, try to install playwright itself if not available
        try:
            import playwright
        except ImportError:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "playwright"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        # Install browsers silently
        process = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=300,  # 5 minute timeout
        )

        if process.returncode == 0:
            return True, "Browsers installed successfully"
        else:
            return False, "Browser installation failed"

    except subprocess.TimeoutExpired:
        logging.error("Playwright installation timed out after 5 minutes")
        return False, "Installation timed out after 5 minutes"
    except subprocess.CalledProcessError as e:
        logging.error(f"Subprocess error during Playwright installation: {e}")
        return False, f"Subprocess error: {e}"
    except Exception as e:
        logging.error(f"Unexpected error during Playwright installation: {e}")
        return False, f"Unexpected error: {e}"


@st.cache_resource(ttl=3600)
def _check_system_browser():
    """Check if system browser is available - NO UI"""
    try:
        result = subprocess.run(["which", "chromium"], capture_output=True, text=True)
        if result.returncode == 0:
            return {"available": True, "path": result.stdout.strip()}
        return {"available": False, "path": None}
    except:
        return {"available": False, "path": None}


@st.cache_resource(ttl=3600)
def _setup_for_streamlit_cloud():
    """Optimized setup for Streamlit Community Cloud - NO UI"""
    try:
        # Check if we're in Streamlit Cloud environment
        is_cloud = os.getenv("STREAMLIT_CLOUD", False) or "/app/" in os.getcwd()

        if is_cloud:
            # Try minimal Playwright setup
            try:
                process = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "playwright",
                        "install",
                        "chromium",
                        "--with-deps",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if process.returncode == 0:
                    return {
                        "success": True,
                        "message": "Cloud setup successful",
                        "is_cloud": True,
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Installation failed: {process.stderr}",
                        "is_cloud": True,
                    }

            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "message": "Installation timed out",
                    "is_cloud": True,
                }
            except Exception as e:
                return {"success": False, "message": str(e), "is_cloud": True}
        else:
            return {
                "success": False,
                "message": "Not in cloud environment",
                "is_cloud": False,
            }

    except Exception as e:
        return {"success": False, "message": str(e), "is_cloud": False}


def setup_environment():
    """Main setup function with UI elements - NOT CACHED"""

    # Show initial toast
    st.toast("🔧 Setting up environment...")

    # Try Streamlit Cloud setup first
    cloud_result = _setup_for_streamlit_cloud()

    if cloud_result["is_cloud"]:
        if cloud_result["success"]:
            st.toast("✅ Streamlit Cloud setup complete!")
            st.session_state.playwright_installed = True
            st.session_state.cloud_setup_complete = True
            return True
        else:
            st.toast("⚠️ Cloud setup failed, trying alternatives...")

    # Check system browser
    system_browser = _check_system_browser()
    if system_browser["available"]:
        st.toast("✅ System Chromium found - using system browser")
        st.session_state.browsers_checked = True
        st.session_state.use_system_browser = True
        return True

    # Try regular Playwright installation
    setup_result = _setup_environment_cached()

    if setup_result["success"]:
        if setup_result["status"] == "cached":
            st.toast("✅ Environment already set up!")
        else:
            st.toast("✅ Playwright browsers installed successfully!")
        st.session_state.playwright_installed = True
        return True
    else:
        # Show error but don't crash the app
        st.toast("❌ Browser setup failed - some features may not work")

        # Show a warning instead of stopping the app
        st.warning(
            """
            **Browser Setup Issue**
            
            Browser automation setup failed, but you can still use other features.
            
            **For full functionality:**
            1. Run this app locally
            2. Check the browser installation
            3. Try refreshing the page
            """
        )

        # Don't return False - let the app continue
        return True  # Changed this to True so app doesn't stop


# Alternative simpler version if you want minimal setup
def setup_environment_minimal():
    """Minimal setup that won't fail"""

    # Just show a toast and continue
    st.toast("🔧 Initializing...")

    # Set some basic session state
    if not hasattr(st.session_state, "setup_attempted"):
        st.session_state.setup_attempted = True
        st.toast("✅ Basic setup complete!")

    # Always return True so the app continues
    return True


def validate_url(url: str) -> bool:
    """Validate URL format"""
    url = url.strip()
    return url.startswith(("http://", "https://")) and len(url) >= 10


def parse_urls_from_text(text: str) -> List[str]:
    """Parse URLs from text input with validation"""
    urls = []

    # Split by newlines and commas
    for line in text.split("\n"):
        for url in line.split(","):
            url = url.strip()
            if url and validate_url(url):
                urls.append(url)

    return list(set(urls))  # Remove duplicates


def parse_urls_from_file(uploaded_file) -> tuple[List[str], Optional[str]]:
    """Parse URLs from uploaded file with enhanced error handling"""
    try:
        # Check file size
        if uploaded_file.size > Config.MAX_FILE_SIZE:
            return (
                [],
                f"File too large. Maximum size: {Config.MAX_FILE_SIZE // (1024*1024)}MB",
            )

        # Generate file hash for caching
        file_content = uploaded_file.read()
        file_hash = hashlib.md5(file_content).hexdigest()
        uploaded_file.seek(0)  # Reset file pointer

        # Check if we've already processed this file
        if st.session_state.processed_file_hash == file_hash:
            return (
                [],
                "File already processed. Upload a different file or modify the content.",
            )

        urls = []

        if uploaded_file.type == "text/csv":
            try:
                df = pd.read_csv(uploaded_file, header=None)
                # Try multiple columns in case URLs are not in the first column
                for col in df.columns:
                    potential_urls = df[col].dropna().astype(str).tolist()
                    for url in potential_urls:
                        if validate_url(url):
                            urls.append(url)
                    if urls:  # If we found URLs in this column, stop looking
                        break
            except pd.errors.EmptyDataError:
                return [], "CSV file is empty"
            except Exception as e:
                return [], f"Error reading CSV: {str(e)}"

        elif uploaded_file.type == "text/plain":
            try:
                content = file_content.decode("utf-8")
                urls = parse_urls_from_text(content)
            except UnicodeDecodeError:
                try:
                    content = file_content.decode("latin-1")
                    urls = parse_urls_from_text(content)
                except Exception as e:
                    return [], f"Cannot decode file: {str(e)}"

        # Remove duplicates and validate
        unique_urls = list(set(url for url in urls if validate_url(url)))

        if not unique_urls:
            return [], "No valid URLs found in file"

        # Store file hash
        st.session_state.processed_file_hash = file_hash

        return unique_urls, None

    except Exception as e:
        return [], f"Unexpected error processing file: {str(e)}"


def display_processing_metrics(stats: Dict[str, int]):
    """Display processing metrics in cards"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
        <div class="metric-card">
            <h3>📊 Total Processed</h3>
            <h2>{stats['total']}</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
        <div class="metric-card success-card">
            <h3>✅ Successful</h3>
            <h2>{stats['successful']}</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
        <div class="metric-card error-card">
            <h3>❌ Failed</h3>
            <h2>{stats['failed']}</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
        <div class="metric-card">
            <h3>📝 With Content</h3>
            <h2>{stats['with_text']}</h2>
        </div>
        """,
            unsafe_allow_html=True,
        )


def display_enhanced_results():
    """Enhanced results display with better formatting and error handling"""
    if not st.session_state.scraping_result:
        return

    results = st.session_state.scraping_result
    articles = results.get("articles", [])
    file_path = results.get("file_path")

    if not articles:
        st.warning(
            "⚠️ No articles were processed. Please check your URLs and try again."
        )
        return

    # Download button
    if file_path and Path(file_path).exists():
        with open(file_path, "rb") as fp:
            st.download_button(
                label="📥 Download Results (CSV)",
                data=fp,
                file_name=f"processed_urls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📄 All Results", "✅ Successful", "❌ Failed"])

    with tab1:
        display_article_results(articles, show_all=True)

    with tab2:
        successful_articles = [
            a for a in articles if isinstance(a.get("article_info"), ArticleInfo)
        ]
        display_article_results(successful_articles, show_all=False)

    with tab3:
        failed_articles = [
            a for a in articles if not isinstance(a.get("article_info"), ArticleInfo)
        ]
        display_article_results(failed_articles, show_all=False)


def display_article_results(articles: List[Dict], show_all: bool = True):
    """Display article results with improved formatting"""
    if not articles:
        st.info("No articles in this category.")
        return

    for idx, entry in enumerate(articles, 1):
        article_info = entry.get("article_info")
        url = entry.get("url", "Unknown URL")
        llm_used = entry.get("llm_used", "N/A")
        status = entry.get("status", "Unknown")

        if isinstance(article_info, ArticleInfo):
            title = fix_mojibake(article_info.title or "Untitled Article")
            authors = fix_mojibake(article_info.authors or "N/A")
            text_preview = fix_mojibake(article_info.article_text or "")
            source = fix_mojibake(article_info.source or "N/A")
            published_date = fix_mojibake(article_info.published_date or "N/A")
            modified_date = fix_mojibake(article_info.modified_date or "N/A")

            # Truncate title for display
            display_title = title[:80] + "..." if len(title) > 80 else title
            expander_title = f"✅ {display_title}"
            is_expanded = False
        else:
            # Truncate URL for display
            display_url = url[:60] + "..." if len(url) > 60 else url
            expander_title = f"❌ {display_url} ({status})"
            is_expanded = False

        with st.expander(expander_title, expanded=is_expanded):
            if isinstance(article_info, ArticleInfo):
                # Create two columns for better layout
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"**📰 Title:** {title}")
                    st.markdown(f"**🔗 URL:** [{url}]({url})")
                    st.markdown(f"**✍️ Author(s):** {authors}")

                with col2:
                    st.markdown(f"**📅 Published:** {published_date}")
                    if (
                        modified_date
                        and modified_date != "N/A"
                        and modified_date != published_date
                    ):
                        st.markdown(f"**🔄 Updated:** {modified_date}")
                    st.markdown(f"**🤖 LLM:** `{llm_used}`")
                    st.markdown(f"**📊 Source:** {source}")

                # Article text preview
                if text_preview:
                    st.markdown("**📝 Article Preview:**")
                    preview_length = min(1000, len(text_preview))

                    # 1. Prepare the text content (same logic as before)
                    text_to_display = text_preview[:preview_length]
                    if len(text_preview) > preview_length:
                        text_to_display += "..."

                    # 2. Escape the text to prevent it from being interpreted as HTML
                    safe_text = html.escape(text_to_display)

                    # 3. Define the CSS for the styled box
                    # You can customize colors, padding, etc. here
                    css_style = """
                        background-color: #f0f2f6;
                        border: 1px solid #e6e6e6;
                        border-radius: 0.5rem;
                        padding: 1rem;
                        height: 200px;
                        overflow-y: auto;
                        font-family: 'Source Sans Pro', sans-serif;
                        color: #262730;
                    """
                    # We replace newlines with spaces for the HTML style attribute
                    css_style_str = css_style.replace("\n", " ")

                    # 4. Create the HTML for the box using an f-string
                    markdown_content = f'<div style="{css_style_str}">{safe_text}</div>'

                    # 5. Add a header (optional, but good practice since the original label was collapsed)
                    st.markdown("##### Content Preview")

                    # 6. Render the styled box using st.markdown
                    st.markdown(markdown_content, unsafe_allow_html=True)
                else:
                    st.warning("No article text extracted")
            else:
                st.error(f"**Failed to process:** {url}")
                st.write(f"**Status:** {status}")
                if "error" in entry:
                    st.write(f"**Error Details:** {entry['error']}")


# --- Main Application ---


def main():
    """Main application flow"""

    # Header
    st.markdown(
        """
    <div class="main-header">
        <h1>🔗 URL Parser</h1>
        <p>Extract metadata and article content from web URLs using gemini</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Setup environment
    if not setup_environment():
        st.stop()

    initialize_session_state()

    # Sidebar with settings
    with st.sidebar:
        st.header("⚙️ Settings")
        max_urls = st.slider("Max URLs to process", 1, Config.MAX_URLS, 20)
        timeout_seconds = st.slider("Timeout per URL (seconds)", 10, 120, 30)

    # Main content
    st.header("📥 Input URLs")

    # URL input form
    with st.form(key="enhanced_url_form", clear_on_submit=False):
        col1, col2 = st.columns([3, 2])

        with col1:
            input_urls_text = st.text_area(
                "Enter URLs (one per line or comma-separated)",
                height=200,
                placeholder="https://example.com/article1\nhttps://example.com/article2",
                help="Paste URLs here, separated by new lines or commas",
            )

        with col2:
            uploaded_file = st.file_uploader(
                "Or upload a file",
                type=Config.SUPPORTED_FILE_TYPES,
                help=f"Supported formats: {', '.join(Config.SUPPORTED_FILE_TYPES).upper()}",
            )

            if uploaded_file:
                st.info(f"📁 File: {uploaded_file.name} ({uploaded_file.size:,} bytes)")

        # Submit button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button(
                "🚀 Process URLs", use_container_width=True, type="primary"
            )

    # Process form submission
    if submitted:
        urls_to_process = []
        error_message = None

        # Process text input first
        if input_urls_text:
            urls_to_process = parse_urls_from_text(input_urls_text)

        # Process file input if no text input
        elif uploaded_file:
            urls_to_process, error_message = parse_urls_from_file(uploaded_file)

        # Validation
        if error_message:
            st.error(f"❌ {error_message}")
        elif not urls_to_process:
            st.warning(
                "⚠️ Please provide URLs either in the text area or by uploading a file."
            )
        elif len(urls_to_process) > max_urls:
            st.error(
                f"❌ Too many URLs ({len(urls_to_process)}). Maximum allowed: {max_urls}"
            )
        else:

            # --- MODIFIED PART ---
            # Start processing immediately after the first button press
            process_urls_enhanced(urls_to_process, timeout_seconds)
            # --- END OF MODIFICATION ---

    # Display results
    display_enhanced_results()


def process_urls_enhanced(urls: List[str], timeout_seconds: int):
    """Enhanced URL processing with better status updates"""

    output_filename = (
        Config.OUTPUT_DIR
        / f"processed_urls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    # Progress tracking
    progress_bar = st.progress(0)
    status_container = st.empty()

    def enhanced_status_callback(message: str, progress: float = None):
        """Enhanced status callback with progress tracking"""
        status_container.info(f"🔄 {message}")
        if progress is not None:
            progress_bar.progress(min(progress, 1.0))
        logging.info(f"Processing: {message}")

    try:
        with st.spinner("🚀 Processing URLs..."):
            start_time = time.time()

            # Process URLs
            results = process_urls(
                urls,
                str(output_filename),
                status_callback=enhanced_status_callback,
                # timeout=timeout_seconds,
            )

            processing_time = time.time() - start_time

            # Store results and history
            st.session_state.scraping_result = results

            # Clear progress indicators
            progress_bar.progress(1.0)
            status_container.success(
                f"✅ Processing completed in {processing_time:.1f} seconds!"
            )

            # Show success message
            st.success(f"🎉 Successfully processed {len(urls)} URLs!")

    except Exception as e:
        st.error(f"❌ Processing failed: {str(e)}")
        logging.error(f"Processing error: {str(e)}")
    finally:
        # Clean up progress indicators after a delay
        time.sleep(2)
        progress_bar.empty()
        status_container.empty()


if __name__ == "__main__":
    main()
