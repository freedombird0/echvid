import os
import sqlite3
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from routes.utils import login_required

profile_bp = Blueprint("profile", __name__)

# Directory to store profile images
UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "profiles"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Database path
DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "users.db"))

@profile_bp.route("/api/profile/update", methods=["POST"])
@login_required
def update_profile():
    user_id = session.get("user_id")
    name = request.form.get("name")
    email = request.form.get("email")
    image = request.files.get("profileImage")

    image_url = None
    if image:
        ext = os.path.splitext(image.filename)[1].lower()
        filename = f"user_{user_id}{ext}"
        path = os.path.join(UPLOAD_DIR, filename)
        image.save(path)
        image_url = f"/static/profiles/{filename}"

    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                "UPDATE users SET username = ?, email = ?, image_url = ? WHERE id = ?",
                (name, email, image_url, user_id)
            )
    except Exception as e:
        return jsonify({"error": "Database update failed", "details": str(e)}), 500

    return jsonify({
        "message": "Profile updated successfully.",
        "user": {
            "id": user_id,
            "username": name,
            "email": email,
            "image_url": image_url
        }
    })

@profile_bp.route("/api/profile-image", methods=["GET"])
@login_required
def get_profile_image():
    user_id = session.get("user_id")
    for ext in [".png", ".jpg", ".jpeg", ".webp"]:
        path = os.path.join(UPLOAD_DIR, f"user_{user_id}{ext}")
        if os.path.exists(path):
            return jsonify({"image": f"user_{user_id}{ext}"})
    return jsonify({"image": None})
