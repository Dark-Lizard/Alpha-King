import streamlit as st
import pandas as pd
from brain_api import BrainAPIHandler

st.set_page_config(page_title="Alpha King - Quant Research Workspace", page_icon="👑", layout="wide")

# Sidebar Credentials Configuration
st.sidebar.title("👑 Alpha King Control")
st.sidebar.markdown("---")

st.sidebar.subheader("🔑 API Integrations")
gemini_api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Enter your Google Gemini API key.")
wq_email = st.sidebar.text_input("WorldQuant Email", help="Your WorldQuant Brain account email.")
wq_password = st.sidebar.text_input("WorldQuant Password", type="password", help="Your WorldQuant Brain account password.")

# Initialize API Handler
brain_handler = BrainAPIHandler(email=wq_email, password=wq_password, gemini_key=gemini_api_key)

# Main Application Layout
st.title("👑 Alpha King: Quant Research Workspace")
st.markdown("Use the sidebar to configure your credentials, sync live platform data, and analyze quantitative factors.")

tab1, tab2 = st.tabs(["📊 Data Explorer & Sync", "✨ Gemini AI Lab"])

with tab1:
    st.header("Real-Time Data Sync")
    st.write("Click the button below to authenticate and pull live data from WorldQuant Brain.")

    if st.button("🚀 Sync Real-Time Data from Brain", type="primary"):
        if not wq_email or not wq_password:
            st.warning("Please enter your WorldQuant Brain credentials in the sidebar first.")
        else:
            with st.spinner("Connecting to WorldQuant Brain platform..."):
                data, message = brain_handler.sync_realtime_data()
                if data:
                    st.success(message)
                    st.json(data)
                    st.session_state['synced_data'] = data
                else:
                    st.error(message)

with tab2:
    st.header("Gemini Quant Analysis")
    st.write("Ask Gemini to analyze your synced workspace status or offer factor optimizations.")

    analysis_prompt = st.text_area(
        "Gemini Prompt", 
        value="Analyze the current alpha research pipeline status and suggest optimization strategies."
    )

    if st.button("✨ Run Gemini Analysis"):
        if not gemini_api_key:
            st.warning("Please enter your Gemini API key in the sidebar.")
        else:
            with st.spinner("Consulting Gemini..."):
                context = st.session_state.get('synced_data', {"info": "No live sync data loaded yet."})
                result = brain_handler.ask_gemini_analysis(analysis_prompt, context)
                st.subheader("Gemini Insights:")
                st.markdown(result)
