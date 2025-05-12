import core.gemini as gemini
import core.crawler as crawler
from bs4 import BeautifulSoup
import json
import os
import atexit
import concurrent.futures
import time
from datetime import datetime

# 註冊程式結束時的清理函數
atexit.register(crawler.cleanup)

def crawl_with_depth(user_query, base_url, max_depth=2, current_depth=0, visited_urls=None, max_links_per_page=None, priority_keywords=None):
    if visited_urls is None:
        visited_urls = set()
    
    if priority_keywords is None:
        priority_keywords = ["信用卡", "卡片", "優惠", "card", "credit"]
    
    if current_depth >= max_depth or base_url in visited_urls:
        return None
    
    visited_urls.add(base_url)
    print(f"正在爬取第 {current_depth + 1} 層: {base_url}")
    
    # 獲取當前頁面的內容
    content = crawler.url_to_markdown(base_url, use_selenium=True)
    if content is None:
        return None
    
    # 使用 Gemini 分析內容並取得相關連結
    response = gemini.gemini_response(user_query, content)
    
    try:
        # 解析 Gemini 回傳的 JSON
        result = json.loads(response)
        related_links = result.get('related_links', [])
        
        # 如果有相關性評分的連結優先處理
        if related_links and "relevance" in related_links[0]:
            # 連結已經在 gemini.py 中排序了，這裡不需要再排序
            print(f"收到 {len(related_links)} 個按相關性排序的連結")
        else:
            # 用於舊版本的回應格式或沒有相關性評分的情況
            # 根據優先關鍵詞給連結評分
            for link in related_links:
                # 計算連結標題和URL中包含優先關鍵詞的數量
                score = sum(1 for keyword in priority_keywords if keyword in (link.get("title", "").lower() + link.get("url", "").lower()))
                link["priority_score"] = score
            
            # 按評分排序連結
            related_links = sorted(related_links, key=lambda x: x.get("priority_score", 0), reverse=True)
            print(f"找到 {len(related_links)} 個連結並按優先順序排序")
        
        # 限制每頁最多爬取的連結數量（如果設定了限制）
        if max_links_per_page is not None and len(related_links) > max_links_per_page:
            print(f"連結數量過多，限制為 {max_links_per_page} 個")
            related_links = related_links[:max_links_per_page]
        
        # 如果是最後一層，就不需要再爬取子頁面
        if current_depth == max_depth - 1:
            return {
                'url': base_url,
                'content': content,
                'sub_pages': []
            }
        
        # 準備子頁面爬取
        sub_pages = []
        valid_links = []
        
        # 先過濾有效連結
        for link in related_links:
            url = link.get('url')
            if url and url.startswith('http') and url not in visited_urls:
                valid_links.append(link)
        
        # 使用並行處理爬取子頁面
        if valid_links:
            # 建立線程池
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # 提交爬取任務
                future_to_link = {
                    executor.submit(
                        crawl_with_depth, 
                        user_query, 
                        link.get('url'), 
                        max_depth, 
                        current_depth + 1, 
                        visited_urls,
                        max_links_per_page,
                        priority_keywords
                    ): link for link in valid_links
                }
                
                # 獲取結果
                for future in concurrent.futures.as_completed(future_to_link):
                    link = future_to_link[future]
                    try:
                        sub_content = future.result()
                        if sub_content:
                            sub_pages.append({
                                'url': link.get('url'),
                                'title': link.get('title', ''),
                                'content': sub_content
                            })
                    except Exception as exc:
                        print(f'爬取 {link.get("url")} 時發生錯誤: {exc}')
        
        return {
            'url': base_url,
            'content': content,
            'sub_pages': sub_pages
        }
    
    except json.JSONDecodeError:
        print(f"JSON 解析錯誤: {response}")
        return {
            'url': base_url,
            'content': content,
            'sub_pages': []
        }

def crawl_multiple_urls(user_query, base_urls, max_depth=2, max_links_per_page=None, priority_keywords=None):
    """爬取多個起始 URL 並將結果合併"""
    all_results = []
    visited_urls = set()
    saved_files = []
    
    # 並行爬取起始 URL
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(base_urls)) as executor:
        # 提交爬取任務
        future_to_url = {
            executor.submit(
                crawl_with_depth, 
                user_query, 
                url, 
                max_depth, 
                0, 
                visited_urls,
                max_links_per_page,
                priority_keywords
            ): url for url in base_urls
        }
        
        # 獲取結果
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                print(f"開始爬取 URL: {url}")
                result = future.result()
                if result:
                    # 每個 URL 爬取完成後立即儲存結果
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'data/crawl_result_{url.replace("://", "_").replace("/", "_").replace(".", "_")}_{timestamp}.json'
                    saved_file = save_crawl_result(result, filename)
                    saved_files.append(saved_file)
                    print(f"URL {url} 爬蟲結果已儲存至: {saved_file}")
                    all_results.append(result)
            except Exception as exc:
                print(f'爬取 {url} 時發生錯誤: {exc}')
    
    # 儲存所有結果的合併版本
    if all_results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        combined_filename = f'data/crawl_result_combined_{timestamp}.json'
        save_crawl_result(all_results, combined_filename)
        saved_files.append(combined_filename)
        print(f"所有爬蟲結果合併版本已儲存至: {combined_filename}")
    
    return all_results, saved_files

