from flask import Blueprint, request, jsonify
import os
from PIL import Image, ImageDraw, ImageFont
import uuid

image_bp = Blueprint("image_tools", __name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_FOLDER = os.path.join(BASE_DIR, "output")
FRAMES_FOLDER = os.path.join(BASE_DIR, "frames")

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(FRAMES_FOLDER, exist_ok=True)

def generate_unique_filename(prefix, ext):
    return f"{prefix}_{uuid.uuid4().hex[:8]}.{ext}"

# ✅ توليد صورة مخصصة
@image_bp.route("/api/generate-image", methods=["POST"])
def generate_image():
    try:
        data = request.get_json()

        width = int(data.get("width", 1280))
        height = int(data.get("height", 720))
        color = data.get("color", "#000000")
        transparent = data.get("transparent", False)
        text = data.get("text", "")
        font_size = int(data.get("fontSize", 32))
        position = data.get("position", "top-left").lower()

        mode = "RGBA" if transparent else "RGB"
        bg_color = (0, 0, 0, 0) if transparent else color
        image = Image.new(mode, (width, height), bg_color)

        if text.strip():
            draw = ImageDraw.Draw(image)
            try:
                font_path = os.path.join(BASE_DIR, "fonts", "arial.ttf")
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()

            text_size = draw.textsize(text, font=font)

            if position == "center":
                x = (width - text_size[0]) // 2
                y = (height - text_size[1]) // 2
            elif position == "bottom-right":
                x = width - text_size[0] - 20
                y = height - text_size[1] - 20
            else:
                x, y = 20, 20

            draw.text((x, y), text, fill="white", font=font)

        ext = "png" if transparent else "jpg"
        filename = generate_unique_filename("custom_image", ext)
        path = os.path.join(OUTPUT_FOLDER, filename)
        image.save(path)

        return jsonify({
            "message": "✅ Image generated successfully.",
            "image_url": f"/output/{filename}"
        })

    except Exception as e:
        return jsonify({"error": f"❌ Failed to generate image: {str(e)}"}), 500

# ✅ تعديل صورة موجودة بإضافة نص
@image_bp.route("/api/edit-image", methods=["POST"])
def edit_image():
    image_name = request.form.get("filename")
    text = request.form.get("text", "")
    position = request.form.get("position", "top-left")

    if not image_name:
        return jsonify({"error": "Filename is required."}), 400

    try:
        path = os.path.join(FRAMES_FOLDER, image_name)
        if not os.path.exists(path):
            return jsonify({"error": "Image not found."}), 404

        image = Image.open(path).convert("RGBA")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        width, height = image.size
        text_size = draw.textsize(text, font=font)

        if position == "center":
            x = (width - text_size[0]) // 2
            y = (height - text_size[1]) // 2
        elif position == "bottom-right":
            x = width - text_size[0] - 10
            y = height - text_size[1] - 10
        else:
            x, y = 10, 10

        draw.text((x, y), text, fill="white", font=font)

        edited_filename = generate_unique_filename("edited", "png")
        edited_path = os.path.join(OUTPUT_FOLDER, edited_filename)
        image.save(edited_path)

        return jsonify({
            "message": "✅ Text added to image.",
            "image_url": f"/output/{edited_filename}"
        })

    except Exception as e:
        return jsonify({"error": f"❌ Failed to edit image: {str(e)}"}), 500

# ✅ عرض الصور المتوفرة في مجلد frames
@image_bp.route("/api/list-frames")
def list_frames():
    try:
        frames = [f for f in os.listdir(FRAMES_FOLDER) if f.lower().endswith((".jpg", ".png"))]
        return jsonify({"frames": frames})
    except Exception as e:
        return jsonify({"error": f"❌ Failed to list frames: {str(e)}"}), 500

# ✅ حذف صورة من frames
@image_bp.route("/api/delete-frame/<filename>", methods=["DELETE"])
def delete_frame(filename):
    path = os.path.join(FRAMES_FOLDER, filename)
    if not os.path.exists(path):
        return jsonify({"error": "Image not found."}), 404
    os.remove(path)
    return jsonify({"message": "✅ Image deleted successfully."})