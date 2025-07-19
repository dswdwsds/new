import os
import re
import json
import time
import base64
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import cloudscraper
from notifier import send_discord_notification

# إعداد GitHub و Discord
access_token = os.getenv("ACCESS_TOKEN")

repo_name = "abdo12249/1"
remote_folder = "test1/episodes"
repo_name_log = "abdo12249/test"
missing_anime_log_filename = "missing_anime_log.json"

BASE_URL = "https://4i.nxdwle.shop"
EPISODE_LIST_URL = BASE_URL + "/episode/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
scraper = cloudscraper.create_scraper()

def to_id_format(text):
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9()!\- ]", "", text.replace(":", ""))
    return text.replace(" ", "-")

def get_episode_links():
    print("📄 تحميل صفحة الحلقات...")
    response = scraper.get(EPISODE_LIST_URL, headers=HEADERS)
    if response.status_code != 200:
        print("❌ فشل تحميل الصفحة")
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    return [a.get("href") for a in soup.select(".episodes-card-title a") if a.get("href", "").startswith("http")]

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
    log_data, sha = [], None

    if response.status_code == 200:
        sha = response.json().get("sha")
        try:
            content_decoded = base64.b64decode(response.json()["content"]).decode("utf-8")
            log_data = json.loads(content_decoded)
        except:
            print("⚠️ فشل فك تشفير أو تحليل ملف السجل الحالي.")
    elif response.status_code == 404:
        print(f"ℹ️ سيتم إنشاء ملف {missing_anime_log_filename}.")

    new_entry = {
        "anime_title": anime_title,
        "episode_link": episode_link,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if not any(item.get("anime_title") == anime_title and item.get("episode_link") == episode_link for item in log_data):
        log_data.append(new_entry)
        content_encoded = base64.b64encode(json.dumps(log_data, indent=2, ensure_ascii=False).encode()).decode()

        payload = {
            "message": f"إضافة {anime_title} إلى سجل الأنميات المفقودة",
            "content": content_encoded,
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha

        r = scraper.put(api_url, headers=headers, json=payload)
        if r.status_code in [200, 201]:
            print("✅ تم تحديث سجل الأنميات المفقودة.")
        else:
            print("❌ فشل رفع سجل الأنميات المفقودة:", r.status_code, r.text)
    else:
        print(f"ℹ️ الأنمي '{anime_title}' موجود مسبقًا، تم التخطي.")

def update_new_json_list(new_anime_filename):
    new_json_url = f"https://abdo12249.github.io/1/test1/episodes/{new_anime_filename}"
    api_url = f"https://api.github.com/repos/{repo_name}/contents/test1/الجديد.json"
    headers = {"Authorization": f"token {access_token}"}

    response = scraper.get(api_url, headers=headers)
    sha, data = None, {"animes": []}

    if response.status_code == 200:
        sha = response.json().get("sha")
        try:
            content_decoded = base64.b64decode(response.json()["content"]).decode("utf-8")
            data = json.loads(content_decoded)
        except Exception as e:
            print("⚠️ فشل قراءة محتوى الجديد.json:", str(e))

    if new_json_url not in data["animes"]:
        data["animes"].append(new_json_url)
        encoded_content = base64.b64encode(json.dumps(data, indent=2, ensure_ascii=False).encode()).decode()

        payload = {
            "message": f"تحديث الجديد.json بإضافة {new_anime_filename}",
            "content": encoded_content,
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha

        r = scraper.put(api_url, headers=headers, json=payload)
        if r.status_code in [200, 201]:
            print("📄 تم تحديث الجديد.json ✅")
        else:
            print("❌ فشل تحديث الجديد.json:", r.status_code, r.text)
    else:
        print("ℹ️ الرابط موجود مسبقًا، تم التخطي.")

def save_to_json(anime_title, episode_number, episode_title, servers):
    anime_id = to_id_format(anime_title)
    filename = anime_id + ".json"
    api_url = f"https://api.github.com/repos/{repo_name}/contents/{remote_folder}/{filename}"
    headers = {"Authorization": f"token {access_token}"}
    exists, github_data = check_episode_on_github(anime_title)

    ep_data = {
        "number": int(episode_number) if episode_number.isdigit() else episode_number,
        "title": f"الحلقة {episode_number}",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "link": f"https://abdo12249.github.io/1/test1/المشاهده.html?id={anime_id}&episode={episode_number}",
        "image": f"https://abdo12249.github.io/1/images/{anime_id}.webp",
        "servers": servers
    }

    if not exists:
        print(f"🚀 إنشاء ملف جديد: {filename}")
        new_data = {
            "animeTitle": anime_title,
            "episodes": [ep_data]
        }
        encoded = base64.b64encode(json.dumps(new_data, indent=2, ensure_ascii=False).encode()).decode()
        payload = {
            "message": f"إنشاء {filename} - الحلقة {episode_number}",
            "content": encoded,
            "branch": "main"
        }
        r = scraper.put(api_url, headers=headers, json=payload)
        if r.status_code in [200, 201]:
            print(f"✅ تم إنشاء الملف ورفع البيانات.")
            send_discord_notification(anime_title, episode_number, ep_data["link"], ep_data["image"])
            log_missing_anime(anime_title, ep_data["link"])
            update_new_json_list(filename)
        else:
            print(f"❌ فشل رفع الملف: {r.status_code} {r.text}")
        return

    if github_data is None:
        print("⚠️ تعذر تحميل البيانات من GitHub.")
        return

    updated, found = False, False
    for i, ep in enumerate(github_data["episodes"]):
        if str(ep["number"]) == str(ep_data["number"]):
            found = True
            if ep["servers"] != ep_data["servers"]:
                github_data["episodes"][i] = ep_data
                updated = True
                print(f"🔄 تحديث الحلقة {episode_number} بسبب تغير السيرفرات.")
                send_discord_notification(anime_title, episode_number, ep_data["link"], ep_data["image"])
            else:
                print(f"⚠️ الحلقة {episode_number} لم تتغير، تم التخطي.")
            break

    if not found:
        github_data["episodes"].append(ep_data)
        updated = True
        print(f"➕ إضافة الحلقة {episode_number}.")
        send_discord_notification(anime_title, episode_number, ep_data["link"], ep_data["image"])

    if updated:
        content = json.dumps(github_data, indent=2, ensure_ascii=False)
        encoded = base64.b64encode(content.encode()).decode()
        sha_response = scraper.get(api_url, headers=headers)
        sha = sha_response.json().get("sha") if sha_response.status_code == 200 else None

        payload = {
            "message": f"تحديث {filename} - الحلقة {episode_number}",
            "content": encoded,
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha

        r = scraper.put(api_url, headers=headers, json=payload)
        if r.status_code in [200, 201]:
            print("🚀 تم رفع التحديث إلى GitHub.")
        else:
            print("❌ فشل رفع التحديث:", r.status_code, r.text)

# --------- بدء التنفيذ ---------
if __name__ == "__main__":
    all_links = get_episode_links()
    for idx, link in enumerate(all_links):
        print(f"\n🔢 حلقة {idx+1}/{len(all_links)}")
        anime_name, episode_number, full_title, server_list = get_episode_data(link)
        if anime_name and server_list:
            save_to_json(anime_name, episode_number, full_title, server_list)
        else:
            print("❌ تخطيت الحلقة بسبب خطأ.")
        time.sleep(1)
