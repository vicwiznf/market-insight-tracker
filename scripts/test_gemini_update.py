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


def run_ytdlp(url):
    command = [
        "yt-dlp",
        "--flat-playlist",
        "--playlist-end", "1",
        "--dump-json",
        url
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True
    )

    lines = [line for line in result.stdout.splitlines() if line.strip()]

    if not lines:
        raise RuntimeError(f"No result from yt-dlp: {url}")

    return json.loads(lines[0])


def normalize_date(upload_date):
    if not upload_date or len(upload_date) != 8:
        return "未知"

    return f"{upload_date[0:4]}/{upload_date[4:6]}/{upload_date[6:8]}"


def fetch_video(source):
    video = run_ytdlp(source["url"])

    video_id = video.get("id")
    title = video.get("title", "無標題")
    upload_date = normalize_date(video.get("upload_date"))

    if not video_id:
        raise RuntimeError(f"Missing video id for {source['channel']}")

    return {
        "channel": source["channel"],
        "title": title,
        "publishDate": upload_date,
        "url": f"https://www.youtube.com/watch?v={video_id}",
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
        print(f"Fetching latest video: {source['channel']}")
        videos.append(fetch_video(source))

    now = datetime.now(TAIWAN_TZ)

    data = {
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
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("latest.json updated successfully.")


if __name__ == "__main__":
    main()
