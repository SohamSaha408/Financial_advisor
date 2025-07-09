# ai_financial_advisor.py (Full version with scrolling + features)

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
import numpy as np

# External logic
from advisor import generate_recommendation, search_funds

# --- Page Setup ---
st.set_page_config(page_title="AI Financial Advisor", layout="centered")

# --- JavaScript for Scrolling ---
st.markdown("""
<script>
function scrollToElement(id) {
    var el = document.getElementById(id);
    if (el) {
        setTimeout(() => {
            el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 300);
    } else {
        console.warn("Scroll target with ID '" + id + "' not found.");
    }
}
</script>
""", unsafe_allow_html=True)

# --- Background Styling ---
def set_background(image_file):
    if not os.path.exists(image_file):
        st.error(f"Missing background image: {image_file}")
        return
    with open(image_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    css = f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{encoded}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: white;
    }}
    .block-container {{
        background-color: rgba(0,0,0,0.75);
        padding: 2rem;
        border-radius: 1rem;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

set_background("black-particles-background.avif")

# --- Sidebar Dashboard ---
st.sidebar.title("📋 Dashboard")
sections = [
    ("Investment Plan", "investment_plan"),
    ("Mutual Fund Research", "mutual_fund_research"),
    ("Document Analyzer", "document_analyzer"),
    ("Economic Data (FRED)", "fred_data"),
    ("Market Trends Data", "market_trends_data"),
    ("Latest Financial News", "financial_news"),
    ("Company Financials", "company_financials"),
    ("AI Summary", "ai_summary"),
    ("Ask the AI", "ask_the_ai")
]
for label, anchor_id in sections:
    st.sidebar.button(label, on_click=lambda id=anchor_id: st.markdown(f"<script>scrollToElement('{id}')</script>", unsafe_allow_html=True))

# --- Initialize state ---
if 'ai_summary_data' not in st.session_state:
    st.session_state['ai_summary_data'] = {}

# --- Define helper functions ---
def extract_amount(value_str):
    match = re.search(r"\u20b9([0-9]+)", value_str)
    return int(match.group(1)) if match else 0

def get_pdf_text(pdf_file):
    try:
        return "".join([page.extract_text() for page in PdfReader(pdf_file).pages])
    except Exception as e:
        st.error(f"PDF read error: {e}")
        return ""

def get_fred_data(series_id, start_date=None, end_date=None):
    try:
        fred = Fred(api_key=st.secrets["fred"]["api_key"])
        data = fred.get_series(series_id, observation_start=start_date, observation_end=end_date)
        return pd.DataFrame(data).rename(columns={0: series_id}) if not data.empty else None
    except Exception as e:
        st.error(f"FRED error: {e}")
        return None

def get_financial_news(query="finance", language="en", page_size=5):
    try:
        url = (
            f"https://newsapi.org/v2/everything?q={query}&language={language}&pageSize={page_size}&"
            f"apiKey={st.secrets['newsapi']['api_key']}"
        )
        return requests.get(url).json().get("articles", [])
    except Exception as e:
        st.error(f"News fetch error: {e}")
        return []

def get_company_financials(symbol, statement_type="INCOME_STATEMENT"):
    try:
        url = f"https://www.alphavantage.co/query?function={statement_type}&symbol={symbol}&apikey={st.secrets['alphavantage']['api_key']}"
        data = requests.get(url).json()
        return pd.DataFrame(data.get("annualReports", [])) if "annualReports" in data else None
    except Exception as e:
        st.error(f"Alpha Vantage error: {e}")
        return None


st.title("💸 AI Financial Advisor")

# --- Dashboard Tiles ---
st.markdown("### 📂 Dashboard")
st.markdown("""
<style>
.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
}
.dashboard-tile {
    background-color: rgba(255, 255, 255, 0.1);
    border: 1px solid #4CAF50;
    border-radius: 0.75rem;
    padding: 1rem;
    text-align: center;
    cursor: pointer;
    color: white;
    font-weight: bold;
    transition: background-color 0.3s;
}
.dashboard-tile:hover {
    background-color: rgba(76, 175, 80, 0.3);
}
</style>

<div class="dashboard-grid">
  <div class="dashboard-tile" onclick="scrollToElement('investment_plan')">📊 Investment Plan</div>
  <div class="dashboard-tile" onclick="scrollToElement('mutual_fund_research')">🔍 Mutual Funds</div>
  <div class="dashboard-tile" onclick="scrollToElement('document_analyzer')">📄 Document Analyzer</div>
  <div class="dashboard-tile" onclick="scrollToElement('fred_data')">📈 FRED Data</div>
  <div class="dashboard-tile" onclick="scrollToElement('market_trends_data')">📊 Market Trends</div>
  <div class="dashboard-tile" onclick="scrollToElement('financial_news')">📰 Financial News</div>
  <div class="dashboard-tile" onclick="scrollToElement('company_financials')">🏢 Company Financials</div>
  <div class="dashboard-tile" onclick="scrollToElement('ai_summary')">🧠 AI Summary</div>
  <div class="dashboard-tile" onclick="scrollToElement('ask_the_ai')">💬 Ask the AI</div>
</div>
""", unsafe_allow_html=True)




# --- Investment Plan Section ---
st.markdown("<div id='investment_plan'></div>", unsafe_allow_html=True) # Anchor for scrolling
st.header("📊 Get Your Investment Plan")

age = st.number_input("Age", min_value=18, key="age_input")
income = st.number_input("Monthly Income (₹)", step=1000, key="income_input")
profession = st.selectbox("Profession", ["Student", "Salaried", "Self-employed"], key="prof_select")
region = st.selectbox("Region", ["Metro", "Urban", "Rural"], key="region_select")
goal = st.selectbox("🎯 Investment Goal", [
    "Wealth Accumulation", "Retirement Planning", "Short-term Savings", "Tax Saving (ELSS)"
], key="goal_select")

if st.button("Get Advice", key="get_advice_btn"):
    result = generate_recommendation(age, income, profession, region, goal)
    st.subheader("🧠 Advice")
    st.markdown(f"<p style='color: white;'>{result['advice_text']}</p>", unsafe_allow_html=True)

    st.subheader("📊 Allocation Data")
    alloc = result["allocation"]
    eq = extract_amount(alloc["Equity"])
    de = extract_amount(alloc["Debt"])
    go = extract_amount(alloc["Gold"])

    # Display allocation as text/dataframe instead of chart
    st.write(f"Equity: ₹{eq:,}")
    st.write(f"Debt: ₹{de:,}")
    st.write(f"Gold: ₹{go:,}")

    # --- Capture for AI Summary ---
    st.session_state['ai_summary_data']['Investment Plan'] = {
        "user_inputs": f"Age: {age}, Income: {income}, Profession: {profession}, Region: {region}, Goal: {goal}",
        "advice": result['advice_text'],
        "allocation": f"Equity: {eq}, Debt: {de}, Gold: {go}"
    }

st.markdown("---")


# --- Mutual Fund Research Section ---
st.markdown("<div id='mutual_fund_research'></div>", unsafe_allow_html=True) # Anchor for scrolling
st.header("🔍 Mutual Fund Research")
search_query = st.text_input("Enter fund name to search", key="fund_search_input")
if search_query:
    funds = search_funds(search_query)
    found_funds_info = []
    if funds:
        for fund in funds[:5]:
            st.markdown(f"<p style='color: white;'><b>{fund['schemeName']}</b></p>", unsafe_allow_html=True)
            st.markdown(f"<p style='color: white;'>Scheme Code: {fund.get('schemeCode', 'N/A')}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='color: white;'>[Live NAV](https://api.mfapi.in/mf/{fund.get('schemeCode', '')})</p>", unsafe_allow_html=True)
            found_funds_info.append(f"{fund['schemeName']} (Code: {fund.get('schemeCode', 'N/A')})")
        # --- Capture for AI Summary ---
        st.session_state['ai_summary_data']['Mutual Fund Research'] = {
            "query": search_query,
            "results": f"Found {len(funds)} funds. Top 5: {', '.join(found_funds_info)}"
        }
    else:
        st.markdown("<p style='color: white;'>No funds found for your query.</p>", unsafe_allow_html=True)
        st.session_state['ai_summary_data']['Mutual Fund Research'] = {
            "query": search_query,
            "results": "No funds found."
        }
st.markdown("---")


# --- Document Analyzer Section ---
st.markdown("<div id='document_analyzer'></div>", unsafe_allow_html=True) # Anchor for scrolling
st.header("📄 Document Analyzer")
st.write("Upload a document (PDF or TXT) for the AI to analyze and provide advice.")
uploaded_file = st.file_uploader("Choose a file", type=["pdf", "txt"], key="doc_uploader")

document_text = ""
if uploaded_file is not None:
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()

    if file_extension == ".pdf":
        st.info("Extracting text from PDF... This may take a moment for large files.")
        document_text = get_pdf_text(uploaded_file)
    elif file_extension == ".txt":
        st.info("Reading text from TXT file...")
        document_text = uploaded_file.getvalue().decode("utf-8")
    else:
        st.warning("Unsupported file type. Please upload a PDF or TXT file.")

    if document_text:
        st.subheader("Extracted Document Text (Preview)")
        preview_text = document_text[:1000]
        if len(document_text) > 1000:
            preview_text += "\n\n... (Document truncated for preview. Full content sent to AI.)"
        st.text_area("Document Content", preview_text, height=300, disabled=True)

        st.markdown("---")
        st.subheader("Ask AI about this Document")
        document_question = st.text_area("What do you want to know or analyze about this document?", key="doc_ai_question_area")

        if st.button("Analyze Document", key="analyze_doc_btn"):
            if document_question:
                try:
                    genai.configure(api_key=st.secrets["gemini"]["api_key"])
                except KeyError:
                    st.error("Gemini API key not found in Streamlit secrets. Please ensure .streamlit/secrets.toml is correctly configured.")
                    st.stop()

                model = genai.GenerativeModel('gemini-1.5-flash')

                with st.spinner("Analyzing document..."):
                    try:
                        prompt = (
                            f"You are a helpful and expert Indian financial advisor. Analyze the following document and provide advice/answers based on the user's question.\n\n"
                            f"--- Document Content ---\n{document_text}\n\n"
                            f"--- User Question ---\n{document_question}\n\n"
                            f"--- Financial Advice/Analysis ---"
                        )
                        response = model.generate_content(contents=[{"role": "user", "parts": [prompt]}])
                        st.subheader("🤖 AI's Document Analysis:")
                        st.markdown(f"<p style='color: white;'>{response.text}</p>", unsafe_allow_html=True)
                        # --- Capture for AI Summary ---
                        st.session_state['ai_summary_data']['Document Analysis'] = {
                            "document_question": document_question,
                            "ai_response": response.text
                        }
                    except Exception as e:
                        st.error(f"Error calling Gemini AI for document analysis: {e}. This might be due to model token limits or other API issues. Try a shorter document or question.")
            else:
                st.warning("Please enter a question to analyze the document.")
    else:
        st.warning("Could not extract text from the uploaded document. Please try another file or ensure it's a readable PDF/TXT.")
st.markdown("---")


# --- Economic Data from FRED Section ---
st.markdown("<div id='fred_data'></div>", unsafe_allow_html=True) # Anchor for scrolling
st.header("📈 Economic Data from FRED")
st.write("Enter a FRED Series ID (e.g., `UNRATE` for Unemployment Rate, `GDP` for Gross Domestic Product) to view economic data.")

fred_series_id = st.text_input(
    "FRED Series ID:",
    value="UNRATE", # Default example
    key="fred_series_input"
).strip().upper()

if st.button("Get FRED Data", key="fetch_fred_data_btn"):
    if fred_series_id:
        with st.spinner(f"Fetching data for {fred_series_id} from FRED..."):
            fred_df = get_fred_data(fred_series_id)

            if fred_df is not None:
                st.subheader(f"Latest Data for {fred_series_id}")
                st.dataframe(fred_df.tail())

                # --- Capture for AI Summary ---
                st.session_state['ai_summary_data']['FRED Data'] = {
                    "series_id": fred_series_id,
                    "data_summary": f"Latest 5 observations for {fred_series_id}:\n" + fred_df.tail().to_markdown()
                }
            else:
                st.info("No data could be retrieved for the provided FRED Series ID.")
                st.session_state['ai_summary_data']['FRED Data'] = {
                    "series_id": fred_series_id,
                    "data_summary": "No data retrieved."
                }
    else:
        st.warning("Please enter a FRED Series ID to fetch data.")
st.markdown("---")


# --- Market Trends Data Section ---
st.markdown("<div id='market_trends_data'></div>", unsafe_allow_html=True) # Anchor for scrolling
st.header("📊 Market Trends Data (Raw Data Only)")
st.write("View raw historical data for Nifty 50 or other stock/index symbols.")
st.info("Hint: For **Nifty 50**, use ticker `^NSEI`. For **Reliance Industries**, use `RELIANCE.NS`. For **Apple**, use `AAPL`.")

market_ticker = st.text_input(
    "Enter Stock/Index Ticker Symbol (e.g., ^NSEI, RELIANCE.NS):",
    value="^NSEI", # Default to Nifty 50
    key="market_ticker_input"
).strip().upper()

# Set default start date to 1 year ago and end date to today
end_date = datetime.now().date()
start_date = end_date - timedelta(days=365) # One year ago

col1, col2 = st.columns(2)
with col1:
    chart_start_date = st.date_input("Start Date", value=start_date, key="chart_start_date")
with col2:
    chart_end_date = st.date_input("End Date", value=end_date, key="chart_end_date")

if st.button("Get Market Data", key="get_market_data_btn"): # Changed button text
    if market_ticker:
        with st.spinner(f"Fetching historical data for {market_ticker}..."):
            try:
                # Fetch data using yfinance
                data = yf.download(market_ticker, start=chart_start_date, end=chart_end_date)

                if data.empty:
                    st.warning(f"No historical data found for '{market_ticker}' in the specified date range ({chart_start_date} to {chart_end_date}). This could be due to an incorrect ticker, an unsupported date range, or no trading activity.")
                    st.session_state['ai_summary_data']['Market Trend Visualization'] = {
                        "ticker": market_ticker,
                        "date_range": f"{chart_start_date} to {chart_end_date}",
                        "data_summary": "No data found."
                    }
                else:
                    st.write("--- Raw Data Fetched (Head) ---")
                    st.dataframe(data.head()) # Show the first few rows of data to verify
                    st.write("--- Raw Data Fetched (Tail) ---")
                    st.dataframe(data.tail()) # Also show tail to give more context if data is large
                    st.write("-----------------------------")

                    # --- Capture for AI Summary ---
                    first_open = data['Open'].iloc[0] if not data['Open'].empty else None
                    last_close = data['Close'].iloc[-1] if not data['Close'].empty else None
                    max_high = data['High'].max() if not data['High'].empty else None
                    min_low = data['Low'].min() if not data['Low'].empty else None

                    summary_parts = [f"Fetched {len(data)} data points."]
                    if first_open is not None:
                        summary_parts.append(f"Start Open: {first_open:.2f}")
                    if last_close is not None:
                        summary_parts.append(f"End Close: {last_close:.2f}")
                    if max_high is not None:
                        summary_parts.append(f"Max High: {max_high:.2f}")
                    if min_low is not None:
                        summary_parts.append(f"Min Low: {min_low:.2f}")

                    st.session_state['ai_summary_data']['Market Trend Visualization'] = {
                        "ticker": market_ticker,
                        "date_range": f"{chart_start_date} to {chart_end_date}",
                        "data_summary": ", ".join(summary_parts)
                    }

            except Exception as e:
                st.error(f"An error occurred while fetching market data for {market_ticker}: {e}. Please ensure the ticker is correct and try again with a valid date range.")
                st.session_state['ai_summary_data']['Market Trend Visualization'] = {
                    "ticker": market_ticker,
                    "date_range": f"{chart_start_date} to {chart_end_date}",
                    "data_summary": f"Error during fetch: {e}"
                }
    else:
        st.warning("Please enter a ticker symbol to fetch market trends.")
st.markdown("---")


# --- Latest Financial News Section ---
st.markdown("<div id='financial_news'></div>", unsafe_allow_html=True) # Anchor for scrolling
st.header("📰 Latest Financial News")
st.write("Current top financial headlines from around the world.")

if st.button("Refresh News", key="refresh_news_btn"):
    with st.spinner("Fetching latest news..."):
        articles = get_financial_news(query="finance OR economy OR stock market OR investing", language="en", page_size=5)
        news_summary_list = []
        if articles:
            for i, article in enumerate(articles):
                st.subheader(f"{i+1}. {article.get('title', 'No Title')}")
                published_date = article.get('publishedAt')
                if published_date:
                    try:
                        published_date = pd.to_datetime(published_date).strftime('%Y-%m-%d %H:%M')
                    except ValueError:
                        published_date = "N/A"
                else:
                    published_date = "N/A"
                st.write(f"**Source:** {article.get('source', {}).get('name', 'N/A')} - **Published:** {published_date}")
                st.write(article.get('description', 'No description available.'))
                st.markdown(f"[Read Full Article]({article.get('url', '#')})")
                st.markdown("---")
                news_summary_list.append(f"Title: {article.get('title', 'N/A')}, Source: {article.get('source', {}).get('name', 'N/A')}, Description: {article.get('description', 'N/A')[:150]}...")
            # --- Capture for AI Summary ---
            st.session_state['ai_summary_data']['Financial News'] = {
                "number_of_articles": len(articles),
                "articles_summary": "\n".join(news_summary_list)
            }
        else:
            st.info("Could not fetch financial news at this moment. Please try again later.")
            st.session_session_state['ai_summary_data']['Financial News'] = {
                "number_of_articles": 0,
                "articles_summary": "No news articles fetched."
            }
st.markdown("---")


# --- Company Financials (via Alpha Vantage) Section ---
st.markdown("<div id='company_financials'></div>", unsafe_allow_html=True) # Anchor for scrolling
st.header("🏢 Company Financials (via Alpha Vantage)")
st.write("Get key financial statements (e.g., Income Statement) for publicly traded companies using their ticker symbol.")

company_ticker_av = st.text_input(
    "Enter Company Stock Ticker (e.g., IBM, GOOGL, MSFT):",
    key="company_ticker_av_input"
).strip().upper()

statement_type_selected = st.selectbox(
    "Select Statement Type:",
    options=["INCOME_STATEMENT", "BALANCE_SHEET", "CASH_FLOW"],
    key="statement_type_select"
)

if st.button("Get Company Financials", key="get_company_financials_btn"):
    if company_ticker_av:
        with st.spinner(f"Fetching {statement_type_selected.replace('_', ' ').lower()} for {company_ticker_av}..."):
            company_df = get_company_financials(company_ticker_av, statement_type=statement_type_selected)
            if company_df is not None:
                # --- Capture for AI Summary ---
                st.session_state['ai_summary_data']['Company Financials'] = {
                    "ticker": company_ticker_av,
                    "statement_type": statement_type_selected,
                    "financial_data_head": company_df.head().to_markdown() # Ensure tabulate is installed for this to work
                }
            else:
                st.session_state['ai_summary_data']['Company Financials'] = {
                    "ticker": company_ticker_av,
                    "statement_type": statement_type_selected,
                    "financial_data_head": "No data found."
                }
    else:
        st.warning("Please enter a company stock ticker.")
st.markdown("---")


# --- AI Summary Section ---
st.markdown("<div id='ai_summary'></div>", unsafe_allow_html=True) # Anchor for scrolling
st.header("🧠 AI Summary")
st.write("Click the button below to get an AI-generated summary and commentary on the outputs from the features you've used above.")

if st.button("Generate AI Summary", key="generate_ai_summary_btn"):
    if not st.session_state['ai_summary_data']:
        st.info("No data has been generated by the features yet. Please use the features above first.")
    else:
        try:
            genai.configure(api_key=st.secrets["gemini"]["api_key"])
        except KeyError:
            st.error("Gemini API key not found in Streamlit secrets. Please set it as `gemini.api_key` in .streamlit/secrets.toml or Streamlit Cloud secrets.")
            st.stop()

        model = genai.GenerativeModel('gemini-1.5-flash')

        summary_prompt_parts = []
        summary_prompt_parts.append("You are an expert Indian financial advisor providing a summary and commentary. Below are outputs generated from various financial tools. Please consolidate this information, identify key insights, and provide actionable commentary. If a feature was not used, ignore it. Focus on the most relevant financial implications.\n\n")

        for feature_name, data in st.session_state['ai_summary_data'].items():
            summary_prompt_parts.append(f"--- {feature_name} Output ---")
            if feature_name == "Investment Plan":
                summary_prompt_parts.append(f"User Inputs: {data['user_inputs']}")
                summary_prompt_parts.append(f"AI Advice: {data['advice']}")
                summary_prompt_parts.append(f"Allocation: {data['allocation']}")
            elif feature_name == "Mutual Fund Research":
                summary_prompt_parts.append(f"Search Query: {data['query']}")
                summary_prompt_parts.append(f"Results: {data['results']}")
            elif feature_name == "Document Analysis":
                summary_prompt_parts.append(f"Document Question: {data['document_question']}")
                summary_prompt_parts.append(f"AI's Analysis: {data['ai_response']}")
            elif feature_name == "FRED Data":
                summary_prompt_parts.append(f"FRED Series ID: {data['series_id']}")
                summary_prompt_parts.append(f"Data Summary:\n{data['data_summary']}")
            elif feature_name == "Market Trend Visualization":
                summary_prompt_parts.append(f"Ticker: {data['ticker']}")
                summary_prompt_parts.append(f"Date Range: {data['date_range']}")
                summary_prompt_parts.append(f"Summary: {data['data_summary']}")
            elif feature_name == "Financial News":
                summary_prompt_parts.append(f"Number of Articles: {data['number_of_articles']}")
                summary_prompt_parts.append(f"Articles:\n{data['articles_summary']}")
            elif feature_name == "Company Financials":
                summary_prompt_parts.append(f"Company Ticker: {data['ticker']}")
                summary_prompt_parts.append(f"Statement Type: {data['statement_type']}")
                summary_prompt_parts.append(f"Financial Data (Head):\n{data['financial_data_head']}")
            elif feature_name == "Direct AI Question":
                summary_prompt_parts.append(f"User Question: {data['question']}")
                summary_prompt_parts.append(f"AI Response: {data['ai_response']}")
            summary_prompt_parts.append("\n")

        full_summary_prompt = "\n".join(summary_prompt_parts)

        with st.spinner("Generating AI Summary..."):
            try:
                summary_response = model.generate_content(contents=[{"role": "user", "parts": [full_summary_prompt]}])
                st.subheader("💡 AI's Consolidated Summary & Commentary:")
                st.markdown(f"<p style='color: white;'>{summary_response.text}</p>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error calling Gemini AI for summary: {e}. This might be due to the prompt being too long or other API issues. Try using fewer features or shorter inputs.")
st.markdown("---")


# --- Ask the AI Section ---
st.markdown("<div id='ask_the_ai'></div>", unsafe_allow_html=True) # Anchor for scrolling
st.header("💬 Ask the AI")
user_question = st.text_area("Ask your financial question:", key="ai_question_area")

if user_question:
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
    except KeyError:
        st.error("Gemini API key not found in Streamlit secrets. Please set it as `gemini.api_key` in .streamlit/secrets.toml or Streamlit Cloud secrets.")
        st.stop()

    model = genai.GenerativeModel('gemini-1.5-flash')

    with st.spinner("Thinking..."):
        try:
            prompt = (
                f"You are a helpful and expert Indian financial advisor. "
                f"Analyze the user's question and provide your financial advice based on the question.\n\n"
                f"--- User Question ---\n{user_question}"
            )
            response = model.generate_content(
                contents=[
                    {"role": "user", "parts": [prompt]}
                ]
            )
            st.subheader("🤖 AI Says:")
            st.markdown(f"<p style='color: white;'>{response.text}</p>", unsafe_allow_html=True)
            # --- Capture for AI Summary ---
            st.session_state['ai_summary_data']['Direct AI Question'] = {
                "question": user_question,
                "ai_response": response.text
            }
        except Exception as e:
            st.error(f"Error calling Gemini AI: {e}. Please check your API key and model usage.")
