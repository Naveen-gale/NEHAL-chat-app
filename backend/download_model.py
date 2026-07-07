import os
import urllib.request

# Replace this URL with the direct download link to your svm_model.pkl (e.g., from Google Drive, AWS S3, or Hugging Face)
MODEL_URL = os.getenv("SVM_MODEL_URL", "")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "model")
MODEL_PATH = os.path.join(MODEL_DIR, "svm_model.pkl")

def download_model():
    if os.path.exists(MODEL_PATH):
        print("Model already exists locally. Skipping download.")
        return

    if not MODEL_URL:
        print("SVM_MODEL_URL environment variable is not set. Skipping model download.")
        print("The app will fallback to using 'langdetect'.")
        return

    os.makedirs(MODEL_DIR, exist_ok=True)
    print(f"Downloading model from {MODEL_URL}...")
    try:
        # Note: If using Google Drive, you may need to use the 'gdown' package instead of urllib.
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Model downloaded successfully!")
    except Exception as e:
        print(f"Failed to download model: {e}")

if __name__ == "__main__":
    download_model()
