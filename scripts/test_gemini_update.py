import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = ROOT / "data" / "latest.json"

TAIWAN_TZ = timezone(timedelta(hours=8))

SOURCES = [
    {
        "channel": "游庭皓",
        "url": "https://www.youtube.com/@yutinghaofinance/streams"
    },
    {
        "channel": "股癌",
        "url": "https://www.youtube.com/@Gooaye/videos"
    },
    {
        "channel": "M觀點",
        "url": "https://www.youtube.com/@miulaviewpoint/streams"
    },
    {
        "channel": "科技浪",
        "url": "https://www.youtube.com/@tech_wav/videos"
    }
]


def run_ytdlp(url: str) -> dict:
    command = [
        "yt-dlp",
        "--dump-single-json",
        "--playlist-end",
        "1",
        "--flat-playlist",
        url
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True
    )

    return json.loads(result.stdout)


def fetch_latest_video(source: dict) -> dict:
    data = run_ytdlp(source["url"])

    entries = data.get("entries", [])

    if not entries:
        raise RuntimeError(f"No video found for {source['channel']}")

    video = entries[0]

    video_id = video.get("id")
    title = video.get("title", "無標題")

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    return {
        "channel": source["channel"],
        "title": title,
        "publishDate": video.get("upload_date", "未知"),
        "url": video_url,

        "summary": "已抓到最新影片，尚未進行 AI 摘要。",

        "highlights": [
            "尚未分析",
            "尚未分析",
            "尚未分析",
            "尚未分析",
            "尚未分析"
        ],

        "investmentInsight": {
            "shortTerm": "尚未分析",
            "midTerm": "尚未分析",
            "longTerm": "尚未分析"
        },

        "warning": "尚未分析"
    }


def main():
    videos = []

    for source in SOURCES:
        print(f"Fetching: {source['channel']}")
        videos.append(fetch_latest_video(source))

    now = datetime.now(TAIWAN_TZ)

    output = {
        "status": "最後更新成功",
        "lastUpdated": now.strftime("%Y/%m/%d %H:%M"),
        "videos": videos,
        "consensus": {
            "commonTopics": ["尚未分析"],
            "differentViews": ["尚未分析"],
            "marketFocus": ["尚未分析"]
        }
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("latest.json updated with latest YouTube videos.")


if __name__ == "__main__":
    main()
