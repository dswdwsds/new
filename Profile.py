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
remote_path2 = "test/missing_anime_log.json"  # الملف اللي فيه روابط الأنميات المفقودة

scraper = cloudscraper.create_scraper()

# ========== استخراج anime_id من رابط "المشاهده.html" ==========
def extract_anime_id_from_custom_link(link):
    try:
        query = parse_qs(urlparse(link).query)
        anime_id = query.get("id", [""])[0]
        if anime_id:
            anime_id = re.sub(r"--?\d+$", "", anime_id)
        return anime_id
    except Exception as e:
        print(f"❌ خطأ أثناء تحليل الرابط: {e}")
        return ""

# ========== جلب بيانات الأنمي ==========
def fetch_anime_info_from_id(anime_id):
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

# ========== رفع البيانات إلى GitHub ==========
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
        print("📁 سيتم إنشاء ملف جديد animes.json.")
    else:
        print("❌ خطأ أثناء جلب animes.json:", response.status_code)
        return

    updated = False
    for anime_id, info in anime_data.items():
        if anime_id not in current_data:
            print(f"➕ إضافة أنمي جديد: {anime_id}")
            current_data[anime_id] = info
            updated = True
        else:
            print(f"ℹ️ الأنمي موجود مسبقًا: {anime_id}")

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

# ========== تحميل missing_anime_log.json من GitHub ==========
def fetch_missing_log_from_github():
    api_url = f"https://api.github.com/repos/{repo_name}/contents/{remote_path2}"
    headers = {"Authorization": f"token {access_token}"}
    response = scraper.get(api_url, headers=headers)

    if response.status_code != 200:
        print("❌ فشل تحميل missing_anime_log.json من GitHub:", response.status_code)
        return []

    try:
        content_decoded = base64.b64decode(response.json()["content"]).decode("utf-8").strip()
        if not content_decoded:
            print("⚠️ الملف missing_anime_log.json فارغ.")
            return []
        data = json.loads(content_decoded)
        return data
    except Exception as e:
        print("❌ خطأ في قراءة missing_anime_log.json:", str(e))
        return []

# ========== التنفيذ ==========
def main():
    data = fetch_missing_log_from_github()
    if not data:
        print("⚠️ لم يتم العثور على بيانات في missing_anime_log.json")
        return

    processed_ids = set()

    for entry in data:
        episode_link = entry.get("episode_link", "")
        anime_id = extract_anime_id_from_custom_link(episode_link)
        if not anime_id or anime_id in processed_ids:
            continue

        anime_info = fetch_anime_info_from_id(anime_id)
        if anime_info:
            upload_to_github(anime_info)
            processed_ids.add(anime_id)

    print("🎉 تم إنهاء المعالجة.")

if __name__ == "__main__":
    main()
