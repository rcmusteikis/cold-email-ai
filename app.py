import streamlit as st
import openai
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText

# === CONFIG ===
openai.api_key = st.secrets["OPENAI_API_KEY"]
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]  # Gmail App Password

# === FUNCTIONS ===
def scrape_google(query):
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    results = []
    for tag in soup.select("div.tF2Cxc"):
        title = tag.select_one("h3").text if tag.select_one("h3") else "No title"
        link = tag.select_one("a")["href"] if tag.select_one("a") else ""
        results.append({"title": title, "url": link})

    return results[:5]

def generate_email(description, business_name):
    prompt = f"""
Write a friendly, personalized cold email to a {description} who owns {business_name}. 
Offer a helpful service relevant to their industry. Mention how you found them. Keep it under 100 words.
"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    return response['choices'][0]['message']['content']

def send_email(to_email, subject, body):
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

# === STREAMLIT UI ===
st.set_page_config(page_title="AI Cold Email Engine", layout="centered")
st.markdown("""
    <style>
        .main {
            background-color: #f0f2f6;
            padding: 2rem;
            border-radius: 1rem;
            max-width: 600px;
            margin: auto;
            box-shadow: 0px 0px 10px rgba(0,0,0,0.1);
        }
        h1 {
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main">
    <h1>🚀 AI Cold Email Website</h1>
</div>
""", unsafe_allow_html=True)

with st.form("email_form"):
    description = st.text_input("Who are you targeting (e.g. dentists, personal trainers)?")
    location = st.text_input("Which location?")
    offer = st.text_input("What are you offering or emailing them about?")
    subject = st.text_input("Email Subject", "Quick idea for your business")
    sender_email = st.text_input("Test Recipient Email (for demo)")
    submit = st.form_submit_button("Generate & Send")

if submit:
    query = f"{description} in {location}"
    st.write(f"Searching for: {query}")
    leads = scrape_google(query)

    if leads:
        for lead in leads:
            email_body = generate_email(f"a {description} in {location} about {offer}", lead['title'])
            st.write(f"\n---\n### Email to {lead['title']}\n\n{email_body}")

            if sender_email:
                send_email(sender_email, subject, email_body)
                st.success(f"Email sent to test address: {sender_email}")
    else:
        st.warning("No leads found.")
