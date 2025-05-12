import time
import requests
from bs4 import BeautifulSoup
import html2text
import cloudscraper
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from urllib.parse import urlparse
import re

# 全域變數儲存瀏覽器實例
_browser = None
# 緩存已爬取的頁面，避免重複爬取
_page_cache = {}
# 記錄失敗的 URL
_failed_urls = set()

def get_browser():
    """獲取或建立瀏覽器實例"""
    global _browser
    if _browser is None:
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 無頭模式
        chrome_options.add_argument("--start-maximized")  # 最大化窗口
        chrome_options.add_argument("--log-level=3")  # 只顯示嚴重錯誤
        chrome_options.add_argument("--disable-logging")  # 禁用日誌
        chrome_options.add_argument("--disable-dev-shm-usage")  # 避免 /dev/shm 空間不足
        chrome_options.add_argument("--disable-gpu")  # 禁用 GPU 加速
        chrome_options.add_argument("--no-sandbox")  # 非沙盒模式
        chrome_options.add_argument("--disable-extensions")  # 禁用擴充功能
        chrome_options.add_argument("--disable-infobars")  # 禁用資訊列
        chrome_options.add_argument("--disable-notifications")  # 禁用通知
        chrome_options.add_argument("--disable-3d-apis")  # 禁用 3D API
        chrome_options.add_argument("--disable-webgl")  # 禁用 WebGL 
        chrome_options.add_argument("--ignore-certificate-errors")  # 忽略證書錯誤
        
        # 初始化 WebDriver
        _browser = webdriver.Chrome(options=chrome_options)
        # 設定頁面載入超時
        _browser.set_page_load_timeout(60)  # 增加超時時間
        _browser.set_script_timeout(60)  # 增加腳本執行超時時間
    return _browser

def close_browser():
    """關閉瀏覽器實例"""
    global _browser
    if _browser:
        _browser.quit()
        _browser = None

def restart_browser():
    """重新啟動瀏覽器"""
    global _browser
    close_browser()
    time.sleep(2)  # 等待瀏覽器完全關閉
    return get_browser()

def is_similar_url(url1, url2):
    """檢查兩個 URL 是否相似（避免重複爬取相似頁面）"""
    parse1 = urlparse(url1)
    parse2 = urlparse(url2)
    
    # 如果域名不同，則 URL 不相似
    if parse1.netloc != parse2.netloc:
        return False
    
    # 處理路徑部分
    path1 = parse1.path.rstrip('/')
    path2 = parse2.path.rstrip('/')
    
    # 如果是同一頁面的不同參數，可能相似
    if path1 == path2:
        return True
    
    # 移除數字參數後比較（例如 page=1, page=2 視為相似）
    path1_no_digits = re.sub(r'\d+', '', path1)
    path2_no_digits = re.sub(r'\d+', '', path2)
    
    return path1_no_digits == path2_no_digits

