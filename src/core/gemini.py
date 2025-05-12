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
        "temperature": 0.1,  # 進一步降低溫度以提高精確性
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )

    # 檢查是否為信用卡查詢
    is_credit_card_query = any(keyword in user_query.lower() for keyword in ['信用卡', '卡片', '信用卡優惠', '卡別', 'credit card', 'card'])

    # 根據查詢類型使用不同的提示詞
    if "請根據以上內容" in user_query and "JSON格式" in user_query:
        # 用於最終分析並輸出 JSON 的提示詞
        chat_session = model.start_chat(
            history=[{
                "role": "user",
                "parts": [{"text": """請分析信用卡優惠內容，並以 JSON 格式回傳。請嚴格遵守以下規則：

1. 必須返回有效、格式正確的 JSON
2. 不要包含任何 JSON 之外的說明文字
3. 不要在 JSON 中使用註釋
4. 不要使用 JSON 格式以外的任何標記或格式
5. 確保所有雙引號、逗號、括號的使用正確
6. 只有一個根級別的物件，其中包含一個 "cards" 陣列
7. 回應內容須純 JSON 格式, 確保沒有多餘的文字
8. 請確保卡片資訊皆在 cards 陣列中，不要在陣列外新增卡片資訊
9. 如果發現多張卡片，全部資訊必須包含在 cards 陣列內
10. 確保每張卡片的結構一致
11. 請不要包含已停止申辦的卡片，只列出當前可申辦的信用卡
12. 盡可能提取卡片的圖片URL
13. 盡可能提取卡片的詳情頁面連結

JSON 格式必須為：
{
  "cards": [
    {
      "cardName": "信用卡名稱",
      "issuer": "發卡銀行",
      "cardType": "卡片類型",
      "annualFee": "年費資訊",
      "rewardType": "回饋類型",
      "imageUrl": "卡片圖片URL",
      "cardLink": "卡片詳情頁面連結",
      "benefits": [
        {
          "category": "優惠類別",
          "description": "詳細描述",
          "rate": "回饋比率"
        }
      ]
    },
    {
      "cardName": "第二張信用卡名稱",
      "issuer": "發卡銀行",
      "cardType": "卡片類型",
      "annualFee": "年費資訊",
      "rewardType": "回饋類型",
      "imageUrl": "卡片圖片URL",
      "cardLink": "卡片詳情頁面連結",
      "benefits": [
        {
          "category": "優惠類別",
          "description": "詳細描述",
          "rate": "回饋比率"
        }
      ]
    }
  ]
}

記住：所有卡片資訊都必須在 cards 陣列中，不要在外面新增卡片屬性。請只列出當前可申辦的信用卡，不要包含已停止申辦的卡片。
對於圖片URL，請注意從網頁內容中找到img標籤的src屬性，確保提取完整的URL。
對於卡片連結，請優先提取卡片詳情頁面的URL，確保使用完整的網址。"""
}]
            }]
        )
    elif "請根據以上內容" in user_query:
        # 用於一般最終分析的提示詞
        chat_session = model.start_chat(
            history=[{
                "role": "user",
                "parts": [{"text": """請分析內容並提供清晰的總結回應。
如果是優惠內容，請以以下格式回傳：
{
    "cards": [
        {
            "cardName": "卡片名稱",
            "issuer": "發卡銀行",
            "cardType": "卡片類型",
            "cardImage": "圖片URL",
            "cardLink": "卡片詳情頁面連結",
            "rewardType": "回饋類型：現金回饋/紅利點數",
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
                    "category": "日本/韓國地區一般消費",
                    "rate": "3%"
                },
                {
                    "category": "其他海外地區一般消費",
                    "rate": "1%"
                }
            ],
            "other": []
        }
    ]
}

請務必關注網頁內容中的圖片和連結資訊，提取正確的卡片圖片URL和詳情頁面連結。確保提供的URL是完整的網址，可直接訪問。
對於相同卡片出現在不同網站的情況，建議保留為不同的卡片記錄，以保留每個來源網站的特定連結和圖片資訊。"""}]
            }]
        )
    elif is_credit_card_query:
        # 專門用於信用卡爬蟲過程的強化提示詞
        chat_session = model.start_chat(
            history=[{
                "role": "user",
                "parts": [{"text": """你是一個專門分析信用卡資訊的專家。請仔細分析網頁內容，找出所有當前可申辦的信用卡相關的資料和連結。

我需要你特別關注：
1. 頁面中所有提到的當前可申辦的信用卡名稱及其詳細資訊
2. 每張可申辦卡片的優惠內容和特色
3. 頁面中所有指向特定信用卡頁面的連結，特別關注帶有卡片名稱或卡片類型的連結
4. 導航菜單中的信用卡相關連結
5. 產品比較或列表頁面中的卡片連結
6. 卡片的圖片URL（尋找img標籤，特別是包含卡片圖像的img元素）

請執行以下步驟：
1. 先識別頁面上所有的連結元素（a標籤）及其URL
2. 分析連結的文本內容和URL路徑，優先選取：
   - URL路徑中包含 "card", "credit", "bank" 等關鍵詞的連結
   - 連結文本中明確提及卡片名稱的連結
   - 連結的title或alt屬性中包含卡片相關描述的連結
3. 識別與每個卡片相關聯的圖片（img標籤），提取其src屬性中的URL
4. 排除明顯不相關的連結，如登入、註冊、首頁等一般性導航連結
5. 檢查連結是否為真正的卡片產品頁面，而非一般資訊頁面

請以JSON格式回傳，包含以下資訊：
{
  "creditCards": [
    {
      "cardName": "卡片名稱（盡可能提取完整精確的名稱）",
      "description": "卡片簡介（如有）",
      "imageUrl": "卡片圖片的URL"
    }
  ],
  "related_links": [
    {
      "title": "連結的精確描述或標題（優先使用卡片名稱）",
      "url": "完整的URL路徑（包含http/https前綴）",
      "description": "連結對應卡片的簡短描述或特點",
      "imageUrl": "該卡片的圖片URL（如果在連結附近找到相關圖片）",
      "relevance": "高/中/低（評估此連結與查詢卡片的相關性）"
    }
  ]
}

請務必檢查URL是否完整，如果發現相對路徑，請嘗試推斷出完整URL。對於相關度高的卡片連結，給予更多細節描述。圖片URL也應該是完整的，如果是相對路徑，請嘗試使用與頁面相同的基本URL進行轉換。"""
}]
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
"url": "相關連結網址",
"description": "連結內容簡短描述"
}
]
}"""}]
            }]
        )

    # 增強對信用卡資訊的處理
    enhanced_query = user_query
    if is_credit_card_query and "請根據以上內容" not in user_query:
        enhanced_query = f"""請詳細分析此頁面中的所有當前可申辦的信用卡資訊。
