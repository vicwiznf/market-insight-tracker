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

PREFERRED_SUBTITLE_LANGS = [
    "zh-Hant",
    "zh-TW",
    "zh-Hans",
    "zh-CN",
    "zh",
    "en"
]


def run_command(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout


def normalize_date(upload_date):
    if not upload_date or len(upload_date) != 8:
        return "未知"
    return f"{upload_date[0:4]}/{upload_date[4:6]}/{upload_date[6:8]}"


def fetch_latest_video_basic(source):
    command = [
        "yt-dlp",
        "--flat-playlist",
        "--playlist-end", "1",
        "--dump-json",
        source["url"]
    ]

    output = run_command(command)
    lines = [line for line in output.splitlines() if line.strip()]

    if not lines:
        raise RuntimeError(f"No video found for {source['channel']}")

    video = json.loads(lines[0])
    video_id = video.get("id")

    if not video_id:
        raise RuntimeError(f"Missing video id for {source['channel']}")

    return {
        "channel": source["channel"],
        "videoId": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}"
    }


def fetch_video_detail(video_url):
    command = [
        "yt-dlp",
        "--dump-single-json",
        "--skip-download",
        video_url
    ]

    output = run_command(command)
    return json.loads(output)


def choose_subtitle_language(subtitles, automatic_captions):
    for lang in PREFERRED_SUBTITLE_LANGS:
        if lang in subtitles:
            return {
                "status": "有字幕",
                "source": "manual",
                "language": lang
            }

    for lang in PREFERRED_SUBTITLE_LANGS:
        if lang in automatic_captions:
            return {
                "status": "有自動字幕",
                "source": "automatic",
                "language": lang
            }

    if subtitles:
        lang = next(iter(subtitles.keys()))
        return {
            "status": "有字幕",
            "source": "manual",
            "language": lang
        }

    if automatic_captions:
        lang = next(iter(automatic_captions.keys()))
        return {
            "status": "有自動字幕",
            "source": "automatic",
            "language": lang
        }

    return {
        "status": "無字幕，需走音訊轉文字",
        "source": "audio_required",
        "language": "none"
    }


def fetch_video(source):
    basic = fetch_latest_video_basic(source)
    detail = fetch_video_detail(basic["url"])

    subtitles = detail.get("subtitles", {}) or {}
    automatic_captions = detail.get("automatic_captions", {}) or {}

    subtitle_info = choose_subtitle_language(subtitles, automatic_captions)

    return {
        "channel": source["channel"],
        "videoId": basic["videoId"],
        "title": detail.get("title", "無標題"),
        "publishDate": normalize_date(detail.get("upload_date")),
        "url": basic["url"],

        "transcriptStatus": subtitle_info["status"],
        "transcriptSource": subtitle_info["source"],
        "transcriptLanguage": subtitle_info["language"],

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
        video = fetch_video(source)
        print(
            f"{video['channel']} | {video['title']} | "
            f"{video['transcriptStatus']} | {video['transcriptLanguage']}"
        )
        videos.append(video)

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
