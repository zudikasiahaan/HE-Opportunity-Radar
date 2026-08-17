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

    # Strategy: Find all list items, paragraphs, or heading containers that mention 'Status:'
    # This captures all historical and current RFPs/RFQs listed on the page.
    elements = soup.find_all(["li", "p", "div", "article"])

    for el in elements:
        text = el.get_text(" ", strip=True)
        if "Status:" in text:
            # Extract title (usually the text before 'Status:')
            parts = re.split(r"Status\s*:", text, flags=re.I)
            if len(parts) >= 2:
                title_candidates = parts[0].strip()
                # Clean up title trailing punctuation or bullets
                title = re.sub(r"^[•\-\*]\s*", "", title_candidates).strip()
                
                # Extract status and close date using regex
                status_match = re.search(r"^([^\.\n\r]+)", parts[1].strip())
                status = status_match.group(1).strip() if status_match else "N/A"
                
                date_match = re.search(r"Close\s*Date\s*:\s*([^\.\n\r]+)", text, re.I)
                close_date = date_match.group(1).strip() if date_match else "N/A"

                # Find link if available inside this element
                link_tag = el.find("a", href=True)
                url = link_tag["href"] if link_tag else URL

                if title and len(title) > 3:  # Ensure it's a valid title string
                    bids_data.append({
                        "scraped_at": scraped_at,
                        "title": title,
                        "status": status.split()[0],  # Get first word (e.g., Closed, Open)
                        "close_date": close_date,
                        "url": url
                    })

    # Fallback if block parser missed, try looking for general text patterns
    if not bids_data:
        full_text = soup.get_text("\n")
        matches = re.findall(r"([A-Za-z0-9\s–—\-]+)\s*Status\s*:\s*([A-Za-z]+)\s*Close\s*Date\s*:\s*([^\n]+)", full_text, re.I)
        for m in matches:
            bids_data.append({
                "scraped_at": scraped_at,
                "title": m[0].strip(),
                "status": m[1].strip(),
                "close_date": m[2].strip(),
                "url": URL
            })

    if bids_data:
        df = pd.DataFrame(bids_data)
        # Drop duplicate titles to keep clean unique records
        df = df.drop_duplicates(subset=["title"])
        df.to_csv("data.csv", index=False)
        print(f"Successfully scraped {len(df)} total GVEA opportunities into data.csv")
    else:
        print("Still no listings found. The layout might require a headless browser.")

else:
    print(f"Failed to fetch page. Status code: {response.status_code}")