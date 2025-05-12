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

    # 根據查詢類型使用不同的提示詞
    if "請根據以上內容" in user_query:
        # 用於最終分析的提示詞
        chat_session = model.start_chat(
            history=[{
                "role": "user",
                "parts": [{"text": """請分析內容並提供清晰的總結回應。
如果是優惠內容，請以以下格式回傳：
{
    "cards": [
        {
            "cardName": [卡片名稱],
            "cardImage": 如果圖片URL是相對路徑(例如/banking/images/...)，請在前面加上網站的完整網址,
            "rewardType": 回饋類型：現金回饋/紅利點數,
            "domestic": [
                {
                    "category": "一般消費",
                    "rate": "1%"
                },
                {
                    "category": "保費",
                    "rate": "0.5% 或最高12期分期0利率"
                }
            ],
            "foreign": [
                {
                    "category": "日本/韓國地區一般 消費",
                    "rate": "3%"
                },
                {
                    "category": "其他海外地區一般消費",
                    "rate": "1%"
                }
            ],
            "other": []
        },
    ]
}"""}]
            }]
        )
    else:
        # 原有的用於爬蟲過程中的提示詞
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

    prompt = f"""
使用者需求：
{user_query}

網頁內容：
{web_content}
"""

    response = chat_session.send_message(prompt)
    return response.text