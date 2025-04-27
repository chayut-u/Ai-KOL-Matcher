import json
from collections import Counter
import re
from typing import Dict, List, Union
from service.ai_api import call_chatgpt

def count_top_hashtags(data: dict, top_k=10):
    hashtags = []
    for post in data.get("posts", []):
        hashtags.extend(post.get("hashtags", []))
    return Counter(hashtags).most_common(top_k)

def get_all_post_texts(data: dict, max_posts=20):
    texts = [post.get("text_clean", "") for post in data.get("posts", []) if post.get("text_clean")]
    return "\n\n".join(texts[:max_posts])

TYPE_OF_BUSINESS = [
    # การเงิน
    "Financial Services",
    "Finance Applications and Tools",
    "Investment Platforms",
    "Personal Finance Consulting",

    # ความงามและสุขภาพ
    "Beauty and Skincare Products",
    "Wellness and Mental Health Services",
    "Health and Supplement Products",
    "Fitness and Personal Training Services",
    "Medical Clinics and Healthcare Centers",

    # อาหารและเครื่องดื่ม
    "Restaurants and Dining",
    "Home Cooking and Meal Kits",
    "Health Food and Clean Eating",
    "Beverage Brands and Cafes",
    "Food Delivery Services",

    # ค้าปลีกและห้าง
    "Retail Stores and Convenience Stores",
    "Department Stores and Shopping Malls",
    "Supermarkets and Hypermarkets",
    
    # บ้านและอสังหาริมทรัพย์
    "Home Appliances and Smart Home Solutions",
    "Home Decor and Furniture",
    "Real Estate Agencies and Property Development",
    "Interior Design and Home Improvement",

    # ครอบครัวและการศึกษา
    "Parenting and Family Services",
    "Kids Products and Toy Brands",
    "Early Childhood Education Centers",
    "Online Learning Platforms",
    "Language Schools and Tutoring Services",

    # สัตว์เลี้ยง
    "Pet Care Services",
    "Pet Products and Supplies",
    "Veterinary Clinics and Animal Hospitals",

    # ท่องเที่ยว
    "Domestic Travel and Tour Operators",
    "International Travel Agencies",
    "Hotel and Accommodation Services",
    "Travel Gear and Accessories",

    # ไลฟ์สไตล์และแฟชั่น
    "Fashion Brands and Apparel Stores",
    "Lifestyle Products and Services",
    "Shopping Platforms and E-commerce",

    # เทคโนโลยีและอาชีพอิสระ
    "Technology Products and Gadgets",
    "Mobile Applications and Digital Platforms",
    "Freelancing and Remote Work Services",
    "Career Development and Productivity Tools",

    # รถยนต์และเทคโนโลยียานยนต์
    "Automobile Sales and Dealerships",
    "Car Accessories and Modification Services",
    "Automobile Maintenance and Repair Services",
    "Electric Vehicles and Charging Stations",
    "Smart Mobility and Transportation Technology",
    "Green Technology and Sustainability Solutions",

    # กิจกรรมและอีเวนต์
    "Event Organization and Entertainment Venues",
    "Concert and Exhibition Organizers",
    "Pop-up Events and Festivals"
]


CONTENT_STYLE = [
    "Informative", "Educational", "Promotional", "Entertaining",
    "Expert-driven", "Storytelling", "Aesthetic", "Relatable",
    "Tutorial-based",        
    "Behind-the-scenes",      
    "Challenge / Trend-based",
    "Review & Comparison", 
    "Motivational / Inspiring"
]

TARGET_AUDIENCE = [
    "Age 18–24 (Gen Z, students)",
    "Age 25–35 (First jobbers, professionals)",
    "Age 36–50 (Family-oriented, financially stable)",
    "Primarily female", "Primarily male", "Tech-savvy", "Health-conscious", "Budget-conscious",
    # New
    "Parents with young children", "Pet owners", "Fitness-focused adults",
    "Homeowners", "Urban office workers",
    "Parents seeking early education solutions",
    "Parents interested in bilingual or international education",
    "Parents focused on child development",
    "Parents who value online learning platforms"
]

CONTENT_THEMES_EN = {
    "Finance": ["Saving tips", "ETF investment", "Understanding DRs", "Market summaries", "Financial planning"],
    "Food": ["Food reviews", "Home cooking", "Healthy recipes", "Clean eating", "Delivery reviews"],
    "Travel": ["Domestic travel", "International trips", "Accommodation reviews", "Budget travel", "Photo spots"],
    # New
    "Retail": ["Product promotions", "Store tours", "Shopping tips", "New launches", "Flash deals"],
    "Services": ["Beauty treatments", "Salon experiences", "Fitness tips", "Massage reviews", "Clinic walkthrough"],
    "Home & Living": ["Home organization", "Interior design tips", "Appliance reviews"],
    "Pets": ["Pet care routines", "Pet food reviews", "Vet Q&A", "Cute moments"],
    "Kids": ["Toy reviews", "Parenting tips", "Kids learning", "Family activities"],
    "Real Estate": ["Home tours", "Condo reviews", "Property investment tips"]
}

