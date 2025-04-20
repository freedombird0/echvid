import os
from flask import Blueprint, jsonify, current_app
from flask_cors import cross_origin

generate_video_bp = Blueprint("generate_video", __name__, url_prefix="/api/generate-video")

@generate_video_bp.route("/", methods=["POST"])
@cross_origin(origins="http://localhost:5173", supports_credentials=True)
def generate_video():
    current_app.logger.debug(">>> Entered generate_video endpoint (Disabled)")
    return jsonify({
        "message": "Video generation is under development. Please check back soon."
    }), 200
