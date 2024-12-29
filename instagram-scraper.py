from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import pandas as pd
from datetime import datetime
import logging
from dotenv import load_dotenv
import os
import json
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

CHROME_PATH = "/driver/chromedriver.exe"
GECKO_PATH = "/driver/geckodriver.exe"

def create_driver(use_chrome=True):
    if use_chrome:
        options = ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.headless = False
        return webdriver.Chrome(options=options)
    else:
        options = FirefoxOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.headless = False
        return webdriver.Firefox(options=options)

def extract_number(text):
    if not text:
        return 0
    try:
        text = text.replace(',', '').strip()
        if 'K' in text:
            num = float(text.replace('K', ''))
            return int(num * 1000)
        numbers = re.findall(r'\d+', text)
        if numbers:
            return int(numbers[0])
    except Exception as e:
        logging.error(f"Error extracting number from '{text}': {e}")
    return 0

def get_likes_count(driver):
    try:
        selectors = [
            "//span[@class='x1lliihq x1plvlek xryxfnj x1n2onr6 x1ji0vk5 x18bv5gf x193iq5w xeuugli']//span[@class='html-span xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x1hl2dhg x16tdsg8 x1vvkbs']",
            "//a[contains(@href, '/liked_by/')]//span[@class='html-span']",
            "//section[contains(@class, 'x12nagc')]//span[contains(@class, 'html-span')]"
        ]
        
        for selector in selectors:
            try:
                likes_elem = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                if likes_elem:
                    likes_text = likes_elem.text
                    return extract_number(likes_text)
            except:
                continue
                
        logging.warning("Likes element not found with any selector")
        return 0
        
    except Exception as e:
        logging.error(f"Error getting likes count: {e}")
        return 0

def wait_for_element(driver, by, value, timeout=20):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        logging.error(f"Timeout waiting for element: {value}")
        return None

def handle_popups(driver):
    """Handle various Instagram popups"""
    popup_buttons = [
        "//button[contains(text(), 'Not Now')]",
        "//button[contains(text(), 'Skip')]",
        "//button[contains(text(), 'Maybe Later')]",
        "//button[contains(text(), 'Allow essential and optional cookies')]"
    ]
    
    for xpath in popup_buttons:
        try:
            button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            button.click()
            time.sleep(1)
        except:
            continue

def login(driver):
    try:
        time.sleep(5)
        
        handle_popups(driver)
        
        username_input = wait_for_element(driver, By.CSS_SELECTOR, "input[name='username']")
        if not username_input:
            raise Exception("Username input not found")
        username_input.send_keys(os.getenv('INSTAGRAM_USERNAME'))
        
        password_input = wait_for_element(driver, By.CSS_SELECTOR, "input[name='password']")
        if not password_input:
            raise Exception("Password input not found")
        password_input.send_keys(os.getenv('INSTAGRAM_PASSWORD'))
        
        login_button = wait_for_element(driver, By.CSS_SELECTOR, "button[type='submit']")
        if not login_button:
            raise Exception("Login button not found")
        login_button.click()
        
        time.sleep(5)
        
        handle_popups(driver)
        
        logging.info("Login successful")
        return True
        
    except Exception as e:
        logging.error(f"Failed to login: {e}")
        return False

