import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import base64
import os
import requests
import google.generativeai as genai
from pypdf import PdfReader
from fredapi import Fred
import yfinance as yf # NEW IMPORT

from advisor import generate_recommendation, search_funds

# IMPORTANT: st.set_page_config MUST be the first Streamlit command
st.set_page_config(page_title="AI Financial Advisor", layout="centered")

# --- 1. Background and Initial CSS ---
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
            background-color: #4CAF50; color: white; border-radius: 0.5rem; border: none;
            padding: 0.75rem 1.5rem; font-size: 1rem; cursor: pointer; transition: background-color 0.3s;
        }}
        .stButton>button:hover {{
            background-color: #45a049;
        }}
        .stTextInput, .stNumberInput, .stSelectbox, .stTextArea {{
            background-color: rgba(255, 255, 255, 0.1); border-radius: 0.5rem; padding: 0.5rem;
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
        st.error(f"Error loading background image '{image_file}'. Please check the file path and name.")
        fallback_css = """<style>.stApp {background-color: #222222; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-size: cover; background-position: center; background-repeat: no-repeat; background-attachment: fixed;}</style>"""
        st.markdown(fallback_css, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"An unexpected error occurred while setting background: {e}")
        fallback_css = """<style>.stApp {background-color: #222222; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-size: cover; background-position: center; background-repeat: no-repeat; background-attachment: fixed;}</style>"""
        st.markdown(fallback_css, unsafe_allow_html=True)

set_background("black-particles-background.avif")

# --- Initialize session state for AI summary inputs ---
if 'ai_summary_data' not in st.session_state:
    st.session_state['ai_summary_data'] = {}


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
            ordered_cols = [col for col in desired_order if col in df.columns] + \
                           [col for col in df.columns if col not in desired_order]
            df = df[ordered_cols]

            st.dataframe(df.set_index('fiscalDateEnding'))
            return df
        elif "Note" in data:
            st.warning(f"Alpha Vantage API note for {symbol}: {data['Note']}. This often indicates a rate limit, an invalid symbol, or no data for the requested function.")
        else:
            st.warning(f"No {statement_type.replace('_', ' ').lower()} data found for {symbol}. Check the symbol or API key.")
        return None
    except KeyError:
        st.error("Alpha Vantage API key not found in Streamlit secrets. Please add `alphavantage.api_key` to .streamlit/secrets.toml or Streamlit Cloud secrets.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching financial statements for {symbol}: {e}. Check API key or internet connection.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred while fetching financial statements: {e}")
        return None


# --- Streamlit App Layout ---

st.title("💸 AI Financial Advisor")
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

    st.subheader("📊 Allocation Chart")
    alloc = result["allocation"]
    eq = extract_amount(alloc["Equity"])
    de = extract_amount(alloc["Debt"])
    go = extract_amount(alloc["Gold"])
    chart_data = pd.DataFrame({"Type": ["Equity", "Debt", "Gold"], "Amount": [eq, de, go]})
    fig = px.pie(chart_data, names='Type', values='Amount', title="Investment Split")
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    fig.update_traces(textinfo='percent+label', marker=dict(line=dict(color='#000000', width=1)))
    fig.update_layout(title_font_color='white', legend_font_color='white')
    st.plotly_chart(fig, use_container_width=True)

    # --- Capture for AI Summary ---
    st.session_state['ai_summary_data']['Investment Plan'] = {
        "user_inputs": f"Age: {age}, Income: {income}, Profession: {profession}, Region: {region}, Goal: {goal}",
        "advice": result['advice_text'],
        "allocation": f"Equity: {eq}, Debt: {de}, Gold: {go}"
    }

st.markdown("---")
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


# --- Document Analyzer Section ---
st.markdown("---")
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


# --- Economic Data from FRED Section ---
st.markdown("---")
st.header("📈 Economic Data from FRED")
st.write("Enter a FRED Series ID (e.g., `UNRATE` for Unemployment Rate, `GDP` for Gross Domestic Product) to visualize economic data.")

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

                fig = go.Figure(data=go.Scatter(x=fred_df.index, y=fred_df[fred_series_id], mode='lines+markers', name=fred_series_id))
                fig.update_layout(
                    title=f"{fred_series_id} Over Time",
                    xaxis_title="Date",
                    yaxis_title="Value",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.2)'),
                    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.2)')
                )
                st.plotly_chart(fig, use_container_width=True)
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


# --- NEW: Market Trends Visualization Section ---
# ... (rest of your code above this section) ...

# --- NEW: Market Trends Visualization Section ---
st.markdown("---")
st.header("📈 Market Trends Visualization (Candlestick)")
st.write("Visualize historical price trends for Nifty 50 or other stock/index symbols.")
st.info("Hint: For **Nifty 50**, use ticker `^NSEI`. For **Reliance Industries**, use `RELIANCE.NS`. For **Apple**, use `AAPL`.") # Added AAPL as a common example

