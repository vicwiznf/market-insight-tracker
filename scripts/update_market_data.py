import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_FILE = DATA_DIR / "latest.json"

TAIWAN_TZ = timezone(timedelta(hours=8))

SOURCES = [
    {
        "channel": "游庭皓",
        "url": "https://www.youtube.com/@yutinghaofinance/videos"
    },
    {
        "channel": "股癌",
        "url": "https://www.youtube.com/@Gooaye/videos"
    },
    {
        "channel": "M觀點",
        "url": "https://www.youtube.com/@miulaviewpoint/videos"
    },
    {
        "channel": "科技浪",
        "url": "https://www.youtube.com/@tech_wav/videos"
    }
]


def get_latest_video(source):

    result = subprocess.run(
        [
            "yt-dlp",
            "--flat-playlist",
            "--playlist-end", "1",
            "--dump-json",
            source["url"]
        ],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    item = json.loads(result.stdout.splitlines()[0])

    video_id = item["id"]

    return {
        "channel": source["channel"],
        "title": item["title"],
        "publishDate": "未知",
        "url": f"https://www.youtube.com/watch?v={video_id}"
    }


def main():

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    videos = []

    for source in SOURCES:
        videos.append(get_latest_video(source))

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
