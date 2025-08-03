import os, time, pickle
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import urllib.parse
import asyncio
from playwright.async_api import async_playwright
import requests
import json


load_dotenv()
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")


options = Options()
options.add_experimental_option("detach", True) 
driver = webdriver.Chrome(options=options)
driver.maximize_window() 
wait = WebDriverWait(driver, 10)


with open("config.json", "r") as f:
    config = json.load(f)

#/////////////////////////////////// login & save cookie section ///////////////////////////////////
def login() :
    if os.path.exists("cookies.pkl"):
        driver.get("https://maktabkhooneh.org/")
        with open("cookies.pkl", "rb") as f:
            for cookie in pickle.load(f):
                cookie.pop("sameSite", None)
                driver.add_cookie(cookie)
        driver.refresh()
    else:

        driver.get("https://maktabkhooneh.org/")
        login_button = wait.until(EC.element_to_be_clickable((By.ID, "login")))
        login_button.click()

        username_field = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'input[autocomplete="username"]')))
        username_field.send_keys(USERNAME)

        confirm_button = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'button[data-tag="ga-email-phone-login"]')))
        confirm_button.click()

        password_field = wait.until(EC.element_to_be_clickable((By.ID, "password")))
        password_field.send_keys(PASSWORD)

        password_submit = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'button[data-tag="ga-password-submit"]')))
        password_submit.click()


    time.sleep(5)

    with open("cookies.pkl", "wb") as f:
        pickle.dump(driver.get_cookies(), f)
    print("✅ Cookies saved.")  


def load_cookies(driver, file):
    driver.get("https://maktabkhooneh.org/")
    cookies = pickle.load(open(file, "rb"))
    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except:
            pass


#/////////////////////////////////// get courses link ///////////////////////////////////

def get_all_course_links(): 

    load_cookies(driver, "cookies.pkl")

    driver.get(config["course_url"])
    time.sleep(2)


    links = driver.find_elements(By.XPATH, '//a[contains(@href, "/course")]')

    all_hrefs = set()
    for link in links:
        href = link.get_attribute("href")
        if href:
            all_hrefs.add(href)

    for href in all_hrefs:
        print(href)

#/////////////////////////////////// filter phrases ///////////////////////////////////

filtered_links = []

with open("decoded_urls.txt", "r", encoding="utf-8") as f :
    for line in f:
        decoded_link = urllib.parse.unquote(line.strip())
        if "تمرین" in decoded_link or "کوئیز" in decoded_link or "pdf" in decoded_link:
            continue 

        filtered_links.append(decoded_link)

# ذخیره در فایل جدید
with open("filtered_links.txt", "w", encoding="utf-8") as out:
    for link in filtered_links:
        out.write(link + "\n")

print(f"✅ {len(filtered_links)} لینک معتبر ذخیره شد.")


#/////////////////////////////////// get download links ///////////////////////////////////



def load_cookies_for_playwright():
    cookies = pickle.load(open("cookies.pkl", "rb"))
    converted = []
    for cookie in cookies:
        converted.append({
            "name": cookie["name"],
            "value": cookie["value"],
            "domain": cookie["domain"].lstrip('.'),
            "path": cookie.get("path", "/"),
            "secure": cookie.get("secure", False),
            "httpOnly": cookie.get("httpOnly", False),
            "expires": cookie.get("expiry", -1),
        })
    return converted

async def get_video_urls_from_page(page, url):
    video_urls = set()

    def handle_response(response):
        rurl = response.url
        if rurl.endswith(".mp4") and "https://cdn.maktabkhooneh.org/videos/hq" in rurl:
            video_urls.add(rurl)

    page.on("response", handle_response)
    await page.goto(url, timeout=90000, wait_until="domcontentloaded")
    await asyncio.sleep(15)  # منتظر می‌مانیم تا درخواست‌های ویدیو بیاید
    return video_urls

async def main():
    cookies = load_cookies_for_playwright()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(ignore_https_errors=True)
        await context.add_cookies(cookies)
        page = await context.new_page()

        with open("cleaned.txt", "r", encoding="utf-8") as f:
            links = [line.strip() for line in f if line.strip()]

        all_video_links = set()

        for idx, link in enumerate(links, 1):
            print(f"\n[{idx}/{len(links)}] loading page: {link}")
            videos = await get_video_urls_from_page(page, link)
            if videos:
                print(f"founded💸💸💸💸💸({len(videos)}):")
                for v in videos:
                    print(" -", v)
                all_video_links.update(videos)
            else:
                print("no video found.📌📌📌📌📌📌📌")
        
        if all_video_links:
            with open("all_video_links2.txt", "w", encoding="utf-8") as out_f:
                for video_link in sorted(all_video_links):
                    out_f.write(video_link + "\n")
            print(f"\nتمام لینک‌ها ذخیره شد در all_video_links.txt")
        else:
            print("\nهیچ لینک ویدیویی پیدا نشد.📌📌 ")

        await browser.close()

asyncio.run(main())

#/////////////////////////////////// download the list ///////////////////////////////////


def get_filename_from_url(url):
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    return query.get("name", [None])[0]

def download_file(url, output_folder=".", retries=5, timeout=60):
    filename = get_filename_from_url(url)
    if not filename:
        print(f"❌ نام فایل در URL یافت نشد:\n{url}")
        return

    filepath = f"{output_folder}/{filename}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    for attempt in range(1, retries + 1):
        try:
            with requests.get(url, headers=headers, stream=True, timeout=timeout) as response:
                response.raise_for_status()
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            print(f"✅ دانلود موفق: {filename}")
            return
        except requests.exceptions.RequestException as e:
            print(f"⚠️ تلاش {attempt} برای {filename} شکست خورد: {e}")
            if attempt < retries:
                wait = attempt * 5
                print(f"⏳ صبر {wait} ثانیه، تلاش دوباره...")
                time.sleep(wait)
            else:
                print(f"❌ شکست نهایی برای: {filename}")

def batch_download_from_file(file_path, output_folder="."):
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if url:
                download_file(url, output_folder=output_folder)


batch_download_from_file("all_video_links2.txt")



