import os
import time
import datetime
import sqlite3
import uuid
import traceback
import moviepy.editor as mp
import whisper
from yt_dlp import YoutubeDL
from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from deep_translator import GoogleTranslator
from flask_cors import cross_origin
from moviepy.editor import TextClip  # تأكيد استيراد TextClip
import urllib.parse

# استيراد مهمة Celery من ملف tasks.py
from routes.tasks import full_ai_process_task

video_bp = Blueprint("video", __name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "output")
AUDIO_FOLDER = os.path.join(BASE_DIR, "audio")
DB_FILE = os.path.join(BASE_DIR, "users.db")

# ديكوريتر بسيط للتحقق من تسجيل الدخول
def login_required(f):
    def decorated(*args, **kwargs):
        # السماح لطلبات OPTIONS من المرور بدون تحقق
        if request.method == "OPTIONS":
            return f(*args, **kwargs)
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

# ------------- Upload File Endpoint -------------
@video_bp.route("/api/upload", methods=["POST"])
@login_required
def upload():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    # استخدام secure_filename لتفادي أحرف غير مرغوبة
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    try:
        file.save(file_path)
    except Exception as e:
        current_app.logger.error("Error saving file: %s", e, exc_info=True)
        return jsonify({"error": "Error saving file"}), 500

    # استخراج مدة الفيديو
    try:
        clip = mp.VideoFileClip(file_path)
        duration = str(datetime.timedelta(seconds=int(clip.duration)))
    except Exception as e:
        current_app.logger.error("Error processing video duration: %s", e, exc_info=True)
        duration = "Unknown"

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO videos (user_id, title, filename, duration) VALUES (?, ?, ?, ?)",
            (session.get("user_id"), filename, filename, duration)
        )
    return jsonify({"message": "Uploaded", "filename": filename})

# ------------- Download Video from URL Endpoint -------------
@video_bp.route("/api/download_url", methods=["POST"])
@login_required
def download_url():
    data = request.get_json()
    video_url = data.get("video_url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': os.path.join(UPLOAD_FOLDER, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4'
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            # تعديل الامتداد إذا لزم الأمر
            filename = os.path.basename(filename).replace(".webm", ".mp4").replace(".mkv", ".mp4")
    except Exception as e:
        current_app.logger.error("Error downloading video: %s", e, exc_info=True)
        return jsonify({"error": "Failed to download video"}), 500

    try:
        clip = mp.VideoFileClip(os.path.join(UPLOAD_FOLDER, filename))
        duration = str(datetime.timedelta(seconds=int(clip.duration)))
    except Exception as e:
        current_app.logger.error("Error processing video duration: %s", e, exc_info=True)
        duration = "Unknown"

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO videos (user_id, title, filename, duration) VALUES (?, ?, ?, ?)",
            (session.get("user_id"), filename, filename, duration)
        )
    return jsonify({"message": "Downloaded", "filename": filename})

# ------------- Process Video (Transcription) Endpoint -------------
@video_bp.route("/api/process", methods=["POST"])
@login_required
def process_video():
    data = request.get_json()
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "Filename required"}), 400

    video_path = os.path.join(UPLOAD_FOLDER, filename)
    audio_path = os.path.join(AUDIO_FOLDER, f"{filename}_audio.wav")

    try:
        video = mp.VideoFileClip(video_path)
        if video.audio is None:
            return jsonify({"error": "No audio in video"}), 400
        video.audio.write_audiofile(audio_path, logger=None)
    except Exception as e:
        current_app.logger.error("Error processing video: %s", e, exc_info=True)
        return jsonify({"error": "Unable to process video"}), 400

    try:
        model = whisper.load_model("medium", download_root="models/")
        result = model.transcribe(audio_path)
        transcript = result.get("text", "")
    except Exception as e:
        current_app.logger.error("Error during transcription: %s", e, exc_info=True)
        return jsonify({"error": "Transcription failed"}), 500

    transcript_path = os.path.join(OUTPUT_FOLDER, f"{filename}_transcript.txt")
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript)

    return jsonify({"message": "Transcription complete", "transcript": transcript})

