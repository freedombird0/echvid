from flask import Blueprint, request, jsonify, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

auth_bp = Blueprint("auth", __name__)
DB_FILE = os.path.join(os.path.dirname(__file__), "..", "users.db")

def get_db_connection():
    return sqlite3.connect(DB_FILE)

@auth_bp.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    plan = data.get("plan", "free")

    if not username or not email or not password:
        return jsonify({"error": "All fields are required."}), 400

    hashed_pw = generate_password_hash(password)
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, email, password, plan) VALUES (?, ?, ?, ?)",
                (username, email, hashed_pw, plan)
            )
            user = conn.execute(
                "SELECT id, username, plan, role FROM users WHERE email=?", (email,)
            ).fetchone()

        return jsonify({
            "message": "User registered successfully.",
            "user": {"username": user[1], "plan": user[2], "role": user[3]}
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({"error": "Username or email already exists."}), 409

@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT id, username, password, plan, role FROM users WHERE email=?", (email,)
        ).fetchone()

        if row and check_password_hash(row[2], password):
            session.permanent = True
            session.update({
                "user_id": row[0],
                "username": row[1],
                "email": email,
                "role": row[4]
            })

            return jsonify({
                "message": "Login successful.",
                "user": {"username": row[1], "plan": row[3], "role": row[4]}
            })

    return jsonify({"error": "Invalid email or password."}), 401

@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully."})

@auth_bp.route("/api/check-auth")
def check_auth():
    if "user_id" in session:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT username, plan, role FROM users WHERE id=?",
                (session["user_id"],)
            ).fetchone()

            if row:
                return jsonify({
                    "authenticated": True,
                    "username": row[0],
                    "plan": row[1],
                    "role": row[2]
                })

    return jsonify({"authenticated": False}), 401
