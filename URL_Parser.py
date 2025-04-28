import streamlit as st
import pandas as pd
import json
from config import CHAR_LIMIT
from batch_website_scraper import do_the_scraping

st.set_page_config("URL Parser", page_icon=":material/precision_manufacturing:")
st.title("URL Parser")

# --- Initialize session state ---
if "scraping_result" not in st.session_state:
    st.session_state.scraping_result = None

# --- UI: Input text or upload file ---
uploaded_file = st.file_uploader("Or upload a CSV file of URLs:", type=["csv"])
input_url = st.chat_input("Enter a URL or a comma-separated list of URLs:")

urls = []

# --- Handle input ---
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    urls = df.iloc[:, 0].dropna().tolist()
elif input_url:
    urls = [url.strip() for url in input_url.split(",") if url.strip()]

if urls:
    st.chat_message("user").write(f"Received {len(urls)} URL(s).")

    with st.spinner("Scraping website(s)..."):
        # Save to session_state so it persists
        scrape_result = do_the_scraping(urls, for_streamlit=True)
        print(scrape_result)
        st.session_state.scraping_result = scrape_result

# --- Display results if they exist ---
if st.session_state.scraping_result:
    scraping_result = st.session_state.scraping_result
    articles = scraping_result.get("articles", [])
    file_path = scraping_result.get("file_path", None)

    if articles:
        with st.chat_message("ai"):
            st.write(f"Found {len(articles)} articles:")

            for idx, article_entry in enumerate(articles, start=1):
                article_info = article_entry.get("article_info", {})
                llm_used = article_entry.get("llm", "Unknown")
                url = article_entry.get("url", "Unknown URL")

                with st.expander(
                    f"Article {idx}: {article_info.title}",
                    expanded=False,
                ):
                    display_data = {
                        "URL": url,
                        "Title": article_info.title,
                        "Author(s)": article_info.authors,
                        "Source": article_info.source,
                        "Published Date": article_info.published_date,
                        "Updated Date": article_info.updated_date,
                        "Shortened Article Text": f"{article_info.article_text[:500]}...",
                        "LLM": llm_used,
                    }
                    st.json(display_data)

    if file_path:
        with open(file_path, "rb") as f:
            st.download_button(
                label="Download all article info",
                data=f,
                file_name=file_path.split("/")[-1],
                mime="application/json",
            )
