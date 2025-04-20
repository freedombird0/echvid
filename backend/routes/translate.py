# routes/translate.py
import os
from flask import Blueprint, request, jsonify, session, current_app
from flask_cors import cross_origin
from werkzeug.utils import secure_filename
from deep_translator import GoogleTranslator

translate_bp = Blueprint("translate", __name__)

def login_required(f):
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

@translate_bp.route("/api/independent-translate", methods=["POST"])
@login_required
@cross_origin(origins="http://localhost:5173", supports_credentials=True)
def independent_translate():
    """
    وظيفة مستقلة للترجمة:
    - تدعم تلقي المدخلات بصيغة multipart/form-data (حيث يمكن رفع ملف نصي أو إرسال نص عبر حقل "text")
    - أو بصيغة JSON.
    يجب تمرير حقل "language" الذي يحدد رمز اللغة الهدف.
    """
    text = ""
    language = ""
    
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        language = request.form.get("language", "").strip()
        text = request.form.get("text", "").strip()
        uploaded_file = request.files.get("file")
        if uploaded_file:
            safe_filename = secure_filename(uploaded_file.filename)
            try:
                text = uploaded_file.read().decode("utf-8")
            except Exception as e:
                current_app.logger.error("Error reading uploaded file '%s': %s", safe_filename, e, exc_info=True)
                return jsonify({"error": "Failed to read uploaded file."}), 400
    else:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided."}), 400
        text = data.get("text", "").strip()
        language = data.get("language", "").strip()
    
    if not text:
        return jsonify({"error": "Text is required."}), 400
    if not language:
        return jsonify({"error": "Language is required."}), 400

    try:
        translator = GoogleTranslator(source="auto", target=language)
        translated_text = translator.translate(text)
        return jsonify({"translated": translated_text})
    except Exception as e:
        current_app.logger.error("Error translating text: %s", e, exc_info=True)
        return jsonify({"error": "Translation failed."}), 500
