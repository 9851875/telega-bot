#!/usr/bin/env python3
"""YouTube -> Telegram: через Invidious API (перебор серверов если один упал)"""

import os
import sys
import subprocess
import requests
import glob
import random
from datetime import datetime, timezone

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
YOUTUBE_CHANNEL_ID = "@Informator-today"
LAST_VIDEO_FILE = "last_video_id.txt"

INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://invidious.lunar.icu",
    "https://inv.tux.pizza",
    "https://invidious.privacyredirect.com",
    "https://yewtu.be",
    "https://invidious.fdn.fr",
    "https://vid.puffyan.us",
]

def find_daily_news_video():
    """Перебираем Invidious сервера пока не найдём видео"""
    random.shuffle(INVIDIOUS_INSTANCES)
    for instance in INVIDIOUS_INSTANCES:
        url = f"{instance}/api/v1/channels/{YOUTUBE_CHANNEL_ID}/videos"
        print(f"🔍 Пробуем: {instance}")
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                print(f"   ❌ HTTP {resp.status_code}")
                continue
            data = resp.json()
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            continue
        
        if 'videos' not in data:
            print("   ❌ Нет videos в ответе")
            continue
        
        for v in data['videos']:
            title = v.get('title', '')
            if 'Новости Сегодня' in title:
                video_id = v['videoId']
                print(f"   ✅ Найдено: {title}")
                return {"title": title, "id": video_id, "url": f"https://www.youtube.com/watch?v={video_id}"}
        print("   ❌ Видео не найдено в выдаче")
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
    ua_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    ]
    for attempt in range(3):
        ua = random.choice(ua_list)
        cmd = ["yt-dlp", "-f", "best[height<=1080]", "-o", output_template,
               "--user-agent", ua, "--no-warnings", "--max-filesize", "2000M",
               "--extractor-retries", "5", "--retries", "5", video_url]
        print(f"📥 Попытка {attempt+1}/3...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            files = glob.glob("video.*")
            if files:
                return files[0]
        else:
            print(f"   ⚠️ {result.stderr[:200]}")
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
        print("❌ Ни один сервер не вернул видео. Выход.")
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
