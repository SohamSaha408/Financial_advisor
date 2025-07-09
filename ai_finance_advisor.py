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

# --- NEW: Hugging Face Model Loading and Sentiment Analysis ---
@st.cache_resource
def load_sentiment_model():
    """Loads a pre-trained sentiment analysis model from Hugging Face."""
    try:
        # This is a common, relatively lightweight sentiment model
        model_name = "distilbert-base-uncased-finetuned-sst-2-english"
        # Download and load the model and tokenizer
        classifier = pipeline("sentiment-analysis", model=model_name)
        st.success(f"Sentiment model '{model_name}' loaded successfully!")
        return classifier
    except Exception as e:
        st.error(f"Error loading Hugging Face sentiment model: {e}. "
                 "Ensure 'transformers' and 'torch' (or 'tensorflow') are installed in requirements.txt.")
        return None

# Load the model once at startup
sentiment_classifier = load_sentiment_model()
# --- END NEW HUGGING FACE SECTION ---


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

st.markdown("---")
st.header("🔍 Mutual Fund Research")
search_query = st.text_input("Enter fund name to search", key="fund_search_input")
if search_query:
    funds = search_funds(search_query)
    for fund in funds[:5]:
        st.markdown(f"<p style='color: white;'><b>{fund['schemeName']}</b></p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: white;'>Scheme Code: {fund.get('schemeCode', 'N/A')}</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: white;'>[Live NAV](https://api.mfapi.in/mf/{fund.get('schemeCode', '')})</p>", unsafe_allow_html=True)

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
            else:
                st.info("No data could be retrieved for the provided FRED Series ID.")
    else:
        st.warning("Please enter a FRED Series ID to fetch data.")

# --- Latest Financial News Section ---
st.markdown("---")
st.header("📰 Latest Financial News")
st.write("Current top financial headlines from around the world.")

if st.button("Refresh News", key="refresh_news_btn"):
    with st.spinner("Fetching latest news..."):
        articles = get_financial_news(query="finance OR economy OR stock market OR investing", language="en", page_size=5)

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
        else:
            st.info("Could not fetch financial news at this moment. Please try again later.")

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
            get_company_financials(company_ticker_av, statement_type=statement_type_selected)
    else:
        st.warning("Please enter a company stock ticker.")


st.markdown("---")
st.header("💬 Ask the AI")
user_question = st.text_area("Ask your financial question:", key="ai_question_area")

if user_question:
    # --- Option for Hugging Face Sentiment Analysis (if model loaded) ---
    if sentiment_classifier:
        with st.spinner("Analyzing sentiment with Hugging Face..."):
            hf_sentiment_result = sentiment_classifier(user_question)[0]
            st.info(f"Hugging Face Sentiment: **{hf_sentiment_result['label']}** (Confidence: {hf_sentiment_result['score']:.2f})")
    else:
        st.warning("Hugging Face sentiment model not loaded. Please check logs for errors or confirm dependencies.")
    # --- END Hugging Face Sentiment ---

    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
    except KeyError:
        st.error("Gemini API key not found in Streamlit secrets. Please set it as `gemini.api_key` in .streamlit/secrets.toml or Streamlit Cloud secrets.")
        st.stop()

    model = genai.GenerativeModel('gemini-1.5-flash')

    with st.spinner("Thinking..."):
        try:
            # Original Gemini prompt for financial advice (you can remove the explicit sentiment instruction here
            # if you prefer to rely solely on the Hugging Face model for sentiment display).
            # If you want Gemini to *also* comment on sentiment, keep its instruction.
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
        except Exception as e:
            st.error(f"Error calling Gemini AI: {e}. Please check your API key and model usage.")
