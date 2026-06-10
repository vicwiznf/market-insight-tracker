import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(**file**).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_FILE = DATA_DIR / "latest.json"

TAIWAN_TZ = timezone(timedelta(hours=8))

CHANNELS = [
{
"channel": "游庭皓",
"username": "yutinghaofinance"
},
{
"channel": "股癌",
"username": "Gooaye"
},
{
"channel": "M觀點",
"username": "miulaviewpoint"
},
{
"channel": "科技浪",
"username": "tech_wav"
}
]

def get_latest_video(channel):

```
api_key = os.environ["YOUTUBE_API_KEY"]

response = requests.get(
    "https://www.googleapis.com/youtube/v3/search",
    params={
        "key": api_key,
        "part": "snippet",
        "q": channel["username"],
        "type": "video",
        "order": "date",
        "maxResults": 1
    }
)

data = response.json()

if "items" not in data or len(data["items"]) == 0:
    raise RuntimeError(f"{channel['channel']} 找不到影片")

item = data["items"][0]

video_id = item["id"]["videoId"]

return {
    "channel": channel["channel"],
    "title": item["snippet"]["title"],
    "publishDate": item["snippet"]["publishedAt"],
    "url": f"https://www.youtube.com/watch?v={video_id}"
}
```

def main():

```
DATA_DIR.mkdir(parents=True, exist_ok=True)

videos = []

for channel in CHANNELS:
    videos.append(get_latest_video(channel))

now = datetime.now(TAIWAN_TZ)

output = {
    "status": "更新成功",
    "lastUpdated": now.strftime("%Y/%m/%d %H:%M"),
    "videos": videos
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
```

if **name** == "**main**":
main()
