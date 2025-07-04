import streamlit as st
from openai import OpenAI, RateLimitError
import requests
import smtplib
from email.mime.text import MIMEText

# === CONFIG ===
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]
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

def classify_use_case(description, offer):
    combo = f"{description} {offer}".lower()
    if "internship" in combo or "student" in combo:
        return "internship"
    elif "freelancer" in combo or "graphic design" in combo or "copywriting" in combo:
        return "freelancer"
    elif "agency" in combo or "smm" in combo or "seo" in combo:
        return "agency"
    elif "startup" in combo or "partnership" in combo:
        return "startup"
    else:
        return "general"

def generate_email(description, business_name, offer):
    use_case = classify_use_case(description, offer)

    if use_case == "internship":
        prompt = f"""
Write a short, polite cold email from a college student seeking an internship at a company called {business_name}. 
Mention interest in the field, eagerness to learn, and ask for a quick conversation. Keep it under 100 words.
"""
    elif use_case == "freelancer":
        prompt = f"""
Write a friendly cold outreach email offering freelance {offer} services to a business called {business_name}. 
Keep it personal, benefit-driven, and under 100 words.
"""
    elif use_case == "agency":
        prompt = f"""
Write a results-focused cold email from an agency offering {offer} to {business_name}. 
Include a soft CTA and sound professional but not robotic.
"""
    elif use_case == "startup":
        prompt = f"""
Write a casual email suggesting a potential partnership between a startup and {business_name}. 
Mention what the startup offers and how it could help. Under 100 words.
"""
    else:
        prompt = f"""
Write a personalized, short cold email offering {offer} to a business named {business_name}. 
Sound helpful and human. Keep it under 100 words.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except RateLimitError:
        st.error("OpenAI Rate limit exceeded. Try again shortly.")
        return ""
    except Exception as e:
        st.error("An unexpected error occurred generating the email.")
        return ""

def send_email(to_email, subject, body):
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

# === STREAMLIT UI ===
st.set_page_config(page_title="AI Cold Email Generator", layout="centered")
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
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main">
    <h1>🚀 Smart Cold Email Builder</h1>
    <p style='text-align:center;'>Enter who you're trying to reach and what you're offering. We'll find local leads and write the emails for you.</p>
</div>
""", unsafe_allow_html=True)

with st.form("email_form"):
    description = st.text_input("Who do you want to reach?", placeholder="e.g. dentists, gym owners, hiring managers")
    location = st.text_input("Search area (ZIP code, city, or state):", placeholder="e.g. 90210, Dallas, or Florida")
    radius = st.selectbox("Search radius:", options=["Same ZIP code only", "10 miles", "25 miles", "50 miles", "100 miles"], index=1)
    offer = st.text_input("What are you offering (or looking for)?", placeholder="e.g. graphic design services, internship opportunity, SEO help")
    subject = st.text_input("Subject line for your email:", "Quick idea to grow your business")
    sender_email = st.text_input("Your test email (where preview emails will go):", placeholder="your@email.com")
    submit = st.form_submit_button("Search for Leads")

radius_map = {
    "Same ZIP code only": "1",
    "10 miles": "10",
    "25 miles": "25",
    "50 miles": "50",
    "100 miles": "100"
}

if submit:
    radius_value = radius_map[radius]
    st.session_state.leads = search_yelp(description, location, radius_value)
    st.session_state.description = description
    st.session_state.location = location
    st.session_state.offer = offer
    st.session_state.subject = subject
    st.session_state.sender_email = sender_email

if "leads" in st.session_state:
    leads = st.session_state.leads
    if leads:
        selected_lead = st.radio("Choose a business to generate an email for:", [lead["title"] for lead in leads], key="lead_selection")
        st.session_state.current_lead = selected_lead
        if st.button("Generate Email"):
            lead = next(l for l in leads if l["title"] == selected_lead)
            generated = generate_email(st.session_state.description, lead['title'], st.session_state.offer)
            st.session_state.generated_email = generated

    if "generated_email" in st.session_state and st.session_state.generated_email:
        edited_email = st.text_area("Generated Email (you can edit this before sending):", st.session_state.generated_email, height=200, key="editable_email")
        if st.button("Send Test Email"):
            if st.session_state.sender_email:
                send_email(st.session_state.sender_email, st.session_state.subject, edited_email)
                st.success(f"Email sent to: {st.session_state.sender_email}")
            else:
                st.error("Please enter a valid email address.")
    elif "leads" in st.session_state and not st.session_state.generated_email:
        st.info("Select a lead and click 'Generate Email' to preview your message.")
else:
    st.warning("❌ No leads found. Try adjusting your location or search type.")
