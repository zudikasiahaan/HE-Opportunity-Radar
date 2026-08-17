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

    # 1. Remove script, style, and navigation elements
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    # 2. Extract clean text lines
    lines = [line.strip() for line in soup.get_text("\n").split("\n") if line.strip()]

    NAV_KEYWORDS = [
        "my account", "page menu", "font size", "coop connections", 
        "terms of service", "home", "menu", "select language", "fairbanks office"
    ]

    INVALID_TITLES = ["status:", "status", "closed", "open", "close date:", "close date"]

    # 3. Parse line by line
    i = 0
    while i < len(lines):
        line = lines[i]

        if "status:" in line.lower() or "close date:" in line.lower() or line.lower() in ["closed", "open"]:
            title = ""
            for k in range(i - 1, max(-1, i - 5), -1):
                candidate = lines[k].strip()
                candidate_clean = re.sub(r"^[•\-\*\s]+", "", candidate)
                
                # Check candidate is a genuine title (not menu, not a label like "Status:" or "Closed")
                if (
                    len(candidate_clean) > 5 
                    and candidate_clean.lower() not in INVALID_TITLES 
                    and not candidate_clean.lower().startswith("status:")
                    and not any(nav in candidate_clean.lower() for nav in NAV_KEYWORDS)
                ):
                    title = candidate_clean
                    break

            if title:
                # Look around for status and close date in nearby lines
                block_text = " ".join(lines[max(0, i-2):min(len(lines), i+4)])
                
                status_match = re.search(r"Status\s*:\s*([A-Za-z]+)", block_text, re.I)
                if status_match:
                    status = status_match.group(1).capitalize()
                else:
                    status = "Closed" if "closed" in block_text.lower() else "Open"

                date_match = re.search(r"Close\s*Date\s*:\s*([^\.\n\r]+)", block_text, re.I)
                if date_match:
                    close_date = date_match.group(1).strip()
                else:
                    full_date = re.search(
                        r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?,?\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s*\d{4}[^\.]*", 
                        block_text, 
                        re.I
                    )
                    close_date = full_date.group(0).strip() if full_date else "N/A"

                link_tag = soup.find("a", string=re.compile(re.escape(title[:15]), re.I))
                url = link_tag["href"] if link_tag and link_tag.has_attr("href") else URL

                bids_data.append({
                    "scraped_at": scraped_at,
                    "title": title,
                    "status": status,
                    "close_date": close_date,
                    "url": url
                })

        i += 1

    if bids_data:
        df = pd.DataFrame(bids_data)
        # Drop duplicates and invalid titles
        df = df[~df["title"].str.lower().isin(INVALID_TITLES)]
        df = df[~df["title"].str.lower().str.startswith("status:")]
        df = df.drop_duplicates(subset=["title"])
        
        df.to_csv("data.csv", index=False)
        print(f"Successfully scraped {len(df)} clean GVEA bids into data.csv")
    else:
        print("No bids found.")

else:
    print(f"Failed to fetch page. Status code: {response.status_code}")