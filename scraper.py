import requests
from bs4 import BeautifulSoup

def clean_text(text):
    return text.lower().strip()

def scrape_static(url):
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        return clean_text(text)
    except:
        return ""

def scrape_dynamic(url):
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            content = page.content()
            browser.close()

            soup = BeautifulSoup(content, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            return clean_text(text)

    except:
        return ""

def get_content(url):
    content = scrape_static(url)

    if len(content) > 500:
        return content[:5000]

    content = scrape_dynamic(url)
    return content[:5000]