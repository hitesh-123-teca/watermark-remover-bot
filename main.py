import os
import cv2
import tempfile
import subprocess
from pyrogram import Client, filters
from pyrogram.types import Message
from PIL import Image, ImageDraw, ImageFont
import pytesseract
from pytesseract import Output

# Environment variable se token le rahe hain
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("watermark_remover_bot", bot_token=BOT_TOKEN)

def extract_frames(video_path, num_frames=5):
    """Extract first few frames from video"""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_interval = max(1, total_frames // num_frames)

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
    for i in range(len(d['text'])):
        if int(d['conf'][i]) > 50:  # Confidence > 50%
            text = d['text'][i].strip()
            if text:
                x, y, w, h = d['left'][i], d['top'][i], d['width'][i], d['height'][i]
                boxes.append((x, y, w, h, text))
    return boxes

def apply_blur_on_boxes(frame, boxes):
    """Apply strong blur on detected text boxes"""
    for (x, y, w, h, text) in boxes:
        roi = frame[y:y+h, x:x+w]
        blurred_roi = cv2.GaussianBlur(roi, (99, 99), 30)
        frame[y:y+h, x:x+w] = blurred_roi
    return frame

def process_video(input_path, output_path, blur_boxes_list):
    """Process entire video and apply blur on detected regions"""
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Apply blur if boxes were detected in first few frames
        if frame_idx < len(blur_boxes_list):
            frame = apply_blur_on_boxes(frame, blur_boxes_list[frame_idx])

        out.write(frame)
        frame_idx += 1

    cap.release()
    out.release()

@app.on_message(filters.video | filters.document & filters.regex(r'.*\.(mp4|mkv|avi|mov)$'))
async def handle_video(client: Client, message: Message):
    if not message.video and not message.document:
        await message.reply_text("❌ Please send a video file.")
        return

    # Download video
    await message.reply_text("📥 Downloading video...")
    video_path = await message.download()

    # Extract frames and detect text
    frames = extract_frames(video_path, num_frames=5)
    blur_boxes_list = []
    for frame in frames:
        boxes = detect_text_bounding_boxes(frame)
        blur_boxes_list.extend(boxes)

    if not blur_boxes_list:
        await message.reply_text("✅ No text detected — no processing needed.")
        os.remove(video_path)
        return

    # Process entire video
    output_path = tempfile.mktemp(suffix=".mp4")
    await message.reply_text("🎬 Processing video...")
    process_video(video_path, output_path, [blur_boxes_list[:]] * 100)  # Simulate for all frames

    # Send processed video
    await message.reply_video(video=output_path, caption="✅ Watermark removed!")
    
    # Cleanup
    os.remove(video_path)
    os.remove(output_path)

app.run()