# ------------- (Optional) Summarize Endpoint (أداة مستقلة) -------------
@video_bp.route("/api/summarize", methods=["POST"])
@login_required
def summarize():
    data = request.get_json()
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "Filename required"}), 400

    transcript_path = os.path.join(OUTPUT_FOLDER, f"{filename}_transcript.txt")
    summary_path = os.path.join(OUTPUT_FOLDER, f"{filename}_summary.txt")

    if not os.path.exists(transcript_path):
        return jsonify({"error": "Transcript file not found"}), 404

    with open(transcript_path, "r", encoding="utf-8") as f:
        text = f.read()

    summary = " ".join(text.split()[:max(5, int(len(text.split()) * 0.2))])
    
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)

    return jsonify({"message": "Summary generated", "summary": summary})

# ------------- Translate Endpoint -------------
# هنا نستخدم ملف النص الكامل للنُسخ (transcript) وليس التلخيص
@video_bp.route("/api/translate", methods=["POST"])
@login_required
def translate():
    filename = request.form.get("filename")
    lang_code = request.form.get("language")
    if not filename or not lang_code:
        return jsonify({"error": "Filename and language required"}), 400

    transcript_path = os.path.join(OUTPUT_FOLDER, f"{filename}_transcript.txt")
    output_path = os.path.join(OUTPUT_FOLDER, f"{filename}_translated.txt")

    if not os.path.exists(transcript_path):
        return jsonify({"error": "Transcript file not found"}), 404

    with open(transcript_path, "r", encoding="utf-8") as f:
        text = f.read()

    translated = ""
    for i in range(0, len(text), 4000):
        chunk = text[i:i+4000]
        translated += GoogleTranslator(source="auto", target=lang_code).translate(chunk) + "\n"
        time.sleep(1)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(translated.strip())

    return jsonify({"message": "Translation complete", "translated": translated.strip()})

# ------------- Generate Audio Endpoint -------------
@video_bp.route("/api/generate-audio", methods=["POST"])
@login_required
@cross_origin(origins="http://localhost:5173", supports_credentials=True)
def generate_audio():
    filename = request.form.get("filename")
    lang_code = request.form.get("lang_code")
    if not filename or not lang_code:
        return jsonify({"error": "Filename and language code required"}), 400

    translated_file = os.path.join(OUTPUT_FOLDER, f"{filename}_translated.txt")
    audio_output_path = os.path.join(AUDIO_FOLDER, f"{filename}_translated_audio.mp3")

    if not os.path.exists(translated_file):
        return jsonify({"error": "Translated file missing"}), 404

    with open(translated_file, "r", encoding="utf-8") as f:
        text = f.read()

    try:
        from google.cloud import texttospeech
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=lang_code,
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        with open(audio_output_path, "wb") as out:
            out.write(response.audio_content)
    except Exception as e:
        current_app.logger.error("Error in generating audio: %s", e, exc_info=True)
        return jsonify({"error": "Audio generation failed"}), 500

    return jsonify({"message": "Audio generated", "audio_url": f"/output/{filename}_translated_audio.mp3"})

