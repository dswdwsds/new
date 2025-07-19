import cloudscraper
from bs4 import BeautifulSoup
import time
import json
import re
from datetime import datetime
import os
import base64
import requests
# تأكد أن 'notifier' متاح في بيئة GitHub Actions الخاصة بك
# من المفترض أنك قمت بتضمين الكود الخاص بـ send_discord_notification في ملف notifier.py
from notifier import send_discord_notification

# إعداد GitHub و Discord
access_token = os.getenv("ACCESS_TOKEN")

repo_name = "abdo12249/1"
remote_folder = "test1/episodes"

# إعدادات ملف السجل للأنميات المفقودة
repo_name_log = "abdo12249/test" # يمكن تغيير هذا المستودع إذا لزم الأمر
missing_anime_log_filename = "missing_anime_log.json"

BASE_URL = "https://4i.nxdwle.shop"
EPISODE_LIST_URL = BASE_URL + "/episode/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

scraper = cloudscraper.create_scraper()

def to_id_format(text):
    text = text.strip().lower()
    text = text.replace(":", "")
    # تم تصحيح التعبير العادي: تم نقل الواصلة إلى نهاية مجموعة الأحرف
    text = re.sub(r"[^a-z0-9()! -]", "", text)
    return text.replace(" ", "-")

def get_episode_links():
    print("📄 تحميل صفحة الحلقات...")
    response = scraper.get(EPISODE_LIST_URL, headers=HEADERS)
    if response.status_code != 200:
        print(f"❌ فشل تحميل الصفحة. الكود: {response.status_code}")
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
                try:
                    return True, r.json()
                except json.JSONDecodeError:
                    print(f"⚠️ فشل تحليل JSON لملف {filename} من GitHub.")
                    return True, None # الملف موجود لكن لا يمكن قراءته كـ JSON صالح
            else:
                print(f"❌ فشل تنزيل محتوى {filename} من GitHub. الكود: {r.status_code}")
                return True, None # الملف موجود لكن لا يمكن تنزيله
        return True, None # الملف موجود لكن لا يوجد download_url
    elif response.status_code == 404:
        return False, None
    else:
        print(f"❌ فشل التحقق من وجود الملف على GitHub: {response.status_code} {response.text}")
        return False, None

