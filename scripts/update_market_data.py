import json
import re
import shutil
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

import webvtt
import whisper


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_FILE = DATA_DIR / "latest.json"
TRANSCRIPT_DIR = DATA_DIR / "transcripts"
CHUNK_DIR = DATA_DIR / "chunks"
TEMP_DIR = ROOT / "tmp"

TAIWAN_TZ = timezone(timedelta(hours=8))
MAX_SECONDS = 7200
CHUNK_SECONDS = 600

SOURCES = [
    {
        "channel": "游庭皓",
        "key": "yutinghao",
        "url": "https://www.youtube.com/@yutinghaofinance/streams"
    },
    {
        "channel": "股癌",
        "key": "gooaye",
        "url": "https://www.youtube.com/@Gooaye/videos"
    },
    {
        "channel": "M觀點",
        "key": "miula",
        "url": "https://www.youtube.com/@miulaviewpoint/streams"
    },
    {
        "channel": "科技浪",
        "key": "techwav",
        "url": "https://www.youtube.com/@tech_wav/videos"
    }
]


def run_command(command):
    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return result.stdout


def safe_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


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
        "key": source["key"],
        "videoId": video_id,
        "title": title,
        "publishDate": "未知",
        "url": f"https://www.youtube.com/watch?v={video_id}"
    }


def download_subtitle(video):
    video_temp_dir = TEMP_DIR / video["videoId"] / "subs"
    video_temp_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(video_temp_dir / "%(id)s.%(ext)s")

    command = [
        "yt-dlp",
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        "zh-Hant,zh-TW,zh-Hans,zh-CN,zh,en",
        "--sub-format",
        "vtt",
        "-o",
        output_template,
        video["url"]
    ]

    run_command(command)

    vtt_files = list(video_temp_dir.glob("*.vtt"))

    if not vtt_files:
        return None

    priority = ["zh-Hant", "zh-TW", "zh-Hans", "zh-CN", ".zh.", ".en."]

    for item in priority:
        for file in vtt_files:
            if item in file.name:
                return file

    return vtt_files[0]


def parse_vtt(vtt_path):
    lines = []
    last_text = None

    for caption in webvtt.read(str(vtt_path)):
        text = safe_text(caption.text.replace("\n", " "))

        if not text:
            continue

        if text == last_text:
            continue

        lines.append(text)
        last_text = text

    return safe_text(" ".join(lines))


def download_audio(video):
    audio_dir = TEMP_DIR / video["videoId"] / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(audio_dir / "%(id)s.%(ext)s")

    command = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "--download-sections", "*00:00:00-02:00:00",
        "-o",
        output_template,
        video["url"]
    ]

    run_command(command)

    files = list(audio_dir.glob("*.*"))

    if not files:
        raise RuntimeError("音訊下載失敗")

    return files[0]


def split_audio(audio_path, video_id):
    chunk_audio_dir = TEMP_DIR / video_id / "audio_chunks"
    chunk_audio_dir.mkdir(parents=True, exist_ok=True)

    output_pattern = str(chunk_audio_dir / "chunk_%03d.wav")

    command = [
        "ffmpeg",
        "-y",
        "-i", str(audio_path),
        "-ac", "1",
        "-ar", "16000",
        "-f", "segment",
        "-segment_time", str(CHUNK_SECONDS),
        "-c:a", "pcm_s16le",
        output_pattern
    ]

    run_command(command)

    chunks = sorted(chunk_audio_dir.glob("chunk_*.wav"))

    if not chunks:
        raise RuntimeError("音訊切段失敗")

    return chunks


def transcribe_audio_chunks(audio_chunks):
    model = whisper.load_model("tiny")

    chunk_texts = []

    for index, chunk in enumerate(audio_chunks, start=1):
        print(f"Whisper 轉文字：{chunk.name}")

        result = model.transcribe(
            str(chunk),
            language="zh",
            fp16=False
        )

        text = safe_text(result.get("text", ""))
        chunk_texts.append({
            "index": index,
            "text": text
        })

    return chunk_texts


def split_text_to_chunks(text):
    words = text.split()
    chunks = []
    current = []

    for word in words:
        current.append(word)

        if len(" ".join(current)) >= 4000:
            chunks.append(" ".join(current))
            current = []

    if current:
        chunks.append(" ".join(current))

    return chunks


def save_transcript(video, transcript_text):
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{video['key']}_{video['videoId']}.txt"
    path = TRANSCRIPT_DIR / filename

    with path.open("w", encoding="utf-8") as file:
        file.write(transcript_text)

    return f"data/transcripts/{filename}"


