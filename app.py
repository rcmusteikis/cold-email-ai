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
def get_coordinates(location):
    from geopy.geocoders import Nominatim
    geolocator = Nominatim(user_agent="cold-email-ai")
    loc = geolocator.geocode(location)
    return (loc.latitude, loc.longitude) if loc else None

def generate_location_points(center_coords, radius_miles):
    offsets = [
        (0, 0), (0.15, 0), (-0.15, 0), (0, 0.15), (0, -0.15),
        (0.1, 0.1), (-0.1, -0.1), (0.1, -0.1), (-0.1, 0.1)
    ]
    return [(center_coords[0] + dx, center_coords[1] + dy) for dx, dy in offsets]

def fetch_business_website(business_id):
    headers = {"Authorization": f"Bearer {YELP_API_KEY}"}
    url = f"https://api.yelp.com/v3/businesses/{business_id}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        name = data.get("name", "")
        address = " ".join(data.get("location", {}).get("display_address", []))
        website_search_url = f"https://www.google.com/search?q={requests.utils.quote(name + ' ' + address)}"
        return website_search_url, name, data.get("location", {}).get("display_address", []), data.get("phone", ""), data.get("coordinates", {}), data.get("photos", []), data.get("hours", []), data.get("categories", []), data.get("location", {}).get("city", ""), data.get("location", {}).get("state", ""), data.get("location", {}).get("zip_code", ""), data.get("location", {}).get("country", ""), data.get("location", {}).get("address1", ""), website_search_url
    return "", "", "", "", {}, [], [], [], "", "", "", "", "", ""

def search_yelp(term, location, radius_miles):
    headers = {"Authorization": f"Bearer {YELP_API_KEY}"}
    url = "https://api.yelp.com/v3/businesses/search"
    results = []
    center_coords = get_coordinates(location)
    if not center_coords:
        st.error("Could not determine location coordinates.")
        return []

    coords_list = [center_coords] if float(radius_miles) <= 25 else generate_location_points(center_coords, float(radius_miles))

    seen_titles = set()
    for coords in coords_list:
        params = {
            "term": term,
            "latitude": coords[0],
            "longitude": coords[1],
            "radius": 40000,
            "limit": 5,
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            continue
        data = response.json()
        for biz in data.get("businesses", []):
            if biz["name"] not in seen_titles:
                seen_titles.add(biz["name"])
                website_url = fetch_business_website(biz["id"])[13] or biz["url"]
                results.append({
                    "title": biz["name"],
                    "url": website_url,
                    "email": "Not provided"
                })
    if not results:
        st.warning("❌ No leads found. Try adjusting your location or search type.")
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

def generate_email(description, business_name, offer, user_name):
    use_case = classify_use_case(description, offer)
    if use_case == "internship":
        prompt = f"""
Write a short, polite cold email from a college student named {user_name} seeking an internship at a company called {business_name}. 
Mention interest in the field, eagerness to learn, and ask for a quick conversation. Keep it under 100 words.
"""
    elif use_case == "freelancer":
        prompt = f"""
Write a friendly cold outreach email from {user_name}, offering freelance {offer} services to a business called {business_name}. 
Keep it personal, benefit-driven, and under 100 words.
"""
    elif use_case == "agency":
        prompt = f"""
Write a results-focused cold email from an agency representative named {user_name}, offering {offer} to {business_name}. 
Include a soft CTA and sound professional but not robotic.
"""
    elif use_case == "startup":
        prompt = f"""
Write a casual email suggesting a potential partnership between a startup and {business_name}, written by {user_name}. 
Mention what the startup offers and how it could help. Under 100 words.
"""
    else:
        prompt = f"""
Write a personalized, short cold email from {user_name} offering {offer} to a business named {business_name}. 
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
    user_name = st.text_input("Your Name:", placeholder="e.g. John Doe")
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
    st.session_state.user_name = user_name

if "leads" in st.session_state:
    leads = st.session_state.leads
    if leads:
        selected_lead = st.radio("Choose a business to generate an email for:", [f"{lead['title']} ({lead['url']})" for lead in leads], key="lead_selection")
        st.session_state.current_lead = selected_lead
        if st.button("Generate Email"):
            lead_name = selected_lead.split(" (")[0]
            lead = next(l for l in leads if l["title"] == lead_name)
            generated = generate_email(st.session_state.description, lead['title'], st.session_state.offer, st.session_state.user_name)
            st.session_state.generated_email = generated
            st.session_state.current_url = lead['url']

    if "generated_email" in st.session_state and st.session_state.generated_email:
        st.markdown(f"**Previewing email for:** [{st.session_state.current_lead}]( {st.session_state.current_url} )")
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
