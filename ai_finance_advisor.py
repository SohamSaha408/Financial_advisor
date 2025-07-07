import streamlit as st
import pandas as pd
import plotly.express as px
import re
import base64
from advisor import generate_recommendation, search_funds

# Set background image
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
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)

set_background("best-financial-websites-examples.png")

def extract_amount(value_str):
    match = re.search(r"₹([0-9]+)", value_str)
    return int(match.group(1)) if match else 0

st.set_page_config(page_title="AI Financial Advisor", layout="centered")
st.title("💸 AI Financial Advisor")

st.header("📊 Get Your Investment Plan")
age = st.number_input("Age", min_value=18)
income = st.number_input("Monthly Income (₹)", step=1000)
profession = st.selectbox("Profession", ["Student", "Salaried", "Self-employed"])
region = st.selectbox("Region", ["Metro", "Urban", "Rural"])
goal = st.selectbox("🎯 Investment Goal", [
    "Wealth Accumulation", "Retirement Planning", "Short-term Savings", "Tax Saving (ELSS)"
])

if st.button("Get Advice"):
    result = generate_recommendation(age, income, profession, region, goal)
    st.subheader("🧠 Advice")
    st.markdown(result["advice_text"])

    st.subheader("📊 Allocation Chart")
    alloc = result["allocation"]
    eq = extract_amount(alloc["Equity"])
    de = extract_amount(alloc["Debt"])
    go = extract_amount(alloc["Gold"])
    chart_data = pd.DataFrame({"Type": ["Equity", "Debt", "Gold"], "Amount": [eq, de, go]})
    fig = px.pie(chart_data, names='Type', values='Amount', title="Investment Split")
    st.plotly_chart(fig)

st.markdown("---")
st.header("🔍 Mutual Fund Research")
search_query = st.text_input("Enter fund name to search")
if search_query:
    funds = search_funds(search_query)
    for fund in funds[:5]:
        st.markdown(f"**{fund['schemeName']}**")
        st.write(f"Scheme Code: {fund.get('schemeCode', 'N/A')}")
        st.write(f"[Live NAV](https://api.mfapi.in/mf/{fund.get('schemeCode', '')})")

st.markdown("---")
st.header("💬 Ask the AI")
user_question = st.text_area("Ask your financial question:")

if user_question:
    import openai
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
        st.markdown(response.choices[0].message.content)