# ------------- Generate Video Endpoint -------------
@video_bp.route("/api/generate-video", methods=["POST"])
@login_required
def generate_video():
    data = request.get_json()
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "Filename required"}), 400

    # تعريف المسارات
    video_path = os.path.join(UPLOAD_FOLDER, filename)
    audio_path = os.path.join(AUDIO_FOLDER, f"{filename}_translated_audio.mp3")
    translated_txt_path = os.path.join(OUTPUT_FOLDER, f"{filename}_translated.txt")
    output_path = os.path.join(OUTPUT_FOLDER, f"{filename}_final.mp4")

    # قراءة ملف الفيديو الأصلي
    try:
        video = mp.VideoFileClip(video_path)
    except Exception as e:
        current_app.logger.error("Error opening video file: %s", e, exc_info=True)
        return jsonify({"error": "Unable to open video file"}), 400

    # قراءة ملف الصوت المُولَّد
    try:
        audio = mp.AudioFileClip(audio_path)
    except Exception as e:
        current_app.logger.error("Error opening audio file: %s", e, exc_info=True)
        return jsonify({"error": "Unable to open audio file"}), 400

    # دمج الصوت مع الفيديو
    video = video.set_audio(audio)

    # قراءة نص الترجمة (إن وُجد)
    subtitles_text = ""
    if os.path.exists(translated_txt_path):
        try:
            with open(translated_txt_path, "r", encoding="utf-8") as f:
                subtitles_text = f.read().strip()
        except Exception as e:
            current_app.logger.error("Error reading translated text: %s", e, exc_info=True)
    else:
        current_app.logger.warning("Translated text file not found.")

    subtitle_clips = None
    if subtitles_text:
        # تقسيم كل سطر للتعليق لمدة ثابتة (مثلاً 2 ثانية لكل سطر)
        subtitles = [
            ((i * 2, (i + 1) * 2), subtitle.strip())
            for i, subtitle in enumerate(subtitles_text.split("\n"))
            if subtitle.strip()
        ]
        current_app.logger.debug("Subtitles: %s", subtitles)
        from moviepy.video.tools.subtitles import SubtitlesClip
        generator = lambda txt: TextClip(txt, font="Arial", fontsize=24, color="white")
        try:
            subtitle_clips = SubtitlesClip(subtitles, generator)
        except Exception as e:
            current_app.logger.error("Error creating subtitles clip: %s", e, exc_info=True)
            subtitle_clips = None

    
    # توليد الفيديو النهائي: دمج الفيديو (مع أو بدون ترجمات)
    try:
        elements = [video]

        if subtitle_clips:
            elements.append(subtitle_clips.set_pos(("center", "bottom")))

        if session.get("plan") == "free":
            watermark = TextClip(
                "ECHVID FREE VERSION", fontsize=40, color="white", font="Arial"
            ).set_duration(video.duration).set_opacity(0.6).set_pos(("center", "top"))
            elements.append(watermark)

        if len(elements) > 1:
            composite = mp.CompositeVideoClip(elements)
        else:
            composite = video

        composite.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True
        )
        composite.close()
        video.close()
        audio.close()
    except Exception as e:
        current_app.logger.error("Error generating final video: %s", e, exc_info=True)
        return jsonify({"error": "Video generation failed"}), 500

    if not os.path.exists(output_path):
        current_app.logger.error("Final video file not found at %s", output_path)
        return jsonify({"error": "Final video file not created"}), 500

    # ترميز اسم الملف للتأكد من أن الرابط صحيح
    final_file_url = f"/output/{urllib.parse.quote(filename + '_final.mp4')}"
    return jsonify({"message": "Video generated", "video_url": final_file_url})

# ------------- Endpoint لإطلاق العملية الشاملة (Full AI Process) -------------
@video_bp.route("/api/full_process", methods=["POST"])
@login_required
def full_process():
    data = request.get_json()
    filename = data.get("filename")
    source_lang = data.get("source_lang", "en")
    target_lang = data.get("target_lang", "en")
    language = data.get("language", "en")  # اللغة المستخدمة للترجمة

    if not filename:
        return jsonify({"error": "Filename required"}), 400

    task = full_ai_process_task.delay(filename, source_lang, target_lang, language)
    return jsonify({"message": "Full process started", "task_id": task.id}), 202

# ------------- Endpoints لإدارة الفيديوهات -------------
@video_bp.route("/api/videos", methods=["GET"])
@login_required
def get_user_videos():
    user_id = session.get("user_id")
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        # استخدام عمود "created_at" بدلاً من "date" لتنظيم الفيديوهات
        videos = conn.execute("SELECT * FROM videos WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
        return jsonify([dict(v) for v in videos])

@video_bp.route("/api/videos/<int:video_id>", methods=["DELETE"])
@login_required
def delete_video(video_id):
    user_id = session.get("user_id")
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM videos WHERE id = ? AND user_id = ?", (video_id, user_id))
    return jsonify({"message": "Video deleted"})

@video_bp.route("/api/user-videos", methods=["GET"])
@login_required
def get_video_count():
    user_id = session.get("user_id")
    with sqlite3.connect(DB_FILE) as conn:
        count = conn.execute("SELECT COUNT(*) FROM videos WHERE user_id = ?", (user_id,)).fetchone()[0]
    return jsonify({"count": count})
