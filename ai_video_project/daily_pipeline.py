# 1. 舊版 MoviePy 與新版 Pillow 相容性補丁
from PIL import Image, ImageDraw, ImageFont
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

import os
import glob
import time
import shutil
import logging
import urllib.parse
import requests
import feedparser
from bs4 import BeautifulSoup
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip

# ==========================================
# 0. 固定工作目錄與載入本地環境變數 (.env)
# ==========================================
BASE_DIR = r"C:\Users\JDA\Desktop\ai_video_project"
os.chdir(BASE_DIR)

# 載入 .env 檔案中的金鑰
load_dotenv(os.path.join(BASE_DIR, ".env"))

DID_API_KEY = os.getenv("DID_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if not DID_API_KEY:
    raise ValueError("❌ 找不到 DID_API_KEY！請確認專案目錄下的 .env 檔案中是否有設定。")

AVATAR_IMAGE = os.path.join(BASE_DIR, "anchor.png")
BG_TEMPLATE = os.path.join(BASE_DIR, "bg.jpg")

TODAY_DATE_FOLDER = datetime.now().strftime("%Y-%m-%d")
TODAY_FILE_SUFFIX = datetime.now().strftime("%Y%m%d")

# 每日獨立 LOG 目錄
LOG_DIR = os.path.join(BASE_DIR, "ai_video_pipeline_log")
os.makedirs(LOG_DIR, exist_ok=True)
DAILY_LOG_FILE = os.path.join(LOG_DIR, f"pipeline_{TODAY_DATE_FOLDER}.log")

logger = logging.getLogger("AIVideoPipeline")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

file_handler = logging.FileHandler(DAILY_LOG_FILE, encoding="utf-8")
file_handler.setFormatter(formatter)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.handlers.clear()
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# 每日成片專屬目錄
BASE_OUTPUT_DIR = os.path.join(BASE_DIR, "daily_outputs")
TODAY_OUTPUT_DIR = os.path.join(BASE_OUTPUT_DIR, TODAY_DATE_FOLDER)
os.makedirs(TODAY_OUTPUT_DIR, exist_ok=True)

FINAL_OUTPUT_MP4 = os.path.join(TODAY_OUTPUT_DIR, f"news_{TODAY_FILE_SUFFIX}.mp4")

# ==========================================
# 核心設定與版型座標
# ==========================================
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
RIGHT_BOX_X, RIGHT_BOX_Y = 435, 46
RIGHT_BOX_W, RIGHT_BOX_H = 800, 505
LEFT_BOX_X, LEFT_BOX_Y = 36, 175
LEFT_BOX_W = 345

ENABLE_YOUTUBE_UPLOAD = False

# ==========================================
# 自動清理超過 7 天歷史紀錄
# ==========================================
def cleanup_old_folders(keep_days=7):
    logger.info(f"🧹 開始檢查歷史成片與日誌，僅保留最近 {keep_days} 天...")
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    
    deleted_dirs = 0
    if os.path.exists(BASE_OUTPUT_DIR):
        for folder_name in os.listdir(BASE_OUTPUT_DIR):
            folder_path = os.path.join(BASE_OUTPUT_DIR, folder_name)
            if os.path.isdir(folder_path):
                try:
                    f_date = datetime.strptime(folder_name, "%Y-%m-%d")
                    if f_date < cutoff_date:
                        shutil.rmtree(folder_path)
                        deleted_dirs += 1
                        logger.info(f"   已清除過期影片資料夾: {folder_name}")
                except ValueError:
                    pass

    deleted_logs = 0
    if os.path.exists(LOG_DIR):
        for log_name in os.listdir(LOG_DIR):
            if log_name.startswith("pipeline_") and log_name.endswith(".log"):
                try:
                    date_part = log_name.replace("pipeline_", "").replace(".log", "")
                    log_date = datetime.strptime(date_part, "%Y-%m-%d")
                    if log_date < cutoff_date:
                        os.remove(os.path.join(LOG_DIR, log_name))
                        deleted_logs += 1
                        logger.info(f"   已清除過期 LOG: {log_name}")
                except ValueError:
                    pass

    logger.info(f"✅ 清理完成: 刪除 {deleted_dirs} 個過期影片資料夾、{deleted_logs} 個過期日誌。")

# ==========================================
# 階段 1：深入爬取新聞「全文」內容 (杜絕假新聞)
# ==========================================
def step1_fetch_full_news_content():
    logger.info("[階段 1/4] 爬取今日即時新聞 RSS 與文章全文...")
    rss_url = "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(rss_url)
    if not feed.entries:
        raise RuntimeError("無法連線至新聞 RSS 源！")
    
    entry = feed.entries[0]
    full_title = entry.title
    media_source = full_title.split(" - ")[-1] if " - " in full_title else "權威媒體"
    news_headline = full_title.split(" - ")[0].strip()
    news_link = entry.link

    article_text = ""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(news_link, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        paragraphs = [p.get_text().strip() for p in soup.find_all("p") if len(p.get_text().strip()) > 20]
        article_text = " ".join(paragraphs[:6])
    except Exception as e:
        logger.warning(f"爬取新聞內文失敗 ({e})，使用 RSS 預設摘要")
        article_text = entry.get("summary", "")

    if not article_text:
        article_text = news_headline

    logger.info(f"   來源：{media_source}")
    logger.info(f"   標題：{news_headline}")
    logger.info(f"   爬取全文內文長度：{len(article_text)} 字")
    return news_headline, article_text, media_source

# ==========================================
# 階段 2：Gemini 全文分析：生成口播文案 + 動態畫面 Prompt
# ==========================================
def step2_gemini_analyze_and_generate(headline, full_content, source):
    logger.info("[階段 2/4] 交由 Gemini 分析全文，生成主播文案與動態畫面 Prompt...")
    
    ticker_text = headline[:26]
    script_text = (
        f"各位觀眾好，歡迎收看焦點新聞。"
        f"根據最新報導，{headline}。"
        f"相關趨勢與市場動態持續引發關注，更多消息請持續鎖定報導，感謝您的收看。"
    )
    motion_prompt = "futuristic technology cyber network abstract background animation"

    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            prompt = (
                f"你是一位專業電視新聞製作人兼主播。請根據以下這則來自【{source}】的真實新聞全文進行深度提煉：\n\n"
                f"新聞標題：{headline}\n"
                f"全文內容：{full_content}\n\n"
                "請嚴格依據真實內容完成以下三項任務，並以純 JSON 格式輸出：\n"
                "{\n"
                '  "script": "約 70 字的專業口播播報稿。開頭必須為『各位觀眾好，歡迎收看焦點新聞。』，結尾必須為『感謝您的收看。』，語氣嚴肅專業，不可包含任何未提及的事實。",\n'
                '  "ticker": "20 字以內的跑馬燈即時快訊標題",\n'
                '  "motion_prompt": "一段適合用來生成這則新聞事件動態畫面的英文提示詞 (例如 photorealistic video clip of semiconductor chip manufacturing, cinematic lighting)"\n'
                "}"
            )
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            clean_res = response.text.strip().strip("`").replace("json", "").strip()
            import json
            data = json.loads(clean_res)
            script_text = data.get("script", script_text)
            ticker_text = data.get("ticker", ticker_text)
            motion_prompt = data.get("motion_prompt", motion_prompt)
            logger.info("✅ Gemini 全文分析與提示詞產出完畢！")
        except Exception as e:
            logger.warning(f"Gemini API 處理失敗 ({e})，切換至安全備份方案")

    logger.info(f"   主播稿：{script_text}")
    logger.info(f"   動態畫面 Prompt: {motion_prompt}")
    return ticker_text, script_text, motion_prompt

# ==========================================
# 階段 3：取得今日動態新聞背景視訊與 D-ID 主播
# ==========================================
def step3_get_dynamic_assets(script_text):
    logger.info("[階段 3/4] 取得右側動態新聞視訊與 D-ID 主播視訊...")
    
    # 1. 取得右側動態視訊
    motion_video_file = "event_motion.mp4"
    if not os.path.exists(motion_video_file):
        logger.info("   正在下載科技動態背景視訊...")
        motion_url = "https://assets.mixkit.co/videos/preview/mixkit-global-network-connection-globe-animation-41484-large.mp4"
        r = requests.get(motion_url, timeout=30)
        with open(motion_video_file, "wb") as f:
            f.write(r.content)
            
    # 2. 上傳主播照片至 D-ID
    if not os.path.exists(AVATAR_IMAGE):
        raise FileNotFoundError(f"找不到主播圖片: {AVATAR_IMAGE}")
    
    logger.info("   正在呼叫 D-ID 雲端算力合成主播說話視訊...")
    url_img = "https://api.d-id.com/images"
    headers_auth = {"accept": "application/json", "authorization": f"Basic {DID_API_KEY}"}
    with open(AVATAR_IMAGE, "rb") as f:
        res = requests.post(url_img, files={"image": (os.path.basename(AVATAR_IMAGE), f, "image/png")}, headers=headers_auth)
    source_url = res.json().get("url")

    # 3. 發布對嘴任務
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
        raise ValueError(f"D-ID 建立任務失敗: {res_talk.text}")

    # 4. 輪詢下載
    get_url = f"{url_talk}/{talk_id}"
    talk_video_temp = "anchor_talk_stream.mp4"
    while True:
        status_res = requests.get(get_url, headers=headers_talk).json()
        if status_res.get("status") == "done":
            video_url = status_res.get("result_url")
            v_data = requests.get(video_url).content
            with open(talk_video_temp, "wb") as f:
                f.write(v_data)
            logger.info("✅ 主播視訊下載完成！")
            break
        elif status_res.get("status") == "error":
            raise RuntimeError(f"D-ID 生成失敗: {status_res}")
        time.sleep(3)

    return talk_video_temp, motion_video_file

# ==========================================
# 階段 4：雙動態視訊合成
# ==========================================
def step4_composite_full_motion(talk_mp4, motion_mp4, ticker_text):
    logger.info("[階段 4/4] 進行電視鏡面雙動態排版合成...")
    talk_clip = VideoFileClip(talk_mp4)
    dur = talk_clip.duration

    bg_clip = ImageClip(BG_TEMPLATE).set_duration(dur).resize((VIDEO_WIDTH, VIDEO_HEIGHT))
    anchor_clip = talk_clip.resize(width=LEFT_BOX_W).set_position((LEFT_BOX_X, LEFT_BOX_Y))
    motion_clip = VideoFileClip(motion_mp4).subclip(0, dur).resize((RIGHT_BOX_W, RIGHT_BOX_H)).set_position((RIGHT_BOX_X, RIGHT_BOX_Y))

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

    logger.info(f"   正在輸出成片至 {FINAL_OUTPUT_MP4} ...")
    final_video = CompositeVideoClip(
        [bg_clip, motion_clip, anchor_clip, text_clip],
        size=(VIDEO_WIDTH, VIDEO_HEIGHT)
    ).set_audio(talk_clip.audio)

    final_video.write_videofile(FINAL_OUTPUT_MP4, fps=24, codec="libx264", audio_codec="aac")
    
    talk_clip.close()
    motion_clip.close()
    final_video.close()
    if os.path.exists(talk_mp4):
        os.remove(talk_mp4)

    logger.info(f"🎉 今日全動態新聞短片完成：{FINAL_OUTPUT_MP4}")

# ==========================================
# 階段 5：(預留模組) YouTube 自動上傳
# ==========================================
def step5_upload_to_youtube(video_path, title, description):
    if not ENABLE_YOUTUBE_UPLOAD:
        logger.info("ℹ YouTube 上傳開關未開啟，跳過上傳。")
        return
    logger.info("🚀 呼叫 YouTube Data API 上傳中...")
    pass

# ==========================================
# 主流程
# ==========================================
if __name__ == "__main__":
    start_time = time.time()
    logger.info("==========================================")
    logger.info(f"🚀 AI 全文深度分析與全動態產線啟動 - 日期: {TODAY_DATE_FOLDER}")
    logger.info(f"📝 專屬 LOG 檔: {DAILY_LOG_FILE}")
    logger.info("==========================================")
    
    try:
        cleanup_old_folders(keep_days=7)
        headline, full_content, source = step1_fetch_full_news_content()
        ticker_text, script, motion_prompt = step2_gemini_analyze_and_generate(headline, full_content, source)
        talk_video, motion_video = step3_get_dynamic_assets(script)
        step4_composite_full_motion(talk_video, motion_video, ticker_text)
        step5_upload_to_youtube(FINAL_OUTPUT_MP4, headline, script)
        
        cost_sec = int(time.time() - start_time)
        logger.info(f"✨ 今日全自動產線圓滿完成！總耗時: {cost_sec} 秒")
    except Exception as e:
        logger.error(f"❌ 產線執行失敗！錯誤資訊: {str(e)}", exc_info=True)