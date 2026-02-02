# Deployment Guide for IPL Chatbot
This guide explains how to deploy the IPL Chatbot to the cloud while ensuring your database is persistent and accessible.

## 1. Why use a Cloud Database?
By default, this app uses SQLite (`chatbot_history.db`). This file lives inside the container.
- **Problem**: On cloud platforms like Streamlit Cloud, Heroku, or Render, the file system is *ephemeral*. Every time you deploy or the app restarts, **the file is deleted**.
- **Solution**: Connect to an external Postgres database (e.g., Supabase, Neon, AWS RDS).

## 2. Choosing a Database Provider
We recommend **Supabase** (easiest, free tier, great UI) or **Neon**.

### Set up Supabase:
1. Go to [database.new](https://database.new) and create a new project.
2. Go to **Project Settings** -> **Database** -> **Connection String**.
3. Copy the URI. It looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
   ```

## 3. Prepare for Deployment
We have already updated the code to support switching between SQLite (local) and Postgres (cloud).

### Steps:
1. **GitHub**: Push your code to a GitHub repository.
2. **Streamlit Community Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io).
   - Connect your GitHub repo.
   - Select `streamlit_app.py` as the main file.
3. **Secrets Management**:
   - In the Streamlit Cloud dashboard, go to your app settings -> **Secrets**.
   - Add your database connection string and API keys:

   ```toml
   # .streamlit/secrets.toml format
   DATABASE_URL = "postgresql://postgres:password@host:5432/postgres"
   HF_API_KEY = "your-huggingface-key"
   GEMINI_API_KEY = "your-gemini-key" # Optional if using Gemini
   LLM_PROVIDER = "gemini" # Optional: set to use Gemini by default
   BRAINTRUST_API_KEY = "your-braintrust-key"
   ```

## 4. How the Code Works
The app checks for the existence of the `DATABASE_URL` environment variable.
- **Local**: If not found, it uses `data/chatbot_history.db` (SQLite).
- **Cloud**: If found, it connects to Postgres.

The table `interactions` will be automatically created in your Postgres database when the app first runs.

## 5. Viewing Your Data
Since you are using Supabase (or similar):
1. Log in to your Supabase dashboard.
2. Go to the **Table Editor**.
3. You will see the `interactions` table with all your chat history, full JSON logs, and logic traces!

## Troubleshooting
- **Connection Error**: Ensure you installed `psycopg2-binary` (it's in `requirements.txt`).
- **Missing Data**: Check the "Secrets" in Streamlit Cloud to ensure `DATABASE_URL` is set correctly.
