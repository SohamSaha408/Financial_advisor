import streamlit as st
import pandas as pd
import plotly.express as px
import re
import base64
import os
import google.generativeai as genai
from pypdf import PdfReader # Import PdfReader for PDF processing

# Assuming 'advisor.py' is in the same directory and contains these functions
from advisor import generate_recommendation, search_funds

# IMPORTANT: st.set_page_config MUST be the first Streamlit command
st.set_page_config(page_title="AI Financial Advisor", layout="centered")

# --- 1. Background and Initial CSS (Revised to target Streamlit's main content) ---
def set_background(image_file):
    # Check if the image file exists to prevent FileNotFoundError
    if not os.path.exists(image_file):
        st.error(f"Background image not found: '{image_file}'. Please ensure the image is in the correct directory.")
        # Fallback CSS for a default dark background if image is not found
        fallback_css = """
        <style>
        .stApp {
            background-color: #222222; /* Dark fallback color */
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-size: cover; /* Added for consistency even with solid color */
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }
        </style>
        """
        st.markdown(fallback_css, unsafe_allow_html=True)
        return # Exit the function if image not found

    try:
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
        }}

        /* Target Streamlit's main content block (the area that holds your elements) */
        .main .block-container {{
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
            overflow: auto; /* In case content overflows */
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
    except FileNotFoundError:
        st.error(f"Error loading background image '{image_file}'. Please check the file path and name.")
        # Fallback CSS for a default dark background if loading fails
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
    except Exception as e:
        st.error(f"An unexpected error occurred while setting background: {e}")
        # Fallback CSS
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


# Set your background image (ensure 'black-particles-background.avif' is in your project directory)
set_background("black-particles-background.avif")

# --- 2. Main App Logic ---

# --- Helper function for extracting amount ---
def extract_amount(value_str):
    match = re.search(r"₹([0-9]+)", value_str)
    return int(match.group(1)) if match else 0

# Function to extract text from PDF
def get_pdf_text(pdf_file):
    text = ""
    try:
        pdf_reader = PdfReader(pdf_file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
    return text

# --- Streamlit App Layout ---

# These titles should be *outside* the black box if you want them on the full background
st.title("💸 AI Financial Advisor")
st.header("📊 Get Your Investment Plan")


# The content below will automatically be within the `.main .block-container`
# which we are now styling as the black box.

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

# --- New: Document Analyzer Section ---
st.markdown("---")
st.header("📄 Document Analyzer")
st.write("Upload a document (PDF or TXT) for the AI to analyze and provide advice.")
uploaded_file = st.file_uploader("Choose a file", type=["pdf", "txt"], key="doc_uploader")

document_text = ""
if uploaded_file is not None:
    # Get file extension for specific handling
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
        # Show only first 1000 characters for preview, indicate if truncated
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

                # Using 'gemini-1.5-flash' as it's generally good for larger context windows
                # Make sure this model is available to your API key
                model = genai.GenerativeModel('gemini-1.5-flash')

                with st.spinner("Analyzing document..."):
                    try:
                        # Construct a detailed prompt for document analysis
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

st.markdown("---")
st.header("💬 Ask the AI")
user_question = st.text_area("Ask your financial question:", key="ai_question_area")

if user_question:
    # --- Configure Gemini AI ---
    try:
        genai.configure(api_key=st.secrets["gemini"]["api_key"])
    except AttributeError: # Changed from KeyError as per your original code, but KeyError is more specific for st.secrets
        st.error("Gemini API key not found in Streamlit secrets. Please set it as `gemini.api_key` in .streamlit/secrets.toml")
        st.stop() # Stop execution if API key is not found

    # Initialize the Generative Model (you can choose 'gemini-pro', 'gemini-1.5-flash', etc.)
    model = genai.GenerativeModel('gemini-1.5-flash') # Retained the model you were using

    with st.spinner("Thinking..."):
        try:
            # Send the user's question to the Gemini model
            response = model.generate_content(
                contents=[
                    {"role": "user", "parts": ["You are a helpful and expert Indian financial advisor.", user_question]}
                ]
            )
            st.subheader("🤖 AI Says:")
            # Access the text from the response object
            st.markdown(f"<p style='color: white;'>{response.text}</p>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error calling Gemini AI: {e}. Please check your API key and model usage.")
