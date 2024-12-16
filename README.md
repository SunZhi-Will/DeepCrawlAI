<div align="center">

# DeepCrawlAI

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/your-username/DeepCrawlAI/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![Gemini](https://img.shields.io/badge/Gemini-1.5-flash-blue.svg)](https://github.com/your-username/DeepCrawlAI/blob/main/assets/gemini.png)

DeepCrawlAI 是一個結合網頁爬蟲和 AI 分析的智能爬蟲工具，能夠深度爬取網頁內容並使用 Gemini AI 進行智能分析。

</div>

## 功能特點

- 智能網頁爬蟲，支援多層次深度爬取
- 使用 Google Gemini AI 進行內容分析
- 支援動態網頁爬取（Selenium）和靜態網頁爬取
- 自動提取相關連結並遞迴爬取
- 將網頁內容轉換為結構化的 Markdown 格式
- 防止重複爬取相同網頁

## 安裝需求
```bash
pip install -r requirements.txt
```

主要依賴：
- google.generativeai
- beautifulsoup4
- selenium
- cloudscraper
- html2text
- python-dotenv

## 環境設定

1. 創建 `.env` 檔案並設定：

```env
GEMINI_API_KEY=your_gemini_api_key
```

2. 確保已安裝 Chrome 瀏覽器（用於 Selenium）

## 使用方法

```python
from src.main import crawl_with_depth
```

## 設定起始URL和查詢需求

```python   
base_url = "https://example.com"
user_query = "你的查詢需求"
```

## 開始爬取

```python
result = crawl_with_depth(user_query, base_url, max_depth=2)
```

## 專案結構

```
DeepCrawlAI/
├── src/
│ ├── core/
│ │ ├── crawler.py # 爬蟲核心功能
│ │ └── gemini.py # Gemini AI 整合
│ └── main.py # 主程式
├── .env # 環境變數
└── README.md
```

## 注意事項

- 請確保遵守目標網站的爬蟲政策
- 建議設定適當的爬取延遲，避免對目標網站造成負擔
- Gemini API 可能有使用限制，請注意配額使用情況

## 授權條款

本專案採用 MIT 授權條款 - 詳見 LICENSE 檔案