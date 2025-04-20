from google.cloud import texttospeech

try:
    client = texttospeech.TextToSpeechClient()
    voices = client.list_voices()
    print("✅ الاتصال ناجح! عدد الأصوات المتوفرة:", len(voices.voices))
except Exception as e:
    print("❌ فشل الاتصال بـ Google TTS API:")
    print(e)
