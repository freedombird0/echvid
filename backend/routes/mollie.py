# backend/routes/mollie.py

import os
from flask import Blueprint, request, jsonify, current_app
from mollie.api.client import Client
import hmac
import hashlib
from flask import request, abort, current_app


mollie_bp = Blueprint("mollie", __name__, url_prefix="/api/mollie")

def get_mollie_client():
    """تهيئة عميل Mollie باستخدام مفتاح API من متغيّرات البيئة"""
    client = Client()
    client.set_api_key(current_app.config["MOLLIE_API_KEY"])
    return client

@mollie_bp.route("/create-payment", methods=["POST"])
def create_payment():
    """
    ينشئ فاتورة دفع ويُعيد رابط صفحة الدفع (checkoutUrl)
    متوقّع JSON في الجسم يحتوي على:
      - amount (String): القيمة، مثال "9.99"
      - description (String) اختياري
      - redirectUrl (String) اختياري
    """
    data = request.get_json() or {}
    amount      = data.get("amount")
    description = data.get("description", "Echvid Subscription")
    redirect_url = data.get("redirectUrl", "http://localhost:5173/payment-success")

    mollie = get_mollie_client()
    payment = mollie.payments.create({
        "amount"     : {"currency": "EUR", "value": amount},
        "description": description,
        "redirectUrl": redirect_url,
        # تحديد طرق الدفع التجريبية
        "method": ["creditcard", "paypal", "ideal"]
    })

    # استخدم الخاصية الصحيحة checkout_url بدلاً من الدالة
    return jsonify({"checkoutUrl": payment.checkout_url})

@mollie_bp.route("/webhook", methods=["POST"])
def payment_webhook():
    """
    يعالج Webhook من Mollie فقط إذا كان التوقيع صحيحًا.
    """
    # 1) احصل على النص الخام للطلب (Payload) والتوقيع المرسل في الهيدر
    payload = request.get_data()  # البيانات كما أرسلها Mollie
    signature_header = request.headers.get("X-Mollie-Signature", "")

    # 2) أحضر الـ Secret من متغيرات البيئة
    secret = current_app.config["MOLLIE_WEBHOOK_SECRET"].encode()

    # 3) احسب HMAC_SHA256 على الـ payload باستخدام الـ secret
    expected_sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()

    # 4) قارن التوقيع المحسوب مع الهيدر بطريقة آمنة
    if not hmac.compare_digest(expected_sig, signature_header):
        # إذا التوقيع غير صحيح، ارفض الطلب برمز 403
        abort(403, "Invalid Mollie webhook signature")

    # 5) إذا وصلنا هنا، الطلب مؤمّن ومن Mollie فعلاً
    data = request.form  # أو request.get_json() حسب نوع البيانات
    payment_id = data.get("id")
    # TODO: ضع هنا منطق تفعيل الاشتراك أو تسليم المنتج
    print(f"🟢 Mollie payment {payment_id} paid successfully")

    return ("", 204)