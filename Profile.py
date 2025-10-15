# Profile.py
import cloudscraper
from lxml import html
import re
import json
import base64
import os
import time
from urllib.parse import urlparse, parse_qs, quote

# ----------- إعدادات (عدّلها لو تحب) -----------
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")  # لازم يكون PAT عندك للرفع على الريبو الهدف
INPUT_REPO = "abdo12249/test"             # مكان missing_anime_log.json الصحيح
INPUT_PATH = "missing_anime_log.json"
OUTPUT_REPO = "abdo12249/1"               # الريبو اللي هنرفع فيه animes.json
OUTPUT_PATH = "test1/animes1.json"
BRANCH = "main"
SLEEP_BETWEEN_FETCHES = 0.6               # لتخفيف الضغط على السيرفر
# ------------------------------------------------

scraper = cloudscraper.create_scraper()
headers = {"Authorization": f"token {ACCESS_TOKEN}"} if ACCESS_TOKEN else {}

def fetch_file_from_github(repo, path):
    api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
    resp = scraper.get(api_url, headers=headers)
    if resp.status_code == 200:
        j = resp.json()
        content_b64 = j.get("content", "")
        try:
            decoded = base64.b64decode(content_b64).decode("utf-8")
        except Exception as e:
            print("❌ خطأ فك ترميز المحتوى:", e)
            return None, None
        return decoded, j.get("sha")
    elif resp.status_code == 404:
        print(f"❌ 404 — الملف '{path}' غير موجود في الريبو '{repo}'.")
        return None, None
    else:
        print(f"❌ خطأ {resp.status_code} عند جلب {repo}/{path}: {resp.text}")
        return None, None

def extract_anime_id_from_custom_link(link):
    try:
        query = parse_qs(urlparse(link).query)
        anime_id = query.get("id", [""])[0].strip()
        # إزالة رقم الحلقة المتواجد في آخر الـ id مثل: name--2 أو name-2
        anime_id = re.sub(r'(?:--|-)\d+$', '', anime_id)
        return anime_id
    except Exception as e:
        print("❌ خطأ أثناء تحليل الرابط:", e)
        return ""

def fetch_anime_info_from_id(anime_id):
    slug = quote(anime_id, safe='')
    anime_url = f"https://4d.qerxam.shop/anime/{slug}/"
    print(f"📥 جلب: {anime_url}")
    try:
        resp = scraper.get(anime_url)
    except Exception as e:
        print("❌ خطأ طلب الصفحة:", e)
        return None

    if resp.status_code != 200:
        print(f"⚠️ الصفحة رجعت status {resp.status_code} — تخطي {anime_id}")
        return None

    tree = html.fromstring(resp.content)

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
    image = get_attr('/html/body/div/div/div[1]/div/div/div[1]/div/img', 'src')
    tags = [tag.text_content().strip() for tag in tree.xpath('//div[@class="anime-details"]/ul/li') if tag.text_content().strip()]
    type_ = get_text('/html/body/div/div/div[1]/div/div/div[2]/div/div[1]/div[2]/div/a')
    status = get_text('/html/body/div/div/div[1]/div/div/div[2]/div/div[1]/div[4]/div/a')
    episode_count = get_text('/html/body/div/div/div[1]/div/div/div[2]/div/div[1]/div[5]/div/span')
    duration = get_text('/html/body/div/div/div[1]/div/div/div[2]/div/div[1]/div[6]/div')
    season = get_text('/html/body/div/div/div[1]/div/div/div[2]/div/div[1]/div[7]/div/a')
    source = get_text('/html/body/div/div/div[1]/div/div/div[2]/div/div[1]/div[10]/div')

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

def merge_and_upload_batch(new_items):
    existing_raw, existing_sha = fetch_file_from_github(OUTPUT_REPO, OUTPUT_PATH)
    current_data = {}

    if existing_raw:
        try:
            current_data = json.loads(existing_raw)
        except Exception as e:
            print("⚠️ فشل قراءة animes.json الموجودة (سيتم استخدام فارغ):", e)
            current_data = {}
    else:
        print("⚠️ لم أستطع تحميل animes.json القديم — لن أرفع أي تحديث لتجنب حذف البيانات.")
        return  # <-- مهم جدًا لتجنب الكتابة الفارغة

    added = 0
    for anime_id, info in new_items.items():
        if anime_id not in current_data:
            current_data[anime_id] = info
            added += 1
        else:
            print(f"ℹ️ متواجد مسبقًا، تخطي: {anime_id}")

    if added == 0:
        print("✅ لا توجد أنميات جديدة ليتم إضافتها.")
        return

    new_content = json.dumps(current_data, ensure_ascii=False, indent=2)
    encoded = base64.b64encode(new_content.encode()).decode()

    payload = {
        "message": f"تحديث animes.json — إضافة {added} أنميات",
        "content": encoded,
        "branch": BRANCH
    }
    if existing_sha:
        payload["sha"] = existing_sha

    put_url = f"https://api.github.com/repos/{OUTPUT_REPO}/contents/{OUTPUT_PATH}"
    resp = scraper.put(put_url, headers=headers, json=payload)
    if resp.status_code in (200, 201):
        print(f"✅ تم رفع animes.json بنجاح — أضيفت {added} أنميات.")
    else:
        print("❌ فشل الرفع:", resp.status_code, resp.text)


def main():
    if not ACCESS_TOKEN:
        print("⚠️ تحذير: لم يتم توفير ACCESS_TOKEN عبر متغير البيئة. القراءة من الريبو العام ممكنة، لكن الرفع يتطلب توكن مع صلاحية repo.")
    # جلب ملف missing_anime_log.json من الريبو الصحيح
    raw, _ = fetch_file_from_github(INPUT_REPO, INPUT_PATH)
    if not raw:
        print("⚠️ لم يتم العثور على بيانات في missing_anime_log.json أو فشل تحميله.")
        return

    try:
        data = json.loads(raw)
    except Exception as e:
        print("❌ فشل تحويل محتوى missing_anime_log.json إلى JSON:", e)
        return

    processed = set()
    collected = {}

    for entry in data:
        episode_link = entry.get("episode_link", "")
        anime_id = extract_anime_id_from_custom_link(episode_link)
        if not anime_id:
            print("⚠️ لم استخرج id من الرابط:", episode_link)
            continue
        if anime_id in processed:
            continue

        info = fetch_anime_info_from_id(anime_id)
        if info:
            collected.update(info)
            processed.add(anime_id)
        time.sleep(SLEEP_BETWEEN_FETCHES)

    if not collected:
        print("⚠️ لا توجد أنميات صالحة للمعالجة.")
        return

    # رفع دفعة واحدة (أسرع وأوفر لطلبات API)
    merge_and_upload_batch(collected)
    print("🎉 انتهت المعالجة.")

if __name__ == "__main__":
    main()
