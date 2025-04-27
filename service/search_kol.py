from service.ai_api import call_chatgpt_kol_analys ,search_kols_with_perplexity , search_kols_with_gpt , extract_json_from_text
import json
import requests
import service.tiktok_kol as tiktok_kol
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def bullet(items): return "\n".join(f"- {i}" for i in items) if items else "-"

def parse_follower_count(text):
    # แปลง "573.2K" → 573200
    text = text.strip().lower().replace(',', '')
    if 'm' in text:
        return int(float(text.replace('m', '')) * 1_000_000)
    elif 'k' in text:
        return int(float(text.replace('k', '')) * 1_000)
    else:
        try:
            return int(text)
        except:
            return 0


def create_stealth_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

def parse_follower_count(text):
    text = text.lower().replace(",", "")
    if "k" in text:
        return int(float(text.replace("k", "")) * 1_000)
    elif "m" in text:
        return int(float(text.replace("m", "")) * 1_000_000)
    return int(text)

def filter_valid_kol_profiles(profile_list, min_followers=50000):
    driver = create_stealth_driver()
    valid_profiles = []

    for profile in profile_list:
        try:
            url = profile["profile_link"]
            driver.get(url)

            # รอโหลด follower หรือ error
            WebDriverWait(driver, 7).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, '//strong[@data-e2e="followers-count"]')),
                    EC.presence_of_element_located((By.XPATH, '//p[contains(text(), "Couldn\'t find this account")]'))
                )
            )

            # ถ้ามีข้อความว่า "ไม่พบบัญชี"
            if driver.find_elements(By.XPATH, '//p[contains(text(), "Couldn\'t find this account")]'):
                print(f"[SKIP] Not found: {profile['username']}")
                continue

            followers_elem = driver.find_element(By.XPATH, '//strong[@data-e2e="followers-count"]')
            followers_count = parse_follower_count(followers_elem.text)

            if followers_count >= min_followers:
                profile['followers'] = followers_count
                valid_profiles.append(profile)
                print(f"[OK] {profile['username']} - {followers_count:,} followers")
            else:
                print(f"[SKIP] {profile['username']} - only {followers_count:,} followers")

        except Exception as e:
            print(f"[ERROR] While checking {profile['username']}: {e}")
    
    driver.quit()
    return valid_profiles

def filter_existing_tiktok_accounts(profile_list):
    driver = create_stealth_driver()
    valid_profiles = []

    for profile in profile_list:
        try:
            url = profile["profile_link"]
            driver.get(url)
            
            WebDriverWait(driver, 7).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, '//p[contains(text(), "Couldn\'t find this account")]')),
                    EC.presence_of_element_located((By.XPATH, '//h1'))  # Header บนหน้า profile
                )
            )

            if driver.find_elements(By.XPATH, '//p[contains(text(), "Couldn\'t find this account")]'):
                print(f"[SKIP] Account not found: {profile['username']}")
            else:
                valid_profiles.append(profile)
                print(f"[OK] Found valid account: {profile['username']}")

        except Exception as e:
            print(f"[ERROR] While checking {profile['username']}: {e}")
    
    driver.quit()
    return filter_valid_kol_profiles(valid_profiles)

def bullet(items): return "\n".join(f"- {i}" for i in items) if items else "- ไม่ระบุ"

