import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

from faster_whisper import WhisperModel


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = ROOT / "data" / "latest.json"
AUDIO_DIR = ROOT / "audio"
TAIWAN_TZ = timezone(timedelta(hours=8))

SOURCES = [
    {"channel": "游庭皓", "url": "https://www.youtube.com/@yutinghaofinance/streams"},
    {"channel": "股癌", "url": "https://www.youtube.com/@Gooaye/videos"},
    {"channel": "M觀點", "url": "https://www.youtube.com/@miulaviewpoint/streams"},
    {"channel": "科技浪", "url": "https://www.youtube.com/@tech_wav/videos"}
]


def run_command(command):
    result = subprocess.run(command, capture_output=True, text=True)

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

    return {
        "channel": source["channel"],
        "videoId": video_id,
        "title": title,
        "publishDate": "未知",
        "url": f"https://www.youtube.com/watch?v={video_id}"
    }


def download_audio_sample(video):
    AUDIO_DIR.mkdir(exist_ok=True)

    output_path = AUDIO_DIR / f"{video['videoId']}.mp3"

    command = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "--download-sections", "*00:00:00-00:03:00",
        "-o", str(AUDIO_DIR / f"{video['videoId']}.%(ext)s"),
        video["url"]
    ]

    run_command(command)

    if not output_path.exists():
        files = list(AUDIO_DIR.glob(f"{video['videoId']}.*"))
        if files:
            return files[0]
        raise RuntimeError("音訊下載失敗")

    return output_path


def transcribe_audio(model, audio_path):
    segments, info = model.transcribe(
        str(audio_path),
        language="zh",
        beam_size=1
    )

    texts = []
    for segment in segments:
        texts.append(segment.text.strip())

    return " ".join(texts).strip()


def build_video(video, model):
    try:
        audio_path = download_audio_sample(video)
        transcript = transcribe_audio(model, audio_path)

        video["transcriptStatus"] = "Whisper 測試成功"
        video["transcriptSource"] = "audio_whisper"
        video["transcriptLanguage"] = "zh"
        video["transcriptLength"] = len(transcript)
        video["transcriptPreview"] = transcript[:200]

        video["summary"] = "已完成前 3 分鐘音訊轉文字測試，尚未進行 AI 摘要。"
        video["warning"] = "目前只測試前 3 分鐘，不代表完整影片。"

    except Exception as error:
        video["transcriptStatus"] = "Whisper 測試失敗"
        video["transcriptSource"] = "error"
        video["transcriptLanguage"] = "unknown"
        video["transcriptLength"] = 0
        video["transcriptPreview"] = str(error)[:200]

        video["summary"] = "音訊轉文字測試失敗。"
        video["warning"] = "請查看 GitHub Actions log。"

    video["highlights"] = ["尚未分析", "尚未分析", "尚未分析", "尚未分析", "尚未分析"]

    video["investmentInsight"] = {
        "shortTerm": "尚未分析",
        "midTerm": "尚未分析",
        "longTerm": "尚未分析"
    }

    return video


def main():
    print("載入 Whisper tiny 模型...")
    model = WhisperModel("tiny", device="cpu", compute_type="int8")

    videos = []

    for source in SOURCES:
        print(f"處理：{source['channel']}")
        video = get_latest_video(source)
        video = build_video(video, model)

        print(
            video["channel"],
            video["title"],
            video["transcriptStatus"],
            video["transcriptLength"]
        )

        videos.append(video)

    now = datetime.now(TAIWAN_TZ)

    data = {
        "status": "Whisper 測試完成",
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