def save_crawl_result(result, filename=None):
    # 創建 data 目錄（如果不存在）
    if not os.path.exists('data'):
        os.makedirs('data')
    
    # 如果沒有指定檔名，使用時間戳建立檔名
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'data/crawl_result_{timestamp}.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return filename

def load_crawl_result(filename):
    """載入爬蟲結果，並處理可能的格式差異"""
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 檢查並適應不同的資料結構
    if isinstance(data, list) and len(data) == 1:
        # 有時資料可能被儲存為單元素列表
        return data[0]
    
    return data

def combine_content(results):
    """整合所有爬取結果的內容"""
    combined_content = "所有頁面內容：\n"
    
    # 檢查 results 的型別
    if isinstance(results, dict):
        # 如果 results 是一個字典，可能是單一爬取結果
        results = [results]
    elif isinstance(results, str):
        # 如果 results 是一個字串，直接返回
        return f"所有頁面內容：\n{results}\n"
    
    # 遍歷所有結果
    for result in results:
        try:
            # 檢查 result 是否是字典且包含必要的鍵
            if isinstance(result, dict) and 'url' in result and 'content' in result:
                combined_content += f"\n主頁面 ({result['url']})：\n{result['content']}\n"
                
                # 處理子頁面
                if 'sub_pages' in result and isinstance(result['sub_pages'], list):
                    for sub_page in result['sub_pages']:
                        if isinstance(sub_page, dict) and 'title' in sub_page and 'url' in sub_page and 'content' in sub_page:
                            if isinstance(sub_page['content'], dict) and 'content' in sub_page['content']:
                                # 如果子頁面的 content 是一個字典且包含 content 鍵
                                sub_content = sub_page['content']['content']
                            elif isinstance(sub_page['content'], dict) and 'url' in sub_page['content']:
                                # 遞迴處理巢狀結構
                                sub_content = combine_content([sub_page['content']])
                            else:
                                # 否則直接使用 content
                                sub_content = sub_page['content']
                            
                            combined_content += f"\n子頁面：{sub_page['title']} ({sub_page['url']}):\n{sub_content}\n"
            elif isinstance(result, str):
                # 如果 result 是一個字串，直接添加
                combined_content += f"\n頁面內容：\n{result}\n"
            else:
                print(f"警告：發現不符合預期格式的爬蟲結果: {type(result)}")
                if isinstance(result, dict):
                    print(f"可用的鍵：{list(result.keys())}")
        except Exception as e:
            print(f"處理爬蟲結果時發生錯誤: {e}")
            print(f"結果類型: {type(result)}")
            if isinstance(result, dict):
                print(f"可用的鍵: {list(result.keys())}")
    
    return combined_content

