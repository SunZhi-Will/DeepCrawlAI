import core.gemini as gemini
import core.crawler as crawler
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

def crawl_with_depth(user_query ,base_url, max_depth=2, current_depth=0, visited_urls=None):
    if visited_urls is None:
        visited_urls = set()
    
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
        
        # 遞迴爬取相關連結
        sub_pages = []
        for link in related_links:
            url = link.get('url')
            if url and url.startswith('http') and url not in visited_urls:
                sub_content = crawl_with_depth(user_query, url, max_depth, current_depth + 1, visited_urls)
                if sub_content:
                    sub_pages.append({
                        'url': url,
                        'title': link.get('title', ''),
                        'content': sub_content
                    })
        
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
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def combine_content(result):
    combined_content = f"""
主頁面內容：
{result['content']}

子頁面內容：
"""
    for sub_page in result.get('sub_pages', []):
        combined_content += f"\n{sub_page['title']} ({sub_page['url']}):\n{sub_page['content']}\n"
    
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
        base_url = "https://www.fubon.com/banking/personal/credit_card/all_card/all_card.htm"
        result = crawl_with_depth("條列出所有信用卡優惠", base_url, max_depth=3)
        
        if result:
            # 儲存爬蟲結果
            saved_file = save_crawl_result(result)
            print(f"爬蟲結果已儲存至: {saved_file}")
        else:
            print("爬取失敗")
            return
    else:
        print(f"載入既有的爬蟲結果: {latest_result_file}")
        result = load_crawl_result(latest_result_file)
    
    # 整合內容
    combined_content = combine_content(result)
    
    # 最終分析
    print("正在進行最終分析...")
    final_response = gemini.gemini_response(
        "請根據以上內容，條列出所有信用卡優惠，並以易讀的方式呈現",
        combined_content
    )
    print("\n=== 分析結果 ===")
    print(final_response)

if __name__ == "__main__":
    main()
        