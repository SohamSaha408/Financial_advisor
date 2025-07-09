# ai_financial_advisor.py
import streamlit as st
import os, base64, re, requests, pandas as pd, numpy as np
import yfinance as yf, google.generativeai as genai
from pypdf import PdfReader
from fredapi import Fred
from datetime import datetime, timedelta
from advisor import generate_recommendation, search_funds

st.set_page_config(page_title="AI Financial Advisor", layout="centered")

# 1. Section IDs Map
SECTION_IDS = {
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

# 2. Auto-scroll snippet
query = st.experimental_get_query_params().get("section", [None])[0]
if query:
    st.markdown(f"""<script>
    document.getElementById("{query}")?.scrollIntoView({{behavior: 'smooth', block: 'start'}});
    </script>""", unsafe_allow_html=True)

# 3. Professional styling (dark theme)
st.markdown("""
<style>
body, .stApp { font-family:'Segoe UI',sans-serif; background:#1B1F24; color:#E0E0E0; }
[data-testid="stSidebar"] {background:#14171A; padding-top:1rem;}
[data-testid="stSidebar"] .stRadio>label {color:#E0E0E0;}
.section-container {background:#22272E; padding:1.5rem; margin:1rem auto;
  border-radius:0.6rem; max-width:900px; box-shadow:0 4px 16px rgba(0,0,0,0.5);}
.card {background:#2C3138; padding:1rem; margin-bottom:1rem;
  border-radius:0.5rem; box-shadow:0 2px 8px rgba(0,0,0,0.3);}
.stButton>button {background:#0A84FF;color:#fff;border:none;
  padding:0.6rem 1.2rem;border-radius:0.4rem;}
.stButton>button:hover {background:#006FD6;}
.stTextInput>div,.stNumberInput>div,.stSelectbox>div {
  background:#2C3138;border:1px solid #3A424C;border-radius:0.4rem;}
.stTextInput input,.stNumberInput input,
.stSelectbox div[role="button"]{background:transparent;color:#E0E0E0;}
</style>""", unsafe_allow_html=True)

# 4. Background image (optional)
if os.path.exists("black-particles-background.avif"):
    img = base64.b64encode(open("black-particles-background.avif","rb").read()).decode()
    st.markdown(f"<style>.stApp{{background:url(data:image/png;base64,{img}) "
                "center/cover fixed}}</style>", unsafe_allow_html=True)

# 5. Sidebar Navigation
st.sidebar.title("📁 Dashboard")
choice = st.sidebar.radio("Go to:", list(SECTION_IDS.keys()))
if choice:
    st.experimental_set_query_params(section=SECTION_IDS[choice])

# 6. Initialize summary state
if 'ai_summary_data' not in st.session_state:
    st.session_state['ai_summary_data'] = {}

# 7. Utility Functions
def extract_amount(s): return int(re.search(r"\u20B9([0-9]+)", s).group(1)) if s else 0
def get_pdf_text(f): txt=""; [txt:=txt+p.extract_text() for p in PdfReader(f).pages]; return txt
def get_fred(id): return pd.DataFrame(Fred(api_key=st.secrets["fred"]["api_key"]).get_series(id), columns=[id])
def get_news(): return requests.get(
    f"https://newsapi.org/v2/top-headlines?category=business&apiKey={st.secrets['newsapi']['api_key']}"
).json().get("articles",[])
def get_company(sym): return requests.get(
    f"https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={sym}&apikey={st.secrets['alphavantage']['api_key']}"
).json()

# === MAIN CONTENT ===
st.title("💸 AI Financial Advisor")

def section_start(name, emoji=None):
    sec_id = SECTION_IDS[name]
    st.markdown(f"<div id='{sec_id}'></div>", unsafe_allow_html=True)
    header = f"{emoji} {name}" if emoji else name
    st.markdown(f"<div class='section-container'><h2>{header}</h2>", unsafe_allow_html=True)

def section_end():
    st.markdown("</div>", unsafe_allow_html=True)

# Investment Plan
section_start("Investment Plan", emoji="📊")
age = st.number_input("Age", min_value=18)
income = st.number_input("Monthly Income (₹)", step=1000)
profession = st.selectbox("Profession", ["Student","Salaried","Self-employed"])
region = st.selectbox("Region", ["Metro","Urban","Rural"])
goal = st.selectbox("Goal", ["Wealth Accumulation","Retirement Planning","Short-term","Tax Saving (ELSS)"])
if st.button("Get Advice"):
    r = generate_recommendation(age, income, profession, region, goal)
    st.markdown(f"<div class='card'>{r['advice_text']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='card'>{r['allocation']}</div>", unsafe_allow_html=True)
section_end()

# Mutual Fund Research
section_start("Mutual Fund Research", emoji="🔍")
q = st.text_input("Fund Name")
if q:
    for f in search_funds(q)[:5]:
        st.markdown(f"<div class='card'><b>{f['schemeName']}</b><br/>Code: {f.get('schemeCode')}</div>", unsafe_allow_html=True)
section_end()

# Document Analyzer
section_start("Document Analyzer", emoji="📄")
up = st.file_uploader("Upload PDF/TXT", type=["pdf","txt"])
if up:
    txt = get_pdf_text(up) if up.name.endswith("pdf") else up.getvalue().decode()
    st.text_area("Preview", txt[:500], height=150)
    q2 = st.text_area("Ask question")
    if st.button("Analyze"):
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
        resp = genai.GenerativeModel('gemini-1.5-flash').generate_content(f"{txt}\n\nQ: {q2}")
        st.markdown(f"<div class='card'>{resp.text}</div>", unsafe_allow_html=True)
section_end()

# FRED Data
section_start("Economic Data (FRED)", emoji="📊")
sid = st.text_input("Series ID", value="UNRATE")
if st.button("Fetch"):
    df = get_fred(sid)
    if df is not None: st.dataframe(df.tail())
section_end()

# Market Trends
section_start("Market Trends Data", emoji="📊")
tkr = st.text_input("Ticker", value="AAPL")
sd = st.date_input("From", datetime.today() - timedelta(days=365))
ed = st.date_input("To", datetime.today())
if st.button("Fetch Data"):
    df = yf.download(tkr, start=sd, end=ed)
    st.dataframe(df.head())
    st.dataframe(df.tail())
section_end()

# Financial News
section_start("Latest Financial News", emoji="📰")
if st.button("Refresh News"):
    for art in get_news():
        st.markdown(f"<div class='card'><b>{art.get('title')}</b><br/>{art.get('source',{}).get('name')}</div>", unsafe_allow_html=True)
section_end()

# Company Financials
section_start("Company Financials", emoji="🏛️")
sym = st.text_input("Ticker", value="AAPL")
if st.button("Fetch Company Data"):
    comp = get_company(sym)
    if "annualReports" in comp:
        st.dataframe(pd.DataFrame(comp["annualReports"]))
    else:
        st.error(comp.get("Note","No data found"))
section_end()

# Ask the AI
section_start("Ask the AI", emoji="💬")
q3 = st.text_area("Your question")
if st.button("Ask AI"):
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    resp = genai.GenerativeModel('gemini-1.5-flash').generate_content(q3)
    st.markdown(f"<div class='card'>{resp.text}</div>", unsafe_allow_html=True)
section_end()
