import streamlit as st
import pandas as pd
from batch_website_scraper import do_the_scraping
import os


# Import the ArticleInfo class so we can work with the object directly
from utils.llm_utils import ArticleInfo

st.set_page_config("URL Parser", page_icon=":material/precision_manufacturing:")
st.title("URL Parser")


# --- One-time-setup using st.cache_resource for Playwright ---
@st.cache_resource
def install_playwright_and_browsers():
    """
    Installs Playwright browsers and their system dependencies.
    This is cached and will only run once per application startup.
    """
    st.write("⏳ Installing Playwright browsers, this may take a moment...")
    os.system("playwright install")
    os.system("playwright install-deps")


# --- Trigger the installation at startup ---
# The decorator ensures this only runs once.
install_playwright_and_browsers()


# --- Initialize session state ---
if "scraping_result" not in st.session_state:
    st.session_state.scraping_result = None
if "urls_to_process" not in st.session_state:
    st.session_state.urls_to_process = None

# --- UI: Input text or upload file ---
uploaded_file = st.file_uploader("Or upload a CSV file of URLs:", type=["csv"])
input_url = st.chat_input("Enter a URL or a comma-separated list of URLs:")

# --- Handle input and set URLs to be processed ---
if uploaded_file is not None:
    # Use a unique identifier for the uploaded file to avoid reprocessing
    if st.session_state.get("processed_file_name") != uploaded_file.name:
        df = pd.read_csv(uploaded_file)
        urls = df.iloc[:, 0].dropna().tolist()
        st.session_state.urls_to_process = urls
        st.session_state.processed_file_name = uploaded_file.name
elif input_url:
    urls = [url.strip() for url in input_url.split(",") if url.strip()]
    st.session_state.urls_to_process = urls

# --- Trigger scraping if new URLs are available in session state ---
if st.session_state.urls_to_process:
    urls_to_run = st.session_state.urls_to_process
    st.chat_message("user").write(
        f"Received {len(urls_to_run)} URL(s). Processing now..."
    )

    with st.spinner("Scraping website(s) and analyzing content..."):
        # The scraper function is called here
        scrape_result = do_the_scraping(urls_to_run, for_streamlit=True)
        st.session_state.scraping_result = scrape_result

    # Clear the processing queue to prevent re-running on the next interaction
    st.session_state.urls_to_process = None


# --- Display results if they exist in session state ---
if st.session_state.scraping_result:
    scraping_result = st.session_state.scraping_result
    articles = scraping_result.get("articles", [])
    file_path = scraping_result.get("file_path", None)

    if not articles:
        st.warning(
            "Scraping did not return any articles. Please check the URLs and try again."
        )
    else:
        with st.chat_message("ai"):
            st.write(f"Successfully processed {len(articles)} article(s):")

            for idx, article_entry in enumerate(articles, start=1):
                # FIX: Extract the ArticleInfo object from the dictionary
                article_info_obj = article_entry.get("article_info")
                llm_used = article_entry.get("llm", "Unknown")
                url = article_entry.get("url", "Unknown URL")

                # Safety check: ensure we have a valid ArticleInfo object before proceeding
                if isinstance(article_info_obj, ArticleInfo):
                    # Now we can safely use dot notation (e.g., article_info_obj.title)
                    expander_title = article_info_obj.title or "Untitled Article"
                    with st.expander(
                        f"Article {idx}: {expander_title}",
                        expanded=False,
                    ):
                        # Create a display dictionary using the object's attributes
                        display_data = {
                            "URL": url,
                            "Title": article_info_obj.title,
                            "Author(s)": article_info_obj.authors,
                            "Source": article_info_obj.source,
                            "Published Date": article_info_obj.published_date,
                            "Updated Date": article_info_obj.updated_date,
                            "Shortened Article Text": (
                                f"{article_info_obj.article_text[:500]}..."
                                if article_info_obj.article_text
                                else "N/A"
                            ),
                            "LLM Used": llm_used,
                        }
                        # Use a more readable format for display
                        for key, value in display_data.items():
                            st.markdown(f"**{key}:** {value}")
                else:
                    st.warning(f"Could not parse article data for URL: {url}")

    if file_path:
        try:
            with open(file_path, "rb") as f:
                st.download_button(
                    label="Download all article info as CSV",
                    data=f,
                    file_name=file_path.split("/")[-1],
                    # The scraper creates a CSV file
                    mime="text/csv",
                )
        except FileNotFoundError:
            st.error(f"Could not find the results file at path: {file_path}")
