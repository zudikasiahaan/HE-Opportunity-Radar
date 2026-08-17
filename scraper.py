import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

# 1. Target URL
URL = "https://news.ycombinator.com/" # Example: Hacker News

# 2. Fetch page content
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
response = requests.get(URL, headers=headers)

if response.status_code == 200:
    soup = BeautifulSoup(response.content, "html.parser")
    
    # 3. Parse specific elements
    titles = []
    links = []
    
    for item in soup.select(".titleline > a"):
        titles.append(item.get_text())
        links.append(item.get("href"))
    
    # 4. Save to pandas DataFrame & CSV
    df = pd.DataFrame({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": titles,
        "url": links
    })
    
    df.to_csv("data.csv", index=False)
    print(f"Successfully scraped {len(titles)} items into data.csv")
else:
    print(f"Failed to fetch page. Status code: {response.status_code}")