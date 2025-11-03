import os
import cv2
import tempfile
from pyrogram import Client, filters
from pyrogram.types import Message
from PIL import Image
import pytesseract
from pytesseract import Output
from flask import Flask
import threading

# Environment variables (Koyeb or .env)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7852091851:AAHQr_w4hi-RuJ5sJ8JvQCo_fOZtf6EWhvk")
API_ID = os.environ.get("API_ID", "21688431")
API_HASH = os.environ.get("API_HASH", "db274cb8e9167e731d9c8305197badeb")

if not all([BOT_TOKEN, API_ID, API_HASH]):
    raise RuntimeError("Missing BOT_TOKEN, API_ID or API_HASH environment variables.")

# Initialize bot client
app = Client(
    "watermark_remover_bot",
    bot_token=BOT_TOKEN,
    api_id=int(API_ID),
    api_hash=API_HASH
)

def extract_frames(video_path, num_frames=5):
    """Extract first few frames from the video."""
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    frame_interval = max(1, total_frames // max(1, num_frames))

    frames = []
    for i in range(num_frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i * frame_interval)
        ret, frame = cap.read()
        if ret:
            frames.append(frame)
    cap.release()
    return frames

def detect_text_bounding_boxes(frame):
    """Detect text in a frame using Tesseract OCR."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    d = pytesseract.image_to_data(gray, output_type=Output.DICT)
    boxes = []
    for i, txt in enumerate(d.get('text', [])):
        try:
            conf = float(d.get('conf', [])[i])
        except Exception:
            conf = 0
        if conf > 50:
            text = str(txt).strip()
            if text:
                x, y, w, h = d['left'][i], d['top'][i], d['width'][i], d['height'][i]
                boxes.append((int(x), int(y), int(w), int(h), text))
    return boxes

def apply_blur_on_boxes(frame, boxes):
    """Apply strong blur on detected text boxes."""
    for (x, y, w, h, text) in boxes:
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(frame.shape[1], x + w), min(frame.shape[0], y + h)
        if x2 <= x1 or y2 <= y1:
            continue
        roi = frame[y1:y2, x1:x2]
        ksize = (99, 99) if roi.shape[0] > 10 and roi.shape[1] > 10 else (21, 21)
        blurred_roi = cv2.GaussianBlur(roi, ksize, 30)
        frame[y1:y2, x1:x2] = blurred_roi
    return frame

def process_video(input_path, output_path, boxes_to_apply):
    """Process the entire video and blur detected text regions."""
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = apply_blur_on_boxes(frame, boxes_to_apply)
        out.write(frame)

    cap.release()
    out.release()

@app.on_message(filters.video | filters.document)
async def handle_video(client: Client, message: Message):
    """Handle incoming video/document and remove watermarks."""
    if not (message.video or message.document):
        await message.reply_text("❌ Please send a valid video file.")
        return

    await message.reply_text("📥 Downloading video...")
    video_path = await message.download()
    if not video_path:
        await message.reply_text("⚠️ Failed to download the video.")
        return

    await message.reply_text("🔎 Scanning video for watermark text...")
    frames = extract_frames(video_path, num_frames=5)
    merged_boxes = []
    for frame in frames:
        boxes = detect_text_bounding_boxes(frame)
        for b in boxes:
            key = (b[0], b[1], b[2], b[3])
            if not any(abs(key[0]-x) < 10 and abs(key[1]-y) < 10 and abs(key[2]-w) < 10 and abs(key[3]-h) < 10 for (x, y, w, h, _) in merged_boxes):
                merged_boxes.append(b)

    if not merged_boxes:
        await message.reply_text("✅ No watermark or text detected — no changes needed.")
        os.remove(video_path)
        return

    output_path = tempfile.mktemp(suffix=".mp4")
    await message.reply_text("🎬 Processing video... (This might take some time)")
    process_video(video_path, output_path, merged_boxes)

    await message.reply_video(video=output_path, caption="✅ Watermark successfully blurred.")
    os.remove(video_path)
    os.remove(output_path)

# ---------------------------
# Koyeb Health Check Server
# ---------------------------
def run_health_server():
    health_app = Flask(__name__)

    @health_app.route('/')
    def home():
        return "OK", 200

    health_app.run(host='0.0.0.0', port=8080)

# ---------------------------
# Main entry point
# ---------------------------
if __name__ == "__main__":
    # Run Flask health-check server in background
    threading.Thread(target=run_health_server, daemon=True).start()

    print("✅ Watermark Remover Bot Started")
    app.run()
