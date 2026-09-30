# 1. 舊版 MoviePy 與新版 Pillow 相容性補丁
from PIL import Image, ImageDraw, ImageFont
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

import os
import glob
import time
import json
import logging
import urllib.parse
import requests
import feedparser
import numpy as np
from datetime import datetime, timedelta
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip

# ==========================================
# 記錄日誌 (Logging) 設定
# ==========================================
LOG_FILE = "pipeline_log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# ==========================================
# 核心設定與 API 金鑰
# ==========================================
DID_API_KEY = "Z29vZ2xlLW9hdXRoMnwxMTU5NzY0Mzg2NTQ0NDYyNjU5NjBAYWtfY01WaldwR1FIWW1CMDRCR0JoQWJN:0NxD998Y7eFPQOjKCP5E-"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

BG_IMAGE = "bg.jpg"
OUTPUT_DIR = "daily_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TODAY_STR = datetime.now().strftime("%Y%m%d")
FINAL_OUTPUT_MP4 = os.path.join(OUTPUT_DIR, f"news_{TODAY_STR}.mp4")
EVENT_IMG_FILE = "temp_event.jpg"

VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
RIGHT_BOX_X, RIGHT_BOX_Y = 435, 46
RIGHT_BOX_W, RIGHT_BOX_H = 800, 505
LEFT_BOX_X, LEFT_BOX_Y = 36, 175
LEFT_BOX_W = 345

ENABLE_YOUTUBE_UPLOAD = False  # 待拿到 Google client_secrets.json 後改為 True

# ==========================================
# 功能：自動清理超過 7 天的歷史影片
# ==========================================
def cleanup_old_videos(keep_days=7):
    logging.info(f"🧹 開始檢查歷史影片，僅保留最近 {keep_days} 天...")
    now = datetime.now()
    cutoff_time = now - timedelta(days=keep_days)
    
    mp4_files = glob.glob(os.path.join(OUTPUT_DIR, "*.mp4"))
    deleted_count = 0
    for file_path in mp4_files:
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        if file_mtime < cutoff_time:
            try:
                os.remove(file_path)
                deleted_count += 1
                logging.info(f"   已刪除過期影片: {os.path.basename(file_path)}")
            except Exception as e:
                logging.error(f"   刪除檔案失敗 {file_path}: {e}")
    logging.info(f"✅ 清理完成，共刪除 {deleted_count} 支舊影片。")

# ==========================================
# 階段 1：抓取即時新聞
# ==========================================
def step1_fetch_news():
    logging.info("[階段 1/5] 抓取即時新聞 RSS...")
    rss_url = "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(rss_url)
    if not feed.entries:
        raise RuntimeError("無法連線至新聞 RSS 源！")
    
    top_entry = feed.entries[0]
    raw_title = top_entry.title.split(" - ")[0].strip()
    raw_summary = top_entry.get("summary", "")
    logging.info(f"   今日頭條新聞：{raw_title}")
    return raw_title, raw_summary

