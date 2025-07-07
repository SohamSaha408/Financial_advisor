import streamlit as st
import pandas as pd
import plotly.express as px
from advisor import generate_recommendation


import base64

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
        }}
        </style>
        """
        st.markdown(css, unsafe_allow_html=True)

set_background("best-financial-websites-examples.png
")  # Replace with your image file name

st.set_page_config(page_title="AI Financial Advisor", layout="centered")
st.title("💸 AI Financial Advisor")

st.header("📊 Get Your Investment Plan")
age = st.number_input("Age", min_value=18)
income = st.number_input("Monthly Income (₹)", step=1000)
profession = st.selectbox("Profession", ["Student", "Salaried", "Self-employed"])
region = st.selectbox("Region", ["Metro", "Urban", "Rural"])

if st.button("Get Advice"):
    result = generate_recommendation(age, income, profession, region)

    st.subheader("🧠 Advice")
    st.markdown(result["advice_text"])

    # Pie chart
    st.subheader("📊 Allocation Chart")
    alloc = result["allocation"]
    eq = extract_amount(alloc["Equity"])
    de = extract_amount(alloc["Debt"])
    go = extract_amount(alloc["Gold"])

    chart_data = pd.DataFrame({"Type": ["Equity", "Debt", "Gold"], "Amount": [eq, de, go]})
    fig = px.pie(chart_data, names='Type', values='Amount', title="Investment Split")
    st.plotly_chart(fig)
