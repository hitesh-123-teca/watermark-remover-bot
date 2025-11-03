# Watermark remove bot

This repository is a deploy-ready Telegram bot that attempts to detect text/watermarks in video files using Tesseract OCR and blur those regions with OpenCV.

## Files included
- `main.py` - Bot implementation (Pyrogram). Reads BOT_TOKEN from environment.
- `requirements.txt` - Python dependencies (numpy<2 to keep OpenCV compatibility).
- `Dockerfile` - Lightweight image with Tesseract and ffmpeg preinstalled (suitable for Koyeb).
- `.env` - Example environment variables file (contains placeholders).
- `README.md` - This file.

## Quick deploy to Koyeb

1. Create a GitHub repo (or use this project) and push the code.
2. In Koyeb dashboard, create a new app and connect your GitHub repository.
3. Configure build settings (Koyeb will build the Dockerfile by default).
4. Set environment variables in the Koyeb app settings:
   - BOT_TOKEN
   - API_ID (optional for bot token mode, but useful if you later use user sessions)
   - API_HASH
5. Deploy / Redeploy the app.
6. Watch the build logs. Common issues:
   - `ImportError: numpy.core.multiarray failed to import` -> ensure `numpy<2` is present in requirements.
   - `pytesseract.pytesseract.TesseractNotFoundError` -> ensure Dockerfile installs `tesseract-ocr` (this Dockerfile does).
7. Test by sending a video to your bot in Telegram.

## Notes & Tips
- This bot applies the same detected boxes (from sample frames) across the whole video. This works well for static watermarks. Dynamic/moving watermarks may need frame-by-frame detection and more advanced inpainting techniques.
- The processing can be CPU and time intensive for large videos. Consider restricting file size or running on a more powerful plan if needed.
- Replace placeholders in `.env` or set env vars directly in Koyeb. Do NOT commit real secrets to public repos.

