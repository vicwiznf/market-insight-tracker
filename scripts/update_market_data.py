import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import webvtt


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_FILE = DATA_DIR / "latest.json"
TEMP_DIR = ROOT / "tmp"

TAIWAN_TZ = timezone(timedelta(hours=8))

OPENROUTER_MODEL = "openrouter/free"
MAX_TRANSCRIPT_CHARS = 45000

YTDLP = [
    "yt-dlp",
    "--js-runtimes",
    "node"
]

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
    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return result.stdout


def clean_text(text):
    text = text or ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_json_text(text):
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("AI 沒有回傳 JSON")

    return text[start:end + 1]


def openrouter_json(prompt):
    api_key = os.environ.get("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError("缺少 OPENROUTER_API_KEY")

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://vicwiznf.github.io/market-insight-tracker/",
        "X-Title": "Market Insight Tracker"
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2
    }

    last_error = None

    for attempt in range(3):
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=120
            )

            if response.status_code >= 400:
                raise RuntimeError(
                    f"OpenRouter HTTP {response.status_code}: {response.text[:500]}"
                )

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            return json.loads(clean_json_text(content))

        except Exception as error:
            last_error = error
            print(f"OpenRouter 嘗試失敗 {attempt + 1}/3：{error}")
            time.sleep(10)

    raise RuntimeError(last_error)


def get_latest_video(source):
    command = YTDLP + [
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
        "url": f"https://www.youtube.com/watch?v={video_id}"
    }


def download_subtitle(video):
    subtitle_dir = TEMP_DIR / video["videoId"] / "subs"
    subtitle_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(subtitle_dir / "%(id)s.%(ext)s")

    command = YTDLP + [
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

    vtt_files = list(subtitle_dir.glob("*.vtt"))

    if not vtt_files:
        raise RuntimeError("找不到字幕或自動字幕")

    priority = ["zh-Hant", "zh-TW", "zh-Hans", "zh-CN", ".zh.", ".en."]

    for key in priority:
        for file in vtt_files:
            if key in file.name:
                return file

    return vtt_files[0]


def parse_vtt(vtt_path):
    lines = []
    last_text = None

    for caption in webvtt.read(str(vtt_path)):
        text = clean_text(caption.text.replace("\n", " "))

        if not text:
            continue

        if text == last_text:
            continue

        lines.append(text)
        last_text = text

    return clean_text(" ".join(lines))


def get_transcript(video):
    vtt_path = download_subtitle(video)
    text = parse_vtt(vtt_path)

    if len(text) < 100:
        raise RuntimeError("字幕內容太短，無法分析")

    return text[:MAX_TRANSCRIPT_CHARS]


def analyze_video(video, transcript):
    prompt = f"""
你是一個市場與股市影片整理系統。

請完全依照影片內容整理，不要加入你自己的投資建議，不要自行補充影片沒有說的內容。
如果影片沒有明確談到市場、總經、產業、股市或投資，請直接說明「本影片市場與股市內容有限」。

影片資料：
頻道：{video["channel"]}
標題：{video["title"]}
連結：{video["url"]}

文字稿：
{transcript}

請只輸出 JSON，不要 Markdown，不要 ```。

格式必須是：

{{
  "summary": "約 300 字摘要",
  "highlights": [
    "重點一",
    "重點二",
    "重點三",
    "重點四",
    "重點五"
  ],
  "investmentInsight": {{
    "shortTerm": "短期 1～3 個月，完全依照影片內容；沒有提到就寫影片未明確提到",
    "midTerm": "中期 3～12 個月，完全依照影片內容；沒有提到就寫影片未明確提到",
    "longTerm": "長期 1 年以上，完全依照影片內容；沒有提到就寫影片未明確提到"
  }},
  "warning": "影片中提到的風險、前提、限制；如果影片沒有提到，請寫：影片未明確提到相關風險。"
}}
"""

    return openrouter_json(prompt)


def fallback_analysis(error):
    return {
        "summary": f"摘要失敗：{str(error)[:220]}",
        "highlights": [
            "摘要失敗",
            "摘要失敗",
            "摘要失敗",
            "摘要失敗",
            "摘要失敗"
        ],
        "investmentInsight": {
            "shortTerm": "摘要失敗",
            "midTerm": "摘要失敗",
            "longTerm": "摘要失敗"
        },
        "warning": "請查看 GitHub Actions log，可能是 OpenRouter 額度、YouTube 字幕或 yt-dlp 問題。"
    }


def analyze_consensus(videos):
    compact = []

    for video in videos:
        compact.append({
            "channel": video["channel"],
            "title": video["title"],
            "summary": video["summary"],
            "highlights": video["highlights"],
            "investmentInsight": video["investmentInsight"],
            "warning": video["warning"]
        })

    prompt = f"""
你是一個市場觀點整理系統。

以下是四支影片的摘要結果。
請只根據這些內容整理市場共識，不要自行補充外部資訊，不要做看多看空投票。

資料：
{json.dumps(compact, ensure_ascii=False)}

請只輸出 JSON，不要 Markdown，不要 ```。

格式：

{{
  "commonTopics": [
    "共同關注主題一",
    "共同關注主題二",
    "共同關注主題三"
  ],
  "differentViews": [
    "有分歧的議題一",
    "有分歧的議題二"
  ],
  "marketFocus": [
    "今日市場焦點一",
    "今日市場焦點二",
    "今日市場焦點三"
  ]
}}
"""

    return openrouter_json(prompt)


def build_video(source):
    video = get_latest_video(source)

    try:
        transcript = get_transcript(video)

        video["transcriptStatus"] = "已取得字幕"
        video["transcriptSource"] = "youtube_subtitle"
        video["transcriptLength"] = len(transcript)

        analysis = analyze_video(video, transcript)

        video["summary"] = analysis["summary"]
        video["highlights"] = analysis["highlights"]
        video["investmentInsight"] = analysis["investmentInsight"]
        video["warning"] = analysis["warning"]

    except Exception as error:
        video["transcriptStatus"] = "字幕或 AI 分析失敗"
        video["transcriptSource"] = "error"
        video["transcriptLength"] = 0

        analysis = fallback_analysis(error)

        video["summary"] = analysis["summary"]
        video["highlights"] = analysis["highlights"]
        video["investmentInsight"] = analysis["investmentInsight"]
        video["warning"] = analysis["warning"]

    return video


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)

    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    videos = []

    for source in SOURCES:
        print(f"處理：{source['channel']}")
        video = build_video(source)
        print(f"{video['channel']} | {video['title']} | {video['transcriptStatus']}")
        videos.append(video)

    try:
        consensus = analyze_consensus(videos)
    except Exception as error:
        consensus = {
            "commonTopics": [f"市場共識整理失敗：{str(error)[:120]}"],
            "differentViews": ["市場共識整理失敗"],
            "marketFocus": ["市場共識整理失敗"]
        }

    now = datetime.now(TAIWAN_TZ)

    data = {
        "status": "OpenRouter 摘要更新完成",
        "lastUpdated": now.strftime("%Y/%m/%d %H:%M"),
        "videos": videos,
        "consensus": consensus
    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    print("latest.json 已更新完成。")


if __name__ == "__main__":
    main()
