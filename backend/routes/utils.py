import os
import uuid
from flask import Blueprint, session, jsonify, send_from_directory
from functools import wraps

utils_bp = Blueprint("utils", __name__)

# Define base directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "output")
AUDIO_FOLDER = os.path.join(BASE_DIR, "audio")
FRAMES_FOLDER = os.path.join(BASE_DIR, "frames")
SUBTITLE_FOLDER = os.path.join(BASE_DIR, "subtitles")

# Ensure all required folders exist
def ensure_dirs():
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, AUDIO_FOLDER, FRAMES_FOLDER, SUBTITLE_FOLDER]:
        os.makedirs(folder, exist_ok=True)

# Login-required decorator
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# Serve a file from a specific folder
def serve_file(folder, filename):
    path = os.path.join(BASE_DIR, folder)
    return send_from_directory(path, filename)

# Generate a unique filename
def generate_unique_filename(prefix="", suffix=""):
    unique_id = uuid.uuid4().hex[:8]
    return f"{prefix}{unique_id}{suffix}"

# Ping route for testing server availability
@utils_bp.route("/api/ping")
def ping():
    return jsonify({"message": "pong"})

# Cleanup temporary folders
@utils_bp.route("/api/cleanup")
@login_required
def cleanup():
    for folder in [UPLOAD_FOLDER, AUDIO_FOLDER, FRAMES_FOLDER, SUBTITLE_FOLDER]:
        try:
            for f in os.listdir(folder):
                file_path = os.path.join(folder, f)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        except:
            pass
    return jsonify({"message": "Temporary files cleaned successfully."})