def generate_brand_analysis_and_kol_prompt_from_file(facebook_path: str = None, website_path: str = None):
    import json

    info_parts = []
    business_reference_input = ""

    if facebook_path:
        with open(facebook_path, encoding="utf-8") as f:
            fb_data = json.load(f)

        name = fb_data.get("page_name", "")
        about = fb_data.get("about", "")
        category = fb_data.get("category", "")
        posts = get_all_post_texts(fb_data, max_posts=20)
        hashtags = count_top_hashtags(fb_data)
        hashtags_list = "\n".join([f"- {tag} ({count} times)" for tag, count in hashtags])

        business_reference_input += f'Analyze this Facebook Page: "{name}"\n'

        info_parts.append(f"""
[Facebook Page]
Page Name: {name}
Category: {category}
About: {about}

Top Hashtags:
{hashtags_list}

Sample Posts:
{posts}
        """.strip())

    if website_path:
        with open(website_path, encoding="utf-8") as f:
            web_data = json.load(f)

        title = web_data.get("title", "")
        description = web_data.get("description", "")
        content = "\n\n".join(
            [c["content"] for c in web_data.get("content_posts", []) if c.get("content")]
        )[:1500]

        business_reference_input += f'Analyze this Website: "{title}"\n'

        info_parts.append(f"""
[Website]
Website Title: {title}
Meta Description: {description}

Website Content Sample:
{content}
        """.strip())

    if not info_parts:
        return "❌ No Facebook Page or Website data found for analysis"

    context_block = "\n\n".join(info_parts)

    prompt = f"""
You are a senior Thai marketing strategist with deep experience analyzing brands and finding TikTok KOLs (creators) who can support product visibility, drive audience engagement, and generate sales impact.

Your task is to analyze the following brand information, and then produce structured marketing insights to help match the brand with suitable KOLs.  
This will be used to guide a campaign focused on **brand awareness, product relevance, and conversion**.

---

📌 INSTRUCTIONS

- **DO NOT** include hashtags or phrases that mention specific brands or company names.
- Use only **generic, creator-style hashtags** commonly seen in TikTok content for this niche.
- Focus on behavior of KOLs — how they tag, describe, or caption their content.
- Use **Thai-language hashtags and captions** unless English terms are clearly common in this vertical.

KOLs must be independent influencers — not representatives of a specific product, business, or company.
🧠 Think like a **KOL/creator** — not a customer.
- What words would creators use to describe their videos or titles?
- Who is the actual **decision-maker** in the buying process? (Does not have to be the end user.)
- Analyze the **tone, audience type, and core interest group** this brand speaks to — not just product features.

Return your findings in the following structure:
json
{{
  "hashtags": ["#...", "#..."],
  "search": ["...", "..."],

  "business_type": ["..."],  // Choose from: {', '.join(TYPE_OF_BUSINESS)}
  "content_style": ["..."],  // Choose from: {', '.join(CONTENT_STYLE)}
  "target_audience": ["..."],  // Choose from: {', '.join(TARGET_AUDIENCE)},

  "content_themes": {{
    "Category": ["...", "..."]
  }},

  "clues": ["...", "..."]
}}
+ Focus on behavior of KOLs — how they tag, describe, or caption their content to **connect with the real buyer group**.
+ Hashtags and search terms must reflect the natural language and mindset of the buyer or decision-maker, not just the service provider.
+ Example: For parenting-focused education products, hashtags like "#พัฒนาทักษะลูก", "#แม่รีวิวคลาสเรียน", or phrases like "ประสบการณ์แม่มือใหม่เลือกโรงเรียนออนไลน์" are preferred over generic course descriptions.

{business_reference_input}

📄 Context Data: {context_block} """.strip()
    
    return prompt

def extract_block(name: str, text: str) -> str:
    pattern = rf"\"{re.escape(name)}\":\s*(\{{.*?\}}|\[.*?\])(?=,?\n\s*\"|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else ""

def extract_json_field(text: str, field: str) -> Union[list, dict]:
    block = extract_block(field, text)
    try:
        return json.loads(block)
    except Exception:
        return []

def normalize_extracted_tags(result: dict) -> dict:
    return result

def extract_structured_blocks(text: str) -> Dict:
    print(text)
    return {
        "business_type": extract_json_field(text, "business_type"),
        "content_style": extract_json_field(text, "content_style"),
        "target_audience": extract_json_field(text, "target_audience"),
        "content_themes": extract_json_field(text, "content_themes"),
        "clues": extract_json_field(text, "clues"),
        "hashtags": extract_json_field(text, "hashtags"),
        "search": extract_json_field(text, "search")
    }

def analyze_brand_prompt_and_extract(prompt: str) -> Dict:
    print("เริ่มวิเคราะห์ Brand...")
    response_text = call_chatgpt(prompt)
    raw_result = extract_structured_blocks(response_text)
    clean_result = normalize_extracted_tags(raw_result)
    return clean_result