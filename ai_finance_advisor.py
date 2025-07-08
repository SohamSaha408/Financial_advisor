import streamlit as st
import pandas as pd
import plotly.express as px
import re
import base64
import os
import google.generativeai as genai

# IMPORTANT: st.set_page_config MUST be the first Streamlit command
st.set_page_config(page_title="AI Financial Advisor", layout="centered")

# --- Debugging Secrets (TEMPORARY - REMOVE LATER) ---
st.write("--- Debugging Secrets ---")
st.write(f"Does secrets.toml exist? {os.path.exists('.streamlit/secrets.toml')}")
try:
    st.write(f"Content of st.secrets: {st.secrets.to_dict()}")
    st.write(f"Does 'gemini' key exist in st.secrets? {'gemini' in st.secrets}")
    if 'gemini' in st.secrets:
        st.write(f"Does 'api_key' exist in st.secrets['gemini']? {'api_key' in st.secrets['gemini']}")
except Exception as e:
    st.write(f"Error accessing st.secrets during debug: {e}")
st.write("--- End Debugging Secrets ---")
# --- END Debugging Secrets ---

def set_background(image_file):
    # ... (rest of your set_background function, which should be unchanged) ...
    # (Paste your set_background function here from the previous response)
    if not os.path.exists(image_file):
        st.error(f"Background image not found: '{image_file}'. Please ensure the image is in the correct directory.")
        fallback_css = """
        <style>
        .stApp {
            background-color: #222222; /* Dark fallback color */
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }
        </style>
        """
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
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        .main .block-container {{
            background-color: rgba(0, 0, 0, 0.75);
            padding: 2rem;
            border-radius: 1rem;
            margin: 2rem auto;
            max-width: 700px;
            width: 90%;
            color: white;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(5px);
            -webkit-backdrop-filter: blur(5px);
            overflow: auto;
        }}
        .stMarkdown, .stText, .stLabel, .stTextInput > div > label, .stNumberInput > label, .stSelectbox > label, .stTextArea > label {{
            color: white !important;
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: #E0E0E0 !important;
            text-shadow: 1px 1px 3px rgba(0,0,0,0.7);
        }}
        .stButton>button {{
            background-color: #4CAF50;
            color: white;
            border-radius: 0.5rem;
            border: none;
            padding: 0.75rem 1.5rem;
            font-size: 1rem;
            cursor: pointer;
            transition: background-color 0.3s;
        }}
        .stButton>button:hover {{
            background-color: #45a049;
        }}
        .stTextInput, .stNumberInput, .stSelectbox, .stTextArea {{
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 0.5rem;
            padding: 0.5rem;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }}
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stTextArea > div > div > textarea {{
            color: white;
            background-color: transparent;
            border: none;
        }}
        .stSelectbox > div > div[data-baseweb="select"] > div[role="button"] {{
            color: white;
            background-color: transparent;
            border: none;
        }}
        .stSelectbox div[data-baseweb="select"] div[role="listbox"] {{
            background-color: rgba(0, 0, 0, 0.9);
            color: white;
        }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"Error loading background image '{image_file}'. Please check the file path and name.")
        fallback_css = """
        <style>
        .stApp {
            background-color: #222222;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }
        </style>
        """
        st.markdown(fallback_css, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"An unexpected error occurred while setting background: {e}")
        fallback_css = """
        <style>
        .stApp {
            background-color: #222222;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }
        </style>
        """
        st.markdown(fallback_css, unsafe_allow_html=True)


set_background("best-financial-websites-examples.png")

# --- 2. Main App Logic ---

def extract_amount(value_str):
    match = re.search(r"₹([0-9]+)", value_str)
    return int(match.group(1)) if match else 0

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

st.markdown("---")
st.header("💬 Ask the AI")
user_question = st.text_area("Ask your financial question:", key="ai_question_area")

if user_question:
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
    except KeyError: # More specific exception for secrets not found
        st.error("Gemini API key not found in Streamlit secrets. Please ensure .streamlit/secrets.toml is correctly configured.")
        st.stop()

    model = genai.GenerativeModel('gemini-pro')

    with st.spinner("Thinking..."):
        try:
            response = model.generate_content(
                contents=[
                    {"role": "user", "parts": ["You are a helpful and expert Indian financial advisor.", user_question]}
                ]
            )
            st.subheader("🤖 AI Says:")
            st.markdown(f"<p style='color: white;'>{response.text}</p>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error calling Gemini AI: {e}. Please check your API key and model usage.")
