import cloudscraper
from lxml import html
import re
import json
import base64
import os
from urllib.parse import urlparse, parse_qs

# إعدادات GitHub
access_token = os.getenv("ACCESS_TOKEN")
repo_name = "abdo12249/1"
remote_path = "test1/animes.json"
missing_anime_file = "missing_anime_log.json"

scraper = cloudscraper.create_scraper()

def extract_anime_id_from_custom_url(custom_url):
    """استخراج id من رابط مثل /المشاهده.html?id=bullet-bullet&episode=1"""
    query = parse_qs(urlparse(custom_url).query)
    return query.get("id", [None])[0]

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

if not os.path.exists(missing_anime_file):
    print("❌ لم يتم العثور على ملف missing_anime_log.json")
    exit()

with open(missing_anime_file, "r", encoding="utf-8") as f:
    try:
        missing_log = json.load(f)
    except json.JSONDecodeError:
        print("❌ خطأ في قراءة ملف missing_anime_log.json (صيغة غير صحيحة)")
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
