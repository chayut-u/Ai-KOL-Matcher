
# 🎯 TikTok KOL Matcher Tool

A Python application to **find relevant TikTok creators (KOLs)** for specific business needs.  
It automatically **extracts**, **processes**, and **matches** TikTok profiles using APIs and web scraping.

---

## 🛠 Setup Instructions

### 1. Create and activate a virtual environment
```bash
virtualenv venv --python=python3.12.2
```

Activate the environment:
- Windows:
  ```bash
  venv\Scripts\activate
  ```
- Mac/Linux:
  ```bash
  source venv/bin/activate
  ```

---

### 2. Install project dependencies
```bash
pip install -r requirements.txt
```

---

### 3. Set up environment variables
Create a `.env` file in the root directory with the following content:
```env
APIFY_TOKEN=your_apify_api_token
PERPLEXITY_API_KEY=your_perplexity_api_key
CHATGPT_TOKEN=your_openai_project_token
```
> Replace with your actual API keys.

---

### 4. Run the application
If it is a console app:
```bash
python app.py
```

If it is a Streamlit app:
```bash
streamlit run app.py
```

---

## 📈 Output
- The tool will generate a list of **relevant TikTok profile links**.
- Results will be displayed in the console or a web UI (Streamlit).

---

## ⚙️ Tech Stack
- Python 3.12.2
- Virtualenv
- APIs:
  - Apify (Web Scraping)
  - Perplexity AI (Search Enhancement)
  - OpenAI (Content Analysis)

---

## 📢 Important Notes
- Ensure a stable internet connection.
- Make sure your API keys are active and have sufficient quota.
- If any dependency errors occur, install missing modules manually:
  ```bash
  pip install <missing-module>
  ```