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


def run_command(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return result.stdout


def get_latest_video(source):
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
        raise RuntimeError(f"找不到影片：{source['channel']}")

    data = json.loads(lines[0])

    video_id = data.get("id")
    title = data.get("title", "無標題")

    if not video_id:
        raise RuntimeError(f"找不到影片 ID：{source['channel']}")

    return {
        "channel": source["channel"],
        "videoId": video_id,
        "title": title,
        "publishDate": "未知",
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "transcriptStatus": "暫未啟用",
        "transcriptSource": "disabled",
        "transcriptLanguage": "unknown",
        "transcriptLength": 0,
        "transcriptPreview": "",
        "summary": "已抓到最新影片，AI 摘要尚未啟用。",
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
        "warning": "目前版本僅抓取最新影片，不進行字幕、語音或 AI 分析。"
    }


def build_error_card(source, error):
    return {
        "channel": source["channel"],
        "videoId": "unknown",
        "title": "抓取失敗",
        "publishDate": "未知",
        "url": source["url"],
        "transcriptStatus": "未執行",
        "transcriptSource": "error",
        "transcriptLanguage": "unknown",
        "transcriptLength": 0,
        "transcriptPreview": "",
        "summary": f"抓取失敗：{str(error)[:180]}",
        "highlights": [
            "抓取失敗",
            "抓取失敗",
            "抓取失敗",
            "抓取失敗",
            "抓取失敗"
        ],
        "investmentInsight": {
            "shortTerm": "抓取失敗",
            "midTerm": "抓取失敗",
            "longTerm": "抓取失敗"
        },
        "warning": "請查看 GitHub Actions log。"
    }


def main():
    videos = []
    failed_channels = []

    for source in SOURCES:
        print(f"處理：{source['channel']}")

        try:
            video = get_latest_video(source)
            print(f"成功：{video['channel']} | {video['title']} | {video['url']}")
            videos.append(video)

        except Exception as error:
            print(f"失敗：{source['channel']} | {error}")
            failed_channels.append(source["channel"])
            videos.append(build_error_card(source, error))

    now = datetime.now(TAIWAN_TZ)

    status = "最後更新成功"
    if failed_channels:
        status = "部分來源抓取失敗"

    data = {
        "status": status,
        "lastUpdated": now.strftime("%Y/%m/%d %H:%M"),
        "videos": videos,
        "consensus": {
            "commonTopics": ["AI 摘要尚未啟用"],
            "differentViews": ["AI 摘要尚未啟用"],
            "marketFocus": ["AI 摘要尚未啟用"]
        }
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    print("latest.json 已更新完成。")


if __name__ == "__main__":
    main()
