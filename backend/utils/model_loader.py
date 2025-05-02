import os
import requests

# المسار المحلي لحفظ النموذج
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "medium.pt")
# رابط GCS للحصول على النموذج
DOWNLOAD_URL = os.getenv(
    "MODEL_DOWNLOAD_URL",
    "https://storage.cloud.google.com/echvid-models-video-mov/models/medium.pt"
)

def ensure_model():
    if not os.path.exists(MODEL_PATH):
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        print(f"🔄 Downloading model from {DOWNLOAD_URL} …")
        resp = requests.get(DOWNLOAD_URL, stream=True)
        resp.raise_for_status()
        with open(MODEL_PATH, "wb") as f:
            for chunk in resp.iter_content(1024*1024):
                f.write(chunk)
        print("✅ Model downloaded.")
    else:
        print("✅ Model already present.")
