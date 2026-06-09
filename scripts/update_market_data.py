import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = ROOT / "data" / "latest.json"
TAIWAN_TZ = timezone(timedelta(hours=8))

SOURCES = [
    {"channel": "游庭皓", "url": "https://www.youtube.com/@yutinghaofinance/streams"},
    {"channel": "股癌", "url": "https://www.youtube.com/@Gooaye/videos"},
    {"channel": "M觀點", "url": "https://www.youtube.com/@miulaviewpoint/streams"},
    {"channel": "科技浪", "url": "https://www.youtube.com/@tech_wav/videos"}
]

PREFERRED_SUBTITLE_LANGS = [
    "zh-Hant", "zh-TW", "zh-Hans", "zh-CN", "zh", "en"
]


def run_command(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(command)
            + "\nSTDOUT:\n"
            + result.stdout
            + "\nSTDERR:\n"
            + result.stderr
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
        "title": video.get("title", "無標題"),
        "url": f"https://www.youtube.com/watch?v={video_id}"
    }


def fetch_video_detail(video_url):
    command = [
        "yt-dlp",
        "--dump-single-json",
        "--skip-download",
        "--ignore-no-formats-error",
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


def placeholder_video(source, error_message):
    return {
        "channel": source["channel"],
        "videoId": "unknown",
        "title": "抓取失敗",
        "publishDate": "未知",
        "url": source["url"],
        "transcriptStatus": "影片抓取失敗",
        "transcriptSource": "error",
        "transcriptLanguage": "unknown",
        "summary": f"抓取失敗：{error_message[:200]}",
        "highlights": ["抓取失敗", "抓取失敗", "抓取失敗", "抓取失敗", "抓取失敗"],
        "investmentInsight": {
            "shortTerm": "抓取失敗",
            "midTerm": "抓取失敗",
            "longTerm": "抓取失敗"
        },
        "warning": "請查看 GitHub Actions log。"
    }


def fetch_video(source):
    basic = fetch_latest_video_basic(source)

    video = {
        "channel": source["channel"],
        "videoId": basic["videoId"],
        "title": basic["title"],
        "publishDate": "未知",
        "url": basic["url"],
        "transcriptStatus": "字幕偵測失敗",
        "transcriptSource": "unknown",
        "transcriptLanguage": "unknown",
        "summary": "已抓到最新影片，尚未進行 AI 摘要。",
        "highlights": ["尚未分析", "尚未分析", "尚未分析", "尚未分析", "尚未分析"],
        "investmentInsight": {
            "shortTerm": "尚未分析",
            "midTerm": "尚未分析",
            "longTerm": "尚未分析"
        },
        "warning": "尚未分析"
    }

    try:
        detail = fetch_video_detail(basic["url"])

        subtitles = detail.get("subtitles", {}) or {}
        automatic_captions = detail.get("automatic_captions", {}) or {}
        subtitle_info = choose_subtitle_language(subtitles, automatic_captions)

        video["title"] = detail.get("title", basic["title"])
        video["publishDate"] = normalize_date(detail.get("upload_date"))
        video["transcriptStatus"] = subtitle_info["status"]
        video["transcriptSource"] = subtitle_info["source"]
        video["transcriptLanguage"] = subtitle_info["language"]

    except Exception as error:
        print(f"Subtitle detection failed for {source['channel']}: {error}")
        video["warning"] = "影片已抓到，但字幕偵測失敗。"

    return video


def main():
    videos = []
    errors = []

    for source in SOURCES:
        print(f"Fetching latest video: {source['channel']}")

        try:
            video = fetch_video(source)
            print(
                f"{video['channel']} | {video['title']} | "
                f"{video['transcriptStatus']} | {video['transcriptLanguage']}"
            )
            videos.append(video)

        except Exception as error:
            print(f"Failed source: {source['channel']}: {error}")
            errors.append(source["channel"])
            videos.append(placeholder_video(source, str(error)))

    now = datetime.now(TAIWAN_TZ)

    status = "最後更新成功"
    if errors:
        status = "部分來源抓取失敗"

    data = {
        "status": status,
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