def get_comments(driver, max_comments=800):
    comments = []
    try:
        try:
            view_more = driver.find_element(By.XPATH, "//span[contains(text(), 'View all')]")
            view_more.click()
            time.sleep(3)
        except:
            pass
        
        last_comment_count = 0
        stagnant_count = 0
        max_stagnant_tries = 5
        scroll_delay = 3
        
        while len(comments) < max_comments:
            try:
                load_more_present = False
                load_more_buttons = driver.find_elements(
                    By.XPATH,
                    "//*[local-name()='svg' and contains(@aria-label, 'Load more comment')]//..//.."
                )
                
                if load_more_buttons:
                    for button in load_more_buttons:
                        try:
                            if not button.is_displayed():
                                continue
                                
                            driver.execute_script("""
                                arguments[0].scrollIntoView();
                                window.scrollBy(0, -200);
                            """, button)
                            time.sleep(scroll_delay)
                                
                            try:
                                driver.execute_script("arguments[0].click();", button)
                            except:
                                button.click()
                                
                            load_more_present = True
                            time.sleep(scroll_delay)
                            break
                            
                        except StaleElementReferenceException:
                            continue
                        except Exception as e:
                            logging.warning(f"Error clicking button: {e}")
                            continue
                            
                if not load_more_present:
                    logging.info("No more load more buttons found")
                    break
                
                current_comments = len(driver.find_elements(By.CSS_SELECTOR, "ul._a9ym ._a9zr"))
                if current_comments == last_comment_count:
                    stagnant_count += 1
                    if stagnant_count >= max_stagnant_tries:
                        logging.warning("Comment loading appears to be stuck")
                        break
                else:
                    stagnant_count = 0
                    last_comment_count = current_comments
                    logging.info(f"Loaded {current_comments} comments so far...")
                    
            except Exception as e:
                logging.warning(f"Error in comment loading loop: {e}")
                stagnant_count += 1
                if stagnant_count >= max_stagnant_tries:
                    break
                time.sleep(scroll_delay)
                continue

        try:
            reply_buttons = driver.find_elements(By.XPATH, "//span[contains(@class, '_a9yi') and contains(text(), 'View replies')]/..")
            for button in reply_buttons:
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(2)
                except:
                    continue
        except:
            pass

        comment_elements = driver.find_elements(By.CSS_SELECTOR, "ul._a9ym ._a9zr")
        logging.info(f"Found {len(comment_elements)} comments")
        
        for comment in comment_elements[:max_comments]:
            try:
                driver.execute_script("""
                    arguments[0].scrollIntoView({
                        behavior: 'smooth',
                        block: 'center'
                    });
                """, comment)
                time.sleep(0.5)
                
                username = comment.find_element(By.CSS_SELECTOR, "._a9zc").text
                text = comment.find_element(By.CSS_SELECTOR, "._a9zs").text
                
                is_reply = False
                reply_to = None

                if text.startswith("@"):
                    # Extract username
                    is_reply = True
                    reply_to = text.split(" ")[0][1:]
                    logging.info("The message is replying to @" + reply_to)
                else:
                    logging.info("The text does not start with '@'.")
                
                comment_likes = 0
                try:
                    likes_elem = comment.find_element(By.CSS_SELECTOR, "._a9zb span")
                    if likes_elem:
                        comment_likes = extract_number(likes_elem.text)
                except:
                    pass
                
                timestamp = ""
                try:
                    time_elem = comment.find_element(By.CSS_SELECTOR, "time")
                    if time_elem:
                        timestamp = time_elem.get_attribute("datetime")
                except:
                    pass
                
                comment_data = {
                    "username": username,
                    "comment": text,
                    "is_reply": is_reply,
                    "reply_to": reply_to if is_reply else None,
                    "likes": comment_likes,
                    "timestamp": timestamp
                }
                
                comments.append(comment_data)
                
            except StaleElementReferenceException:
                logging.warning("Comment element became stale, skipping...")
                continue
            except Exception as e:
                logging.warning(f"Error extracting comment data: {e}")
                continue
                
    except Exception as e:
        logging.error(f"Error getting comments: {e}")
    
    logging.info(f"Successfully extracted {len(comments)} comments")
    return comments


def get_post_data(post_url, driver):
    try:
        driver.get(post_url)
        time.sleep(3)
        
        post_data = {
            "post_link": post_url,
            "post_time": "",
            "likes_count": 0,
            "comments_count": 0,
            "shares_count": 0,
            "comments": []
        }
        
        time_elem = wait_for_element(driver, By.TAG_NAME, "time")
        if time_elem:
            post_data["post_time"] = time_elem.get_attribute("datetime")
        
        post_data["likes_count"] = get_likes_count(driver)
        
        try:
            shares_elem = driver.find_element(By.XPATH, "//span[contains(text(), 'shares')]")
            shares_text = shares_elem.text
            post_data["shares_count"] = extract_number(shares_text)
        except:
            pass
        
        comments = get_comments(driver, max_comments=800)
        post_data["comments"] = comments
        post_data["comments_count"] = len(comments)
        
        logging.info(f"Post scraped: {post_url} | Likes: {post_data['likes_count']} | Comments: {post_data['comments_count']}")
        
        return post_data
    
    except Exception as e:
        logging.error(f"Error getting post data for {post_url}: {e}")
        return None