def url_to_markdown(url, use_selenium=False, retry_count=0):
    """將 URL 轉換為 Markdown 格式的內容"""
    global _page_cache, _failed_urls
    
    # 如果 URL 已知失敗，直接返回
    if url in _failed_urls:
        print(f"跳過已知失敗的 URL: {url}")
        return None
    
    # 檢查緩存
    if url in _page_cache:
        print(f"使用緩存: {url}")
        return _page_cache[url]
    
    # 檢查是否有相似的 URL 已經爬取過
    for cached_url in _page_cache.keys():
        if is_similar_url(url, cached_url):
            print(f"使用相似 URL 的緩存: {url} -> {cached_url}")
            return _page_cache[cached_url]
    
    # 最大重試次數
    max_retries = 3
    
    if use_selenium:
        # 使用 Selenium 模式
        try:
            driver = get_browser()  # 使用或建立瀏覽器實例
            
            try:
                print(f"正在使用 Selenium 載入: {url}")
                driver.get(url)
                
                # 等待頁面基本元素載入
                try:
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                except TimeoutException:
                    print(f"等待 body 元素超時: {url}，但繼續處理頁面")
                
                # 等待頁面加載完成，但最多等待 10 秒
                wait_time = 0
                while driver.execute_script("return document.readyState") != "complete" and wait_time < 10:
                    time.sleep(1)
                    wait_time += 1
                    print(f"等待頁面載入中... {wait_time}/10 秒")
                
                # 即使頁面未完全載入，也嘗試獲取當前內容
                page_source = driver.page_source
                
            except TimeoutException as e:
                if retry_count < max_retries:
                    print(f"載入 {url} 超時，嘗試重新啟動瀏覽器 (重試 {retry_count + 1}/{max_retries})")
                    restart_browser()
                    return url_to_markdown(url, use_selenium, retry_count + 1)
                else:
                    print(f"載入 {url} 多次嘗試後仍然超時，放棄爬取")
                    _failed_urls.add(url)
                    return None
            
        except WebDriverException as e:
            if retry_count < max_retries:
                print(f"瀏覽器異常: {e}，嘗試重新啟動瀏覽器 (重試 {retry_count + 1}/{max_retries})")
                restart_browser()
                return url_to_markdown(url, use_selenium, retry_count + 1)
            else:
                print(f"處理 {url} 多次嘗試後仍然出錯: {e}")
                _failed_urls.add(url)
                return None
        except Exception as e:
            print(f"Selenium 請求失敗: {e}")
            _failed_urls.add(url)
            return None
    else:
        # 使用 cloudscraper 替代 requests
        try:
            scraper = cloudscraper.create_scraper(delay=3)  # 減少延遲
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            response = scraper.get(url, headers=headers, timeout=30)  # 增加超時時間
            
            if response.status_code != 200:
                print(f"請求失敗: {url}, 狀態碼: {response.status_code}")
                _failed_urls.add(url)
                return None
            
            page_source = response.content
            
        except Exception as e:
            if retry_count < max_retries:
                print(f"請求 {url} 失敗: {e}，重試 ({retry_count + 1}/{max_retries})")
                time.sleep(3)  # 等待幾秒再重試
                return url_to_markdown(url, use_selenium, retry_count + 1)
            else:
                print(f"請求 {url} 多次嘗試後仍然失敗: {e}")
                _failed_urls.add(url)
                return None

    # 其餘邏輯保持不變，但優化處理
    try:
        soup = BeautifulSoup(page_source, "html.parser")

        # 移除不需要的元素，加快處理速度
        for unwanted in soup.find_all(['nav', 'footer', 'aside', 'header', 'script', 'style', 'iframe', 'noscript']):
            unwanted.decompose()

        # 更智能地查找主要內容
        # 首先尋找可能的主要內容區域
        main_content = None
        for tag_name in ['main', 'article', 'section', 'div[class*="content"], div[class*="main"], div[id*="content"], div[id*="main"]']:
            main_elements = soup.select(tag_name)
            if main_elements:
                # 選擇包含最多段落的元素
                main_content = max(main_elements, key=lambda tag: len(tag.find_all('p')))
                break
        
        # 如果找不到明確的主要內容區域，則使用之前的方法
        if not main_content:
            candidates = soup.find_all(True)
            if candidates:
                main_content = max(candidates, key=lambda tag: len(tag.find_all('p')))
        
        if not main_content:
            print(f"無法找到主要內容: {url}")
            return "無法提取此頁面的主要內容。"

        # 修正圖片URL為絕對路徑
        base_url = url
        parsed_url = urlparse(url)
        base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # 修正圖片路徑為絕對路徑
        for img in main_content.find_all('img'):
            src = img.get('src', '')
            if src:
                if src.startswith('//'):
                    img['src'] = f"{parsed_url.scheme}:{src}"
                elif src.startswith('/'):
                    img['src'] = f"{base_domain}{src}"
                elif not (src.startswith('http://') or src.startswith('https://')):
                    img['src'] = f"{base_domain}/{src.lstrip('/')}"

        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = False  # 不忽略圖片，保留圖片URL
        converter.body_width = 0  # 不自動換行
        markdown_content = converter.handle(str(main_content))

        print(f"成功爬取: {url}")
        
        # 儲存到緩存
        _page_cache[url] = markdown_content
        
        return markdown_content
    except Exception as e:
        print(f"處理 HTML 時發生錯誤: {e}")
        return f"爬取過程中發生錯誤: {str(e)}"

# 清理函數，在程式結束時調用
def cleanup():
    """清理資源"""
    global _page_cache, _failed_urls
    close_browser()
    print(f"爬取完成，成功: {len(_page_cache)} 頁，失敗: {len(_failed_urls)} 頁")
    if _failed_urls:
        print("失敗的 URL:")
        for url in _failed_urls:
            print(f" - {url}")
    _page_cache = {}  # 清空緩存
    _failed_urls = set()  # 清空失敗記錄

# print(url_to_markdown("https://news.google.com/home?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"))





