import cloudscraper
from lxml import html
import re
import json
import base64
import os
from urllib.parse import urlparse

# إعدادات GitHub
access_token = os.getenv("ACCESS_TOKEN")
repo_name = "abdo12249/1"
remote_path = "test1/animes.json"

scraper = cloudscraper.create_scraper()

def extract_anime_id_from_episode_url(episode_url):
    path = urlparse(episode_url).path
    last_part = path.strip("/").split("/")[-1]
    anime_id = re.sub(r"-الحلقة-[0-9]+", "", last_part)
    return anime_id

def fetch_anime_info_from_url(episode_url):
    anime_id = extract_anime_id_from_episode_url(episode_url)
    anime_url = f"https://4d.qerxam.shop/anime/{anime_id}/"

    print(f"📥 فتح الصفحة: {anime_url}")
    response = scraper.get(anime_url)
    if response.status_code != 200:
        print("❌ فشل تحميل الصفحة")
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

    # استخراج البيانات
    title = get_text('//div[@class="anime-details"]/h1')
    description = get_text('//div[@class="anime-details"]/p')
    image = get_attr('//div[@class="anime-cover"]/img', 'src')
    tags = [tag.text_content().strip() for tag in tree.xpath('//div[@class="anime-details"]/ul/li') if tag.text_content().strip()]
    type_ = get_text('//div[@class="anime-info"]/div[1]/div/a')
    status = get_text('//div[@class="anime-info"]/div[3]/div/a')
    episode_count = get_text('//div[@class="anime-info"]/div[4]/div')
    duration = get_text('//div[@class="anime-info"]/div[5]/div')
    season = get_text('//div[@class="anime-info"]/div[6]/div/a')
    source = get_text('//div[@class="anime-info"]/div[7]/div')

    return {
        anime_id: {
            "title": title,
            "description": description,
            "image": image,
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

    # جلب الملف الحالي
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
            current_data = {}
    elif response.status_code == 404:
        print("📁 سيتم إنشاء ملف animes.json جديد.")
    else:
        print("❌ خطأ غير متوقع أثناء جلب animes.json:", response.status_code)
        return

    # تحديث البيانات
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

    # تجهيز المحتوى للرفع
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

# ========= التنفيذ =========
episode_url = "https://4d.qerxam.shop/episode/bullet-bullet-%d8%a7%d9%84%d8%ad%d9%84%d9%82%d8%a9-7/"
anime_info = fetch_anime_info_from_url(episode_url)

if anime_info:
    upload_to_github(anime_info)
