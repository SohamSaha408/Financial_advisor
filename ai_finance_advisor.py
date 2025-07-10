import streamlit as st
import pandas as pd
import re
import base64
import os
import requests
import google.generativeai as genai
from pypdf import PdfReader
from fredapi import Fred
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np # Ensure numpy is imported for np.isnan

# Assuming 'advisor' module exists and contains these functions
# Make sure 'advisor.py' is in the same directory as this app.py
from advisor import generate_recommendation, search_funds

# IMPORTANT: st.set_page_config MUST be the first Streamlit command
st.set_page_config(page_title="AI Financial Advisor", layout="centered")

# --- JavaScript for Scrolling (Full Polling Mechanism and 'nearest' block) ---
# This script defines a function to scroll to an HTML element by its ID.
# It uses a polling mechanism to ensure the element is in the DOM before attempting to scroll.
st.markdown("""
<script>
    function scrollToElement(id) {
        let attempts = 0;
        const maxAttempts = 100; // Increased attempts for more robustness (up to 5 seconds)
        const intervalTime = 50; // Check every 50 milliseconds

        const checkAndScroll = setInterval(() => {
            var element = document.getElementById(id);

            if (element) {
                clearInterval(checkAndScroll); // Stop polling once found
                console.log("Found element with ID: " + id + " after " + (attempts + 1) + " attempts. Attempting to scroll.");
                // Changed 'block: start' to 'block: nearest' for potentially better behavior
                element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                attempts++;
                if (attempts >= maxAttempts) {
                    clearInterval(checkAndScroll); // Stop polling after max attempts
                    console.error("Failed to find element with ID '" + id + "' after " + maxAttempts + " attempts. Scrolling aborted.");
                } else {
                    // console.warn("Attempt " + (attempts) + ": Scroll target element with ID '" + id + "' NOT FOUND yet. Retrying...");
                    // Uncomment the above line for verbose debugging if needed in console
                }
            }
        }, intervalTime);
    }
</script>
""", unsafe_allow_html=True)


# --- 1. Background and Initial CSS (Full Code) ---
def set_background(image_file):
    if not os.path.exists(image_file):
        st.error(f"Background image not found: '{image_file}'. Please ensure the image is in the correct directory.")
        fallback_css = """<style>.stApp {background-color: #222222; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-size: cover; background-position: center; background-repeat: no-repeat; background-attachment: fixed;}</style>"""
        st.markdown(fallback_css, unsafe_allow_html=True)
        return

    try:
        with open(image_file, "rb") as f:
            data = f.read()
        encoded = base64.b64encode(data).decode()
        css = f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{encoded}");
            background-size: cover; background-position: center; background-repeat: no-repeat; background-attachment: fixed;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        .main .block-container {{
            background-color: rgba(0, 0, 0, 0.75); padding: 2rem; border-radius: 1rem; margin: 2rem auto;
            max-width: 700px; width: 90%; color: white; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(5px); -webkit-backdrop-filter: blur(5px); overflow: auto;
        }}
        .stMarkdown, .stText, .stLabel, .stTextInput > div > label, .stNumberInput > label, .stSelectbox > label, .stTextArea > label {{
            color: white !important;
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: #E0E0E0 !important; text-shadow: 1px 1px 3px rgba(0,0,0,0.7);
        }}
        .stButton>button {{
            background-color: #34495e; /* Dark blue-gray for harmony */
            color: white; border-radius: 0.5rem; border: none;
            padding: 0.75rem 1.5rem; font-size: 1rem; cursor: pointer; transition: background-color 0.3s;
        }}
        .stButton>button:hover {{
            background-color: #44607a; /* Slightly lighter blue-gray on hover */
        }}
        .stTextInput, .stNumberInput, .stSelectbox, .stTextArea {{
            background-color: rgba(0, 0, 0, 0.4); /* Darker semi-transparent for inputs */
            border-radius: 0.5rem; padding: 0.5rem;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }}
        .stTextInput > div > div > input, .stNumberInput > div > div > input, .stTextArea > div > div > textarea {{
            color: white; background-color: transparent; border: none;
        }}
        .stSelectbox > div > div[data-baseweb="select"] > div[role="button"] {{
            color: white; background-color: transparent; border: none;
        }}
        .stSelectbox div[data-baseweb="select"] div[role="listbox"] {{
            background-color: rgba(0, 0, 0, 0.9); color: white;
        }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"Background image not found: '{image_file}'. Please ensure the image is in the correct directory.")
        fallback_css = """<style>.stApp {background-color: #222222; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-size: cover; background-position: center; background-repeat: no-repeat; background-attachment: fixed;}</style>"""
        st.markdown(fallback_css, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"An unexpected error occurred while setting background: {e}")
        fallback_css = """<style>.stApp {background-color: #222222; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-size: cover; background-position: center; background-repeat: no-repeat; background-attachment: fixed;}</style>"""
        st.markdown(fallback_css, unsafe_allow_html=True)

