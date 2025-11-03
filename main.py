import os
import cv2
import tempfile
from pyrogram import Client, filters
from pyrogram.types import Message
from PIL import Image
import pytesseract
from pytesseract import Output

# Load environment variables (Koyeb will set these)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7852091851:AAHQr_w4hi-RuJ5sJ8JvQCo_fOZtf6EWhvk")
API_ID = int(os.environ.get("API_ID", "21688431"))
API_HASH = os.environ.get("API_HASH", "db274cb8e9167e731d9c8305197badeb")

if not all([BOT_TOKEN, API_ID, API_HASH]):
    raise RuntimeError("Missing one of BOT_TOKEN, API_ID, or API_HASH.")

# ✅ FIXED: include api_id and api_hash
app = Client(
    "watermark_remover_bot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)

def extract_frames(video_path, num_frames=5):
    """Extract first few frames from video"""
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
    """Detect text in frame using Tesseract OCR"""
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
                x, y, w, h = d.get('left', [])[i], d.get('top', [])[i], d.get('width', [])[i], d.get('height', [])[i]
                boxes.append((int(x), int(y), int(w), int(h), text))
    return boxes

def apply_blur_on_boxes(frame, boxes):
    """Apply strong blur on detected text boxes"""
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
    """Process entire video and apply blur on detected regions (same boxes for all frames)"""
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

# Accept videos (video message or document with video extension)
video_filter = (filters.video | filters.document) & filters.regex(r'.*\.(mp4|mkv|avi|mov)$', flags=0)

@app.on_message(video_filter)
async def handle_video(client: Client, message: Message):
    if not message.video and not message.document:
        await message.reply_text("❌ Please send a video file.")
        return

    await message.reply_text("📥 Downloading video...")
    video_path = await message.download()

    await message.reply_text("🔎 Scanning sample frames for text (this may take a moment)...")
    frames = extract_frames(video_path, num_frames=5)
    merged_boxes = []
    for frame in frames:
        boxes = detect_text_bounding_boxes(frame)
        for b in boxes:
            key = (b[0], b[1], b[2], b[3])
            if not any(abs(key[0]-x) < 10 and abs(key[1]-y) < 10 and abs(key[2]-w) < 10 and abs(key[3]-h) < 10 for (x,y,w,h,_) in merged_boxes):
                merged_boxes.append(b)

    if not merged_boxes:
        await message.reply_text("✅ No text detected — no processing needed.")
        try:
            os.remove(video_path)
        except Exception:
            pass
        return

    output_path = tempfile.mktemp(suffix=".mp4")
    await message.reply_text("🎬 Processing video (applying blur)... This can take time depending on video length.")
    process_video(video_path, output_path, merged_boxes)

    await message.reply_video(video=output_path, caption="✅ Watermark blurred/removed.")
    try:
        os.remove(video_path)
        os.remove(output_path)
    except Exception:
        pass

if __name__ == "__main__":
    app.run()
