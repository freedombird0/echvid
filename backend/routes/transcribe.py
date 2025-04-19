from flask import Blueprint, request, jsonify, session, current_app
import os, uuid, traceback, whisper, yt_dlp, re
from werkzeug.utils import secure_filename
from pydub import AudioSegment
from deep_translator import GoogleTranslator

transcribe_bp = Blueprint("transcribe", __name__)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# تعديل ديكوريتر login_required ليسمح بمرور طلبات OPTIONS بدون تحقق
def login_required(f):
    def wrapped(*args, **kwargs):
        if request.method == "OPTIONS":
            return f(*args, **kwargs)
        if "user_id" not in session:
            current_app.logger.error("Unauthorized access - user_id not found in session")
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    wrapped.__name__ = f.__name__
    return wrapped

# دالة لتقسيم النص إلى أجزاء أصغر بحيث لا يتجاوز طول كل جزء الحد الأقصى (4900 حرف)
def split_text(text, max_length=4900):
    # محاولة التقسيم بناءً على نهاية الجمل (نقاط، علامتي تعجب أو استفهام)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 > max_length:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def process_transcription(input_path, source_lang, target_lang):
    try:
        model = whisper.load_model("large")  # ثابت
    except Exception as e:
        current_app.logger.error("Failed to load Whisper model: %s", e, exc_info=True)
        return None, f"Failed to load model: {str(e)}", 500

    # تحويل الملف إلى WAV إذا لزم الأمر
    if not input_path.lower().endswith(".wav"):
        try:
            current_app.logger.debug("Converting file to WAV: %s", input_path)
            audio = AudioSegment.from_file(input_path)
            uid = os.path.splitext(os.path.basename(input_path))[0]
            wav_path = os.path.join(UPLOAD_FOLDER, f"{uid}.wav")
            audio.export(wav_path, format="wav")
            os.remove(input_path)
            input_path = wav_path
            current_app.logger.debug("Conversion complete, WAV file: %s", input_path)
        except Exception as conv_err:
            current_app.logger.error("Error converting to WAV: %s", conv_err, exc_info=True)
            return None, f"Error converting media to WAV: {str(conv_err)}", 500

    # تنفيذ عملية النسخ (Transcription)
    try:
        current_app.logger.debug("Starting transcription on: %s", input_path)
        result = model.transcribe(input_path, language=source_lang or None)
        transcript = result.get("text", "")
        current_app.logger.debug("Transcription successful: %s", transcript)
    except Exception as trans_err:
        current_app.logger.error("Transcription error: %s", trans_err, exc_info=True)
        return None, f"Transcription failed: {str(trans_err)}", 500

    # تنفيذ الترجمة إذا كانت مطلوبة، مع تقسيم النص ليتناسب مع الحد الأقصى (5000 حرف)
    translated = ""
    if target_lang:
        try:
            chunks = split_text(transcript, 4900)  # تقسيم النص إلى أجزاء
            current_app.logger.debug("Text split into %d chunks for translation.", len(chunks))
            translator = GoogleTranslator(source="auto", target=target_lang)
            translated_chunks = []
            for i, chunk in enumerate(chunks):
                current_app.logger.debug("Translating chunk %d: %s", i+1, chunk[:100] + "...")
                translated_chunk = translator.translate(chunk)
                translated_chunks.append(translated_chunk)
            translated = " ".join(translated_chunks)
            current_app.logger.debug("Translation successful: %s", translated[:100] + "...")
        except Exception as translt_err:
            current_app.logger.error("Translation error: %s", translt_err, exc_info=True)
            return None, f"Translation failed: {str(translt_err)}", 500

    return {"transcript": transcript.strip(), "translated": translated.strip() if translated else ""}, None, 200

# ---------------------------------------------------------------------
# Endpoint لمعالجة رفع الملف فقط
@transcribe_bp.route("/api/transcribe-file", methods=["POST", "OPTIONS"])
@login_required
def transcribe_file():
    try:
        current_app.logger.debug("=== Processing transcribe-file ===")
        file = request.files.get("file")
        if not file or not file.filename.strip():
            current_app.logger.error("No file uploaded.")
            return jsonify({"error": "No file uploaded"}), 400

        uid = uuid.uuid4().hex
        original_filename = secure_filename(file.filename)
        filename = f"{uid}_{original_filename}"
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            file.save(input_path)
            current_app.logger.debug("File saved: %s", input_path)
        except Exception as save_err:
            current_app.logger.error("Error saving file: %s", save_err, exc_info=True)
            return jsonify({"error": f"Error saving file: {str(save_err)}"}), 500

        source_lang = request.form.get("source_lang", "")
        target_lang = request.form.get("target_lang", "")

        response, error_msg, status = process_transcription(input_path, source_lang, target_lang)
        if error_msg:
            return jsonify({"error": error_msg}), status
        return jsonify(response), 200
    except Exception as e:
        current_app.logger.error("Unexpected error in transcribe_file: %s", e, exc_info=True)
        traceback.print_exc()
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

# ---------------------------------------------------------------------
# Endpoint لمعالجة روابط الفيديو فقط
@transcribe_bp.route("/api/transcribe-url", methods=["POST", "OPTIONS"])
@login_required
def transcribe_url():
    try:
        current_app.logger.debug("=== Processing transcribe-url ===")
        video_url = request.form.get("video_url", "").strip()
        if not video_url:
            current_app.logger.error("No valid URL provided.")
            return jsonify({"error": "No valid video URL provided."}), 400

        uid = uuid.uuid4().hex
        try:
            current_app.logger.debug("Attempting to download video from URL: %s", video_url)
            ydl_opts = {
                'outtmpl': os.path.join(UPLOAD_FOLDER, f"{uid}.%(ext)s"),
                'quiet': True,
                'no_warnings': True,
                'format': 'bestaudio/best',
                'retries': 10,
                'socket_timeout': 30,
                'user_agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/98.0.4758.102 Safari/537.36'
                )
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                current_app.logger.debug("yt-dlp info: %s", info)
                ext = info.get('ext', 'mp4')
                filename = f"{uid}.{ext}"
                input_path = os.path.join(UPLOAD_FOLDER, filename)
                current_app.logger.debug("Video downloaded: %s", input_path)
        except Exception as yt_err:
            current_app.logger.error("Error downloading video: %s", yt_err, exc_info=True)
            return jsonify({"error": f"Failed to download media using yt-dlp: {str(yt_err)}"}), 500

        source_lang = request.form.get("source_lang", "")
        target_lang = request.form.get("target_lang", "")

        response, error_msg, status = process_transcription(input_path, source_lang, target_lang)
        if error_msg:
            return jsonify({"error": error_msg}), status
        return jsonify(response), 200
    except Exception as e:
        current_app.logger.error("Unexpected error in transcribe_url: %s", e, exc_info=True)
        traceback.print_exc()
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500
