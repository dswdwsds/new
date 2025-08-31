import cloudscraper
from bs4 import BeautifulSoup
import time
import json
import re
from datetime import datetime
import os
import base64
import requests
from notifier import send_discord_notification

# إعداد GitHub و Discord
access_token = os.getenv("ACCESS_TOKEN")
repo_name = "abdo12249/1"
remote_folder = "test1/episodes"

# إعدادات ملف السجل للأنميات المفقودة
repo_name_log = "abdo12249/test"
missing_anime_log_filename = "missing_anime_log.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Referer": "https://google.com/",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1"
}

scraper = cloudscraper.create_scraper()

# --------------------
# 🔹 جلب الدومين الجديد تلقائيًا
# --------------------
def get_base_url():
    start_url = "https://4i.nxdwle.shop/episode/"  # أي دومين قديم كمفتاح
    r = scraper.get(start_url, headers=HEADERS, allow_redirects=True)
    base = r.url.split("/")[0] + "//" + r.url.split("/")[2]
    print("🌐 الدومين المستخدم:", base)
    return base

BASE_URL = get_base_url()
EPISODE_LIST_URL = BASE_URL + "/episode/"

# --------------------
def to_id_format(text):
    text = text.strip().lower()
    text = text.replace(":", "")
    text = re.sub(r"[^a-z0-9()!\- ]", "", text)
    return text.replace(" ", "-")

# --------------------
# دالة لجلب الصفحة مع cookies من الصفحة الرئيسية
# --------------------
def fetch_with_cookies(url):
    # افتح الصفحة الرئيسية الأول للحصول على cookies
    home = scraper.get(BASE_URL, headers=HEADERS, allow_redirects=True)
    cookies = home.cookies
    # جلب الصفحة المطلوبة بنفس cookies
    response = scraper.get(url, headers=HEADERS, cookies=cookies, allow_redirects=True)
    return response

# --------------------
def get_episode_links():
    print("📄 تحميل صفحة الحلقات...")
    response = fetch_with_cookies(EPISODE_LIST_URL)
    print("🔗 الرابط النهائي:", response.url, "status:", response.status_code)
    if response.status_code != 200:
        print("❌ فشل تحميل الصفحة")
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    return [a.get("href") for a in soup.select(".episodes-card-title a") if a.get("href", "").startswith("http")]

# --------------------
def check_episode_on_github(anime_title):
    anime_id = to_id_format(anime_title)
    filename = anime_id + ".json"
    url = f"https://api.github.com/repos/{repo_name}/contents/{remote_folder}/{filename}"
    headers = {"Authorization": f"token {access_token}"}
    response = scraper.get(url, headers=headers)
    if response.status_code == 200:
        download_url = response.json().get("download_url")
        if download_url:
            r = scraper.get(download_url)
            if r.status_code == 200:
                return True, r.json()
        return True, None
    elif response.status_code == 404:
        return False, None
    else:
        return False, None

# --------------------
def get_episode_data(episode_url):
    response = fetch_with_cookies(episode_url)
    if response.status_code != 200:
        return None, None, None, None
    soup = BeautifulSoup(response.text, "html.parser")
    h3 = soup.select_one("div.main-section h3")
    full_title = h3.get_text(strip=True) if h3 else "غير معروف"
    if "الحلقة" in full_title:
        parts = full_title.rsplit("الحلقة", 1)
        anime_title = parts[0].strip()
        episode_number = parts[1].strip()
    else:
        anime_title = full_title
        episode_number = "غير معروف"
    servers = []
    for a in soup.select("ul#episode-servers li a"):
        name = a.get_text(strip=True)
        data_url = a.get("data-ep-url")
        if isinstance(data_url, str):
            url = data_url.strip()
            if url.startswith("//"):
                url = "https:" + url
            servers.append({"serverName": name, "url": url})
    return anime_title, episode_number, full_title, servers

# --------------------
# باقي دوال log_missing_anime, update_new_json_list, save_to_json ...
# --------------------

all_links = get_episode_links()
episodes_to_upload = {}

for idx, link in enumerate(all_links):
    print(f"\n🔢 حلقة {idx+1}/{len(all_links)}")
    anime_name, episode_number, full_title, server_list = get_episode_data(link)
    if anime_name and server_list:
        filename, updated_data, status, ep_data = save_to_json(anime_name, episode_number, full_title, server_list)
        if status in ["new", "update"]:
            episodes_to_upload[filename] = updated_data
            send_discord_notification(anime_name, episode_number, ep_data["link"], ep_data["image"])
            if status == "new":
                log_missing_anime(anime_name, ep_data["link"])
                update_new_json_list(filename)
    else:
        print("❌ تخطيت الحلقة بسبب خطأ.")
    time.sleep(1)

print("\n🚀 رفع كل الملفات إلى GitHub...")
for filename, data in episodes_to_upload.items():
    api_url = f"https://api.github.com/repos/{repo_name}/contents/{remote_folder}/{filename}"
    headers = {"Authorization": f"token {access_token}"}
    response = scraper.get(api_url, headers=headers)
    sha = response.json().get("sha") if response.status_code == 200 else None
    content = json.dumps(data, indent=2, ensure_ascii=False)
    encoded = base64.b64encode(content.encode()).decode()
    payload = {
        "message": f"رفع أو تحديث {filename}",
        "content": encoded,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha
    r = scraper.put(api_url, headers=headers, json=payload)
    if r.status_code in [200, 201]:
        print(f"✅ تم رفع {filename}")
    else:
        print(f"❌ فشل رفع {filename}: {r.status_code} {r.text}")
