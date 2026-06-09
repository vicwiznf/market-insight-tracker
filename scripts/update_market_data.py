import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)


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

PREFERRED_LANGS = [
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
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return result.stdout


def get_latest_video(source):
    command = [
        "yt-dlp",
        "--flat-playlist",
        "--playlist-end",
        "1",
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
        "url": f"https://www.youtube.com/watch?v={video_id}"
    }


def get_transcript_info(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        transcript = None
        selected_language = "unknown"

        for lang in PREFERRED_LANGS:
            try:
                transcript = transcript_list.find_transcript([lang])
                selected_language = lang
                break
            except Exception:
                pass

        if transcript is None:
            try:
                transcript = transcript_list.find_generated_transcript(PREFERRED_LANGS)
                selected_language = "auto"
            except Exception:
                pass

        if transcript is None:
            try:
                transcript = next(iter(transcript_list))
                selected_language = transcript.language_code
            except Exception:
                return {
                    "transcriptStatus": "無字幕，需走音訊轉文字",
                    "transcriptSource": "audio_required",
                    "transcriptLanguage": "none",
                    "transcriptLength": 0,
                    "transcriptPreview": ""
                }

        transcript_data = transcript.fetch()

        texts = []
        for item in transcript_data:
            start_time = item.get("start", 0)

            if start_time <= 7200:
                texts.append(item.get("text", ""))

        full_text = " ".join(texts).replace("\n", " ").strip()

        return {
            "transcriptStatus": "有字幕",
            "transcriptSource": "youtube",
            "transcriptLanguage": selected_language,
            "transcriptLength": len(full_text),
            "transcriptPreview": full_text[:120]
        }

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        return {
            "transcriptStatus": "無字幕，需走音訊轉文字",
            "transcriptSource": "audio_required",
            "transcriptLanguage": "none",
            "transcriptLength": 0,
            "transcriptPreview": ""
        }

    except Exception as error:
        return {
            "transcriptStatus": "字幕偵測失敗",
            "transcriptSource": "error",
            "transcriptLanguage": "unknown",
            "transcriptLength": 0,
            "transcriptPreview": str(error)[:120]
        }


def build_video_card(source):
    try:
        video = get_latest_video(source)
        transcript = get_transcript_info(video["videoId"])

        video.update(transcript)

        video["summary"] = "已抓到最新影片與字幕狀態，尚未進行 AI 摘要。"
        video["highlights"] = [
            "尚未分析",
            "尚未分析",
            "尚未分析",
            "尚未分析",
            "尚未分析"
        ]
        video["investmentInsight"] = {
            "shortTerm": "尚未分析",
            "midTerm": "尚未分析",
            "longTerm": "尚未分析"
        }
        video["warning"] = "尚未分析"

        return video

    except Exception as error:
        return {
            "channel": source["channel"],
            "videoId": "unknown",
            "title": "抓取失敗",
            "publishDate": "未知",
            "url": source["url"],
            "transcriptStatus": "抓取失敗",
            "transcriptSource": "error",
            "transcriptLanguage": "unknown",
            "transcriptLength": 0,
            "transcriptPreview": "",
            "summary": f"抓取失敗：{str(error)[:150]}",
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

    for source in SOURCES:
        print(f"處理：{source['channel']}")
        video = build_video_card(source)
        print(
            f"{video['channel']} | "
            f"{video['title']} | "
            f"{video['transcriptStatus']} | "
            f"{video['transcriptLanguage']} | "
            f"{video['transcriptLength']}"
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

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    print("latest.json 已更新完成。")


if __name__ == "__main__":
    main()