market_ticker = st.text_input(
    "Enter Stock/Index Ticker Symbol (e.g., ^NSEI, RELIANCE.NS):",
    value="^NSEI", # Default to Nifty 50
    key="market_ticker_input"
).strip().upper()

# Set default start date to 1 year ago and end date to today
from datetime import datetime, timedelta
end_date = datetime.now().date()
start_date = end_date - timedelta(days=365) # One year ago

col1, col2 = st.columns(2)
with col1:
    chart_start_date = st.date_input("Start Date", value=start_date, key="chart_start_date")
with col2:
    chart_end_date = st.date_input("End Date", value=end_date, key="chart_end_date")

if st.button("Get Market Trend Chart", key="get_market_trend_btn"):
    if market_ticker:
        with st.spinner(f"Fetching historical data for {market_ticker}..."):
            try:
                # Ensure dates are in correct format for yfinance (it handles datetime.date objects fine)
                data = yf.download(market_ticker, start=chart_start_date, end=chart_end_date)

                # --- DEBUGGING STEP: Display the raw data ---
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
                    st.write("-----------------------------")

                    st.subheader(f"Candlestick Chart for {market_ticker}")
                    fig = go.Figure(data=[go.Candlestick(
                        x=data.index,
                        open=data['Open'],
                        high=data['High'],
                        low=data['Low'],
                        close=data['Close']
                    )])
                    fig.update_layout(
                        title=f"{market_ticker} Price Trend ({chart_start_date} to {chart_end_date})",
                        xaxis_title="Date",
                        yaxis_title="Price",
                        xaxis_rangeslider_visible=False, # Hide the range slider for cleaner look
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font_color='white',
                        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.2)'),
                        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.2)')
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # --- Capture for AI Summary ---
                    # Safely get the first/last values for summary
                    first_open = data['Open'].iloc[0] if not data['Open'].empty else 'N/A'
                    last_close = data['Close'].iloc[-1] if not data['Close'].empty else 'N/A'
                    max_high = data['High'].max() if not data['High'].empty else 'N/A'
                    min_low = data['Low'].min() if not data['Low'].empty else 'N/A'

                    st.session_state['ai_summary_data']['Market Trend Visualization'] = {
                        "ticker": market_ticker,
                        "date_range": f"{chart_start_date} to {chart_end_date}",
                        "data_summary": (
                            f"Fetched {len(data)} data points. "
                            f"Start Open: {first_open:.2f}, "
                            f"End Close: {last_close:.2f}, "
                            f"Max High: {max_high:.2f}, "
                            f"Min Low: {min_low:.2f}"
                        ) if isinstance(first_open, (int, float)) and isinstance(last_close, (int, float)) else "Data summary not available due to missing values or non-numeric data."
                    }

            except Exception as e:
                st.error(f"An error occurred while fetching or plotting market data for {market_ticker}: {e}. Please ensure the ticker is correct and try again with a valid date range.")
                st.session_state['ai_summary_data']['Market Trend Visualization'] = {
                    "ticker": market_ticker,
                    "date_range": f"{chart_start_date} to {chart_end_date}",
                    "data_summary": f"Error during fetch/plot: {e}"
                }
    else:
        st.warning("Please enter a ticker symbol to fetch market trends.")
# --- END NEW SECTION ---

# ... (rest of your code below this section) ...
# --- END NEW SECTION ---


# --- Latest Financial News Section ---
st.markdown("---")
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
            st.session_state['ai_summary_data']['Financial News'] = {
                "number_of_articles": 0,
                "articles_summary": "No news articles fetched."
            }

# --- Company Financials (via SEC EDGAR/Alpha Vantage) Section ---
st.markdown("---")
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
                    "financial_data_head": company_df.head().to_markdown() # Send top rows as markdown
                }
            else:
                st.session_state['ai_summary_data']['Company Financials'] = {
                    "ticker": company_ticker_av,
                    "statement_type": statement_type_selected,
                    "financial_data_head": "No data found."
                }
    else:
        st.warning("Please enter a company stock ticker.")

# --- AI Summary Section ---
st.markdown("---")
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
            elif feature_name == "Market Trend Visualization": # NEW CASE
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
            summary_prompt_parts.append("\n") # Add a newline for separation

        full_summary_prompt = "\n".join(summary_prompt_parts)

        with st.spinner("Generating AI Summary..."):
            try:
                summary_response = model.generate_content(contents=[{"role": "user", "parts": [full_summary_prompt]}])
                st.subheader("💡 AI's Consolidated Summary & Commentary:")
                st.markdown(f"<p style='color: white;'>{summary_response.text}</p>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error calling Gemini AI for summary: {e}. This might be due to the prompt being too long or other API issues. Try using fewer features or shorter inputs.")

# --- Ask the AI Section ---
st.markdown("---")
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
