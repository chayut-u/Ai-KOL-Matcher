from apify_client import ApifyClient
import os

def fetch_kols_with_captions(brand_data: dict, resultsPerPage=20):
    print("📌 BRAND DATA:", brand_data)

    client = ApifyClient(os.getenv("APIFY_TOKEN"))

    # ✅ ใช้ hashtags เป็นคำค้นหา
    hashtags = brand_data.get("hashtags", [])
    keywords = list(set([kw.strip("#").lower() for kw in hashtags]))

    print("🔍 Hashtags used as search terms:", hashtags)
    print("🔍 Keywords used for relevance check:", keywords)

    # เรียก Apify โดยใช้ hashtags เท่านั้น
    run = client.actor("clockworks/free-tiktok-scraper").call(run_input={
        "hashtags": hashtags,
        "resultsPerPage": resultsPerPage,
        "shouldDownloadVideos": False
    })

    final_results = []
    seen_usernames = set()

    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        try:
            profile = item["authorMeta"]
            caption = item.get("text", "")
            username = profile.get("name")
            followers = profile.get("fans", 0)
            hashtags_used = [h.get("name", "").lower() for h in item.get("hashtags", [])]
            combined_text = (caption + " " + " ".join(hashtags_used)).lower()
        except Exception as e:
            print("⚠️ Error parsing item:", e)
            continue

        if not username or username in seen_usernames:
            continue

        if followers < 50000:
            continue
        else:
            print(profile)
        # ตรวจสอบว่า hashtag หรือ caption มีคำที่เกี่ยวข้อง
        is_relevant = any(kw in combined_text for kw in keywords)

        if is_relevant:
            final_results.append({
                "username": username,
                "profile_link": f"https://www.tiktok.com/@{username}",
                "description": "มีผู้ติดตามมากกว่า 50,000 คน และมีเนื้อหาที่เกี่ยวข้องกับสินค้าหรือความสนใจของแบรนด์",
                "sample_caption": caption.strip()[:200],
                "audience": "ผู้ติดตามชาวไทยที่สนใจสินค้าหรือบริการที่เกี่ยวข้อง",
                "follower": followers
            })
            seen_usernames.add(username)

            print("✅ FOUND:", username, "|", followers, "followers")

    print("📊 KOLs Found:", len(final_results))
    return final_results
