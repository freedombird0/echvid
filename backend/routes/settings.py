# routes/settings.py
import sqlite3
from flask import Blueprint, request, jsonify, session
from routes.utils import login_required

settings_bp = Blueprint("settings", __name__)
DB_FILE = "users.db"

@settings_bp.route("/api/settings", methods=["GET"])
@login_required
def get_user_settings():
    user_id = session.get("user_id")
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT username, email FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "User not found."}), 404
        return jsonify({
            "username": row[0],
            "email": row[1],
            "language": "English",
            "notifications": True
        })

@settings_bp.route("/api/settings", methods=["POST"])
@login_required
def update_user_settings():
    user_id = session.get("user_id")
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor()
            if password:
                from werkzeug.security import generate_password_hash
                hashed_pw = generate_password_hash(password)
                cur.execute("UPDATE users SET username=?, email=?, password=? WHERE id=?", (username, email, hashed_pw, user_id))
            else:
                cur.execute("UPDATE users SET username=?, email=? WHERE id=?", (username, email, user_id))
            conn.commit()
        return jsonify({"message": "Settings updated successfully."})
    except Exception as e:
        print("Update error:", e)
        return jsonify({"error": "Failed to update settings."}), 500
