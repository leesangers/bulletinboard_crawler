import requests
from bs4 import BeautifulSoup
import re

class KofairCrawler:
    BASE_URL = "https://www.kofair.or.kr"

    def __init__(self, menu_cd="000064"):
        self.menu_cd = menu_cd
        self.list_url = f"{self.BASE_URL}/home/board/brdList.do?menu_cd={self.menu_cd}"
        self.detail_url_template = f"{self.BASE_URL}/home/board/brdDetail.do?menu_cd={self.menu_cd}&num={{}}"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch_posts(self):
        """
        Fetches the list of posts from the board (JSON response).
        Returns a list of dictionaries containing post info.
        """
        try:
            response = requests.get(self.list_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            board_list = data.get("brdList", [])
            
            posts = []
            for item in board_list:
                post_num = str(item.get("num"))
                title = item.get("title", "")
                date = item.get("write_dt", "")
                
                posts.append({
                    "id": post_num,
                    "title": title,
                    "date": date,
                    "url": self.detail_url_template.format(post_num),
                    "source": "KOFAIR"
                })
            
            # Handle notices if needed from fstBrdList
            fst_list = data.get("fstBrdList", [])
            notice_ids = [str(i.get("num")) for i in fst_list]
            for post in posts:
                if post["id"] in notice_ids:
                    post["title"] = f"[공지] {post['title']}"

            return posts
        except Exception as e:
            print(f"Error fetching KOFAIR posts ({self.menu_cd}): {e}")
            return None

class MssCrawler:
    BASE_URL = "https://www.mss.go.kr"
    LIST_URL = f"{BASE_URL}/site/smba/ex/bbs/List.do?cbIdx=310"
    DETAIL_URL_TEMPLATE = f"{BASE_URL}/site/smba/ex/bbs/View.do?cbIdx=310&bcIdx={{}}"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.mss.go.kr/site/smba/ex/bbs/List.do?cbIdx=310",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive"
        }

    def fetch_posts(self):
        """
        Fetches the list of posts from the MSS board.
        Returns a list of dictionaries containing post info.
        """
        try:
            response = requests.get(self.LIST_URL, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            # Try finding the table more generically
            table = soup.select_one("table.board-list")
            if not table:
                table = soup.find("table", {"summary": re.compile("공지사항")})
            
            if not table:
                # Fallback to the first table if others fail
                table = soup.find("table")

            if not table:
                print("  No table found on MSS page.")
                return []
            
            rows = table.select("tbody tr")
            posts = []
            for row in rows:
                # Find the subject link - could be 'a.pc-detail' or just an anchor in a subject cell
                subject_link = row.select_one("a.pc-detail") or row.select_one("td.subject a") or row.select_one("a")
                if not subject_link:
                    continue
                
                title = subject_link.get_text(strip=True)
                if not title:
                    continue
                
                # Extract bcIdx from onclick: doBbsFView('310', '1066313', ...)
                onclick_text = subject_link.get("onclick", "") or row.get("onclick", "")
                match = re.search(r"doBbsFView\(\s*'(\d+)'\s*,\s*'(\d+)'", onclick_text)
                if not match:
                    # Try a more relaxed regex
                    match = re.search(r"doBbsFView\([^,]+,\s*'(\d+)'", onclick_text)
                
                if not match:
                    continue
                
                # The second ID is usually the bc_idx
                bc_idx = match.group(2) if match.lastindex >= 2 else match.group(1)
                
                # Date is usually in the 4th column (index 3)
                tds = row.find_all("td")
                date = ""
                if len(tds) > 3:
                    date = tds[3].get_text(strip=True)
                
                posts.append({
                    "id": bc_idx,
                    "title": title,
                    "date": date,
                    "url": self.DETAIL_URL_TEMPLATE.format(bc_idx),
                    "source": "MSS"
                })
            
            return posts
        except Exception as e:
            print(f"CRITICAL ERROR fetching MSS posts: {type(e).__name__}: {e}")
            return None

if __name__ == "__main__":
    print("--- Testing KOFAIR Crawler ---")
    k_crawler = KofairCrawler()
    k_posts = k_crawler.fetch_posts()
    for post in k_posts[:3]:
        print(f"[{post['source']}] {post['id']}: {post['title']} ({post['date']})")

    print("\n--- Testing MSS Crawler ---")
    m_crawler = MssCrawler()
    m_posts = m_crawler.fetch_posts()
    for post in m_posts[:3]:
        print(f"[{post['source']}] {post['id']}: {post['title']} ({post['date']})")
