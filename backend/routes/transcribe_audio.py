from flask import Blueprint, request, jsonify, send_from_directory, session
import os
import uuid
import tempfile
import whisper
from deep_translator import GoogleTranslator
from google.cloud import texttospeech
from werkzeug.utils import secure_filename

# إنشاء Blueprint باسم transcribe_audio_bp
transcribe_audio_bp = Blueprint("transcribe_audio", __name__)

# 📂 إعداد المسارات
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AUDIO_FOLDER = os.path.join(BASE_DIR, "audio")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "output")
os.makedirs(AUDIO_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# تحميل نموذج Whisper مرة واحدة
whisper_model = whisper.load_model("base")  # يمكنك تغييره إلى "medium" أو "large"

# 🔐 التحقق من الجلسة
def login_required(f):
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

# 🎷 توليد صوت من نص باستخدام Google TTS (Generate Audio)
@transcribe_audio_bp.route("/api/generate-audio", methods=["POST"])
@login_required
def generate_audio():
    lang_code = request.form.get("lang_code", "en")
    custom_text = request.form.get("custom_text", "").strip()
    uploaded_file = request.files.get("file")

    text = ""
    if custom_text:
        text = custom_text
    elif uploaded_file:
        filename = secure_filename(uploaded_file.filename)
        filepath = os.path.join(OUTPUT_FOLDER, filename)
        uploaded_file.save(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        return jsonify({"error": "Please provide text or upload a .txt file."}), 400

    if not text.strip():
        return jsonify({"error": "Text is empty"}), 400

    try:
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=lang_code,
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        output_filename = f"tts_{uuid.uuid4().hex}.mp3"
        output_path = os.path.join(AUDIO_FOLDER, secure_filename(output_filename))
        with open(output_path, "wb") as out:
            out.write(response.audio_content)

        return jsonify({
            "message": "✅ Audio generated successfully with Google TTS.",
            "audio_url": f"/output/audio/{output_filename}"
        })

    except Exception as google_err:
        return jsonify({"error": f"❌ Google TTS failed: {google_err}"}), 500


# 🎙️ تفريغ وترجمة ملف صوتي باستخدام Whisper (Transcribe Audio)
@transcribe_audio_bp.route("/api/transcribe-audio", methods=["POST"])
@login_required
def transcribe_audio():
    file = request.files.get("file")
    source_lang = request.form.get("source_lang", "")
    target_lang = request.form.get("target_lang", "")

    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
        file.save(temp.name)
        audio_path = temp.name

    try:
        result = whisper_model.transcribe(audio_path, language=source_lang if source_lang else None)
        transcript = result.get("text", "").strip()
    except Exception as e:
        os.remove(audio_path)
        return jsonify({"error": f"Whisper transcription failed: {str(e)}"}), 500

    os.remove(audio_path)

    translated_text = ""
    if target_lang:
        try:
            translated_text = GoogleTranslator(source="auto", target=target_lang).translate(transcript)
        except Exception as t_err:
            return jsonify({"error": f"Translation failed: {str(t_err)}"}), 500

    return jsonify({
        "transcript": transcript,
        "translated": translated_text
    })


# 🎵 تقديم الصوت
@transcribe_audio_bp.route("/output/audio/<filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_FOLDER, filename)
