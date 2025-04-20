# backend/routes/paddle.py

import os
from flask import Blueprint, jsonify
from dotenv import load_dotenv

# -----------------------------------------
# تم تعطيل تكامل Paddle مؤقتًا
# يمكن إعادة تفعيل هذا الكود لاحقًا إذا لزم الأمر
# -----------------------------------------

load_dotenv()

paddle_bp = Blueprint("paddle", __name__, url_prefix="/api")

@paddle_bp.route("/create-paddle-session", methods=["POST"])
def create_paddle_session_disabled():
    """
    هذه الدالة مُعطّلة حاليًا - Paddle integration temporarily disabled.
    تستخدم لاحقًا إذا عُدت للـ Paddle بعد حل المتطلبات.
    """
    return jsonify({
        "error": "Paddle integration is temporarily disabled."
    }), 503

# باقي تكامل Paddle محفوظ هنا للتوثيق، لكن معلق:
#
# PADDLE_VENDOR_ID = os.getenv("PADDLE_VENDOR_ID")
# PADDLE_VENDOR_AUTH_CODE = os.getenv("PADDLE_VENDOR_AUTH_CODE")
# PADDLE_ENV = os.getenv("PADDLE_MODE", "live")
# PADDLE_CHECKOUT_BASE = (
#     "https://vendors.paddle.com/api/2.0/product/generate_pay_link"
#     if PADDLE_ENV == "live"
#     else "https://sandbox-vendors.paddle.com/api/2.0/product/generate_pay_link"
# )
# PRODUCT_IDS = {
#     "monthly": "pri_01js27mb3nj0f0vnzgnmf6sx68",
#     "lifetime": "pri_01js27qcncwt0fnjqe9sj1wh6t",
# }
#
# @paddle_bp.route("/create-paddle-session", methods=["POST"])
# def create_paddle_session():
#     data = request.get_json()
#     plan = data.get("plan")
#     if plan not in PRODUCT_IDS:
#         return jsonify({"error": "Invalid plan selected"}), 400
#     payload = {
#         "product_id": PRODUCT_IDS[plan],
#         "vendor_id": PADDLE_VENDOR_ID,
#         "vendor_auth_code": PADDLE_VENDOR_AUTH_CODE,
#         "return_url": "https://echvid.com/payment-success",
#         "cancel_url": "https://echvid.com/payment-failed"
#     }
#     try:
#         import requests
#         response = requests.post(PADDLE_CHECKOUT_BASE, data=payload)
#         result = response.json()
#         if not result.get("success"):
#             raise Exception(result.get("error", {}).get("message", "Unknown error"))
#         checkout_url = result["response"]["url"]
#         return jsonify({"checkout_url": checkout_url})
#     except Exception as e:
#         print("❌ Paddle error:", e)
#         return jsonify({"error": str(e)}), 500