def scrape_tagged_posts(driver):
    posts_data = []
    processed_urls = set()
    processed_positions = set()
    consecutive_empty_scrolls = 0
    max_empty_scrolls = 5
    target_url = 'https://www.instagram.com/kulasyafiq/tagged/'
    
    def get_visible_posts():
        return driver.find_elements(By.CSS_SELECTOR, "div._aagw")
    
    def get_post_position(post):
        location = post.location
        size = post.size
        return {
            'x': location['x'],
            'y': location['y'],
            'bottom': location['y'] + size['height']
        }
    
    def sort_posts_by_position(posts):
        posts_with_pos = []
        row_height_tolerance = 10
        
        for post in posts:
            try:
                pos = get_post_position(post)
                position_key = f"{round(pos['x'])},{round(pos['y'] / row_height_tolerance)}"
                
                if position_key not in processed_positions:
                    posts_with_pos.append((post, pos, position_key))
            except StaleElementReferenceException:
                continue
        
        posts_with_pos.sort(key=lambda x: (
            round(x[1]['y'] / row_height_tolerance) * row_height_tolerance,
            x[1]['x']
        ))
        
        return [(post, pos_key) for post, _, pos_key in posts_with_pos]
    
    def scroll_to_next_row(last_processed_y):
        viewport_height = driver.execute_script("return window.innerHeight;")
        scroll_amount = max(viewport_height * 0.4, last_processed_y - viewport_height * 0.2)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(2)
    
    def ensure_on_tagged_page():
        current_url = driver.current_url
        if target_url not in current_url:
            logging.info("Navigating back to tagged posts page")
            driver.get(target_url)
            time.sleep(3)  
            return True
        return False
    
    last_processed_y = 0
    
    ensure_on_tagged_page()
    
    while True:
        try:
            if ensure_on_tagged_page():
                continue
                
            visible_posts = get_visible_posts()
            sorted_posts = sort_posts_by_position(visible_posts)
            
            if not sorted_posts:
                consecutive_empty_scrolls += 1
                if consecutive_empty_scrolls >= max_empty_scrolls:
                    logging.info(f"No new posts found after {max_empty_scrolls} scrolls. Stopping.")
                    break
                scroll_to_next_row(last_processed_y)
                continue
            
            consecutive_empty_scrolls = 0
            new_posts_found = False
            
            for post, position_key in sorted_posts:
                if position_key in processed_positions:
                    continue
                
                try:
                    link_elem = None
                    for selector in ["./ancestor::a", ".//a", "../a"]:
                        try:
                            link_elem = post.find_element(By.XPATH, selector)
                            break
                        except:
                            continue
                    
                    if link_elem:
                        post_url = link_elem.get_attribute("href")
                        if post_url and post_url not in processed_urls:
                            current_scroll = driver.execute_script("return window.pageYOffset;")
                            
                            original_window = driver.current_window_handle
                            driver.execute_script("window.open('');")
                            driver.switch_to.window(driver.window_handles[-1])
                            
                            post_data = get_post_data(post_url, driver)
                            if post_data:
                                posts_data.append(post_data)
                                processed_urls.add(post_url)
                                processed_positions.add(position_key)
                                new_posts_found = True
                                logging.info(f"Scraped post {len(posts_data)}: {post_url}")
                            
                            driver.close()
                            driver.switch_to.window(original_window)
                            
                            driver.execute_script(f"window.scrollTo(0, {current_scroll});")
                            time.sleep(1)
                            
                            post_pos = get_post_position(post)
                            last_processed_y = post_pos['bottom']
                
                except StaleElementReferenceException:
                    logging.warning("Post element became stale, skipping...")
                    continue
                except Exception as e:
                    logging.error(f"Error processing post: {e}")
                    ensure_on_tagged_page()
                    continue
            
            if not new_posts_found:
                scroll_to_next_row(last_processed_y)
            
            current_height = driver.execute_script("return document.documentElement.scrollHeight;")
            current_scroll = driver.execute_script("return window.pageYOffset + window.innerHeight;")
            if current_scroll >= current_height:
                consecutive_empty_scrolls += 1
            
        except Exception as e:
            logging.error(f"Error during scrolling: {e}")
            time.sleep(5)
            ensure_on_tagged_page()
    
    return posts_data

def save_results(posts_data):
    if not posts_data:
        logging.error("No data to save")
        return
        
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'./data/instagram_tagged_posts_{timestamp}.json'
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(posts_data, f, ensure_ascii=False, indent=2)
        logging.info(f"Results saved to {filename}")
    except Exception as e:
        logging.error(f"Error saving results: {e}")

def main():
    driver = None
    try:
        driver = create_driver(use_chrome=True)
        
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })
        
        driver.get('https://www.instagram.com/accounts/login/')
        if not login(driver):
            raise Exception("Login failed")
        
        time.sleep(3)
        driver.get('https://www.instagram.com/kulasyafiq/tagged/')
        time.sleep(5)
        
        first_post = wait_for_element(driver, By.CSS_SELECTOR, "div._aagw")
        if not first_post:
            raise Exception("No posts found")
            
        posts_data = scrape_tagged_posts(driver)
        # posts_data = get_post_data('https://www.instagram.com/jonyrahardja/reel/DDrYIDHv27g/', driver)
        
        if posts_data:
            save_results(posts_data)
            logging.info(f"Successfully scraped {len(posts_data)} posts")
        else:
            logging.error("No posts were scraped")
            
    except Exception as e:
        logging.error(f"Script failed: {e}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
