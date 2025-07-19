import cloudscraper
from lxml import html
import json
import base64
import os
import requests
from urllib.parse import urlparse, parse_qs
from PIL import Image
from io import BytesIO

# إعدادات GitHub
access_token = os.getenv("ACCESS_TOKEN")
repo_name = "abdo12249/1"
repo_name_log = "abdo12249/test"
remote_path = "test1/animes.json"
missing_file_path = "missing_anime_log.json"
github_image_base = "https://abdo12249.github.io/1/images"

scraper = cloudscraper.create_scraper()

def extract_anime_id_from_custom_url(custom_url):
    query = parse_qs(urlparse(custom_url).query)
    return query.get("id", [None])[0]

def upload_image_to_github(image_bytes, path, commit_message):
    api_url = f"https://api.github.com/repos/{repo_name}/contents/{path}"
    headers = {"Authorization": f"token {access_token}"}

    sha = None
    check_response = scraper.get(api_url, headers=headers)
    if check_response.status_code == 200:
        try:
            sha = check_response.json().get("sha")
        except:
            pass

    encoded_content = base64.b64encode(image_bytes).decode()

    payload = {
        "message": commit_message,
        "content": encoded_content,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha

    put_response = scraper.put(api_url, headers=headers, json=payload)
    if put_response.status_code in [200, 201]:
        print(f"✅ تم رفع الصورة إلى GitHub: {path}")
    else:
        print(f"❌ فشل رفع الصورة: {put_response.status_code} {put_response.text}")

def download_and_convert_to_webp(image_url, anime_id):
    try:
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content)).convert("RGB")
            buffer = BytesIO()
            img.save(buffer, "webp")
            buffer.seek(0)

            filename = f"{anime_id}.webp"
            github_path = f"images/{filename}"
            github_url = f"{github_image_base}/{filename}"

            upload_image_to_github(buffer.getvalue(), github_path, f"رفع صورة الأنمي {anime_id}")

            return github_url
        else:
            print(f"❌ فشل تحميل الصورة: {image_url}")
            return ""
    except Exception as e:
        print(f"❌ خطأ أثناء تحميل أو تحويل الصورة: {e}")
        return ""

def fetch_anime_info(anime_id):
    anime_url = f"https://4d.qerxam.shop/anime/{anime_id}/"
    print(f"📥 فتح الصفحة: {anime_url}")
    response = scraper.get(anime_url)
    if response.status_code != 200:
        print(f"❌ فشل تحميل الصفحة: {anime_url}")
        return None

    tree = html.fromstring(response.content)

    def get_text(xpath):
        try:
            return tree.xpath(xpath)[0].text_content().strip()
        except:
            return ""

    def get_attr(xpath, attr):
        try:
            return tree.xpath(xpath)[0].attrib.get(attr, "").strip()
        except:
            return ""

    title = get_text("/html/body/div[2]/div/div/div[2]/div/h1")
    description = get_text("/html/body/div[2]/div/div/div[2]/div/p")
    original_image_url = get_attr("/html/body/div[2]/div/div/div[1]/div/img", "src")
    image_url = download_and_convert_to_webp(original_image_url, anime_id)
    tags = [tag.text_content().strip() for tag in tree.xpath("/html/body/div[2]/div/div/div[2]/div/ul/li") if tag.text_content().strip()]
    type_ = get_text("/html/body/div[2]/div/div/div[2]/div/div[1]/div[1]/div/a")
    status = get_text("/html/body/div[2]/div/div/div[2]/div/div[1]/div[3]/div/a")
    episode_count = get_text("/html/body/div[2]/div/div/div[2]/div/div[1]/div[4]/div")
    duration = get_text("/html/body/div[2]/div/div/div[2]/div/div[1]/div[5]/div")
    season = get_text("/html/body/div[2]/div/div/div[2]/div/div[1]/div[6]/div/a")
    source = get_text("/html/body/div[2]/div/div/div[2]/div/div[1]/div[7]/div")

    return {
        anime_id: {
            "title": title,
            "description": description,
            "image": image_url,
            "tags": tags,
            "type": type_,
            "status": status,
            "episodeCount": episode_count,
            "duration": duration,
            "season": season,
            "source": source
        }
    }

