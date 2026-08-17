import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re

URL = "https://www.gvea.com/community/bid-opportunities/"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(URL, headers=headers)

if response.status_code == 200:
    soup = BeautifulSoup(response.content, "html.parser")
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bids_data = []

    # 1. Strip out header, footer, and navigation menus entirely
    for nav in soup.find_all(["nav", "header", "footer", "aside"]):
        nav.decompose()

    NAV_KEYWORDS = ["my account", "page menu", "font size", "coop connections", "terms of service", "start/stop service", "mygvea"]

    # 2. Target block elements
    elements = soup.find_all(["li", "p", "div", "article"])

    for el in elements:
        # Skip parent containers that have nested elements containing 'Status:' to prevent duplicate full-page text
        if el.find_all(lambda e: e != el and "Status:" in e.get_text()):
            continue

        text = el.get_text(" ", strip=True)
        text_lower = text.lower()

        # Skip blocks that contain navigation text
        if any(keyword in text_lower for keyword in NAV_KEYWORDS):
            continue

        if "Status:" in text or "Closed" in text or "Open" in text:
            if "Status:" in text:
                parts = re.split(r"Status\s*:", text, flags=re.I)
                raw_title = parts[0].strip()
                rest = parts[1].strip()
                status_match = re.search(r"^([^\.\n\r\t]+)", rest)
                status = status_match.group(1).strip() if status_match else "N/A"
            else:
                match = re.search(r"^(.*?)\s*(Closed|Open)\s*(.*)$", text, re.I)
                if match:
                    raw_title = match.group(1).strip()
                    status = match.group(2).strip()
                else:
                    continue

            # Extract Close Date
            date_match = re.search(r"Close\s*Date\s*:\s*([^\.\n\r]+)", text, re.I)
            if not date_match:
                date_match = re.search(r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?,?\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s*\d{4}", text, re.I)
            close_date = date_match.group(0).strip() if date_match else "N/A"

            # Clean title
            clean_title = re.sub(r"^[•\-\*]\s*", "", raw_title).strip()
            clean_title = re.sub(r"^Bid Opportunities\s*", "", clean_title, flags=re.I).strip()

            link_tag = el.find("a", href=True)
            url = link_tag["href"] if link_tag else URL

            # Filter titles by reasonable length and exclude navigation text
            if clean_title and 5 < len(clean_title) < 150 and not any(k in clean_title.lower() for k in NAV_KEYWORDS):
                bids_data.append({
                    "scraped_at": scraped_at,
                    "title": clean_title,
                    "status": status.split()[0],
                    "close_date": close_date,
                    "url": url
                })

    if bids_data:
        df = pd.DataFrame(bids_data)
        df = df.drop_duplicates(subset=["title"])
        df.to_csv("data.csv", index=False)
        print(f"Successfully scraped {len(df)} clean GVEA opportunities into data.csv")
    else:
        print("No valid bids matched the criteria.")

else:
    print(f"Failed to fetch page. Status code: {response.status_code}")