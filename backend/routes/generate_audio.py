print("Using generate_audio.py from:", __file__)

import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
from werkzeug.utils import secure_filename

AUDIO_TOOL_ENABLED = True

# Blueprint
generate_audio_bp = Blueprint("generate_audio", __name__, url_prefix="/api/generate-audio")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AUDIO_FOLDER = os.path.join(BASE_DIR, "audio")
os.makedirs(AUDIO_FOLDER, exist_ok=True)

@generate_audio_bp.route("/", methods=["POST"])
@cross_origin(origins="http://localhost:5173", supports_credentials=True)
def generate_audio():
    if not AUDIO_TOOL_ENABLED:
        return jsonify({"message": "Audio generation is under development."}), 200

    current_app.logger.debug("Request Content-Type: %s", request.content_type)

    # دعم كلا النوعين من البيانات
    if request.content_type and "multipart/form-data" in request.content_type:
        form_data = request.form.to_dict()
        file = request.files.get("file")
    else:
        form_data = request.form.to_dict() if request.form else request.get_json() or {}
        file = None

    custom_text = form_data.get("custom_text", "").strip()
    output_lang = form_data.get("output_lang", "").strip()
    gender = form_data.get("gender", "NEUTRAL").strip()

    current_app.logger.debug("Form Data: %s", form_data)

    if not output_lang:
        return jsonify({"error": "Output language is required."}), 400

    language_map = {
        "ar": "ar-XA", "en": "en-US", "fr": "fr-FR", "de": "de-DE",
        "es": "es-ES", "tr": "tr-TR", "it": "it-IT", "ru": "ru-RU",
        "zh": "zh-CN", "hi": "hi-IN"
    }

    lang_code_full = language_map.get(output_lang.lower())
    if not lang_code_full:
        return jsonify({"error": "Invalid output language."}), 400

    # قراءة النص من الملف إن لم يكن موجودًا
    if file and not custom_text:
        try:
            content = file.read()
            try:
                custom_text = content.decode("utf-8").strip()
            except UnicodeDecodeError:
                custom_text = content.decode("cp1256").strip()
        except Exception as e:
            return jsonify({"error": f"Failed to read file: {e}"}), 400

    if not custom_text:
        return jsonify({"error": "Text input is required."}), 400

    output_filename = f"audio_{uuid.uuid4().hex[:8]}.mp3"
    audio_output_path = os.path.join(AUDIO_FOLDER, secure_filename(output_filename))

    try:
        from google.cloud import texttospeech

        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=custom_text)
        voice_params = texttospeech.VoiceSelectionParams(
            language_code=lang_code_full,
            ssml_gender=getattr(texttospeech.SsmlVoiceGender, gender.upper(), texttospeech.SsmlVoiceGender.NEUTRAL)
        )
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config
        )

        with open(audio_output_path, "wb") as out:
            out.write(response.audio_content)

    except Exception as e:
        current_app.logger.error("Synthesis failed: %s", e, exc_info=True)
        return jsonify({"error": f"Audio generation failed: {e}"}), 500

    return jsonify({
        "message": "Audio generated successfully",
        "audio_url": f"/output/audio/{output_filename}"
    })
