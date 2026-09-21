"""Streamlit UI for the AI Data Analyst Agent.

Run locally:      streamlit run app.py
Run in Colab:      see README section "Running the web UI in Google Colab"
"""
import os
import tempfile

import streamlit as st

from agent import DataAnalystAgent

st.set_page_config(page_title="AI Data Analyst Agent", page_icon="📊", layout="centered")

st.title("📊 AI Data Analyst Agent")
st.caption("Upload a CSV or Excel file, then ask a question in plain English.")

if "agent" not in st.session_state:
    st.session_state.agent = None
    st.session_state.filename = None

uploaded_file = st.file_uploader("Upload your data", type=["csv", "xlsx", "xls"])

if uploaded_file is not None and uploaded_file.name != st.session_state.filename:
    suffix = os.path.splitext(uploaded_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name
    try:
        st.session_state.agent = DataAnalystAgent(tmp_path)
        st.session_state.filename = uploaded_file.name
        st.success(f"Loaded {uploaded_file.name}")
    except Exception as e:
        st.error(f"Couldn't read that file: {e}")
        st.session_state.agent = None

if st.session_state.agent is not None:
    with st.expander("📋 Data summary", expanded=False):
        st.text(st.session_state.agent.describe_data())

    st.subheader("Ask a question")
    example = "What were our top 5 products last quarter?"
    question = st.text_input("Your question", placeholder=example)

    col1, col2 = st.columns([1, 4])
    ask_clicked = col1.button("Ask", type="primary")
    if col2.button("Use example question"):
        question = example
        ask_clicked = True

    if ask_clicked and question.strip():
        with st.spinner("Analyzing..."):
            response = st.session_state.agent.ask(question)

        if response.error:
            st.warning(response.explanation)
        else:
            st.markdown(response.explanation)
            if response.chart_path:
                st.image(response.chart_path)
            if response.table is not None:
                with st.expander("See underlying data table"):
                    st.dataframe(response.table, use_container_width=True)
    elif ask_clicked:
        st.info("Type a question first.")
else:
    st.info("Upload a CSV or Excel file above to get started. No file yet? Use the sample dataset:")
    if st.button("Load sample sales data"):
        st.session_state.agent = DataAnalystAgent("sample_sales_data.csv")
        st.session_state.filename = "sample_sales_data.csv"
        st.rerun()
