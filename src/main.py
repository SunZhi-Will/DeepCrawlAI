import core.gemini as gemini
import core.crawler as crawler
from bs4 import BeautifulSoup
import json

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

def main():
    base_url = "https://www.fubon.com/banking/personal/credit_card/all_card/all_card.htm"
    result = crawl_with_depth("條列出所有信用卡優惠",base_url)
    
    if result:
        # 整合所有內容
        combined_content = f"""
主頁面內容：
{result['content']}

子頁面內容：
"""
        print(combined_content)
        for sub_page in result.get('sub_pages', []):
            combined_content += f"\n{sub_page['title']} ({sub_page['url']}):\n{sub_page['content']}\n"
            print(f"\n{sub_page['title']} ({sub_page['url']}):\n{sub_page['content']}\n")
        
        # 最終分析
        # final_response = gemini.gemini_response("條列出所有信用卡優惠", combined_content)
        # print(final_response)
    else:
        print("爬取失敗")
if __name__ == "__main__":
    main()
        