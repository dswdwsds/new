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

BASE_URL = "https://4i.nxdwle.shop"
EPISODE_LIST_URL = BASE_URL + "/episode/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# تفعيل محاكي متصفح قوي لتفادي الحماية
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})


def to_id_format(text):
    text = text.strip().lower()
    text = text.replace(":", "")
    text = re.sub(r"[^a-z0-9()!\- ]", "", text)
    return text.replace(" ", "-")


def get_episode_links():
    print("📄 تحميل صفحة الحلقات...")
    response = scraper.get(EPISODE_LIST_URL, headers=HEADERS)

    print("📡 حالة الصفحة:", response.status_code)
    print("🔗 الرابط:", EPISODE_LIST_URL)

    with open("page.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("📁 تم حفظ الصفحة في page.html")

    if response.status_code != 200:
        print("❌ فشل تحميل الصفحة")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    # 🧠 البحث عن جميع الروابط داخل كروت الحلقات
    possible_selectors = [
        "div a[href*='/episode/']",  # أي رابط فيه /episode/
        "div div a[href*='4i.nxdwle.shop/episode']",  # روابط مطلقة
        "a[href*='/episode/']",  # كاحتياط
    ]

    links = []
    for selector in possible_selectors:
        found = [a.get("href") for a in soup.select(selector) if a.get("href")]
        links.extend(found)

    # إزالة التكرار
    links = list(dict.fromkeys(links))

    # تصفية الروابط للتأكد أنها فعلاً تخص الحلقات
    links = [l if l.startswith("http") else BASE_URL + l for l in links if "/episode/" in l]

    print(f"🔍 تم العثور على {len(links)} روابط.")
    print(links[:5])
    return links



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


def get_episode_data(episode_url):
    response = scraper.get(episode_url, headers=HEADERS)
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


def log_missing_anime(anime_title, episode_link):
    api_url = f"https://api.github.com/repos/{repo_name_log}/contents/{missing_anime_log_filename}"
    headers = {"Authorization": f"token {access_token}"}
    response = scraper.get(api_url, headers=headers)
    log_data = []
    sha = None

    if response.status_code == 200:
        sha = response.json().get("sha")
        try:
            content_decoded = base64.b64decode(response.json().get("content")).decode("utf-8")
            log_data = json.loads(content_decoded)
        except:
            log_data = []
    elif response.status_code != 404:
        return

    new_entry = {
        "anime_title": anime_title,
        "episode_link": episode_link,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if not any(item.get("anime_title") == anime_title and item.get("episode_link") == episode_link for item in log_data):
        log_data.append(new_entry)
        content_to_upload = json.dumps(log_data, indent=2, ensure_ascii=False)
        encoded_content = base64.b64encode(content_to_upload.encode("utf-8")).decode()
        payload = {
            "message": f"تحديث سجل الأنميات المفقودة: إضافة {anime_title}",
            "content": encoded_content,
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha
        scraper.put(api_url, headers=headers, json=payload)


def update_new_json_list(new_anime_filename):
    new_json_url = f"https://abdo12249.github.io/1/test1/episodes/{new_anime_filename}"
    api_url = f"https://api.github.com/repos/{repo_name}/contents/test1/الجديد.json"
    headers = {"Authorization": f"token {access_token}"}
    response = scraper.get(api_url, headers=headers)
    sha = None
    data = {"animes": []}

    if response.status_code == 200:
        sha = response.json().get("sha")
        try:
            content_decoded = base64.b64decode(response.json().get("content")).decode("utf-8")
            data = json.loads(content_decoded)
        except:
            data = {"animes": []}

    if new_json_url not in data["animes"]:
        data["animes"].append(new_json_url)
        content_to_upload = json.dumps(data, indent=2, ensure_ascii=False)
        encoded_content = base64.b64encode(content_to_upload.encode()).decode()
        payload = {
            "message": f"تحديث ملف الجديد.json بإضافة {new_anime_filename}",
            "content": encoded_content,
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha
        scraper.put(api_url, headers=headers, json=payload)


def save_to_json(anime_title, episode_number, episode_title, servers):
    anime_id = to_id_format(anime_title)
    filename = anime_id + ".json"
    exists_on_github, github_data = check_episode_on_github(anime_title)

    ep_data = {
        "number": int(episode_number) if episode_number.isdigit() else episode_number,
        "title": f"الحلقة {episode_number}",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "link": f"https://abdo12249.github.io/1/test1/المشاهده.html?id={anime_id}&episode={episode_number}",
        "image": f"https://abdo12249.github.io/1/images/{anime_id}.webp",
        "servers": servers
    }

    if not exists_on_github or github_data is None:
        return filename, {
            "animeTitle": anime_title,
            "episodes": [ep_data]
        }, "new", ep_data

    updated = False
    found = False
    for i, ep in enumerate(github_data["episodes"]):
        if str(ep["number"]) == str(ep_data["number"]):
            found = True
            if ep["servers"] != ep_data["servers"]:
                github_data["episodes"][i] = ep_data
                updated = True
            break
    if not found:
        github_data["episodes"].append(ep_data)
        updated = True

    if updated:
        return filename, github_data, "update", ep_data
    else:
        return None, None, "skip", None


# التنفيذ
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
