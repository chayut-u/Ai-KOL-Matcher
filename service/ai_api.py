import os , json
from openai import OpenAI
import re

def call_chatgpt(prompt: str,temperature=0.7) -> str:
    api_key = os.getenv("CHATGPT_TOKEN")  
    client = OpenAI(api_key=api_key)  

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a professional brand analyst."},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature
    )
    return response.choices[0].message.content

def call_chatgpt_kol_analys(prompt: str,temperature=0.3) -> str:
    api_key = os.getenv("CHATGPT_TOKEN")  
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a professional brand and influencer analyst. Your job is to understand brand identity from content, then help match or evaluate TikTok influencers who align with the brand’s tone, audience, and message."},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature
    )
    return response.choices[0].message.content


def extract_json_from_text(text: str):
    """
    พยายามหา JSON ที่อยู่ในข้อความขนาดใหญ่ เช่น จาก Perplexity response
    """
    try:
        # ลองโหลดแบบ JSON ตรง ๆ ก่อน
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    print("⚠️ JSON parse failed. Trying to locate embedded JSON...")

    # พยายามดึงส่วนที่เป็น JSON ด้วย regex (จับ list หรือ object)
    match = re.search(r"(\[\s*{.*?}\s*])", text, re.DOTALL)
    if not match:
        match = re.search(r"({\s*\".*?}\s*)", text, re.DOTALL)
    
    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except Exception as e:
            print(f"❌ Failed to load extracted JSON: {e}")
            return None
    
    print("❌ No JSON-like structure found.")
    return None


def search_kols_with_perplexity(prompt: str, model: str = "sonar-pro") -> list:
    api_key = os.getenv("PERPLEXITY_API_KEY")
    client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")

    messages = [
        {
            "role": "system",
            "content": (
                "You are a professional KOL researcher specializing in the Thai market.\n"
                "Your task is to find **real and verifiable Thai TikTok creators (KOLs)** who are a strong match for the brand’s target audience.\n"
                "✅ Include only KOLs who meet ALL of the following criteria:\n"
                "- Create content **entirely in Thai** for Thai audiences\n"
                "- Are real individuals (not brands, celebrities, or repost pages)\n"
                "- Have a valid, public, and verifiable TikTok profile link\n"
                "- Have content or influence clearly related to the brand’s business or audience\n"
                "- Can be found on TikTok.com or Google.co.th"
            )
        },
        {"role": "user", "content": prompt}
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
        frequency_penalty=0.2
    )

    content = response.choices[0].message.content.strip()
    print("🧠 Raw Perplexity Response:\n", content)

    result = extract_json_from_text(content)

    if isinstance(result, list):
        return result
    elif isinstance(result, dict):
        return [result]
    else:
        return []


def search_kols_with_gpt(prompt: str) -> list:
    api_key = os.getenv("CHATGPT_TOKEN")
    client = OpenAI(api_key=api_key)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a professional TikTok KOL researcher for Thai brands.\n"
                "Your job is to identify **real, well-aligned, and verifiable Thai TikTok creators (KOLs)** "
                "who can help promote the brand and drive sales.\n"
                "✅ Each KOL must:\n"
                "- Be a real person (not a company, bot, or repost account)\n"
                "- Have content that is **100% in Thai language**, clearly targeting Thai audiences\n"
                "- Match the brand’s business type, content style, or target audience\n"
                "- Provide a public, working TikTok profile link\n"
                "- Be findable via TikTok.com or Google.co.th"
            )
        },
        {"role": "user", "content": prompt}
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.3,
        frequency_penalty=0.2,
        presence_penalty=0.1
    )

    content = response.choices[0].message.content.strip()
    print("🧠 Raw GPT Response:\n", content)

    result = extract_json_from_text(content)

    if isinstance(result, list):
        return result
    elif isinstance(result, dict):
        return [result]
    else:
        return []