def build_tiktok_kol_prompt_thai(brand_data: dict, max_kol: int = 20) -> str:
    business_type = brand_data.get("business_type", ["ไม่ระบุ"])[0]
    content_style = brand_data.get("content_style", ["ไม่ระบุ"])[0]
    target_audience = brand_data.get("target_audience", ["ไม่ระบุ"])[0]
    content_themes = next(iter(brand_data.get("content_themes", {}).values()), [])



    prompt = f"""
คุณคือเอเจนซี่โฆษณาชั้นนำในประเทศไทย ที่เชี่ยวชาญด้านการเลือก TIKTOK KOL ที่สามารถ **ส่งเสริมยอดขายและโปรโมตสินค้า/บริการของแบรนด์ไทย** โดยมุ่งเป้าหมายที่ลูกค้าชาวไทย

[วัตถุประสงค์หลัก]
- ค้นหา KOL ที่สามารถ “ส่งผลต่อการตัดสินใจซื้อ” หรือ “กระตุ้นความสนใจในตัวสินค้า/บริการของแบรนด์”
- ไม่จำเป็นต้องขายตรง แต่ต้องมีอิทธิพลต่อกลุ่มเป้าหมาย เช่น ทำให้เกิดความสนใจ การรับรู้ หรือความเชื่อมั่นในสินค้า/บริการ
- KOL เหล่านี้ต้องมีศักยภาพในการสร้างยอดขาย ทั้งทางตรงและทางอ้อม

[ข้อมูลแบรนด์]
- ธุรกิจ: {business_type}
- กลุ่มเป้าหมาย: {target_audience}
- รูปแบบเนื้อหา: {content_style}
- ธีมเนื้อหา:
{bullet(content_themes)}

[แนวทางการประเมินกลุ่มเป้าหมาย]
- โปรดวิเคราะห์ว่าใครคือ “ผู้มีแนวโน้มตัดสินใจซื้อ” สำหรับแบรนด์นี้ ไม่จำเป็นต้องเป็นผู้ใช้งานปลายทางโดยตรง
- เลือก KOL ที่มีอิทธิพลต่อผู้คนในกลุ่มนั้น และสามารถเชื่อมโยงเนื้อหาเข้ากับสินค้าหรือบริการของแบรนด์ได้อย่างเป็นธรรมชาติ

[ข้อกำหนดสำคัญ]
- ต้องใช้ภาษาไทย และสื่อสารอย่างเข้าใจพฤติกรรมของผู้บริโภคไทย
- ต้องเป็นบุคคลจริง ไม่ใช่แบรนด์ / เพจรีโพสต์ / บัญชีบริษัท
- ต้องมีอิทธิพลที่พิสูจน์ได้ เช่น มีการพูดถึงจากแหล่งข้อมูลที่น่าเชื่อถือ หรือเคยมีบทบาทในการเปลี่ยนพฤติกรรมผู้ติดตาม
- ถ้ามีข้อมูลอ้างอิงจากแหล่งสื่อไทย จะได้รับการพิจารณาเป็นพิเศษ

[คำแนะนำการค้นหา]
- ค้นหาจากแหล่งข้อมูลไทย เช่น:
  - TikTok ประเทศไทย
  - Google.co.th (ใช้คำค้นภาษาไทย)
  - สื่อหรือบทความการตลาดในไทย

[จำนวนที่ต้องการ]
- ส่งรายชื่อ KOL 10–{max_kol} คน
- ถ้าไม่ครบ 10 คน ให้ส่งเฉพาะผู้ที่ตรงกลุ่มเป้าหมายและมีอิทธิพลจริงเท่านั้น

[รูปแบบผลลัพธ์ JSON]:
```json
[
  {{
    "username": "ชื่อ TikTok (ไม่ต้องใส่ @)",
    "profile_link": "ลิงก์ TikTok",
    "description": "เหตุผลที่เหมาะกับแบรนด์ เช่น มีอิทธิพลต่อกลุ่มเป้าหมาย สื่อสารตรงกับแนวทางของแบรนด์",
    "sample_caption": "ตัวอย่างแคปชัน/แฮชแทกล่าสุด",
    "audience": "กลุ่มผู้ติดตาม"
  }}
]

"""
    return prompt.strip()

def build_tiktok_kol_prompt_en(brand_data: dict, max_kol: int = 20) -> str:
    business_type = brand_data.get("business_type", ["Not specified"])[0]
    content_style = brand_data.get("content_style", ["Not specified"])[0]
    target_audience = brand_data.get("target_audience", ["Not specified"])[0]
    content_themes = next(iter(brand_data.get("content_themes", {}).values()), [])

    prompt = f"""
You are a leading advertising agency in Thailand, specializing in selecting **TikTok KOLs (Key Opinion Leaders)** who can effectively **promote Thai brands and drive sales** by influencing Thai customers.

[MAIN OBJECTIVE]
- Identify KOLs who can influence purchase decisions or generate interest in the brand’s products/services
- They don’t need to directly sell, but must build trust, awareness, and interest among the brand’s audience
- KOLs must be capable of driving sales either directly or indirectly

[BRAND PROFILE]
- Business Type: {business_type}
- Target Audience: {target_audience}
- Content Style: {content_style}
- Content Themes:
{bullet(content_themes)}

[INTERPRETING TARGET AUDIENCE]
- Evaluate who the **decision-makers** are, even if they are not the end users
- Choose KOLs who influence those people, and who can naturally align their content with the brand’s offering

[REQUIREMENTS]
- Must primarily communicate in Thai and demonstrate an understanding of Thai consumer behavior
- Must be a real person (not a brand, repost page, or company account)
- Should have **verifiable influence**, such as credible media references or clear impact on audience behavior
- Credibility from Thai media (Google.co.th, Thai articles, social proof) is a strong advantage

[SUGGESTED SOURCES]
- TikTok Thailand
- Google.co.th (use Thai-language keywords)
- Thai marketing blogs, influencer rankings, or press

[QUANTITY REQUESTED]
- Provide 10–{max_kol} KOLs
- If fewer than 10 are relevant, provide only the most suitable ones

[JSON OUTPUT FORMAT]:
```json
[
  {{
    "username": "TikTok username (no @)",
    "profile_link": "TikTok profile URL",
    "description": "Why this KOL fits the brand — e.g., strong influence in the target group, communicates in a style aligned with the brand",
    "sample_caption": "Example of recent caption or hashtags",
    "audience": "Primary follower demographic"
  }}
]

```"""
    return prompt.strip()

