# Telegram Watermark Remover Bot

A Pyrogram-based bot that removes watermarks from videos by detecting text using OCR and applying blur.

## Features

- Detects English text in video frames using Tesseract OCR
- Applies strong blur on detected regions
- Re-encodes video with FFmpeg
- Optimized for deployment on Koyeb

## Deploy on Koyeb

1. Fork this repository
2. Go to [Koyeb](https://koyeb.com)
3. Create new app
4. Connect your GitHub repository
5. Add environment variable:
   - `BOT_TOKEN`: Your Telegram bot token from @BotFather
6. Deploy!

## Requirements

- Python 3.8+
- Docker
- FFmpeg
- Tesseract OCR# watermark-remover-bot
