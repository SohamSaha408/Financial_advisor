import streamlit as st
import pandas as pd
import plotly.express as px
from advisor import generate_recommendation

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
    eq = int(alloc["Equity"].split("~₹")[1])
    de = int(alloc["Debt"].split("~₹")[1])
    go = int(alloc["Gold"].split("~₹")[1])
    chart_data = pd.DataFrame({"Type": ["Equity", "Debt", "Gold"], "Amount": [eq, de, go]})
    fig = px.pie(chart_data, names='Type', values='Amount', title="Investment Split")
    st.plotly_chart(fig)
