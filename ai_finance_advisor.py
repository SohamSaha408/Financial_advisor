# ai_financial_advisor.py

import streamlit as st
import os, base64, re, requests
import pandas as pd, numpy as np
import yfinance as yf
import google.generativeai as genai
from pypdf import PdfReader
from fredapi import Fred
from advisor import generate_recommendation, search_funds

# --- Page Config & JS Scroll ---
st.set_page_config(page_title="AI Financial Advisor", layout="centered")
st.markdown("""
<script>
window.scrollToSection = (id) => {
  const el = document.getElementById(id);
  if (el) setTimeout(()=> el.scrollIntoView({behavior:'smooth', block:'start'}), 300);
}
</script>
""", unsafe_allow_html=True)

# --- Dashboard CSS Styling ---
st.markdown("""
<style>
/* Global */
body, .stApp { font-family: 'Segoe UI', sans-serif; background-color: #1B1F24; color: #E0E0E0; }
/* Sidebar */
[data-testid="stSidebar"] {background: #14171A; padding-top:1rem;}
[data-testid="stSidebar"] .stButton>button {
  width:100%; text-align:left; padding:0.75rem; color:#E0E0E0;
  background:#2C3138; border:none; border-radius:0.4rem; margin:0.2rem 0;
  transition:0.2s;
}
[data-testid="stSidebar"] .stButton>button:hover {background:#3A424C;}
/* Main */
.section-container {
  background: #22272E; padding:1.5rem; margin:1rem auto;
  border-radius:0.6rem; max-width:900px;
  box-shadow:0 4px 16px rgba(0,0,0,0.5);
}
.card {
  background:#2C3138; padding:1rem; margin-bottom:1rem;
  border-radius:0.5rem; box-shadow:0 2px 8px rgba(0,0,0,0.3);
}
/* Form elements */
.stButton>button {background:#0A84FF;color:white;border:none;padding:0.6rem 1.2rem;border-radius:0.4rem;}
.stButton>button:hover {background:#006FD6;}
.stTextInput>div, .stNumberInput>div, .stSelectbox>div {
  background:#2C3138;border:1px solid #3A424C;border-radius:0.4rem;
}
.stTextInput input, .stNumberInput input, .stSelectbox div[role="button"] {
  background:transparent;color:#E0E0E0;
}
</style>
""", unsafe_allow_html=True)

# --- Background Image if present ---
def set_background(image):
    if os.path.exists(image):
        data = base64.b64encode(open(image, "rb").read()).decode()
        st.markdown(f"""<style>.stApp {{
  background-image: url("data:image/png;base64,{data}");
  background-size: cover; background-attachment: fixed;
}}</style>""", unsafe_allow_html=True)

set_background("black-particles-background.avif")

# --- Sidebar Navigation ---
st.sidebar.title("📊 Dashboard")
sections = {
    "Investment Plan": "investment_plan",
    "Mutual Fund Research": "mutual_fund_research",
    "Document Analyzer": "document_analyzer",
    "Economic Data (FRED)": "fred_data",
    "Market Trends Data": "market_trends_data",
    "Latest Financial News": "financial_news",
    "Company Financials": "company_financials",
    "AI Summary": "ai_summary",
    "Ask the AI": "ask_the_ai"
}
for lab, sec in sections.items():
    st.sidebar.button(lab, on_click=lambda s=sec: st.markdown(f"<script>scrollToSection('{s}')</script>", unsafe_allow_html=True))

# --- Session State for Summary ---
if 'ai_summary_data' not in st.session_state:
    st.session_state['ai_summary_data'] = {}

# --- Utility Functions ---
def extract_amount(s): return int(re.search(r"\u20B9([0-9]+)", s).group(1)) if re.search(r"\u20B9([0-9]+)", s) else 0
def get_pdf_text(f): txt=""; [txt := txt + p.extract_text() for p in PdfReader(f).pages]; return txt
def get_fred_data(id): return pd.DataFrame(Fred(api_key=st.secrets["fred"]["api_key"]).get_series(id), columns=[id])
def get_news(): return requests.get(f"https://newsapi.org/v2/top-headlines?category=business&apiKey={st.secrets['newsapi']['api_key']}").json().get("articles",[])
def get_company_fin(sym): return requests.get(f"https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={sym}&apikey={st.secrets['alphavantage']['api_key']}").json()

# === UI Sections ===

st.title("💸 AI Financial Advisor")

