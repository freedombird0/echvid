import os
from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from functools import wraps

# إنشاء Blueprint الخاص بأداة تعديل النصوص
edit_text_bp = Blueprint("edit_text", __name__)

# تحديد المسار الأساسي ومجلد الإخراج الذي سيتم حفظ الملفات النصية به
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_FOLDER = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ديكوراتور للتحقق من تسجيل الدخول باستخدام functools.wraps
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# نقطة النهاية لحفظ النص المُعدل
@edit_text_bp.route("/api/save-text", methods=["POST"])
@login_required
def save_text():
    """
    يستقبل هذا الـ endpoint طلب POST بصيغة JSON يحتوي على مفتاحي "filename" و "content".
    يتم تأمين اسم الملف باستخدام secure_filename وحفظ المحتوى داخل مجلد OUTPUT_FOLDER.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided."}), 400

    filename = data.get("filename")
    content = data.get("content")

    if not filename or content is None:
        return jsonify({"error": "Filename and content are required."}), 400

    # تأمين اسم الملف لتفادي الأحرف غير المرغوب فيها
    safe_filename = secure_filename(filename)
    file_path = os.path.join(OUTPUT_FOLDER, safe_filename)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        current_app.logger.error("Error saving text file: %s", e, exc_info=True)
        return jsonify({"error": "Error saving text file."}), 500

    return jsonify({"message": "Text saved successfully.", "filename": safe_filename})
