import os
import subprocess
import shutil
import logging
from logging.handlers import RotatingFileHandler
from datetime import timedelta

from flask import Flask, jsonify, request, send_from_directory, g
from flask_cors import CORS
from flask_session import Session
from dotenv import load_dotenv
from werkzeug.exceptions import HTTPException

# ----------------------------------------------------------------------
# 0. Load .env
# ----------------------------------------------------------------------
load_dotenv(dotenv_path=".env")

# ----------------------------------------------------------------------
# 1. Create Flask app
# ----------------------------------------------------------------------
app = Flask(__name__, static_folder="static", static_url_path="/static")

FLASK_ENV = os.getenv("FLASK_ENV", "production")
IS_PROD    = FLASK_ENV == "production"

# Base paths
BASE_DIR      = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "output")

app.config.update(
    SECRET_KEY                   = os.getenv("SECRET_KEY", "supersecretkey"),
    MOLLIE_API_KEY               = os.getenv("MOLLIE_API_KEY"),
    MOLLIE_WEBHOOK_SECRET        = os.getenv("MOLLIE_WEBHOOK_SECRET"),
    UPLOAD_FOLDER                = UPLOAD_FOLDER,
    OUTPUT_FOLDER                = OUTPUT_FOLDER,
    SESSION_TYPE                 = "filesystem",
    SESSION_PERMANENT            = True,
    PERMANENT_SESSION_LIFETIME   = timedelta(days=7),
    SESSION_COOKIE_NAME          = "session",
    SESSION_COOKIE_HTTPONLY      = True,
    SESSION_COOKIE_SAMESITE      = "None" if IS_PROD else "Lax",
    SESSION_COOKIE_SECURE        = IS_PROD,
)
Session(app)

# ----------------------------------------------------------------------
# 2. Configure MoviePy ➔ Linux ImageMagick binary
# ----------------------------------------------------------------------
IM_PATH = os.environ.get("IMAGEMAGICK_BINARY", "/usr/bin/convert")
os.environ["IMAGEMAGICK_BINARY"] = IM_PATH
# verify at startup
try:
    subprocess.run([IM_PATH, "--version"], check=True, capture_output=True, text=True)
    print("✅ ImageMagick found at:", IM_PATH)
except Exception as e:
    print("⚠️ Failed to verify ImageMagick:", e)

from moviepy.config import change_settings
change_settings({"IMAGEMAGICK_BINARY": IM_PATH})

# ----------------------------------------------------------------------
# 3. Create folder structure
# ----------------------------------------------------------------------
FOLDERS = { name: os.path.join(BASE_DIR, name) for name in (
    "uploads","output","audio","frames","subtitles","data","logs","static"
)}
for p in FOLDERS.values():
    os.makedirs(p, exist_ok=True)

# ----------------------------------------------------------------------
# 4. (Optional) Load GCP Credentials
# ----------------------------------------------------------------------
key_json = os.path.join(os.path.dirname(__file__), "key.json")
if os.path.exists(key_json):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_json
    app.logger.info("✅ Google credentials loaded")
else:
    app.logger.warning("⚠️ Google credentials not found")

# ----------------------------------------------------------------------
# 5. CORS & URL rules
# ----------------------------------------------------------------------
origins = ["https://echvid.com"] if IS_PROD else ["http://localhost:5173"]
CORS(app, resources={r"/api/*": {"origins": origins}}, supports_credentials=True)
app.url_map.strict_slashes = False

# ----------------------------------------------------------------------
# 6. i18n support
# ----------------------------------------------------------------------
LANGUAGES = {
    "en":"English","ar":"Arabic","fr":"French","de":"German",
    "es":"Spanish","tr":"Turkish","it":"Italian","ru":"Russian",
    "zh":"Chinese","hi":"Hindi",
}
@app.before_request
def set_language():
    g.lang       = request.args.get("lang", "en")
    g.languages  = LANGUAGES

# ----------------------------------------------------------------------
# 7. Database setup
# ----------------------------------------------------------------------
from database import init_app as init_db_app, init_db
init_db_app(app)
with app.app_context():
    init_db()

# ----------------------------------------------------------------------
# 8. Register Blueprints
# ----------------------------------------------------------------------
from routes.auth               import auth_bp
from routes.video_tools        import video_bp
from routes.transcribe_audio   import transcribe_audio_bp
from routes.image_tools        import image_bp
from routes.edit_text          import edit_text_bp
from routes.transcribe         import transcribe_bp
from routes.utils              import utils_bp
from routes.summarize          import summarize_bp
from routes.translate          import translate_bp
from routes.generate_audio     import generate_audio_bp
from routes.admin.ads          import ads_bp
from routes.admin.analytics    import analytics_bp
from routes.admin.site_settings import settings_bp
from routes.admin.users        import users_bp
from routes.paddle             import paddle_bp
from routes.profile            import profile_bp
from routes.mollie             import mollie_bp

for bp in (
    auth_bp, video_bp, transcribe_audio_bp, image_bp, edit_text_bp,
    transcribe_bp, utils_bp, summarize_bp, translate_bp, generate_audio_bp,
    ads_bp, analytics_bp, settings_bp, users_bp,
    paddle_bp, profile_bp, mollie_bp
):
    app.register_blueprint(bp)

# ----------------------------------------------------------------------
# 9. Static & SPA routes
# ----------------------------------------------------------------------
@app.route("/output/<path:fn>")
def serve_output(fn):
    return send_from_directory(FOLDERS["output"], fn)

@app.route("/assets/<path:fn>")
def serve_assets(fn):
    return send_from_directory(os.path.join(FOLDERS["static"], "assets"), fn)

@app.route("/refund-policy")
def refund_policy():
    return app.send_static_file("refund-policy.html")

@app.route("/terms-and-conditions")
def terms_and_conditions():
    return app.send_static_file("terms-and-conditions.html")

@app.route("/cleanup")
def cleanup_temp():
    for key in ("uploads","audio","frames","subtitles"):
        shutil.rmtree(FOLDERS[key], ignore_errors=True)
        os.makedirs(FOLDERS[key], exist_ok=True)
    return "✅ Temporary folders cleaned."

@app.route("/")
def serve_index():
    return send_from_directory(FOLDERS["static"], "index.html")

# ----------------------------------------------------------------------
# 10. Global error handler
# ----------------------------------------------------------------------
@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error("Unhandled Exception", exc_info=e)
    code = e.code if isinstance(e, HTTPException) else 500
    return jsonify({"error": str(e)}), code

# ----------------------------------------------------------------------
# 11. File logging
# ----------------------------------------------------------------------
log_file = os.path.join(FOLDERS["logs"], "flask_errors.log")
handler  = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3)
handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s in %(pathname)s:%(lineno)d'
))
handler.setLevel(logging.ERROR)
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)
app.config["PROPAGATE_EXCEPTIONS"] = True

# ----------------------------------------------------------------------
# 12. Launch
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=not IS_PROD,
        use_reloader=False
    )