## Investment Plan
st.markdown("<div id='investment_plan'></div>", unsafe_allow_html=True)
with st.container():
    st.header("📊 Get Your Investment Plan")
    st.markdown("### Analyze your profile")
    age = st.number_input("Age", min_value=18)
    income = st.number_input("Monthly Income (₹)", step=1000)
    profession = st.selectbox("Profession", ["Student", "Salaried", "Self-employed"])
    region = st.selectbox("Region", ["Metro", "Urban", "Rural"])
    goal = st.selectbox("🎯 Goal", ["Wealth Accumulation","Retirement Planning","Short-term","Tax Saving (ELSS)"])
    if st.button("Get Advice"):
        res = generate_recommendation(age, income, profession, region, goal)
        st.markdown(f"<div class='card'><strong>Advice:</strong><br/>{res['advice_text'].replace(chr(10), '<br/>')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='card'><strong>Allocation:</strong><br/>{res['allocation']}</div>", unsafe_allow_html=True)

## Mutual Fund Research
st.markdown("<div id='mutual_fund_research'></div>", unsafe_allow_html=True)
with st.container():
    st.header("🔍 Mutual Fund Research")
    q = st.text_input("Fund Name")
    if q:
        funds = search_funds(q)
        for f in funds[:5]:
            st.markdown(f"<div class='card'><strong>{f['schemeName']}</strong><br/>Code: {f.get('schemeCode')}</div>", unsafe_allow_html=True)

## Document Analyzer
st.markdown("<div id='document_analyzer'></div>", unsafe_allow_html=True)
with st.container():
    st.header("📄 Document Analyzer")
    up = st.file_uploader("Upload PDF/TXT", type=["pdf","txt"])
    if up:
        txt = get_pdf_text(up) if up.name.lower().endswith("pdf") else up.getvalue().decode()
        st.text_area("Preview", txt[:500], height=200)
        q2 = st.text_area("Ask about this document")
        if st.button("Analyze Document"):
            genai.configure(api_key=st.secrets["gemini"]["api_key"])
            resp = genai.GenerativeModel('gemini-1.5-flash').generate_content(f"{txt}\n\nUser Q: {q2}")
            st.markdown(f"<div class='card'>{resp.text}</div>", unsafe_allow_html=True)

## Economic Data (FRED)
st.markdown("<div id='fred_data'></div>", unsafe_allow_html=True)
with st.container():
    st.header("📈 Economic Data (FRED)")
    sid = st.text_input("FRED Series ID", value="UNRATE")
    if st.button("Get FRED Data"):
        df = get_fred_data(sid)
        if df is not None: st.dataframe(df.tail())
        else: st.error("No data found.")

## Market Trends Data
st.markdown("<div id='market_trends_data'></div>", unsafe_allow_html=True)
with st.container():
    st.header("📊 Market Trends")
    ticker = st.text_input("Ticker (e.g. AAPL, ^NSEI)", value="AAPL")
    sd = st.date_input("From", value=datetime.today() - timedelta(days=365))
    ed = st.date_input("To", value=datetime.today())
    if st.button("Fetch Market Data"):
        df = yf.download(ticker, start=sd, end=ed)
        st.dataframe(df.head())
        st.dataframe(df.tail())

## Financial News
st.markdown("<div id='financial_news'></div>", unsafe_allow_html=True)
with st.container():
    st.header("📰 Latest Financial News")
    if st.button("Refresh News"):
        for art in get_news():
            st.markdown(f"<div class='card'><strong>{art.get('title')}</strong><br/>{art.get('source',{}).get('name')}</div>", unsafe_allow_html=True)

## Company Financials
st.markdown("<div id='company_financials'></div>", unsafe_allow_html=True)
with st.container():
    st.header("🏢 Company Financials")
    sym = st.text_input("Ticker", value="AAPL")
    if st.button("Get Company Data"):
        info = get_company_fin(sym)
        if "annualReports" in info:
            st.dataframe(pd.DataFrame(info["annualReports"]))
        else:
            st.error(info.get("Note","No data"))

## Ask the AI
st.markdown("<div id='ask_the_ai'></div>", unsafe_allow_html=True)
with st.container():
    st.header("💬 Ask the AI")
    q3 = st.text_area("Your Question")
    if st.button("Ask AI"):
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        resp = genai.GenerativeModel('gemini-1.5-flash').generate_content(q3)
        st.markdown(f"<div class='card'>{resp.text}</div>", unsafe_allow_html=True)
