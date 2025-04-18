import streamlit as st
from config import CHAR_LIMIT
from helpers import call_llm, clean_article, parse_html_for_llm

st.set_page_config("URL Parser", page_icon=":material/precision_manufacturing:")
st.title("URL Parser")


input_url = st.chat_input("Enter a URL for data extraction:")

if input_url:
    parsed = ''
    st.chat_message("user").write(input_url)
    with st.spinner("Parsing url..."):
        whole_parsed = parse_html_for_llm(input_url)
        if whole_parsed is not None:
            parsed = f"URL: {input_url}\nWebsite text:{whole_parsed[0]}"
    with st.spinner("Cleaning website text..."):
        with st.chat_message("ai"):
            with st.expander("View parsed article"):
                if whole_parsed is not None:
                    st.write(clean_article(whole_parsed[1][:CHAR_LIMIT]))
        
    with st.spinner("Generating summary..."):
        with st.chat_message("ai"):
            st.write("Article Information in JSON format:")
            st.code(call_llm(parsed), language="JSON")
        