# backend/routes/admin/analytics.py

from flask import Blueprint, jsonify, session
from database import get_db

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/admin/analytics")

def is_admin():
    return session.get("role") == "admin"

@analytics_bp.route("/", methods=["GET"])
def get_stats():
    if not is_admin():
        return jsonify({"error": "Unauthorized access"}), 403

    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE plan = 'premium'")
        premium_users = cursor.fetchone()[0]

        return jsonify({
            "total_users": total_users,
            "premium_users": premium_users
        })
    except Exception as e:
        # Print full traceback to console for debugging
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to retrieve analytics: {e}"}), 500
