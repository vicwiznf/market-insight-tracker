import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_FILE = DATA_DIR / "latest.json"

TAIWAN_TZ = timezone(timedelta(hours=8))

CHANNELS = [
    {
        "channel": "游庭皓",
        "channelId": "UCcb_RxZ_Eh8dGnU7WkH3sxA"
    },
    {
        "channel": "股癌",
        "channelId": "UC7rHjCUbq9pJlCIYHvFQe7A"
    },
    {
        "channel": "M觀點",
        "channelId": "UCtEJYcC9cWJQfQEPHvN7s4A"
    },
    {
        "channel": "科技浪",
        "channelId": "UC6NqqvL2vQq4Y7TjvJ3V9mg"
    }
]


def get_latest_video(channel):

    api_key = os.environ["YOUTUBE_API_KEY"]

    response = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            "key": api_key,
            "part": "snippet",
            "channelId": channel["channelId"],
            "order": "date",
            "type": "video",
            "maxResults": 1
        }
    )

    data = response.json()

    item = data["items"][0]

    video_id = item["id"]["videoId"]

    return {
        "channel": channel["channel"],
        "title": item["snippet"]["title"],
        "publishDate": item["snippet"]["publishedAt"],
        "url": f"https://www.youtube.com/watch?v={video_id}"
    }


def main():

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


if __name__ == "__main__":
    main()
