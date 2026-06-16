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
   - Go to the Render Dashboard.
   - Click **New +** and select **Blueprint**.
   - Connect your GitHub repository.
   - Select the `render.yaml` file to automate the deployment.
3. **Configure Environment Variables**:
   - The Blueprint will prompt you to provide the `GROQ_API_KEY`. Paste your key.
4. **Deploy**:
   - Render will build the environment by running `pip install -r requirements.txt`.
   - Once the build succeeds, it will start the app using `gunicorn app:app`.

## Troubleshooting

- **Memory Limit on Free Tier**: The application uses `speechbrain` and `torchaudio`, which load large machine learning models into memory. If the build or runtime crashes with an "Out of Memory" (OOM) error, you may need to upgrade to a paid Render instance with at least 1GB to 2GB of RAM, or remove `speechbrain` and `torchaudio` from `requirements.txt` and `app.py` to disable voice speaker verification in production.
- **Audio Saving Permissions**: The app saves temporary audio files to `static/audio`. Ensure the application has write access to this directory during runtime.