def upload_to_github(anime_data):
    api_url = f"https://api.github.com/repos/{repo_name}/contents/{remote_path}"
    headers = {"Authorization": f"token {access_token}"}

    response = scraper.get(api_url, headers=headers)
    current_data = {}
    sha = None

    if response.status_code == 200:
        try:
            sha = response.json()["sha"]
            content_decoded = base64.b64decode(response.json()["content"]).decode("utf-8")
            current_data = json.loads(content_decoded)
        except Exception as e:
            print("⚠️ فشل قراءة animes.json:", str(e))
    elif response.status_code == 404:
        print("📁 سيتم إنشاء ملف animes.json جديد.")
    else:
        print("❌ خطأ غير متوقع أثناء جلب animes.json:", response.status_code)
        return

    updated = False
    for anime_id, info in anime_data.items():
        if anime_id not in current_data:
            print(f"➕ إضافة أنمي جديد: {anime_id}")
            current_data[anime_id] = info
            updated = True
        else:
            print(f"ℹ️ الأنمي موجود مسبقًا: {anime_id} (تم التخطي)")

    if not updated:
        print("✅ لا توجد بيانات جديدة لإضافتها.")
        return

    new_content = json.dumps(current_data, ensure_ascii=False, indent=2)
    encoded_content = base64.b64encode(new_content.encode()).decode()
import cloudscraper
from lxml import html
import json
import base64
import os
import requests
from urllib.parse import urlparse, parse_qs
from PIL import Image
from io import BytesIO

# إعدادات GitHub
access_token = os.getenv("ACCESS_TOKEN")
repo_name = "abdo12249/1"
repo_name_log = "abdo12249/test"
remote_path = "test1/animes.json"
missing_file_path = "missing_anime_log.json"
github_image_base = "https://abdo12249.github.io/1/images"

scraper = cloudscraper.create_scraper()

def extract_anime_id_from_custom_url(custom_url):
    query = parse_qs(urlparse(custom_url).query)
    return query.get("id", [None])[0]

def upload_image_to_github(image_bytes, path, commit_message):
    api_url = f"https://api.github.com/repos/{repo_name}/contents/{path}"
    headers = {"Authorization": f"token {access_token}"}

    sha = None
    check_response = scraper.get(api_url, headers=headers)
    if check_response.status_code == 200:
        try:
            sha = check_response.json().get("sha")
        except:
            pass

    encoded_content = base64.b64encode(image_bytes).decode()

    payload = {
        "message": commit_message,
        "content": encoded_content,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha

    put_response = scraper.put(api_url, headers=headers, json=payload)
    if put_response.status_code in [200, 201]:
        print(f"✅ تم رفع الصورة إلى GitHub: {path}")
    else:
        print(f"❌ فشل رفع الصورة: {put_response.status_code} {put_response.text}")

def download_and_convert_to_webp(image_url, anime_id):
    try:
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content)).convert("RGB")
            buffer = BytesIO()
            img.save(buffer, "webp")
            buffer.seek(0)

            filename = f"{anime_id}.webp"
            github_path = f"images/{filename}"
            github_url = f"{github_image_base}/{filename}"

            upload_image_to_github(buffer.getvalue(), github_path, f"رفع صورة الأنمي {anime_id}")

            return github_url
        else:
            print(f"❌ فشل تحميل الصورة: {image_url}")
            return ""
    except Exception as e:
        print(f"❌ خطأ أثناء تحميل أو تحويل الصورة: {e}")
        return ""

