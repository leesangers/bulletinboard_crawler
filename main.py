import os
import json
from crawler import KofairCrawler, MssCrawler
from notifier import EmailNotifier

STATE_FILE = "last_ids.json"

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
    
    # Initialize crawlers: (instance, state_key)
    crawler_configs = [
        (KofairCrawler(), "kofair"),
        (MssCrawler(), "mss")
    ]
    notifier = EmailNotifier()
    
    last_ids = get_last_ids()
    results = {} # {key: [new_posts]}

    for crawler, key in crawler_configs:
        print(f"Checking {key.upper()}...")
        current_posts = crawler.fetch_posts()
        if not current_posts:
            results[key] = []
            continue

        last_id = last_ids.get(key)
        new_posts_for_site = []

        if last_id is None:
            # First run: pick top 3
            new_posts_for_site = current_posts[:3]
            last_ids[key] = current_posts[0]["id"]
        else:
            for post in current_posts:
                if post["id"] == last_id:
                    break
                new_posts_for_site.append(post)
            
            if new_posts_for_site:
                last_ids[key] = current_posts[0]["id"]
        
        results[key] = new_posts_for_site

    # 3. Process and Notify (Always)
    print("Preparing notification...")
    kofair_new = results.get("kofair", [])
    mss_new = results.get("mss", [])
    
    # Filter logic (stars for keywords)
    keywords = ["CP", "하도급", "교육", "제재", "과징금", "동반성장", "사업공고", "모집"]
    for post in kofair_new + mss_new:
        if any(kw in post["title"] for kw in keywords):
            post["title"] = f"★[중점] {post['title']}"
        print(f"- [{post['source']}] {post['title']} ({post['url']})")
    
    # Always send daily status
    notifier.send_notification(kofair_new, mss_new)
    save_last_ids(last_ids)

if __name__ == "__main__":
    main()
