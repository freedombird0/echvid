# backend/routes/admin/ads.py

from flask import Blueprint, jsonify, request, session
from database import get_db

ads_bp = Blueprint("ads", __name__, url_prefix="/api/admin/ads")

def is_admin():
    return session.get("role") == "admin"

@ads_bp.route("/", methods=["GET"])
def get_ads():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, location, image_url, link FROM ads")
        rows = cursor.fetchall()
        ads = [{"id": r[0], "location": r[1], "image_url": r[2], "link": r[3]} for r in rows]
        return jsonify(ads)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch ads: {e}"}), 500

@ads_bp.route("/", methods=["POST"])
def add_ad():
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json()
    location = data.get("location")
    image_url = data.get("image_url")
    link = data.get("link")
    if not location or not image_url:
        return jsonify({"error": "Location and image URL are required"}), 400
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO ads (location, image_url, link) VALUES (?, ?, ?)",
            (location, image_url, link),
        )
        db.commit()
        return jsonify({"message": "Ad created successfully"})
    except Exception as e:
        return jsonify({"error": f"Failed to create ad: {e}"}), 500

@ads_bp.route("/<int:ad_id>", methods=["DELETE"])
def delete_ad(ad_id):
    if not is_admin():
        return jsonify({"error": "Unauthorized"}), 403
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("DELETE FROM ads WHERE id = ?", (ad_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Ad not found"}), 404
        db.commit()
        return jsonify({"message": "Ad deleted successfully"})
    except Exception as e:
        return jsonify({"error": f"Failed to delete ad: {e}"}), 500