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

def url_to_markdown(url, use_selenium=False):
    if use_selenium:
        # 使用 Selenium 模式
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # 無頭模式
            chrome_options.add_argument("--start-maximized")  # 最大化窗口
            
            # 初始化WebDriver
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(url)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(5)  # 額外等待5秒，確保動態內容加載完成
            
            while driver.execute_script("return document.readyState") != "complete":
                time.sleep(1)
            page_source = driver.page_source
        except Exception as e:
            print(f"Request failed: {e}")
            return True
        finally:
            driver.quit()  # 確保關閉瀏覽器
    else:
        # 使用 cloudscraper 替代 requests
        scraper = cloudscraper.create_scraper(delay=10)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        
        try:
            response = scraper.get(url, headers=headers, timeout=50)
        except Exception as e:
            print(f"Request failed: {e}")
            return True
        
        if response.status_code != 200:
            print(f"Failed: {url}, Status code: {response.status_code}")
            return None
        
        page_source = response.content

    # 其餘邏輯保持不變
    soup = BeautifulSoup(page_source, "html.parser")

    for unwanted in soup.find_all(['nav', 'footer', 'aside', 'header', 'script']):
        unwanted.decompose()

    candidates = soup.find_all(True)
    main_content = max(candidates, key=lambda tag: len(tag.find_all('p')))

    if not main_content:
        print(f"Main content not found: {url}")
        return None

    converter = html2text.HTML2Text()
    converter.ignore_links = False
    markdown_content = converter.handle(str(main_content))

    print(f"Successfully fetched: {url}")
    return markdown_content

# print(url_to_markdown("https://news.google.com/home?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"))





