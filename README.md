# 🚀 AI Cold Email Website

This tool lets you generate and send personalized cold emails using OpenAI GPT-4 and Streamlit.

## Features
- Scrapes Google search for business leads
- Uses GPT-4 to write custom cold emails
- Sends emails via Gmail SMTP
- Streamlit-powered frontend with form inputs

## How to Use (Local)
1. Clone repo
2. Add your credentials to Streamlit secrets
3. Run: `streamlit run app.py`

## Deploy Online (Free)
1. Push this folder to a GitHub repo
2. Go to [streamlit.io/cloud](https://streamlit.io/cloud)
3. Connect your GitHub repo and deploy

## Set Streamlit Secrets
In Streamlit Cloud, go to `Settings > Secrets` and add:
```
OPENAI_API_KEY = "your-openai-key"
EMAIL_ADDRESS = "youremail@gmail.com"
EMAIL_PASSWORD = "your-gmail-app-password"
```