def get_episode_data(episode_url):
    response = scraper.get(episode_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"❌ فشل جلب بيانات الحلقة من {episode_url}. الكود: {response.status_code}")
        return None, None, None, None
    soup = BeautifulSoup(response.text, "html.parser")
    h3 = soup.select_one("div.main-section h3")
    full_title = h3.get_text(strip=True) if h3 else "غير معروف"

    anime_title = "غير معروف"
    episode_number = "غير معروف"

    # البحث عن "الحلقة" بأي طريقة كتابة (الحلقة، حلقه)
    match = re.search(r"(الحلقة|حلقه)\s*(\d+)", full_title)
    if match:
        anime_title_parts = full_title.rsplit(match.group(0), 1)
        anime_title = anime_title_parts[0].strip()
        episode_number = match.group(2).strip()
    else:
        # إذا لم يتم العثور على كلمة "الحلقة" أو "حلقه"، اعتبر العنوان بالكامل هو عنوان الأنمي
        anime_title = full_title.strip()
        # يمكننا محاولة استخلاص رقم من النهاية إذا كان موجودًا
        num_match = re.search(r'(\d+)$', anime_title)
        if num_match:
            episode_number = num_match.group(1)
            anime_title = anime_title.rsplit(episode_number, 1)[0].strip()
        else:
            episode_number = "1" # افتراضيًا الحلقة 1 إذا لم يتم العثور على رقم

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
    """
    تسجيل الأنميات التي لم يكن لها ملف JSON موجود وتم إنشاؤه حديثًا.
    """
    api_url = f"https://api.github.com/repos/{repo_name_log}/contents/{missing_anime_log_filename}"
    headers = {"Authorization": f"token {access_token}"}

    # محاولة جلب ملف السجل الحالي
    response = scraper.get(api_url, headers=headers)
    log_data = []
    sha = None

    if response.status_code == 200:
        sha = response.json().get("sha")
        try:
            content_decoded = base64.b64decode(response.json().get("content")).decode("utf-8")
            log_data = json.loads(content_decoded)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"⚠️ فشل فك تشفير أو تحليل ملف السجل الحالي: {e}. سيتم إنشاء ملف جديد.")
            log_data = []
    elif response.status_code == 404:
        print(f"ℹ️ ملف السجل {missing_anime_log_filename} غير موجود على GitHub. سيتم إنشاؤه.")
    else:
        print(f"❌ فشل جلب ملف السجل من GitHub: {response.status_code} {response.text}")
        return # لا يمكن المتابعة إذا فشل الجلب بشكل كامل

    # إضافة الإدخال الجديد إذا لم يكن موجودًا بالفعل
    new_entry = {
        "anime_title": anime_title,
        "episode_link": episode_link,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # التحقق مما إذا كان الإدخال موجودًا بالفعل لتجنب التكرار
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

        r = scraper.put(api_url, headers=headers, json=payload)
        if r.status_code in [200, 201]:
            print(f"✅ تم تحديث سجل الأنميات المفقودة في {missing_anime_log_filename} على GitHub.")
        else:
            print(f"❌ فشل رفع سجل الأنميات المفقودة إلى GitHub: {r.status_code} {r.text}")
    else:
        print(f"ℹ️ الأنمي '{anime_title}' موجود بالفعل في سجل الأنميات المفقودة. تم التخطي.")

def update_new_json_list(new_anime_filename):
    """
    تحديث ملف الجديد.json عند إنشاء ملف جديد لأنمي.
    """
    new_json_url = f"https://abdo12249.github.io/1/test1/episodes/{new_anime_filename}"
    api_url = f"https://api.github.com/repos/{repo_name}/contents/test1/الجديد.json"
    headers = {"Authorization": f"token {access_token}"}

    # جلب المحتوى الحالي
    response = scraper.get(api_url, headers=headers)
    sha = None
    data = {"animes": []}

    if response.status_code == 200:
        sha = response.json().get("sha")
        try:
            content_decoded = base64.b64decode(response.json().get("content")).decode("utf-8")
            data = json.loads(content_decoded)
        except Exception as e:
            print(f"⚠️ فشل قراءة محتوى الجديد.json: {str(e)}. سيتم إنشاء ملف جديد أو استبدال المحتوى.")
            # إذا فشل التحليل، نبدأ ببيانات فارغة لتجنب الأخطاء
            data = {"animes": []}
        
    elif response.status_code == 404:
        print("📁 سيتم إنشاء ملف الجديد.json جديد.")
    else:
        print(f"❌ فشل جلب ملف الجديد.json من GitHub: {response.status_code} {response.text}")
        return # لا يمكن المتابعة إذا فشل الجلب بشكل كامل

    # تحقق من وجود الرابط لتجنب التكرار
    if new_json_url not in data["animes"]:
        data["animes"].append(new_json_url)
        content_to_upload = json.dumps(data, indent=2, ensure_ascii=False)
        encoded_content = base64.b64encode(content_to_upload.encode("utf-8")).decode()

        payload = {
            "message": f"تحديث ملف الجديد.json بإضافة {new_anime_filename}",
            "content": encoded_content,
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha

        r = scraper.put(api_url, headers=headers, json=payload)
        if r.status_code in [200, 201]:
            print("📄 تم تعديل الجديد.json ✅")
        else:
            print(f"❌ فشل تعديل الجديد.json: {r.status_code} {r.text}")
    else:
        print("ℹ️ الرابط موجود مسبقًا في الجديد.json، تم التخطي.")


def save_to_json(anime_title, episode_number, full_title, servers):
    anime_id = to_id_format(anime_title)
    filename = anime_id + ".json"
    api_url = f"https://api.github.com/repos/{repo_name}/contents/{remote_folder}/{filename}"
    headers = {"Authorization": f"token {access_token}"}
    exists_on_github, github_data = check_episode_on_github(anime_title)

    # التعديل هنا: استخدام "الحلقة " + episode_number كعنوان
    ep_data = {
        "number": int(episode_number) if str(episode_number).isdigit() else episode_number,
        "title": f"الحلقة {episode_number}", # تم التعديل ليظهر "الحلقة X" فقط
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "link": f"https://abdo12249.github.io/1/test1/المشاهده.html?id={anime_id}&episode={episode_number}",
        "image": f"https://abdo12249.github.io/1/images/{anime_id}.webp", # تأكد من وجود صورة بهذا الاسم أو قم بتغيير المسار
        "servers": servers
    }

    if not exists_on_github:
        print(f"🚀 إنشاء ملف جديد للأنمي: {filename}")
        new_data = {
            "animeTitle": anime_title,
            "episodes": [ep_data]
        }
        content = json.dumps(new_data, indent=2, ensure_ascii=False)
        encoded = base64.b64encode(content.encode("utf-8")).decode()
        payload = {
            "message": f"إنشاء ملف {filename} مع الحلقة {episode_number}",
            "content": encoded,
            "branch": "main"
        }
        r = scraper.put(api_url, headers=headers, json=payload)
        if r.status_code in [200, 201]:
            print(f"✅ تم إنشاء الملف ورفع البيانات على GitHub.")
            send_discord_notification(anime_title, episode_number, ep_data["link"], ep_data["image"])
            log_missing_anime(anime_title, ep_data["link"])
            update_new_json_list(filename)
        else:
            print(f"❌ فشل إنشاء الملف على GitHub: {r.status_code} {r.text}")
        return

    # إذا كان الملف موجودًا ولكن بياناته فارغة أو غير صالحة، نبدأ من جديد
    if github_data is None or not isinstance(github_data, dict) or "episodes" not in github_data:
        print(f"⚠️ ملف {filename} موجود على GitHub ولكن بياناته غير صالحة. سيتم إعادة تهيئته.")
        github_data = {
            "animeTitle": anime_title,
            "episodes": [ep_data]
        }
        updated = True
        send_discord_notification(anime_title, episode_number, ep_data["link"], ep_data["image"])
    else:
        updated = False
        episode_found = False

        for i, ep in enumerate(github_data["episodes"]):
            if str(ep.get("number")) == str(ep_data["number"]):
                episode_found = True
                # تحقق إذا كانت السيرفرات أو العنوان قد تغير
                # هنا يجب أن نتحقق من أن العنوان أيضاً يتطابق مع النمط الجديد "الحلقة X"
                expected_title_in_json = f"الحلقة {episode_number}"
                if ep["servers"] != ep_data["servers"] or ep.get("title") != expected_title_in_json:
                    github_data["episodes"][i] = ep_data
                    updated = True
                    print(f"🔄 تم تحديث الحلقة {episode_number} لأن السيرفرات أو العنوان تغير.")
                    send_discord_notification(anime_title, episode_number, ep_data["link"], ep_data["image"])
                else:
                    print(f"⚠️ الحلقة {episode_number} موجودة بنفس البيانات، تم تخطيها.")
                break # بما أننا وجدنا الحلقة، نخرج من الحلقة الداخلية ونكمل لرفع التحديث (إذا وجد)
        
        if not episode_found:
            github_data["episodes"].append(ep_data)
            updated = True
            print(f"➕ تم إضافة الحلقة {episode_number} الجديدة.")
            send_discord_notification(anime_title, episode_number, ep_data["link"], ep_data["image"])
    
    if updated:
        # تأكد من ترتيب الحلقات بعد الإضافة أو التحديث
        # هذا يضمن أن الحلقات مرتبة رقميًا في ملف JSON
        github_data["episodes"].sort(key=lambda x: int(x["number"]) if str(x["number"]).isdigit() else float('inf'))

        content = json.dumps(github_data, indent=2, ensure_ascii=False)
        encoded = base64.b64encode(content.encode("utf-8")).decode()

        # جلب SHA الأخير قبل الرفع لتجنب خطأ التضارب
        sha_response = scraper.get(api_url, headers=headers)
        sha = sha_response.json().get("sha") if sha_response.status_code == 200 else None

        payload = {
            "message": f"تحديث {filename} - إضافة/تحديث الحلقة {episode_number}",
            "content": encoded,
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha

        r = scraper.put(api_url, headers=headers, json=payload)
        if r.status_code in [200, 201]:
            print(f"🚀 تم رفع التحديث إلى GitHub بنجاح.")
        else:
            print(f"❌ فشل رفع التحديث إلى GitHub: {r.status_code} {r.text}")


# التنفيذ الرئيسي
def main():
    print("بدء عملية فحص الحلقات الجديدة...")
    all_links = get_episode_links()
    
    if not all_links:
        print("لا توجد روابط حلقات جديدة تم العثور عليها. إنهاء العملية.")
        return

    for idx, link in enumerate(all_links):
        print(f"\n--- معالجة الحلقة {idx+1}/{len(all_links)} ---")
        anime_name, episode_number, full_title, server_list = get_episode_data(link)
        
        if anime_name and episode_number and server_list:
            save_to_json(anime_name, episode_number, full_title, server_list)
        else:
            print(f"❌ تخطيت الحلقة {link} بسبب خطأ في استخلاص البيانات.")
        time.sleep(1) # تأخير لتجنب حظر IP أو تجاوز حدود معدل الطلبات

    print("\n✅ انتهت عملية فحص الحلقات.")

if __name__ == "__main__":
    main()