def fetch_anime_info(anime_id):
    anime_url = f"https://4d.qerxam.shop/anime/{anime_id}/"
    print(f"📥 فتح الصفحة: {anime_url}")
    response = scraper.get(anime_url)
    if response.status_code != 200:
        print(f"❌ فشل تحميل الصفحة: {anime_url}")
        return None

    tree = html.fromstring(response.content)

    def get_text(xpath):
        try:
            return tree.xpath(xpath)[0].text_content().strip()
        except:
            return ""

    def get_attr(xpath, attr):
        try:
            return tree.xpath(xpath)[0].attrib.get(attr, "").strip()
        except:
            return ""

    title = get_text("/html/body/div[2]/div/div/div[2]/div/h1")
    description = get_text("/html/body/div[2]/div/div/div[2]/div/p")
    original_image_url = get_attr("/html/body/div[2]/div/div/div[1]/div/img", "src")
    image_url = download_and_convert_to_webp(original_image_url, anime_id)
    tags = [tag.text_content().strip() for tag in tree.xpath("/html/body/div[2]/div/div/div[2]/div/ul/li") if tag.text_content().strip()]
    type_ = get_text("/html/body/div[2]/div/div/div[2]/div/div[1]/div[1]/div/a")
    status = get_text("/html/body/div[2]/div/div/div[2]/div/div[1]/div[3]/div/a")
    episode_count = get_text("/html/body/div[2]/div/div/div[2]/div/div[1]/div[4]/div")
    duration = get_text("/html/body/div[2]/div/div/div[2]/div/div[1]/div[5]/div")
    season = get_text("/html/body/div[2]/div/div/div[2]/div/div[1]/div[6]/div/a")
    source = get_text("/html/body/div[2]/div/div/div[2]/div/div[1]/div[7]/div")

    return {
        anime_id: {
            "title": title,
            "description": description,
            "image": image_url,
            "tags": tags,
            "type": type_,
            "status": status,
            "episodeCount": episode_count,
            "duration": duration,
            "season": season,
            "source": source
        }
    }

def upload_to_github(anime_data):
    api_url = f"https://api.github.com/repos/{repo_name}/contents/{remote_path}"
    headers = {"Authorization": f"token {access_token}"}

    response = scraper.get(api_url, headers=headers)
    current_data = {}
    sha = None

    if response.status_code == 200:
        try:
            sha = response.json()["sha"]
            content_decoded = base64.b64decode(response.json()["content"]).decode("utf-8")
            current_data = json.loads(content_decoded)
        except Exception as e:
            print("⚠️ فشل قراءة animes.json:", str(e))
    elif response.status_code == 404:
        print("📁 سيتم إنشاء ملف animes.json جديد.")
    else:
        print("❌ خطأ غير متوقع أثناء جلب animes.json:", response.status_code)
        return

    updated = False
    for anime_id, info in anime_data.items():
        if anime_id not in current_data:
            print(f"➕ إضافة أنمي جديد: {anime_id}")
            current_data[anime_id] = info
            updated = True
        else:
            print(f"ℹ️ الأنمي موجود مسبقًا: {anime_id} (تم التخطي)")

    if not updated:
        print("✅ لا توجد بيانات جديدة لإضافتها.")
        return

    new_content = json.dumps(current_data, ensure_ascii=False, indent=2)
    encoded_content = base64.b64encode(new_content.encode()).decode()

    payload = {
        "message": "تحديث animes.json بإضافة أنمي جديد",
        "content": encoded_content,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha

    put_response = scraper.put(api_url, headers=headers, json=payload)
    if put_response.status_code in [200, 201]:
        print("✅ تم رفع animes.json بنجاح.")
    else:
        print("❌ فشل رفع animes.json:", put_response.status_code, put_response.text)

# ========== التنفيذ ==========

# تحميل missing_anime_log.json من GitHub
missing_file_url = f"https://api.github.com/repos/{repo_name_log}/contents/{missing_file_path}"
headers = {"Authorization": f"token {access_token}"}

response = scraper.get(missing_file_url, headers=headers)
if response.status_code == 200:
    try:
        content_decoded = base64.b64decode(response.json()["content"]).decode("utf-8")
        missing_log = json.loads(content_decoded)
        print(f"✅ تم تحميل missing_anime_log.json من GitHub بنجاح.")
    except Exception as e:
        print("❌ فشل في فك تشفير أو قراءة ملف missing_anime_log.json:", e)
        exit()
else:
    print("❌ لم يتم العثور على missing_anime_log.json في GitHub:", response.status_code)
    exit()

for entry in missing_log:
    custom_url = entry.get("episode_link")
    if not custom_url:
        continue

    anime_id = extract_anime_id_from_custom_url(custom_url)
    if not anime_id:
        print("❌ لم يتم استخراج anime_id من الرابط:", custom_url)
        continue

    anime_info = fetch_anime_info(anime_id)
    if anime_info:
        upload_to_github(anime_info)
