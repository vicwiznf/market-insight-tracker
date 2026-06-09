import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from google import genai


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = ROOT / "data" / "latest.json"

TAIWAN_TZ = timezone(timedelta(hours=8))

MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash"
]


def clean_json_text(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("Gemini response does not contain JSON.")

    return text[start:end + 1]


def ask_gemini() -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY")

    client = genai.Client(api_key=api_key)

    prompt = """
你是一個市場影片摘要系統。

請產生一份測試用 JSON，不要輸出 Markdown，不要輸出 ```。
JSON 格式必須完全符合：

{
  "status": "最後更新成功",
  "lastUpdated": "YYYY/MM/DD HH:mm",
  "videos": [
    {
      "channel": "游庭皓",
      "title": "測試標題",
      "publishDate": "YYYY/MM/DD",
      "url": "https://youtube.com",
      "summary": "約 80 字的測試摘要",
      "highlights": ["重點一", "重點二", "重點三", "重點四", "重點五"],
      "investmentInsight": {
        "shortTerm": "短期投資啟發",
        "midTerm": "中期投資啟發",
        "longTerm": "長期投資啟發"
      },
      "warning": "注意事項"
    }
  ],
  "consensus": {
    "commonTopics": ["主題一", "主題二", "主題三"],
    "differentViews": ["分歧一", "分歧二"],
    "marketFocus": ["焦點一", "焦點二", "焦點三"]
  }
}

videos 必須有四筆，channel 分別是：
游庭皓、股癌、M觀點、科技浪。
"""

    last_error = None

    for model in MODELS:
        for attempt in range(3):
            try:
                print(f"Trying model: {model}, attempt: {attempt + 1}")

                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                )

                text = clean_json_text(response.text)
                return json.loads(text)

            except Exception as error:
                last_error = error
                print(f"Failed with {model}: {error}")
                time.sleep(5)

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


def main():
    data = ask_gemini()

    now = datetime.now(TAIWAN_TZ)
    data["status"] = "最後更新成功"
    data["lastUpdated"] = now.strftime("%Y/%m/%d %H:%M")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("latest.json updated successfully.")


if __name__ == "__main__":
    main()
