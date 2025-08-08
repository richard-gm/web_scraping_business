import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import pandas as pd
import time


def safe_get(driver, url, retries=3, wait_time=5):
    for attempt in range(retries):
        try:
            driver.get(url)
            time.sleep(2)
            return True
        except (TimeoutException, WebDriverException) as e:
            print(f"⚠️ Attempt {attempt + 1} failed to load {url}: {e}")
            time.sleep(wait_time * (attempt + 1))  # Exponential backoff
    print(f"❌ Failed to load {url} after {retries} attempts.")
    return False


def setup_driver():
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 15)
    return driver, wait

def accept_cookies(driver, wait):
    try:
        cookie_btn = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
        cookie_btn.click()
        print("Accepted cookies.")
    except:
        print("No cookie banner found.")

# ---------- APPLY FILTERS ----------
def apply_filters(driver, wait):
    try:
        # Asking price
        price_min = wait.until(EC.presence_of_element_located((By.ID, "priceFrom")))
        price_min.clear()
        price_min.send_keys("45000")

        # Net profit
        profit_min = wait.until(EC.presence_of_element_located((By.ID, "profitFrom")))
        profit_min.clear()
        profit_min.send_keys("45000")

        # Disclosed Only for both
        price_disclosed = wait.until(EC.element_to_be_clickable((By.ID, "PriceDisclosedOnly")))
        if not price_disclosed.is_selected():
            price_disclosed.click()

        profit_disclosed = wait.until(EC.element_to_be_clickable((By.ID, "ProfitDisclosedOnly")))
        if not profit_disclosed.is_selected():
            profit_disclosed.click()

        # Update results
        time.sleep(1)
        update_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "li.button.update-results-button")))
        update_btn.click()

        print("✅ Price, profit & disclosed filters applied.")
    except Exception as e:
        print(f"❌ Filter application failed: {e}")

    # Click "Update Results"
    try:
        update_li = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "li.button.update-results-button")))
        update_li.click()
        print("Clicked Update Results.")
    except Exception as e:
        print("Could not click Update:", e)

# === MAIN SCRIPT ===

driver, wait = setup_driver()
results = []

print("Loading search page...")
driver.get("https://uk.businessesforsale.com/uk/search/businesses-for-sale")
accept_cookies(driver, wait)
apply_filters(driver, wait)

page = 1
max_pages = 10  # Set this as needed

while page <= max_pages:
    print(f"\n📄 Processing Page {page}")

    try:
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.result")))
    except Exception as e:
        print("Timed out waiting for listings:", e)
        break

    listing_blocks = driver.find_elements(By.CSS_SELECTOR, "div.result table.result-table caption h2 a")
    listing_urls = []
    listing_titles = []

    for a in listing_blocks:
        try:
            title = a.text.strip()
            if any(keyword in title.lower() for keyword in ["jewellery", "holiday", "web","pizza","amazon", "cafe", "coffee", "restaurant", "franchise", "pub", "bar", "takeaway", "baker", "fish", "chippy", "clothing","tea","print", "bakery", "sandwich shop", "catering", "e-commerce", "online business", "food delivery", "food truck", "mobile catering", "drop shipping", "ecommerce", "online store", "cheese", "hospitality", "events", "care", "dating", "yoga", "kitchen"]):
                print(f"⏭️ Skipping: {title}")
                continue
            url = a.get_attribute("href")
            listing_urls.append(url)
            listing_titles.append(title)
        except Exception as e:
            print(f"Could not extract link: {e}")

    current_page_url = driver.current_url  # To return after visiting a listing

    for i, url in enumerate(listing_urls):
        print(f"\n[{i+1}/{len(listing_urls)}] Visiting listing: {url}")
        try:
            if not safe_get(driver, url):
                continue

            # Scrape reason for selling
            try:
                reason_elem = driver.find_element(By.XPATH, "//dt[contains(text(),'Reasons for selling')]/following-sibling::dd[1]")
                reason_text = reason_elem.text.strip().lower()

                if "retir" in reason_text or "emigrat" in reason_text:
                    print(f"✅ Match found: {reason_text}")
                    try:
                        title = driver.find_element(By.CSS_SELECTOR, "#title-address h1").text.strip()
                    except:
                        title = listing_titles[i]  # fallback

                    try:
                        address_spans = driver.find_elements(By.CSS_SELECTOR, "#address span")
                        address = address_spans[0].text.strip() if address_spans else ""
                    except:
                        address = ""

                    results.append({
                        "title": title,
                        "address": address,
                        "url": url,
                        "reason": reason_text
                    })
                else:
                    print(f"❌ No match: {reason_text}")
            except:
                print("⚠️ Reason for selling not found.")

            # Additional check for retirement/retiring in listing-section-content
            try:
                content_divs = driver.find_elements(By.CSS_SELECTOR, "div.listing-section-content")
                retirement_found = False
                retirement_text = ""

                for div in content_divs:
                    div_text = div.text.strip().lower()
                    if "retirement" in div_text or "retiring" in div_text:
                        retirement_found = True
                        retirement_text = div_text
                        break

                if retirement_found:
                    print(f"✅ Retirement match found in content: {retirement_text[:100]}...")
                    try:
                        title = driver.find_element(By.CSS_SELECTOR, "#title-address h1").text.strip()
                    except:
                        title = listing_titles[i]  # fallback

                    try:
                        address_spans = driver.find_elements(By.CSS_SELECTOR, "#address span")
                        address = address_spans[0].text.strip() if address_spans else ""
                    except:
                        address = ""

                    results.append({
                        "title": title,
                        "address": address,
                        "url": url,
                        "reason": f"retirement content: {retirement_text[:200]}"
                    })
                else:
                    print(f"❌ No retirement content found")
            except:
                print("⚠️ Could not check listing-section-content.")
            # Return to results page
            print("Returning to results page...")
            driver.get(current_page_url)
            time.sleep(2)

        except Exception as e:
            print(f"❌ Failed to process {url}: {e}")
            continue

    # Try to go to next page
    try:
        # Look specifically for the "next-link" element
        next_button = driver.find_element(By.CSS_SELECTOR, "li.next-link a")
        if next_button:
            print(f"Going to next page...")
            next_url = next_button.get_attribute("href")
            driver.get(next_url)
            page += 1
            time.sleep(3)
        else:
            print("🚫 No more pages.")
            break
    except Exception as e:
        print(f"⚠️ Pagination failed: {e}")
        break

# === SAVE RESULTS ===
df = pd.DataFrame(results)
print("\n🎉 Finished. Matching listings:")
print(df)

df.to_csv("filtered_listings.csv", index=False)
print("Saved to filtered_listings.csv")

driver.quit()
