import os
import requests
from datetime import datetime

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DISCORD_USER_NAME = "Anime(AMK4UP)"
DISCORD_USER_ID = "1395041371181809754"

def send_discord_notification(anime_title, episode_number, episode_link, image_url=None):
    if not DISCORD_WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK_URL غير موجود في متغيرات البيئة.")
        return

    embed = {
        "title": f"{anime_title} - الحلقة {episode_number}",
        "url": episode_link,
        "description": f"🎉 تم إصدار حلقة جديدة!\n👤 {DISCORD_USER_NAME}",
        "color": 0x1ABC9C,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    if image_url:
        embed["thumbnail"] = {"url": image_url}
        embed["image"] = {"url": image_url}

    payload = {
        "content": f"<@{DISCORD_USER_ID}>",
        "embeds": [embed],
        "allowed_mentions": {"users": [DISCORD_USER_ID]},
        "components": [
            {
                "type": 1,  # ActionRow
                "components": [
                    {
                        "type": 2,  # Button
                        "style": 5,  # Link button
                        "label": "▶️ مشاهدة",
                        "url": episode_link
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if response.status_code in [200, 204]:
            print("📢 تم إرسال إشعار إلى Discord (مع زر).")
        else:
            print(f"❌ فشل إرسال الإشعار: {response.status_code} {response.text}")
    except Exception as e:
        print(f"❌ خطأ أثناء إرسال الإشعار إلى Discord: {e}")