# ==========================================
# 階段 2：生成主播講稿
# ==========================================
def step2_generate_script(title, summary):
    logging.info("[階段 2/5] 生成主播播報稿與跑馬燈...")
    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            prompt = (
                f"你是一位專業電視新聞主播。根據這則新聞標題：『{title}』，"
                "請生成一份約 60~80 字、口吻專業自然的電視新聞播報稿，"
                "開頭須有『各位觀眾好，歡迎收看焦點新聞』，結尾有感謝收看。"
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            script_text = response.text.replace("\n", "").strip()
            ticker_title = title[:28]
            return ticker_title, script_text
        except Exception as e:
            logging.warning(f"LLM 呼叫失敗 ({e})，切換回標準主播模板")

    ticker_title = title[:28]
    script_text = (
        f"各位觀眾好，歡迎收看焦點新聞。"
        f"今天為您聚焦最新科技進展，{title}。"
        f"相關趨勢與市場動態持續引發關注，更多消息請持續鎖定報導，感謝您的收看。"
    )
    return ticker_title, script_text

# ==========================================
# 階段 3：取得新聞配圖
# ==========================================
def step3_get_event_image(title):
    logging.info("[階段 3/5] 自動生成新聞事件現場配圖...")
    clean_keyword = urllib.parse.quote(f"photorealistic news photography of {title}, dramatic lighting, 8k")
    img_url = f"https://image.pollinations.ai/prompt/{clean_keyword}?width=800&height=500&nologo=true"
    
    res = requests.get(img_url, timeout=30)
    with open(EVENT_IMG_FILE, "wb") as f:
        f.write(res.content)
    logging.info("✅ 事件現場配圖已下載完成。")
    return EVENT_IMG_FILE

# ==========================================
# 階段 4：D-ID 驅動主播對嘴
# ==========================================
def step4_generate_anchor_talk(script_text):
    logging.info("[階段 4/5] 呼叫 D-ID 雲端算力對嘴生成...")
    avatar_path = None
    for name in ["anchor.jpg", "anchor.png", "anchor.jpeg"]:
        if os.path.exists(name):
            avatar_path = name
            break
    if not avatar_path:
        raise FileNotFoundError("找不到主播照片 (anchor.jpg 或 anchor.png)！")

    url_img = "https://api.d-id.com/images"
    headers_auth = {"accept": "application/json", "authorization": f"Basic {DID_API_KEY}"}
    mime = "image/png" if avatar_path.lower().endswith(".png") else "image/jpeg"
    with open(avatar_path, "rb") as f:
        res = requests.post(url_img, files={"image": (os.path.basename(avatar_path), f, mime)}, headers=headers_auth)
    source_url = res.json().get("url")

    url_talk = "https://api.d-id.com/talks"
    headers_talk = {"accept": "application/json", "content-type": "application/json", "authorization": f"Basic {DID_API_KEY}"}
    payload = {
        "script": {
            "type": "text",
            "provider": {"type": "microsoft", "voice_id": "zh-TW-YunJheNeural"},
            "input": script_text
        },
        "source_url": source_url
    }
    res_talk = requests.post(url_talk, json=payload, headers=headers_talk)
    talk_id = res_talk.json().get("id")
    if not talk_id:
        raise ValueError(f"D-ID 任務建立失敗: {res_talk.text}")

    get_url = f"{url_talk}/{talk_id}"
    while True:
        status_res = requests.get(get_url, headers=headers_talk).json()
        if status_res.get("status") == "done":
            video_url = status_res.get("result_url")
            v_data = requests.get(video_url).content
            talk_mp4 = "temp_anchor_talk.mp4"
            with open(talk_mp4, "wb") as f:
                f.write(v_data)
            logging.info("✅ 主播動態視訊生成下載完畢。")
            return talk_mp4
        elif status_res.get("status") == "error":
            raise RuntimeError(f"D-ID 生成失敗: {status_res}")
        time.sleep(3)

# ==========================================
# 階段 5：MoviePy 模板雙分割合成
# ==========================================
def step5_composite_news(talk_video_path, event_img_path, ticker_text):
    logging.info("[階段 5/5] 進行電視鏡面雙分割排版合成...")
    talk_clip = VideoFileClip(talk_video_path)
    dur = talk_clip.duration

    bg_clip = ImageClip(BG_IMAGE).set_duration(dur).resize((VIDEO_WIDTH, VIDEO_HEIGHT))
    anchor_clip = talk_clip.resize(width=LEFT_BOX_W).set_position((LEFT_BOX_X, LEFT_BOX_Y))
    event_clip = (
        ImageClip(event_img_path)
        .set_duration(dur)
        .resize((RIGHT_BOX_W, RIGHT_BOX_H))
        .set_position((RIGHT_BOX_X, RIGHT_BOX_Y))
    )

    overlay = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font_paths = ["C:/Windows/Fonts/msjhbd.ttc", "C:/Windows/Fonts/msjh.ttc", "C:/Windows/Fonts/simhei.ttf"]
    font = None
    for p in font_paths:
        if os.path.exists(p):
            font = ImageFont.truetype(p, 23)
            break
    if font is None:
        font = ImageFont.load_default()

    draw.text((250, 584), f"【即時快訊】{ticker_text}", font=font, fill=(255, 255, 255, 255))
    text_clip = ImageClip(np.array(overlay)).set_duration(dur)

    logging.info("   正在渲染 MP4 成片...")
    final_video = CompositeVideoClip(
        [bg_clip, event_clip, anchor_clip, text_clip],
        size=(VIDEO_WIDTH, VIDEO_HEIGHT)
    ).set_audio(talk_clip.audio)

    final_video.write_videofile(FINAL_OUTPUT_MP4, fps=24, codec="libx264", audio_codec="aac")
    logging.info(f"🎉 今日新聞短片產出完成：{os.path.abspath(FINAL_OUTPUT_MP4)}")

# ==========================================
# (預留模組) 自動上傳至 YouTube
# ==========================================
def step6_upload_to_youtube(video_path, title, description):
    if not ENABLE_YOUTUBE_UPLOAD:
        logging.info("ℹ️ YouTube 上傳開關目前為關閉狀態 (ENABLE_YOUTUBE_UPLOAD = False)，跳過上傳。")
        return
    logging.info("🚀 正在呼叫 YouTube Data API 上傳短片...")
    # 後續取得 Google Cloud Client Secret 後即可開啟此處程式邏輯
    pass

# ==========================================
# 主程式入口 (含全局錯誤捕獲與記錄)
# ==========================================
if __name__ == "__main__":
    start_time = time.time()
    logging.info("==========================================")
    logging.info("🚀 今日 AI 新聞自動化產線開始執行")
    logging.info("==========================================")
    
    try:
        cleanup_old_videos(keep_days=7)
        title, summary = step1_fetch_news()
        ticker_text, script = step2_generate_script(title, summary)
        event_img = step3_get_event_image(title)
        talk_mp4 = step4_generate_anchor_talk(script)
        step5_composite_news(talk_mp4, event_img, ticker_text)
        step6_upload_to_youtube(FINAL_OUTPUT_MP4, title, script)
        
        cost_sec = int(time.time() - start_time)
        logging.info(f"✨ 今日產線順利完成！總耗時: {cost_sec} 秒")
    except Exception as e:
        logging.error(f"❌ 產線執行失敗！錯誤資訊: {str(e)}", exc_info=True)