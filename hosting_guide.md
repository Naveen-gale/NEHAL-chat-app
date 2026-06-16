# Hosting Guide for NEHAL PPT Assistant

This guide explains how to deploy the NEHAL PPT Assistant application to Render.

## Prerequisites

1. A GitHub or GitLab repository containing this code.
2. A Render account (https://render.com).
3. A Groq API Key (https://console.groq.com/keys).
4. MongoDB connection setup (if using external Atlas, ensure network access).

## Deployment Steps

1. **Push to GitHub**: Make sure all changes are pushed to your GitHub repository.
2. **Connect to Render**:
   - Go to the Render Dashboard (https://dashboard.render.com/).
   - Click **New +** and select **Web Service** (Do NOT select Blueprint, as Blueprints require a credit card).
   - Connect your GitHub repository.
3. **Configure the Web Service**:
   - **Name**: `nehal-ppt-assistant`
   - **Environment**: `Python`
   - **Build Command**: `cd backend && pip install -r requirements.txt`
   - **Start Command**: `cd backend && gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Instance Type**: `Free`
4. **Environment Variables**:
   - Scroll down to the Environment Variables section and add:
     - `PYTHON_VERSION` = `3.10.0`
     - `GROQ_API_KEY` = *(paste your Groq key here)*
5. **Deploy**:
   - Click **Create Web Service** at the bottom. Render will now build and deploy the app completely for free!

## Troubleshooting

- **Audio Saving Permissions**: The app saves temporary audio files to `static/audio`. Ensure the application has write access to this directory during runtime.
