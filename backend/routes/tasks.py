import os
import time
import datetime
import sqlite3
import uuid
import traceback
import moviepy.editor as mp
import whisper
from yt_dlp import YoutubeDL
from deep_translator import GoogleTranslator
from celery import Celery

# إعداد مسار المشروع والمجلدات الضرورية
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "output")
AUDIO_FOLDER = os.path.join(BASE_DIR, "audio")

# إعداد Celery باستخدام Redis كـ broker و backend
celery_app = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# تعيين إعدادات Celery الأساسية
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# دالة مساعدة لتقسيم النص إن لزم الأمر (يمكن استخدامه لاحقاً إذا احتجت لتقسيم النص)
def split_text(text, max_length=4900):
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 > max_length:
            if current:
                chunks.append(current)
            current = sentence
        else:
            current += (" " + sentence) if current else sentence
    if current:
        chunks.append(current)
    return chunks

def process_full_ai(filename, source_lang, target_lang, translation_lang):
    """
    تنفيذ العملية الكاملة: استخراج الصوت من الفيديو، نسخ النص باستخدام Whisper،
    ثم ترجمة النص الكامل (بدلاً من التلخيص) وتوليد الصوت والفيديو النهائي.
    """
    result = {}
    try:
        # تحديد مسارات الملفات
        video_path = os.path.join(UPLOAD_FOLDER, filename)
        audio_path = os.path.join(AUDIO_FOLDER, f"{filename}_audio.wav")
        
        # استخراج الصوت من الفيديو
        video = mp.VideoFileClip(video_path)
        if video.audio is None:
            raise Exception("Video has no audio")
        video.audio.write_audiofile(audio_path, logger=None)
        
        # استخراج النص الكامل عبر النسخ باستخدام Whisper
        model = whisper.load_model("medium")
        transcription = model.transcribe(audio_path, language=source_lang or None)
        transcript_text = transcription.get("text", "")
        result["transcript"] = transcript_text
        
        # حذف خطوة التلخيص، إذ سنستخدم النص الكامل للترجمة
        translation_input = transcript_text
        
        # ترجمة النص الكامل باستخدام GoogleTranslator؛
        # إذا تجاوز النص 4000 حرف، نقسمه إلى أجزاء
        translator = GoogleTranslator(source="auto", target=translation_lang)
        if len(translation_input) > 4000:
            chunks = split_text(translation_input, 4000)
            translated_text = ""
            for chunk in chunks:
                translated_text += translator.translate(chunk) + " "
                time.sleep(1)
        else:
            translated_text = translator.translate(translation_input)
        result["translated"] = translated_text.strip()
        
        # توليد الصوت من النص المترجم باستخدام Google Text-to-Speech
        from google.cloud import texttospeech
        tts_client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=translated_text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=translation_lang,
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        tts_response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        audio_output_path = os.path.join(AUDIO_FOLDER, f"{filename}_translated_audio.mp3")
        with open(audio_output_path, "wb") as out:
            out.write(tts_response.audio_content)
        result["audio_url"] = f"/output/{filename}_translated_audio.mp3"
        
        # توليد الفيديو النهائي: دمج الفيديو الأصلي مع الصوت المولّد
        video_output_path = os.path.join(OUTPUT_FOLDER, f"{filename}_final.mp4")
        # إعادة استخدام الفيديو الأصلي وربط الصوت المولّد به
        final_video = video.set_audio(mp.AudioFileClip(audio_output_path))
        final_video.write_videofile(video_output_path, codec="libx264", audio_codec="aac")
        result["video_url"] = f"/output/{filename}_final.mp4"
        
        return result, None
    except Exception as e:
        traceback.print_exc()
        return None, str(e)

@celery_app.task(bind=True)
def full_ai_process_task(self, filename, source_lang, target_lang, translation_lang):
    """المهمة التي تنفذ العملية الكاملة في الخلفية"""
    result, error = process_full_ai(filename, source_lang, target_lang, translation_lang)
    if error:
        raise Exception(error)
    return result
