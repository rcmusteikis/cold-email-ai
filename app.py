import streamlit as st
from openai import OpenAI, RateLimitError
import requests
import smtplib
from email.mime.text import MIMEText
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import time

# === CONFIG ===
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]
YELP_API_KEY = st.secrets["YELP_API_KEY"]

def get_coordinates(location):
    geolocator = Nominatim(user_agent="cold-email-ai")
    loc = geolocator.geocode(location)
    return (loc.latitude, loc.longitude) if loc else None

def generate_location_points(center_coords, radius_miles):
    offsets = [
        (0, 0),
        (0.15, 0),
        (-0.15, 0),
        (0, 0.15),
        (0, -0.15),
        (0.1, 0.1),
        (-0.1, -0.1),
        (0.1, -0.1),
        (-0.1, 0.1)
    ]
    return [(center_coords[0] + dx, center_coords[1] + dy) for dx, dy in offsets]

def search_yelp(term, location, radius_miles):
    headers = {"Authorization": f"Bearer {YELP_API_KEY}"}
    url = "https://api.yelp.com/v3/businesses/search"
    results = []
    center_coords = get_coordinates(location)
    if not center_coords:
        st.error("Could not determine location coordinates.")
        return []

    if float(radius_miles) <= 25:
        coords_list = [center_coords]
    else:
        coords_list = generate_location_points(center_coords, float(radius_miles))

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
                results.append({
                    "title": biz["name"],
                    "url": biz["url"],
                    "email": "Not provided"
                })
        time.sleep(0.2)

    if not results:
        st.warning("❌ No leads found. Try adjusting your location or search type.")
    return results
