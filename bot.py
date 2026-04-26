#!/usr/bin/env python3
"""YouTube -> Telegram: через invidious/yewtu.be зеркала без кукисов"""

import os
import sys
import subprocess
import requests
import glob
import json
import random
from datetime import datetime, timezone

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
YOUTUBE_CHANNEL_ID = "@Informator-today"
LAST_VIDEO_FILE = "last_video_id.txt"

INVIDIOUS_INSTANCES = [
    "https://invidious.fdn.fr",
    "https://inv.nadeko.net",
    "https://invidious.privacyredirect.com",
    "https://vid.puffyan.us",
    "https://invidious.lunar.icu",
    "https://inv.tux.pizza",
]

def find_daily_news_video():
    """Найти последнее видео через Invidious API"""
    instance = random.choice(INVIDIOUS_INSTANCES)
    url = f"{instance}/api/v1/channels/{YOUTUBE_CHANNEL_ID}/videos"
    print(f"🔍 Invidious: {instance}")
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            print(f"❌ HTTP {resp.status_code}")
            return None
        videos = resp.json()
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None
    
    if not videos or 'videos' not in videos:
        print("❌ Пустой ответ")
        return None
    
    for v in videos['videos']:
        title = v.get('title', '')
        if 'Новости Сегодня' in title:
            video_id = v['videoId']
            print(f"✅ Найдено: {title}")
            return {
                "title": title,
                "id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}"
            }
    print("❌ Видео не найдено в выдаче")
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
    """Скачать через yt-dlp с несколькими попытками"""
    output_template = "video.%(ext)s"
    # Пробуем разные user-agent и форматы
    for attempt in range(3):
        ua = random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        ])
        cmd = [
            "yt-dlp",
            "-f", "best[height<=1080]",
            "-o", output_template,
            "--user-agent", ua,
            "--no-warnings",
            "--max-filesize", "2000M",
            "--extractor-retries", "5",
            "--retries", "5",
            video_url
        ]
        print(f"📥 Попытка {attempt+1}/3...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            files = glob.glob("video.*")
            if files:
                return files[0]
        else:
            print(f"⚠️ Ошибка: {result.stderr[:300]}")
    return None

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
    video = find_daily_news_video()
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
    caption = f"{video['title']}\n\nИсточник: {YOUTUBE_CHANNEL_ID}"
    if send_to_telegram(video_path, caption):
        save_last_video_id(video['id'])
        print(f"💾 Сохранён ID видео: {video['id']}")
    os.remove(video_path)
    print("🧹 Временный файл удалён")
    print("=" * 50)
    print("✅ Готово!")

if __name__ == "__main__":
    main()