def save_chunks(video, chunks):
    video_chunk_dir = CHUNK_DIR / f"{video['key']}_{video['videoId']}"
    video_chunk_dir.mkdir(parents=True, exist_ok=True)

    paths = []

    for index, text in enumerate(chunks, start=1):
        filename = f"chunk_{index:02d}.txt"
        path = video_chunk_dir / filename

        with path.open("w", encoding="utf-8") as file:
            file.write(text)

        paths.append(f"data/chunks/{video['key']}_{video['videoId']}/{filename}")

    return paths


def build_video(source):
    video = get_latest_video(source)

    transcript_text = ""
    transcript_source = ""
    transcript_status = ""

    try:
        vtt_path = download_subtitle(video)

        if vtt_path:
            transcript_text = parse_vtt(vtt_path)
            transcript_source = "youtube_subtitle"
            transcript_status = "逐字稿已產出"
        else:
            raise RuntimeError("沒有可用字幕，改用音訊轉文字")

    except Exception as subtitle_error:
        print(f"{video['channel']} 字幕失敗，改用音訊：{subtitle_error}")

        audio_path = download_audio(video)
        audio_chunks = split_audio(audio_path, video["videoId"])
        chunk_texts = transcribe_audio_chunks(audio_chunks)

        transcript_text = safe_text(" ".join(item["text"] for item in chunk_texts))
        transcript_source = "audio_whisper"
        transcript_status = "逐字稿已產出"

    transcript_path = save_transcript(video, transcript_text)
    text_chunks = split_text_to_chunks(transcript_text)
    chunk_paths = save_chunks(video, text_chunks)

    video["transcriptStatus"] = transcript_status
    video["transcriptSource"] = transcript_source
    video["transcriptLanguage"] = "zh/en"
    video["transcriptLength"] = len(transcript_text)
    video["transcriptPreview"] = transcript_text[:300]
    video["transcriptPath"] = transcript_path
    video["chunkCount"] = len(chunk_paths)
    video["chunkPaths"] = chunk_paths

    video["summary"] = "已產出逐字稿與分段檔案，尚未進行 AI 摘要。"
    video["highlights"] = ["尚未分析", "尚未分析", "尚未分析", "尚未分析", "尚未分析"]
    video["investmentInsight"] = {
        "shortTerm": "尚未分析",
        "midTerm": "尚未分析",
        "longTerm": "尚未分析"
    }
    video["warning"] = "目前版本只產出逐字稿與分段檔案，下一階段才接 AI 摘要。"

    return video


def build_error_video(source, error):
    return {
        "channel": source["channel"],
        "key": source["key"],
        "videoId": "unknown",
        "title": "逐字稿產出失敗",
        "publishDate": "未知",
        "url": source["url"],
        "transcriptStatus": "逐字稿產出失敗",
        "transcriptSource": "error",
        "transcriptLanguage": "unknown",
        "transcriptLength": 0,
        "transcriptPreview": str(error)[:300],
        "transcriptPath": "",
        "chunkCount": 0,
        "chunkPaths": [],
        "summary": "逐字稿產出失敗。",
        "highlights": ["失敗", "失敗", "失敗", "失敗", "失敗"],
        "investmentInsight": {
            "shortTerm": "失敗",
            "midTerm": "失敗",
            "longTerm": "失敗"
        },
        "warning": "請查看 GitHub Actions log。"
    }


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)

    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)

    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    videos = []
    failed = []

    for source in SOURCES:
        print(f"處理：{source['channel']}")

        try:
            video = build_video(source)
            print(
                f"{video['channel']} | {video['title']} | "
                f"{video['transcriptSource']} | "
                f"{video['transcriptLength']} 字 | "
                f"{video['chunkCount']} 段"
            )
            videos.append(video)

        except Exception as error:
            print(f"{source['channel']} 失敗：{error}")
            failed.append(source["channel"])
            videos.append(build_error_video(source, error))

    now = datetime.now(TAIWAN_TZ)

    status = "逐字稿更新成功"
    if failed:
        status = "部分逐字稿產出失敗"

    data = {
        "status": status,
        "lastUpdated": now.strftime("%Y/%m/%d %H:%M"),
        "videos": videos,
        "consensus": {
            "commonTopics": ["逐字稿已產出，AI 摘要尚未啟用"],
            "differentViews": ["逐字稿已產出，AI 摘要尚未啟用"],
            "marketFocus": ["逐字稿已產出，AI 摘要尚未啟用"]
        }
    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    print("latest.json 已更新完成。")


if __name__ == "__main__":
    main()
