import streamlit as st
from openai import OpenAI, RateLimitError
import requests
import smtplib
from email.mime.text import MIMEText
from geopy.geocoders import Nominatim

# === CONFIG ===
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]
YELP_API_KEY = st.secrets["YELP_API_KEY"]

# === FUNCTIONS ===
def get_coordinates(location):
    geolocator = Nominatim(user_agent="cold-email-ai")
    loc = geolocator.geocode(location)
    return (loc.latitude, loc.longitude) if loc else None

def generate_location_points(center_coords, radius_miles):
    offsets = [
        (0, 0), (0.15, 0), (-0.15, 0), (0, 0.15), (0, -0.15),
        (0.1, 0.1), (-0.1, -0.1), (0.1, -0.1), (-0.1, 0.1)
    ]
    return [(center_coords[0] + dx, center_coords[1] + dy) for dx, dy in offsets]

def fetch_business_context(business_id):
    headers = {"Authorization": f"Bearer {YELP_API_KEY}"}
    url = f"https://api.yelp.com/v3/businesses/{business_id}"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        title = data.get("name", "")
        address = ", ".join(data.get("location", {}).get("display_address", []))
        phone = data.get("phone", "N/A")
        categories = ", ".join([c["title"] for c in data.get("categories", [])])
        query = requests.utils.quote(f"{title} {address} official website")
        context_url = f"https://www.google.com/search?q={query}"
        return {"title": title, "address": address, "phone": phone, "categories": categories, "url": context_url}
    return {"title": business_id, "address": "N/A", "phone": "N/A", "categories": "N/A", "url": ""}

def search_yelp(term, location, radius_miles):
    headers = {"Authorization": f"Bearer {YELP_API_KEY}"}
    api_url = "https://api.yelp.com/v3/businesses/search"
    leads = []
    coords = get_coordinates(location)
    if not coords:
        st.error("Could not determine location coordinates.")
        return []
    centers = [coords] if float(radius_miles) <= 25 else generate_location_points(coords, float(radius_miles))
    seen = set()
    for lat, lon in centers:
        params = {"term": term, "latitude": lat, "longitude": lon, "radius": 40000, "limit": 5}
        r = requests.get(api_url, headers=headers, params=params)
        if r.status_code != 200:
            continue
        for biz in r.json().get("businesses", []):
            if biz["id"] not in seen:
                seen.add(biz["id"])
                ctx = fetch_business_context(biz["id"])
                leads.append({
                    "id": biz["id"],
                    "title": ctx["title"],
                    "url": ctx["url"],
                    "address": ctx["address"],
                    "phone": ctx["phone"],
                    "categories": ctx["categories"],
                    "email": "Not provided"
                })
    if not leads:
        st.warning("❌ No leads found. Try adjusting your search criteria.")
    return leads

def classify_use_case(description, offer):
    combo = f"{description} {offer}".lower()
    if "internship" in combo or "student" in combo:
        return "internship"
    if "freelancer" in combo or "graphic design" in combo:
        return "freelancer"
    if "agency" in combo or "seo" in combo:
        return "agency"
    if "startup" in combo or "partnership" in combo:
        return "startup"
    return "general"

def generate_email(description, business_name, offer, user_name):
    uc = classify_use_case(description, offer)
    if uc == "internship":
        prompt = f"""
Write a short, polite cold email from a college student named {user_name} seeking an internship at {business_name}. Under 100 words.
"""
    elif uc == "freelancer":
        prompt = f"""
Write a friendly cold outreach email from {user_name}, offering freelance {offer} to {business_name}. Under 100 words.
"""
    elif uc == "agency":
        prompt = f"""
Write a results-focused email from agency rep {user_name}, offering {offer} to {business_name}. Under 100 words.
"""
    elif uc == "startup":
        prompt = f"""
Write a casual partnership email from {user_name} to {business_name}, under 100 words.
"""
    else:
        prompt = f"""
Write a personalized, short cold email from {user_name} offering {offer} to {business_name}. Under 100 words.
"""
    try:
        res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role":"user","content":prompt}])
        return res.choices[0].message.content
    except RateLimitError:
        st.error("Rate limit, try again later.")
        return ""
    except:
        st.error("Error generating email.")
        return ""

def send_email(to, subj, body):
    msg = MIMEText(body)
    msg["Subject"] = subj
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        s.send_message(msg)

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
    h1 { text-align: center; }
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
    radius = st.selectbox("Search radius:", ["Same ZIP code only", "10 miles", "25 miles", "50 miles", "100 miles"], index=1)
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
    st.session_state.user_name = user_name
    st.session_state.description = description
    st.session_state.offer = offer
    st.session_state.subject = subject
    st.session_state.sender_email = sender_email

if "leads" in st.session_state:
    leads = st.session_state.leads
    if leads:
        for lead in leads:
            st.markdown(f"### 🏢 {lead['title']}")
            st.write(f"📍 {lead['address']}")
            st.write(f"📞 {lead['phone']}")
            st.write(f"🔖 {lead['categories']}")
            st.markdown(f"[🌐 View Website]({lead['url']})")
            st.markdown("---")
        selected = st.selectbox("Select a business to email:", [l['title'] for l in leads])
        if st.button("Generate Email"):
            lead = next(l for l in leads if l['title']==selected)
            st.session_state.generated_email = generate_email(
                st.session_state.description,
                lead['title'],
                st.session_state.offer,
                st.session_state.user_name
            )
            st.session_state.current_url = lead['url']

    if "generated_email" in st.session_state and st.session_state.generated_email:
        st.markdown(f"**Email preview for [{selected}]({st.session_state.current_url})**")
        edited = st.text_area("Edit email:", st.session_state.generated_email, height=200)
        if st.button("Send Test Email"):
            if st.session_state.sender_email:
                send_email(st.session_state.sender_email, st.session_state.subject, edited)
                st.success(f"Sent to {st.session_state.sender_email}")
            else:
                st.error("Enter a valid test email.")
    elif "leads" in st.session_state:
        st.info("Select a business and click Generate Email.")
else:
    st.info("Search for leads to get started.")
