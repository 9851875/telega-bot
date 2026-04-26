#!/usr/bin/env python3
"""YouTube -> Telegram: пересылка последнего видео "Новости Сегодня" из канала @Informator-today"""

import os
import sys
import json
import subprocess
import requests
import glob
from datetime import datetime, timezone

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
YOUTUBE_CHANNEL = "https://www.youtube.com/@Informator-today"
LAST_VIDEO_FILE = "last_video_id.txt"

def find_daily_news_video(channel_url):
    cmd = [
        "yt-dlp", "--flat-playlist", "--print", "%(title)s|||%(id)s|||%(url)s",
        "--playlist-end", "15", "--no-warnings", f"{channel_url}/videos"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ yt-dlp ошибка: {result.stderr}")
        return None
    for line in result.stdout.strip().split('\n'):
        if not line: continue
        parts = line.split('|||')
        if len(parts) != 3: continue
        title, video_id, url = parts
        if "Новости Сегодня" in title:
            print(f"✅ Найдено: {title}")
            return {"title": title, "id": video_id, "url": url}
    print("❌ Видео 'Новости Сегодня' не найдено")
    return None

def load_last_video_id():
    try:
        with open(LAST_VIDEO_FILE, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def save_last_video_id(video_id):
    with open(LAST_VIDEO_FILE, 'w') as f:
        f.write(video_id)

def download_video(video_url):
    output_template = "video.%(ext)s"
    cmd = ["yt-dlp", "-f", "best[height<=1080]", "-o", output_template, "--no-warnings", "--max-filesize", "2000M", video_url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Ошибка скачивания: {result.stderr}")
        return None
    files = glob.glob("video.*")
    return files[0] if files else None

def send_to_telegram(video_path, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    with open(video_path, 'rb') as video_file:
        files = {'video': video_file}
        data = {'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}
        response = requests.post(url, data=data, files=files, timeout=300)
    result = response.json()
    if result.get('ok'):
        print(f"✅ Видео отправлено в канал")
        return True
    else:
        print(f"❌ Ошибка отправки: {result}")
        return False

def main():
    print("=" * 50)
    print(f"🕐 Запуск: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 50)
    video = find_daily_news_video(YOUTUBE_CHANNEL)
    if not video:
        print("❌ Нет подходящего видео. Выход.")
        return
    last_id = load_last_video_id()
    if video['id'] == last_id:
        print(f"⚠️ Видео {video['id']} уже было отправлено. Выход.")
        return
    print(f"📥 Скачиваю: {video['title']}")
    video_path = download_video(video['url'])
    if not video_path:
        print("❌ Не удалось скачать видео")
        sys.exit(1)
    caption = f"{video['title']}\n\nИсточник: {YOUTUBE_CHANNEL}"
    if send_to_telegram(video_path, caption):
        save_last_video_id(video['id'])
        print(f"💾 Сохранён ID видео: {video['id']}")
    os.remove(video_path)
    print("🧹 Временный файл удалён")
    print("=" * 50)
    print("✅ Готово!")

if __name__ == "__main__":
    main()
