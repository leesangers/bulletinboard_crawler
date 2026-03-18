from datetime import datetime, timedelta
from crawler import KofairCrawler, MssCrawler
from notifier import EmailNotifier

import os
import json
import sys

STATE_FILE = "last_ids.json"

def get_target_dates():
    """Returns a dictionary of target dates for today and yesterday in different formats."""
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    return {
        "kofair": [today.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d")],
        "mss": [today.strftime("%Y.%m.%d"), yesterday.strftime("%Y.%m.%d")]
    }

def get_last_ids():
    """Reads the last known post IDs for all sites from a JSON file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading state file: {e}")
            return {}
    
    # Migration from old text file if exists
    OLD_STATE_FILE = "last_id.txt"
    if os.path.exists(OLD_STATE_FILE):
        with open(OLD_STATE_FILE, "r") as f:
            old_id = f.read().strip()
            return {"kofair": old_id}
            
    return {}

def save_last_ids(ids_dict):
    """Saves the latest post IDs to a JSON file."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(ids_dict, f, indent=4)

def main():
    print("Starting Bulletin Board Monitor (KOFAIR & MSS)...")
    
    # 1. Initialize Crawlers
    crawler_configs = [
        (KofairCrawler("000063"), "kofair_notice"), # CP 안내
        (KofairCrawler("000064"), "kofair_bid"),    # CP 자료실
        (MssCrawler(), "mss")
    ]
    notifier = EmailNotifier()
    
    last_ids = get_last_ids()
    results = {} # {key: [new_posts]}

    target_dates = get_target_dates()
    
    for crawler, key in crawler_configs:
        print(f"Checking {key.upper()}...")
        current_posts = crawler.fetch_posts()
        if current_posts is None:
            results[key] = None
            continue

        if not current_posts:
            results[key] = []
            continue

        # Filter by 2-day window
        date_format_key = "kofair" if "kofair" in key else "mss"
        allowed_dates = target_dates[date_format_key]
        
        filtered_posts = [
            post for post in current_posts 
            if post["date"] in allowed_dates
        ]
        
        # Still update last_ids for internal reference (newest post)
        if current_posts:
            last_ids[key] = current_posts[0]["id"]
            
        results[key] = filtered_posts

    # 3. Process and Notify (Always)
    print("Preparing notification...")
    # Consolidate KOFAIR boards for the email section
    kofair_notice_res = results.get("kofair_notice")
    kofair_bid_res = results.get("kofair_bid")
    mss_res = results.get("mss")

    kofair_new = []
    if kofair_notice_res is not None: kofair_new += kofair_notice_res
    if kofair_bid_res is not None: kofair_new += kofair_bid_res
    
    # Check if we should notify about errors
    kofair_error = (kofair_notice_res is None or kofair_bid_res is None)
    mss_new = mss_res if mss_res is not None else []
    mss_error = (mss_res is None)
    
    # Filter logic (stars for keywords)
    all_new_posts = kofair_new + mss_new
    keywords = ["CP", "하도급", "교육", "제재", "과징금", "동반성장", "사업공고", "모집"]
    for post in all_new_posts:
        if any(kw in post["title"] for kw in keywords):
            post["title"] = f"★[중점] {post['title']}"
        print(f"- [{post['source']}] {post['title']} ({post['url']})")
    
    # Always send daily status (pass error flags)
    success = notifier.send_notification(kofair_new, mss_new, kofair_error, mss_error)
    
    if not success:
        print("CRITICAL: Notification failed to send.")
        sys.exit(1)
        
    save_last_ids(last_ids)
    print("Process completed successfully.")

if __name__ == "__main__":
    main()