def build_kol_analysis_prompt(kol_list: list, brand_data: dict) -> str:

    business_type = brand_data.get("business_type", ["Unknown"])[0]
    content_style = brand_data.get("content_style", ["Unknown"])[0]
    target_audience = brand_data.get("target_audience", ["Unknown"])[0]
    content_themes = brand_data.get("content_themes", [])
    clues = brand_data.get("clues", [])
    hashtags = brand_data.get("hashtags", [])
    search_terms = brand_data.get("search", [])

    kol_json = json.dumps(kol_list, ensure_ascii=False, indent=2)

    prompt = f"""
            You are a senior KOL strategist and evaluation expert.

            Your primary responsibility is to assess whether each TikTok influencer (KOL) can realistically **support this Thai brand’s sales or services**, either directly or indirectly.

            You must use publicly available signals — such as their video content, tone, engagement style, audience fit, and credibility — to make this judgment.

            ---

            📌 BRAND PROFILE
            - Business Type: {business_type}
            - Content Style: {content_style}
            - Target Audience: {target_audience}
            - Content Themes:
            {''.join(['  - ' + theme + '\n' for theme in content_themes])}
            - Keywords / Clues:
            {''.join(['  - ' + clue + '\n' for clue in clues])}
            - Related Hashtags: {', '.join(hashtags) or '-'}
            - Relevant Search Topics: {', '.join(search_terms) or '-'}

            ---

            👤 KOLs to Analyze:
            {kol_json}

            ---

            🔍 EVALUATION FOCUS

            🎯 MAIN OBJECTIVE:
            > **Can this KOL help drive product sales or brand service adoption among the target audience?**

            This is your main question. If YES, explain why.  
            If NO, remove them entirely from the list.

            ✅ SUITABLE IF:
            - The KOL has real influence over the target audience
            - Their content aligns with the product or service being promoted
            - Their tone or storytelling could support the brand's commercial goals
            - DO NOT include KOLs who are directly associated with the brand, such as brand owners, business founders, or individuals promoting their own products/services.
            - KOLs must be independent influencers — not representatives of a specific product, business, or company.

            ❌ EXCLUDE IF:
            - They are brand owners or promoting their own product
            - They run company or business accounts
            - They do not fit the brand's theme or audience at all
            - They only post generic or entertainment content without relevance
            - They are inactive, unverifiable, or bots

            ---

            📦 OUTPUT FORMAT (return only suitable KOLs):
            
json
            [
            {{
                "username": "tiktokhandle",
                "profile_link": "https://www.tiktok.com/@tiktokhandle",
                "reason": "Has strong influence among Thai parents. Consistently promotes educational content, making her ideal for language learning campaigns.",
                "suitable_for": "Awareness and conversion campaigns for Thai-language edtech"
            }}
            ]
        """ 
    return prompt.strip()

def is_tiktok_profile_valid(url: str) -> bool:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        response = requests.get(url, headers=headers, timeout=8)

        # Check for server or status issues
        if response.status_code != 200:
            return False

        # Parse HTML to look for known invalid markers
        soup = BeautifulSoup(response.text, 'html.parser')

        error_phrases = [
            "couldn't find this account",
            "Couldn't find this account",
            "ไม่พบบัญชีนี้",
            "ไม่สามารถค้นหาบัญชีนี้ได้",
            "ไม่มีบัญชีผู้ใช้นี้"
        ]

        page_text = soup.get_text(separator=" ").lower()

        for phrase in error_phrases:
            if phrase.lower() in page_text:
                return False

        return True

    except requests.exceptions.RequestException:
        return False


def search_kol_main(prompt,brand_detail):
    kol_list_result = search_kols_with_perplexity(prompt)
    # gpt_kol_list = search_kols_with_gpt(prompt)
    seen_usernames = set()
    merged_list = []
    
    # for kol in kol_list_result + gpt_kol_list:
    for kol in kol_list_result :
        username = kol.get("username", "").lower()
        profile_link = kol.get("profile_link", "").lower()

        key = f"{username}|{profile_link}"
        if key not in seen_usernames:
            seen_usernames.add(key)
            merged_list.append(kol)

    filter_merged_list = filter_existing_tiktok_accounts(merged_list)
    print(f"✅ รวมทั้งหมด {len(filter_merged_list)} KOL จาก Perplexity + GPT")
    # valid_kols, invalid_kols = filter_invalid_kols(merged_list)
    prompt_rate_kol = build_kol_analysis_prompt(filter_merged_list,brand_detail)
    result_kol_rate = call_chatgpt_kol_analys(prompt_rate_kol,0)
    result = extract_json_from_text(result_kol_rate)
    return filter_valid_kol_profiles(result)

def search_kol_by_apify(brand_detail):
    filter_merged_list =tiktok_kol.fetch_kols_with_captions(brand_detail)
    prompt_rate_kol = build_kol_analysis_prompt(filter_merged_list,brand_detail)
    result_kol_rate = call_chatgpt_kol_analys(prompt_rate_kol,0)
    result = extract_json_from_text(result_kol_rate)
    return filter_valid_kol_profiles(result)