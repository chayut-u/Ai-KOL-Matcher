from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
import time
import re
from selenium.webdriver.chrome.service import Service
import json
from urllib.parse import urljoin, urlparse
import os

def save_result_to_log(result: dict, base_url: str):
    # ✅ สร้าง slug จาก Facebook Page หรือ Website
    parsed = urlparse(base_url)
    if result.get("type") == "facebook":
        slug = parsed.path.strip("/").replace(".", "_")
        prefix = "facebook_posts_output"
    elif result.get("type") == "website":
        domain = parsed.netloc.replace(".", "_")
        slug = domain
        prefix = "website_content_output"
    else:
        slug = "unknown_source"
        prefix = "output"

    # ✅ สร้างโฟลเดอร์ log/<slug>/
    folder_path = os.path.join("log", slug)
    os.makedirs(folder_path, exist_ok=True)

    # ✅ ตั้งชื่อไฟล์ตาม timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.txt"
    full_path = os.path.join(folder_path, filename)

    # ✅ บันทึกไฟล์
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ บันทึกข้อมูลลงไฟล์: {full_path}")
    return full_path

def extract_intro_text(driver):
    try:
        intro_spans = driver.find_elements(By.XPATH, '//div[@role="main"]//span')
        for span in intro_spans:
            text = span.text.strip()
            if text and len(text) > 30 and "Dime" in text:
                return text
    except:
        pass
    return ""

def extract_facebook_page_info(driver):
    info = {
        "page_name": "",
        "category": "",
        "about": ""
    }

    try:
        title = driver.title
        info["page_name"] = title.split("|")[0].strip() if "|" in title else title.strip()
    except:
        pass

    try:
        category_el = driver.find_element(By.XPATH, '//div[@role="main"]//span[contains(text(), " · ")]')
        info["category"] = category_el.text.strip()
    except:
        pass

    about_parts = []

    # ✅ Step 1: ดึงจาก 'เกี่ยวกับ' (ตรง ๆ)
    try:
        about_el = driver.find_element(By.XPATH, '//div[@role="main"]//span[contains(text(), "เกี่ยวกับ") or contains(text(), "About")]/ancestor::div[1]/following-sibling::div')
        about_text = about_el.text.strip()
        if about_text:
            about_parts.append(about_text)
    except:
        pass

    # ✅ Step 2: ดึง span ยาว ๆ (แต่กรองข้อความขยะ)
    try:
        intro_spans = driver.find_elements(By.XPATH, '//div[@role="main"]//span')
        for span in intro_spans:
            text = span.text.strip()
            # 🔍 ตัวกรอง: ความยาว + ไม่ใช่ footer + ไม่มี "See All" + ไม่ใช่ลิงก์ + ไม่มี #hashtag
            if (
                text
                and len(text) >= 20
                and "likes" not in text.lower()
                and "followers" not in text.lower()
                and "privacy" not in text.lower()
                and "©" not in text
                and "see all" not in text.lower()
                and not text.startswith("Photos")
                and not text.startswith("http")
                and "#" not in text
                and text.lower() not in ["intro", "แนะนำตัว"]
                and text not in about_parts
            ):
                about_parts.append(text)
                break  # ✅ เจออันแรกพอแล้ว
    except:
        pass

    info["about"] = " | ".join(about_parts).strip()
    return info







def scroll_page(driver, scroll_count=50, delay=2):
    for i in range(scroll_count):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(delay)

# 🔹 ปิด popup ด้านบน (แรกเข้า)
def close_top_login_popup(driver):
    try:
        close_btn = driver.find_element(By.XPATH, '//div[@aria-label="Close"]')
        close_btn.click()
        print("✅ ปิด popup login ด้านบนแล้ว")
    except:
        print("ℹ️ ไม่มี popup ด้านบน")

# 🔹 ปิด popup กลางจอ (ระหว่าง scroll)
def close_mid_login_popup(driver):
    try:
        popup = driver.find_element(By.XPATH, '//div[@role="dialog"]//div[@aria-label="Close"]')
        popup.click()
        print("✅ ปิด popup login กลางจอแล้ว")
        time.sleep(2)
    except:
        print("ℹ️ ไม่มี popup login กลางจอ")

# 🔹 แยก hashtag และล้างข้อความ
def process_post_text(text):
    cleaned_text = re.sub(r'\s+', ' ', text).strip()
    hashtags = re.findall(r"#\w[\w\d_ก-๙]*", cleaned_text)
    text_without_hashtags = re.sub(r"#\w[\w\d_ก-๙]*", '', cleaned_text).strip()
    return {
        "text": cleaned_text,
        "text_clean": text_without_hashtags,
        "hashtags": hashtags
    }


