# backend/routes/admin/site_settings.py

from flask import Blueprint, jsonify, request, session
from database import get_db

settings_bp = Blueprint("settings", __name__, url_prefix="/api/admin/settings")

def is_admin():
    return session.get("role") == "admin"

@settings_bp.route("/", methods=["GET"])
def get_settings():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT key, value FROM site_settings")
    rows = cursor.fetchall()
    settings = {key: value for key, value in rows}
    if "maintenanceMode" in settings:
        settings["maintenanceMode"] = settings["maintenanceMode"] == "true"
    return jsonify(settings)

@settings_bp.route("/", methods=["POST"])
def update_settings():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid payload"}), 400
    db = get_db()
    cursor = db.cursor()
    for key, val in data.items():
        if isinstance(val, bool):
            val = "true" if val else "false"
        cursor.execute(
            "REPLACE INTO site_settings (key, value) VALUES (?, ?)",
            (key, str(val))
        )
    db.commit()
    return jsonify({"message": "Settings updated successfully"})