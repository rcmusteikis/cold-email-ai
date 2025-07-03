import streamlit as st
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText

# === CONFIG ===
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]  # Gmail App Password
YELP_API_KEY = st.secrets["YELP_API_KEY"]

# === FUNCTIONS ===
def search_yelp(term, location, radius_miles):
    headers = {"Authorization": f"Bearer {YELP_API_KEY}"}
    url = "https://api.yelp.com/v3/businesses/search"
    params = {
        "term": term,
        "location": location,
        "radius": int(float(radius_miles) * 1609.34),
        "limit": 5,
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        st.error("Failed to fetch leads from Yelp.")
        return []

    data = response.json()
    results = []
    for biz in data["businesses"]:
        results.append({
            "title": biz["name"],
            "url": biz["url"],
            "email": "Not provided"
        })
    return results

def generate_email(description, business_name):
    prompt = f"""
Write a friendly, personalized cold email to a {description} who owns {business_name}. 
Offer a helpful service relevant to their industry. Mention how you found them. Keep it under 100 words.
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

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
            max-width: 700px;
            margin: auto;
            box-shadow: 0px 0px 10px rgba(0,0,0,0.1);
        }
        h1 {
            text-align: center;
        }
        label {
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main">
    <h1>🚀 AI Cold Email Website</h1>
</div>
""", unsafe_allow_html=True)

with st.form("email_form"):
    description = st.text_input(
        "Who are you trying to reach?",
        placeholder="Example: dentists, gym owners, landscaping companies"
    )
    location = st.text_input(
        "Location (type a ZIP code, city, or state)",
        placeholder="Example: 27513, Cary, or North Carolina"
    )
    radius = st.selectbox(
        "How far from the location should we search?",
        options=["Same ZIP code only", "10 miles", "25 miles", "50 miles", "100 miles"],
        index=0
    )
    offer = st.text_input(
        "What are you offering them?",
        placeholder="Example: website redesign, Google review service, SEO audit"
    )
    subject = st.text_input("Email Subject", "Quick idea to help your business")
    sender_email = st.text_input(
        "Where should the test email go?",
        placeholder="Enter your email address to preview the message"
    )
    submit = st.form_submit_button("Generate & Send")

# Convert user-friendly radius to search term
radius_map = {
    "Same ZIP code only": "1",
    "10 miles": "10",
    "25 miles": "25",
    "50 miles": "50",
    "100 miles": "100"
}

if submit:
    radius_value = radius_map[radius]
    st.write(f"Searching Yelp for: '{description}' in '{location}' within {radius.lower()}...")
    leads = search_yelp(description, location, radius_value)

    if leads:
        for lead in leads:
            email_body = generate_email(f"a {description} in {location} about {offer}", lead['title'])
            st.write(f"\n---\n### Email to {lead['title']}\n\n{email_body}")

            if sender_email:
                send_email(sender_email, subject, email_body)
                st.success(f"Email sent to test address: {sender_email}")
    else:
        st.warning("No leads found. Try a different ZIP, city, or service type.")
