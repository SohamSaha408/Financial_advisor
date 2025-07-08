import streamlit as st
import pandas as pd
import plotly.express as px
import re
import base64
from advisor import generate_recommendation, search_funds # Assuming advisor.py is in the same directory

# --- 1. Background and Initial CSS ---
def set_background(image_file):
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

        /* This is the key CSS for your black box */
        .main-block {{
            background-color: rgba(0, 0, 0, 0.75); /* Black with 75% opacity */
            padding: 2rem; /* Padding inside the box */
            border-radius: 1rem; /* Rounded corners */
            margin: 2rem auto; /* Top/bottom margin, auto for left/right to center */
            max-width: 700px; /* Set a max width for better readability on large screens */
            width: 90%; /* Responsive width */
            color: white; /* Ensure text inside is white for contrast */
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5); /* A subtle shadow for depth */
            backdrop-filter: blur(5px); /* Optional: Adds a slight blur to content behind it */
            -webkit-backdrop-filter: blur(5px); /* For Safari support */
        }}

        /* Adjust Streamlit's default elements for better contrast */
        .stMarkdown, .stText, .stLabel, .stTextInput > div > label, .stNumberInput > label, .stSelectbox > label, .stTextArea > label {{
            color: white !important; /* Force white text for labels */
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: #E0E0E0 !important; /* Lighter shade for headers */
            text-shadow: 1px 1px 3px rgba(0,0,0,0.7); /* Add slight shadow to headers */
        }}
        .stButton>button {{
            background-color: #4CAF50; /* A pleasant green for the button */
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
            background-color: rgba(255, 255, 255, 0.1); /* Slightly transparent white for inputs */
            border-radius: 0.5rem;
            padding: 0.5rem;
            border: 1px solid rgba(255, 255, 255, 0.3); /* Light border */
        }}
        .stTextInput > div > div > input, .stNumberInput > div > div > input, .stTextArea > div > div > textarea {{
            color: white; /* Text color inside inputs */
            background-color: transparent; /* Ensure input background is transparent */
            border: none; /* Remove default input border */
        }}
        .stSelectbox > div > div {{
            color: white; /* Text color for selectbox */
            background-color: transparent; /* Ensure selectbox background is transparent */
            border: none; /* Remove default selectbox border */
        }}
        /* Specific styling for the options dropdown in selectbox */
        .stSelectbox div[data-baseweb="select"] div[role="listbox"] {{
            background-color: rgba(0, 0, 0, 0.8); /* Dark background for dropdown */
            color: white; /* White text for dropdown options */
        }}

        </style>
        """
        st.markdown(css, unsafe_allow_html=True)

# Set your background image
# IMPORTANT: Make sure 'best-financial-websites-examples.png' is in the same directory as this Python script
set_background("best-financial-websites-examples.png")

# --- 2. Main App Logic ---
st.set_page_config(page_title="AI Financial Advisor", layout="centered")

# These titles appear *above* the black box, as seen in your image
st.title("💸 AI Financial Advisor")
st.header("📊 Get Your Investment Plan")

# Now, create a Streamlit container for the form elements and results
# This container will receive the black box styling from the CSS injected above.
# We're wrapping this in a `with` statement for convenience.

# Using the explicit `st.markdown` div to wrap the main content
st.markdown("<div class='main-block'>", unsafe_allow_html=True)

# --- Helper function for extracting amount ---
def extract_amount(value_str):
    match = re.search(r"₹([0-9]+)", value_str)
    return int(match.group(1)) if match else 0

# --- Input Section ---
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
    # Ensure Markdown is rendered with appropriate styling for text color
    st.markdown(f"<p style='color: white;'>{result['advice_text']}</p>", unsafe_allow_html=True)

    st.subheader("📊 Allocation Chart")
    alloc = result["allocation"]
    eq = extract_amount(alloc["Equity"])
    de = extract_amount(alloc["Debt"])
    go = extract_amount(alloc["Gold"])
    chart_data = pd.DataFrame({"Type": ["Equity", "Debt", "Gold"], "Amount": [eq, de, go]})
    fig = px.pie(chart_data, names='Type', values='Amount', title="Investment Split")
    # Set chart background to transparent so the black box shows through
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    fig.update_traces(textinfo='percent+label', marker=dict(line=dict(color='#000000', width=1)))
    fig.update_layout(title_font_color='white', legend_font_color='white')
    st.plotly_chart(fig, use_container_width=True)


st.markdown("---") # This divider will also be inside the black box
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
    import openai
    # Ensure you have your OpenAI API key configured in Streamlit secrets or environment variables
    # For local testing, you might temporarily hardcode it, but for deployment, use st.secrets
    # openai.api_key = "YOUR_OPENAI_API_KEY" # <--- ONLY FOR LOCAL TESTING, REMOVE FOR DEPLOYMENT
    openai.api_key = st.secrets["openai"]["api_key"]
    with st.spinner("Thinking..."):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful and expert Indian financial advisor."},
                {"role": "user", "content": user_question}
            ]
        )
        st.subheader("🤖 AI Says:")
        st.markdown(f"<p style='color: white;'>{response.choices[0].message.content}</p>", unsafe_allow_html=True)

# Close the main-block div
st.markdown("</div>", unsafe_allow_html=True)
