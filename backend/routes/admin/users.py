# backend/routes/admin/users.py

from flask import Blueprint, jsonify, request, session
from database import get_db

users_bp = Blueprint("users", __name__, url_prefix="/api/admin/users")

def is_admin():
    return session.get("role") == "admin"

@users_bp.route("/", methods=["GET"])
def get_all_users():
    if not is_admin():
        return jsonify({"error": "Unauthorized access"}), 403

    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT id, username, email, plan, role, created_at FROM users"
        )
        rows = cursor.fetchall()

        result = [
            {
                "id": r[0],
                "username": r[1],
                "email": r[2],
                "plan": r[3],
                "role": r[4],
                "created_at": r[5]
            }
            for r in rows
        ]
        return jsonify(result)
    except Exception as e:
        # Print full traceback to console for debugging
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to retrieve users: {e}"}), 500

@users_bp.route("/<int:user_id>", methods=["POST"])
def update_user(user_id):
    if not is_admin():
        return jsonify({"error": "Unauthorized access"}), 403

    data = request.get_json()
    plan = data.get("plan")
    role = data.get("role")
    if not plan or not role:
        return jsonify({"error": "Both plan and role are required"}), 400

    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "UPDATE users SET plan = ?, role = ? WHERE id = ?",
            (plan, role, user_id)
        )
        db.commit()
        return jsonify({"message": "User updated successfully"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to update user: {e}"}), 500

@users_bp.route("/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    if not is_admin():
        return jsonify({"error": "Unauthorized access"}), 403

    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "User not found"}), 404
        db.commit()
        return jsonify({"message": "User deleted successfully"})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to delete user: {e}"}), 500