def extract_facebook_posts_with_selenium(url, max_posts=10):
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    driver.get(url)

    time.sleep(5)
    close_top_login_popup(driver)
    page_info = extract_facebook_page_info(driver)
    scroll_page(driver, scroll_count=10, delay=2)
    close_mid_login_popup(driver)

    extracted = []
    seen_texts = set()

    posts = driver.find_elements(By.XPATH, '//div[@data-ad-preview="message"]')

    for post in posts:
        if len(extracted) >= max_posts:
            break

        try:
            # คลิก "See More" ถ้ามี
            see_more = post.find_element(By.XPATH, './/div[contains(text(), "See more") or contains(text(), "ดูเพิ่มเติม")]')
            driver.execute_script("arguments[0].click();", see_more)
            time.sleep(0.3)
        except:
            pass

        raw_text = post.text.strip()

        # ไม่เอาโพสต์ซ้ำ
        if not raw_text or raw_text in seen_texts:
            continue
        seen_texts.add(raw_text)

        processed = process_post_text(raw_text)

        extracted.append({
            "index": len(extracted) + 1,
            "text": processed["text"],
            "text_clean": processed["text_clean"],
            "hashtags": processed["hashtags"]
        })

    driver.quit()
    

    result = {
        "type": "facebook",
        "url": url,
        "page_name": page_info["page_name"],
        "category": page_info["category"],
        "about": page_info["about"],
        "total_posts": len(extracted),
        "posts": extracted
    }

    # timestamp = time.strftime("%Y%m%d_%H%M%S")
    # filename = f"facebook_posts_output_{timestamp}.txt"
    # with open(filename, "w", encoding="utf-8") as f:
    #     json.dump(result, f, ensure_ascii=False, indent=2)

    # print(f"\n✅ บันทึกโพสต์ทั้งหมด {len(extracted)} รายการลงไฟล์ facebook_posts_output.txt แล้ว")

    return result


def extract_website(url: str, max_links=5):
    headers = {"User-Agent": "Mozilla/5.0"}
    visited = set()
    content_posts = []

    def is_internal(link, base_domain):
        parsed = urlparse(link)
        return parsed.netloc == "" or parsed.netloc == base_domain

    def scrape_page(url):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            text_parts = []

            for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
                text_parts.append(tag.get_text(strip=True))

            return ' '.join(text_parts).strip()
        except Exception as e:
            print(f"❌ ดึงไม่ได้จาก {url}: {e}")
            return ""

    try:
        domain = urlparse(url).netloc
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        # 🔹 ดึง title + description จากหน้าแรก
        title = soup.title.string.strip() if soup.title else ""
        desc = soup.find("meta", {"name": "description"})
        description = desc["content"].strip() if desc else ""

        # ✅ เก็บเนื้อหาใน content_posts
        visited.add(url)
        main_content = scrape_page(url)
        if main_content:
            content_posts.append({"url": url, "content": main_content})

        internal_links = set()
        for a in soup.find_all('a', href=True):
            full_url = urljoin(url, a['href'])
            if is_internal(full_url, domain) and full_url not in visited:
                internal_links.add(full_url)

        for link in list(internal_links)[:max_links]:
            visited.add(link)
            sub_content = scrape_page(link)
            if sub_content:
                content_posts.append({"url": link, "content": sub_content})
        result = {
            "type": "website",
            "url": url,
            "title": title,
            "description": description,
            "content_posts": content_posts
        }

        # timestamp = time.strftime("%Y%m%d_%H%M%S")
        # filename = f"website_content_{timestamp}.txt"
        # with open(filename, "w", encoding="utf-8") as f:
        #     json.dump(result, f, ensure_ascii=False, indent=2)

        # print(f"✅ บันทึกไฟล์เรียบร้อย: {filename}")
        return result

    except Exception as e:
        return {"error": f"Website scraping failed: {str(e)}"}


def extract_content_from_link(facebook_link=None, website_link=None, num_posts=20):
    print("📥 อ่านรายละเอียดจากลิงก์...")

    facebook_result = None
    web_result = None

    if facebook_link is not None:
        facebook_result = extract_facebook_posts_with_selenium(facebook_link, 10)

    if website_link is not None:
        web_result = extract_website(website_link, num_posts)

    return facebook_result, web_result
