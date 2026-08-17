import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import re
from urllib.parse import urljoin

URL = "https://www.gvea.com/community/bid-opportunities/"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(URL, headers=headers)

if response.status_code == 200:
    soup = BeautifulSoup(response.content, "html.parser")
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bids_data = []

    # Collect all <a> tags before decomposing layout elements
    all_a_tags = soup.find_all("a")

    # Decompose script, style, and navigation elements
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    # Extract clean text lines
    lines = [line.strip() for line in soup.get_text("\n").split("\n") if line.strip()]

    NAV_KEYWORDS = [
        "my account", "page menu", "font size", "coop connections", 
        "terms of service", "home", "menu", "select language", "fairbanks office"
    ]

    INVALID_TITLES = ["status:", "status", "closed", "open", "close date:", "close date"]

    DATE_PATTERN = r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?,?\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s*\d{4}(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:[ap]\.?m\.?))?"

    def get_safe_href(a_element):
        """Safely extracts href attribute without raising AttributeError."""
        if hasattr(a_element, "attrs") and a_element.attrs is not None:
            return a_element.attrs.get("href")
        return None

    def find_specific_url(title_str):
        """Finds the direct hyperlink matching an RFP title on the GVEA page."""
        clean_title_lower = title_str.lower().strip()

        # 1. Match by exact or partial tag text
        for a in all_a_tags:
            href = get_safe_href(a)
            if not href:
                continue
            a_text = a.get_text(" ", strip=True).lower()
            if a_text and (a_text in clean_title_lower or clean_title_lower in a_text):
                return urljoin(URL, href)

        # 2. Match by title keywords in the URL slug
        title_words = [w for w in re.findall(r"\w+", clean_title_lower) if len(w) > 3]
        if title_words:
            for a in all_a_tags:
                href = get_safe_href(a)
                if not href:
                    continue
                href_lower = href.lower()
                matches = sum(1 for word in title_words if word in href_lower)
                if matches >= min(2, len(title_words)):
                    return urljoin(URL, href)

        return URL

    # Parse text line by line
    i = 0
    while i < len(lines):
        line = lines[i]

        if "status:" in line.lower() or "close date:" in line.lower() or line.lower() in ["closed", "open"]:
            title = ""
            for k in range(i - 1, max(-1, i - 5), -1):
                candidate = lines[k].strip()
                candidate_clean = re.sub(r"^[•\-\*\s]+", "", candidate)

                if (
                    len(candidate_clean) > 5 
                    and candidate_clean.lower() not in INVALID_TITLES 
                    and not candidate_clean.lower().startswith("status:")
                    and not any(nav in candidate_clean.lower() for nav in NAV_KEYWORDS)
                ):
                    title = candidate_clean
                    break

            if title:
                block_text = " ".join(lines[max(0, i-2):min(len(lines), i+4)])

                status_match = re.search(r"Status\s*:\s*([A-Za-z]+)", block_text, re.I)
                if status_match:
                    status = status_match.group(1).capitalize()
                else:
                    status = "Closed" if "closed" in block_text.lower() else "Open"

                close_date_match = re.search(r"Close\s*Date\s*:\s*(" + DATE_PATTERN + ")", block_text, re.I)
                if close_date_match:
                    close_date = close_date_match.group(1).strip()
                else:
                    fallback_match = re.search(DATE_PATTERN, block_text, re.I)
                    close_date = fallback_match.group(0).strip() if fallback_match else "N/A"

                specific_url = find_specific_url(title)

                bids_data.append({
                    "scraped_at": scraped_at,
                    "title": title,
                    "status": status,
                    "close_date": close_date,
                    "url": specific_url
                })

        i += 1

    if bids_data:
        df = pd.DataFrame(bids_data)
        df = df[~df["title"].str.lower().isin(INVALID_TITLES)]
        df = df[~df["title"].str.lower().str.startswith("status:")]
        df = df.drop_duplicates(subset=["title"])

        df.to_csv("data.csv", index=False)
        print(f"Successfully scraped {len(df)} clean GVEA bids into data.csv")
    else:
        print("No bids found.")

else:
    print(f"Failed to fetch page. Status code: {response.status_code}")