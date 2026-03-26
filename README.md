# Healthcare Copilot - Deployment Guide

This repository contains the Healthcare Copilot AI project, configured for easy deployment on [Render](https://render.com) and [Vercel](https://vercel.com).

## Setup & Local Development

1. Clone the repository.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your keys:
   ```
   GROQ_API_KEY=your_groq_key
   FLASK_SECRET_KEY=your_secret_key
   ```
4. Run the app:
   ```bash
   flask run
   ```

## Deploying to Render (Recommended for SQLite Database)

Since this app uses an SQLite database (`healthcare.db`), Render is the recommended platform because it supports persistent disks, whereas Vercel serverless functions are read-only and ephemeral.

1. Connect your GitHub repository to Render.
2. Create a new **Web Service**.
3. Render should detect the `render.yaml` Blueprint or the `requirements.txt` and `Procfile`.
4. Ensure the **Build Command** is: `pip install -r requirements.txt`
5. Ensure the **Start Command** is: `gunicorn app:app --bind 0.0.0.0:$PORT`
6. Under Environment variables, add `GROQ_API_KEY` and `FLASK_SECRET_KEY`.
7. Add a persistent disk mounted at `/opt/render/project/src/instance` to persist your SQLite database (already configured if you use `render.yaml`).

## Deploying to Vercel (Frontend + Serverless DB)

If you deploy to Vercel, the SQLite database will be read-only and reset on every cold start. If you want full functionality on Vercel, you should migrate the database to a cloud Postgres provider like Supabase or Neon, and update the `SQLALCHEMY_DATABASE_URI` in `app.py`.

1. Install Vercel CLI or connect via the Vercel Dashboard.
2. In the Vercel Dashboard, import this repository.
3. Vercel will auto-detect the `vercel.json` file.
4. Add the `GROQ_API_KEY` and `FLASK_SECRET_KEY` Environment Variables in Vercel.
5. Deploy!