特別注意：
1. 識別頁面中所有的信用卡產品
2. 提取所有可能通往特定信用卡詳情頁面的連結
3. 區分主要展示卡片和次要展示卡片
4. 檢查導航菜單和頁面底部可能包含的卡片連結
5. 對於每個卡片連結，評估其相關性和內容完整度

{user_query}"""

    prompt = f"""
使用者需求：
{enhanced_query}

網頁內容：
{web_content}
"""

    response = chat_session.send_message(prompt)
    
    # 嘗試優化 JSON 回應格式（如果是信用卡查詢）
    if is_credit_card_query and "請根據以上內容" not in user_query:
        try:
            import json
            response_text = response.text
            # 嘗試解析 JSON
            response_json = json.loads(response_text)
            
            # 優化卡片連結
            if "related_links" in response_json:
                # 根據相關性排序連結
                if any("relevance" in link for link in response_json["related_links"]):
                    relevance_mapping = {"高": 3, "中": 2, "低": 1}
                    response_json["related_links"] = sorted(
                        response_json["related_links"], 
                        key=lambda x: relevance_mapping.get(x.get("relevance", "低"), 0),
                        reverse=True
                    )
                
                # 確保所有URL都是完整的
                for link in response_json["related_links"]:
                    if "url" in link and link["url"] and not (link["url"].startswith("http://") or link["url"].startswith("https://")):
                        # 嘗試修復相對URL
                        if link["url"].startswith("/"):
                            # 從原始URL提取域名
                            import re
                            domain_match = re.search(r'(https?://[^/]+)', web_content[:1000])
                            if domain_match:
                                link["url"] = domain_match.group(1) + link["url"]
            
            # 轉回JSON字符串
            return json.dumps(response_json, ensure_ascii=False)
        except Exception as e:
            # 如果解析失敗，返回原始回應
            print(f"JSON 優化處理失敗: {e}")
            return response.text
    
    return response.text