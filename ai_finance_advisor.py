import streamlit as st
import pandas as pd
import plotly.express as px
from database import create_tables, signup_user, login_user, save_user_data, get_user_data
from advisor import generate_recommendation

create_tables()

st.set_page_config(page_title="AI Financial Advisor", layout="centered")
st.title("💸 AI Financial Advisor")

auth = st.sidebar.selectbox("Login / Signup", ["Login", "Signup"])
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

if auth == "Signup":
    if st.sidebar.button("Create Account"):
        try:
            signup_user(username, password)
            st.sidebar.success("Signup success! Please login.")
        except:
            st.sidebar.error("Username may already exist.")

user_id = None
if auth == "Login":
    if st.sidebar.button("Login"):
        user_id = login_user(username, password)
        if user_id:
            st.session_state["user_id"] = user_id
            st.success(f"Welcome, {username}!")
        else:
            st.error("Invalid credentials")

if "user_id" in st.session_state:
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

        save_user_data(st.session_state["user_id"], age, income, profession, region, result['risk_profile'])

    if st.checkbox("📂 Past Advice"):
        data = get_user_data(st.session_state["user_id"])
        df = pd.DataFrame(data, columns=["ID", "UserID", "Age", "Income", "Profession", "Region", "Risk"])
        st.dataframe(df.drop(columns=["UserID"]))
