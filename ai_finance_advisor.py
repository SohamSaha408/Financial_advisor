import streamlit as st
import pandas as pd
import plotly.express as px
import re
import base64
from advisor import generate_recommendation, search_funds

# Ensure page config is set first
st.set_page_config(page_title="AI Financial Advisor", layout="centered")

# --- 1. Background and Global CSS for the Custom Box ---
def set_background(image_file):
    with open(image_file, "rb") as f:
        data = f.read()
        encoded = base64.b64encode(data).decode()
        css = f"""
        <style>
        /* Styles for the overall app background */
        .stApp {{
            background-image: url("data:image/png;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            /* Ensure .stApp is positioned to allow z-index for children if needed */
            position: relative;
            z-index: 0; /* Background layer */
        }}

        /* Styles for the custom black box (this is the key part) */
        .custom-black-box {{
            background-color: rgba(0, 0, 0, 0.75); /* Black with 75% opacity */
            padding: 2rem; /* Space inside the box */
            border-radius: 1rem; /* Rounded corners */
            margin: 2rem auto; /* Top/bottom margin 2rem, auto for left/right to center */
            max-width: 700px; /* Constrain width on larger screens */
            width: 90%; /* Responsive width */
            color: white; /* Default text color inside the box */
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5); /* Subtle shadow */
            backdrop-filter: blur(5px); /* Optional: Adds a slight blur to content behind it */
            -webkit-backdrop-filter: blur(5px); /* For Safari support */
            z-index: 1; /* Ensure this box is above the background */
            position: relative; /* Needed for z-index to work correctly if using absolute positioning later */
        }}

        /* Adjust Streamlit's default elements for better contrast *within* the black box */
        /* These ensure text within the black box is readable */
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
        /* Target the actual input fields themselves */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stTextArea > div > div > textarea {{
            color: white; /* Text color inside inputs */
            background-color: transparent; /* Ensure input background is transparent */
            border: none; /* Remove default input border */
        }}
        /* Specific styling for the selectbox display area */
        .stSelectbox > div > div[data-baseweb="select"] > div[role="button"] {{
            color: white; /* Text color for selectbox displayed value */
            background-color: transparent; /* Ensure selectbox background is transparent */
            border: none; /* Remove default selectbox border */
        }}
        /* Specific styling for the options dropdown in selectbox */
        .stSelectbox div[data-baseweb="select"] div[role="listbox"] {{
            background-color: rgba(0, 0, 0, 0.9); /* Dark background for dropdown options */
            color: white; /* White text for dropdown options */
        }}

        </style>
        """
        st.markdown(css, unsafe_allow_html=True)

# Set the background image
# IMPORTANT: Make sure 'best-financial-websites-examples.png' is in the same directory as this Python script
set_background("best-financial-websites-examples.png")

# --- 2. Main App Logic ---

# Helper function for extracting amount
def extract_amount(value_str):
    match = re.search(r"₹([0-9]+)", value_str)
    return int(match.group(1)) if match else 0

# --- Streamlit App Layout ---

# These titles appear *above* the black box, directly on the background
st.title("💸 AI Financial Advisor")
st.header("📊 Get Your Investment Plan")

# Now, create a custom div with the black box styling
# This div will wrap ONLY the input form, buttons, and results
st.markdown("<div class='custom-black-box'>", unsafe_allow_html=True)

# --- Input Section (These elements will be inside the black box) ---
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
    # Ensure Markdown content gets the correct text color
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
    # Make sure st.secrets is configured with your OpenAI API key
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

# Close the custom black box div
st.markdown("</div>", unsafe_allow_html=True)
