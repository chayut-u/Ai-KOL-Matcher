import streamlit as st
import pandas as pd
from service import customer_fn as customer
from service import brand_analysis as brand_analysis
from service import ai_api as ai_api
from service import search_kol as search_kol
from dotenv import load_dotenv
import time
import io
import json

# โหลด .env
load_dotenv()

# Tier Classification
def classify_tier(followers):
    if followers < 10_000:
        return "Nano"
    elif followers <= 500_000:
        return "Micro"
    elif followers <= 1_000_000:
        return "Macro"
    else:
        return "Mega"

# UI
st.title("TikTok KOL Matcher 🧠")

with st.form(key="input_form"):
    website_url = st.text_input("🌐 Website URL")
    facebook_url = st.text_input("📘 Facebook Fan Page URL")
    submitted = st.form_submit_button("🔍 Analyze and Match")

# Backend Logic
@st.cache_data
def run_kol_matching_logic(website, facebook):
    progress_text.write("🔍 กำลังวิเคราะห์ข้อมูลจาก Website / Facebook ...")
    facebook_result, web_result = customer.extract_content_from_link(
        facebook_link=facebook,
        website_link=website
    )

    facebook_path = None
    website_path = None

    if facebook_result:
        facebook_path = customer.save_result_to_log(facebook_result, facebook_result["url"])
    if web_result:
        website_path = customer.save_result_to_log(web_result, web_result["url"])

    merged_list = []
    seen_usernames = set()
    brand_detail = {}

    for attempt in range(2):
        try:
            if facebook_path or website_path:
                prompt = brand_analysis.generate_brand_analysis_and_kol_prompt_from_file(
                    facebook_path=facebook_path,
                    website_path=website_path
                )
                progress_text.write(f"🔍 วิเคราะห์ Brand...")
                brand_detail = brand_analysis.analyze_brand_prompt_and_extract(prompt)
                st.markdown("✅ **Brand Insight Extracted:**")
                st.json(brand_detail)
            else:
                st.error("❌ ไม่พบข้อมูล Facebook หรือ Website สำหรับการวิเคราะห์")
                return [], {}

            progress_text.write(f"🔍 กำลังหา KOL ที่เหมาะสม...")
            search_kol_prompt_th = search_kol.build_tiktok_kol_prompt_thai(brand_detail)
            search_kol_prompt_en = search_kol.build_tiktok_kol_prompt_en(brand_detail)

            try:
                result_th = search_kol.search_kol_main(search_kol_prompt_th, brand_detail)
            except:
                result_th = []

            try:
                result_en = search_kol.search_kol_main(search_kol_prompt_en, brand_detail)
            except:
                result_en = []

            result_api_fy = search_kol.search_kol_by_apify(brand_detail)

            for kol in (result_th or []) + (result_en or []) + result_api_fy:
                username = kol.get("username", "").lower()
                profile_link = kol.get("profile_link", "").lower()
                key = f"{username}|{profile_link}"
                if key not in seen_usernames:
                    seen_usernames.add(key)
                    merged_list.append(kol)

            break

        except Exception as e:
            print(f"[RETRY] Error during search_kol_main (Attempt {attempt+1}/2): {e}")
            time.sleep(5)

    if not merged_list:
        st.error("❌ ไม่สามารถหา KOL ที่ตรงกลุ่มได้ในขณะนี้ โปรดลองอีกครั้ง...")

    return merged_list, brand_detail

# Display Results
if submitted:
    website_url = website_url.strip() if website_url.strip() else None
    facebook_url = facebook_url.strip() if facebook_url.strip() else None

    if not website_url and not facebook_url:
        st.warning("⚠️ กรุณากรอกอย่างน้อย 1 ช่อง: Website หรือ Facebook URL")
    else:
        progress_text = st.empty()
        with st.spinner("🔍 Matching KOLs based on brand analysis..."):
            results, brand_detail = run_kol_matching_logic(website_url, facebook_url)

            if results:
                df = pd.DataFrame(results)
                df["tier"] = df["followers"].apply(classify_tier)

                st.success("✅ Found matching KOLs!")

                for tier in ["Nano", "Micro", "Macro", "Mega"]:
                    tier_df = df[df["tier"] == tier]
                    if not tier_df.empty:
                        st.subheader(f"🔹 {tier}-Tier KOLs ({len(tier_df)} คน)")
                        st.dataframe(tier_df[["username", "profile_link", "followers", "suitable_for"]])

                with st.expander("📄 Reasoning Behind Matches"):
                    for r in results:
                        st.markdown(f"**{r['username']}**: {r['reason']}")

                # ✅ Prepare CSV Export
                combined_info = {
                    "Website URL": website_url,
                    "Facebook URL": facebook_url,
                    "Brand Analysis": brand_detail,
                    "Matched KOLs": df.to_dict(orient="records")
                }

                # Convert to DataFrame (simple version)
                csv_rows = []
                for kol in df.to_dict(orient="records"):
                    csv_rows.append({
                        "Website URL": website_url,
                        "Facebook URL": facebook_url,
                        "Business Type": ", ".join(brand_detail.get("business_type", [])),
                        "Target Audience": ", ".join(brand_detail.get("target_audience", [])),
                        "Content Style": ", ".join(brand_detail.get("content_style", [])),
                        "Content Themes": ", ".join(brand_detail.get("content_themes", {}).get("Category", [])),
                        "Username": kol.get("username", ""),
                        "Profile Link": kol.get("profile_link", ""),
                        "Followers": kol.get("followers", ""),
                        "Tier": kol.get("tier", ""),
                        "Suitable For": kol.get("suitable_for", ""),
                        "Reason": kol.get("reason", "")
                    })

                csv_df = pd.DataFrame(csv_rows)

                buffer = io.StringIO()
                csv_df.to_csv(buffer, index=False, encoding="utf-8-sig")

                st.download_button(
                    "📥 Download full result as CSV",
                    data=buffer.getvalue(),
                    file_name="matched_kols_full.csv",
                    mime="text/csv"
                )