set_background("black-particles-background.avif") # Ensure this file exists in your project directory

# --- Initialize session state for AI summary inputs ---
if 'ai_summary_data' not in st.session_state:
    st.session_state['ai_summary_data'] = {}


# --- Sidebar Navigation (Dashboard) ---
st.sidebar.title("App Navigation")
if st.sidebar.button("Investment Plan"):
    st.markdown("<script>scrollToElement('investment_plan')</script>", unsafe_allow_html=True)
if st.sidebar.button("Mutual Fund Research"):
    st.markdown("<script>scrollToElement('mutual_fund_research')</script>", unsafe_allow_html=True)
if st.sidebar.button("Document Analyzer"):
    st.markdown("<script>scrollToElement('document_analyzer')</script>", unsafe_allow_html=True)
if st.sidebar.button("Economic Data (FRED)"):
    st.markdown("<script>scrollToElement('fred_data')</script>", unsafe_allow_html=True)
if st.sidebar.button("Market Trends Data"):
    st.markdown("<script>scrollToElement('market_trends_data')</script>", unsafe_allow_html=True)
if st.sidebar.button("Latest Financial News"):
    st.markdown("<script>scrollToElement('financial_news')</script>", unsafe_allow_html=True)
if st.sidebar.button("Company Financials"):
    st.markdown("<script>scrollToElement('company_financials')</script>", unsafe_allow_html=True)
if st.sidebar.button("AI Summary"):
    st.markdown("<script>scrollToElement('ai_summary')</script>", unsafe_allow_html=True)
if st.sidebar.button("Ask the AI"):
    st.markdown("<script>scrollToElement('ask_the_ai')</script>", unsafe_allow_html=True)


# --- 2. Main App Logic ---

def extract_amount(value_str):
    match = re.search(r"₹([0-9]+)", value_str)
    return int(match.group(1)) if match else 0

def get_pdf_text(pdf_file):
    text = ""
    try:
        pdf_reader = PdfReader(pdf_file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
    return text

def get_fred_data(series_id, start_date=None, end_date=None):
    try:
        fred_api_key = st.secrets["fred"]["api_key"]
        fred = Fred(api_key=fred_api_key)
        data = fred.get_series(series_id, observation_start=start_date, observation_end=end_date)
        if data is not None and not data.empty:
            df = pd.DataFrame(data)
            df.columns = [series_id]
            df.index.name = 'Date'
            return df
        else:
            st.warning(f"No data found for FRED Series ID: `{series_id}`. Please check the ID.")
            return None
    except KeyError:
        st.error("FRED API key not found in Streamlit secrets. Please set it as `fred.api_key` in .streamlit/secrets.toml or Streamlit Cloud secrets.")
        return None
    except Exception as e:
        st.error(f"An error occurred while fetching FRED data: {e}")
        return None

# --- Function to fetch financial news ---
def get_financial_news(query="finance OR economy OR stock market OR investing", language="en", page_size=5):
    try:
        news_api_key = st.secrets["newsapi"]["api_key"]
        url = (
            f"https://newsapi.org/v2/everything?"
            f"q={query}&"
            f"language={language}&"
            f"sortBy=publishedAt&"
            f"pageSize={page_size}&"
            f"apiKey={news_api_key}"
        )
        response = requests.get(url)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        articles = response.json().get("articles", [])
        return articles
    except KeyError:
        st.error("NewsAPI API key not found in Streamlit secrets. Please set it as `newsapi.api_key`.")
        return []
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching news from NewsAPI.org: {e}")
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred while fetching news: {e}")
        return []

# --- Function to fetch company financial statements via Alpha Vantage ---
def get_company_financials(symbol, statement_type="INCOME_STATEMENT"):
    try:
        av_api_key = st.secrets["alphavantage"]["api_key"]
        url = f"https://www.alphavantage.co/query?function={statement_type}&symbol={symbol}&apikey={av_api_key}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if "annualReports" in data:
            st.subheader(f"Annual {statement_type.replace('_', ' ').title()} for {symbol}")
            df = pd.DataFrame(data["annualReports"])
            numeric_cols = [col for col in df.columns if col not in ['fiscalDateEnding', 'reportedCurrency']]
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            desired_order = ['fiscalDateEnding', 'reportedCurrency', 'totalRevenue', 'netIncome', 'earningsPerShare', 'totalShareholderEquity']
            ordered_