def main():
    # 檢查是否有已存在的爬蟲結果
    latest_result_file = None
    if os.path.exists('data'):
        files = [f for f in os.listdir('data') if f.startswith('crawl_result_')]
        if files:
            latest_result_file = os.path.join('data', sorted(files)[-1])
    
    # 如果沒有找到存檔或強制重新爬取
    if latest_result_file is None:
        print("開始新的爬蟲...")
        # 定義多個起始 URL
        base_urls = [
            "https://www.fubon.com/banking/personal/credit_card/all_card/all_card.htm",  # 富邦銀行
            # "https://ecard.bot.com.tw/Pages/Cards/P10.html",  # 台灣銀行
            # "https://www.cathaybk.com.tw/cathaybk/personal/product/credit-card/cards/",  # 國泰世華銀行
            # "https://www.esunbank.com.tw/bank/pershttps://www.esunbank.com/zh-tw/personal/credit-card/intro",  # 玉山銀行
            # "https://www.bankchb.com/frontend/mashup.jsp?funcId=f0f6e5d215",  # 彰化銀行
            # "https://bank.sinopac.com/sinopacBT/personal/credit-card/introduction/list.html",  # 永豐銀行
            # "https://www.taishinbank.com.tw/TSB/personal/credit/intro/overview/",  # 台新銀行
            # "https://www.tcb-bank.com.tw/personal-banking/credit-card/intro/overview",  # 合作金庫
            # "https://card.firstbank.com.tw/sites/card/CreditCardList",  # 第一銀行
            # "https://www.megabank.com.tw/personal/credit-card/card/overview?Card%20Type=All,Bank%20Card,Co%20Branded%20Card,Copy%20of%20Co%20Branded%20Card,Debit%20Card,STOP",  # 兆豐銀行
            # 在此加入其他起始 URL
        ]
        
        # 優先關鍵詞，用於排序連結
        priority_keywords = [
            "信用卡", "卡片", "優惠", "回饋", "紅利", "現金", "哩程", 
            "card", "credit", "reward", "cashback", "miles",
            "visa", "mastercard", "jcb", "美國運通", "amex"
        ]
        
        # 爬取設定
        max_depth = 3  # 設定爬取深度
        max_links_per_page = None  # 限制每頁最多爬取的連結數量，提高效率和精確度
        
        results, saved_files = crawl_multiple_urls(
            "條列出所有信用卡優惠和詳細連結", 
            base_urls, 
            max_depth=max_depth,
            max_links_per_page=max_links_per_page,
            priority_keywords=priority_keywords
        )
        
        if not results:
            print("爬取失敗")
            return
    else:
        print(f"載入既有的爬蟲結果: {latest_result_file}")
        results = load_crawl_result(latest_result_file)
    
    # 整合內容
    combined_content = combine_content(results)
    
    # 最終分析
    print("正在進行最終分析...")
    final_response = gemini.gemini_response(
        "請根據以上內容，條列出所有信用卡優惠，並以JSON格式輸出，必須包含卡名、發卡銀行、卡片類型、年費、回饋類型、卡片圖片URL、卡片詳情頁面連結、優惠內容（包括類別、詳細描述和回饋率）等資訊，要有良好的結構化",
        combined_content
    )
    
    print("\n=== 分析結果 ===")
    print(final_response)
    
    # 解析並格式化 JSON 結果
    try:
        # 嘗試解析 Gemini 回傳的 JSON
        json_result = json.loads(final_response)
        
        # 建立結果目錄（如果不存在）
        if not os.path.exists('results'):
            os.makedirs('results')
        
        # 儲存格式化的 JSON 結果
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_filename = f'results/analysis_result_{timestamp}.json'
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_result, f, ensure_ascii=False, indent=2)
        
        print(f"\n格式化的 JSON 結果已儲存至: {json_filename}")
        
        # 顯示格式化的 JSON
        print("\n=== 格式化的 JSON 結果 ===")
        print(json.dumps(json_result, ensure_ascii=False, indent=2))
    except json.JSONDecodeError as e:
        print(f"\n無法解析回傳的 JSON: {e}")
        print("嘗試修復 JSON 格式並重新解析...")
        
        try:
            # 嘗試修復 JSON
            # 1. 移除可能的額外資訊
            cleaned_json = final_response.strip()
            
            # 2. 嘗試找出 JSON 的起始和結束
            if cleaned_json.find('{') >= 0 and cleaned_json.rfind('}') >= 0:
                start = cleaned_json.find('{')
                end = cleaned_json.rfind('}') + 1
                cleaned_json = cleaned_json[start:end]
            
            # 3. 使用正則表達式嘗試修復常見格式錯誤
            import re
            # 修復逗號後缺少空格
            cleaned_json = re.sub(r',\s*"', ', "', cleaned_json)
            # 修復多餘的逗號
            cleaned_json = re.sub(r',\s*}', '}', cleaned_json)
            # 嘗試修復嵌套在卡片內的卡片（根據原始 JSON 錯誤的特定模式）
            cleaned_json = re.sub(r'"cardName":\s*"[^"]+",\s*"issuer":', '"issuer":', cleaned_json)
            
            # 手動修復特定問題
            if '"cards": [' in cleaned_json and '], "cardName":' in cleaned_json:
                parts = cleaned_json.split('], "cardName":')
                if len(parts) > 1:
                    # 將第二張卡片信息添加到第一個 cards 陣列中
                    second_card = '{' + parts[1].strip()
                    # 確保陣列結構正確
                    first_part = parts[0] + ', ' + second_card
                    cleaned_json = first_part + ']}'
            
            # 4. 嘗試重新解析
            json_result = json.loads(cleaned_json)
            
            # 建立結果目錄（如果不存在）
            if not os.path.exists('results'):
                os.makedirs('results')
            
            # 儲存修復後的 JSON
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            json_filename = f'results/analysis_result_fixed_{timestamp}.json'
            
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(json_result, f, ensure_ascii=False, indent=2)
            
            print(f"\n修復後的 JSON 結果已儲存至: {json_filename}")
            
            # 顯示格式化的 JSON
            print("\n=== 修復後的 JSON 結果 ===")
            print(json.dumps(json_result, ensure_ascii=False, indent=2))
        except Exception as fix_error:
            print(f"修復 JSON 失敗: {fix_error}")
            
            # 儲存原始回應以便手動分析
            if not os.path.exists('results'):
                os.makedirs('results')
                
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            raw_filename = f'results/raw_response_{timestamp}.txt'
            
            with open(raw_filename, 'w', encoding='utf-8') as f:
                f.write(final_response)
            
            print(f"原始回應已儲存至: {raw_filename}")
            print("原始回應:")
            print(final_response)

if __name__ == "__main__":
    try:
        main()
    finally:
        # 確保程式結束時關閉瀏覽器
        crawler.close_browser()
        