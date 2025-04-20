# routes/summarize.py
import os
from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename

# إنشاء Blueprint خاص بأداة تلخيص النصوص
summarize_bp = Blueprint("summarize", __name__)

# ديكوريتر بسيط للتحقق من تسجيل الدخول
def login_required(f):
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

@summarize_bp.route("/api/text-summarize", methods=["POST"])
@login_required
def text_summarize():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    text = data.get("text")
    if not text or not text.strip():
        return jsonify({"error": "Text required"}), 400

    # تنفيذ التلخيص بطريقة مبسطة: أخذ أول نسبة 20٪ من الكلمات (أو على الأقل 5 كلمات)
    words = text.split()
    num_words = max(5, int(len(words) * 0.2))
    summary = " ".join(words[:num_words])
    
    # يمكن إضافة عمليات معالجة أخرى إن لزم الأمر (مثلاً تنظيف النص)
    return jsonify({"message": "Summary generated", "summary": summary})
