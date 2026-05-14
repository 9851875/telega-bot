#!/usr/bin/env python3
"""YouTube -> Telegram: отправка ссылки на самое свежее новостное видео"""

import os
import sys
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
YOUTUBE_CHANNEL_ID = "UC_zpuqpjmFZfKq4E-rMGBvw"
LAST_VIDEO_FILE = "last_video_id.txt"

# Ключевые слова для поиска новостных видео
SEARCH_PATTERNS = ["Сегодня Новости", "Новости Дня"]

def find_daily_news_video():
    """Найти САМОЕ СВЕЖЕЕ видео по ключевым словам"""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={YOUTUBE_CHANNEL_ID}"
    print(f"🔍 RSS: {rss_url}")
    try:
        resp = requests.get(rss_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        print(f"   HTTP {resp.status_code}")
        if resp.status_code != 200:
            return None
    except Exception as e:
        print(f"   ❌ {e}")
        return None
    
    root = ET.fromstring(resp.content)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    
    # Собираем ВСЕ видео, которые подходят под паттерны
    matched = []
    for entry in root.findall("atom:entry", ns):
        title = entry.find("atom:title", ns).text
        video_url = entry.find("atom:link", ns).attrib["href"]
        video_id = entry.find("atom:id", ns).text.split(":")[-1]
        published = entry.find("atom:published", ns).text
        
        for pattern in SEARCH_PATTERNS:
            if pattern in title:
                matched.append({
                    "title": title, "id": video_id, "url": video_url, "date": published
                })
                break
    
    print(f"   Найдено совпадений: {len(matched)}")
    
    if not matched:
        print("   ❌ Ни одно видео не подошло. Последние заголовки:")
        for entry in root.findall("atom:entry", ns)[:5]:
            print(f"      - {entry.find('atom:title', ns).text}")
        return None
    
    # Берём самое свежее (первое в RSS = самое новое)
    best = matched[0]
    print(f"   ✅ Самое свежее: {best['title']} (дата: {best['date']})")
    return {"title": best['title'], "id": best['id'], "url": best['url']}

def load_last_video_id():
    try:
        with open(LAST_VIDEO_FILE, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def save_last_video_id(video_id):
    with open(LAST_VIDEO_FILE, 'w') as f:
        f.write(video_id)

def send_link_to_telegram(title, video_url):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    text = f"📰 {title}\n\n{video_url}"
    data = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': 'false'
    }
    response = requests.post(url, data=data, timeout=30)
    result = response.json()
    if result.get('ok'):
        print(f"✅ Ссылка отправлена в канал")
        return True
    else:
        print(f"❌ Ошибка: {result}")
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
    
    if send_link_to_telegram(video['title'], video['url']):
        save_last_video_id(video['id'])
        print(f"💾 Сохранён ID видео: {video['id']}")
    
    print("=" * 50)
    print("✅ Готово!")

if __name__ == "__main__":
    main()
