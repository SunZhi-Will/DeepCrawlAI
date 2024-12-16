"""
Install an additional SDK for JSON schema support Google AI Python SDK

$ pip install google.ai.generativelanguage
"""

import os
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def gemini_response(user_query, web_content):
    # Create the model
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )

    chat_session = model.start_chat(
        history=[{
            "role": "user",
            "parts": [{"text": """根據網頁內容，整理出使用者需要的資料以及可能會需要查閱的相關 URL，並以 JSON 格式回傳。
JSON格式範例：
{
"content": "完整的使用者需求內容",
"related_links": [
{
"title": "相關連結標題",
"url": "相關連結網址"
}
]
}"""}]
        }]
    )

    # 組合使用者查詢和網頁內容
    prompt = f"""
使用者需求：
{user_query}

網頁內容：
{web_content}
"""

    response = chat_session.send_message(prompt)
    return response.text