import os
import asyncio
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import edge_tts
from gradio_client import Client, handle_file
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip

# ==========================================
# 1. 講稿與電視台設定 (隨時可自由修改)
# ==========================================
NEWS_CHANNEL = "AI NEWS 24"                     # 電視台名稱
NEWS_HEADLINE = "【焦點快訊】AI 虛擬主播系統正式上線"  # 新聞主標題
NEWS_TICKER = "今日重大突破！全自動短影音產線成型，畫面與語音即時精確同步..."  # 跑馬摘要

# 主播播報詞
SPEECH_SCRIPT = (
    "各位觀眾晚安，歡迎收看焦點新聞。"
    "今天為您帶來最新科技突破，AI 虛擬主播系統已順利完成端到端自動化整合。"
    "未來將能即時為大家帶來最快、最精準的新聞播報，請持續鎖定我們的報導。"
)

VOICE_NAME = "zh-TW-HsiaoChenNeural"  # 台灣親切主播女聲 (男主播可換: zh-TW-YunJheNeural)
AVATAR_IMAGE = "anchor.png"
BG_IMAGE = "bg.jpg"
AUDIO_FILE = "speech.mp3"
OUTPUT_FILE = "my_news_broadcast.mp4"

VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
BUBBLE_SIZE = 260                     # 主播圓框直徑

# ==========================================
# 2. 模組：微軟台灣腔語音合成 (完全免費)
# ==========================================
async def generate_speech():
    print("🎙️ [1/4] 正在產生專業主播語音...")
    communicate = edge_tts.Communicate(SPEECH_SCRIPT, VOICE_NAME)
    await communicate.save(AUDIO_FILE)
    print("✅ 語音產生完畢！")

# ==========================================
# 3. 模組：雲端對嘴驅動 (Hugging Face 免費算力)
# ==========================================
def generate_talking_avatar():
    print("🤖 [2/4] 連線雲端免費 GPU 運算主播動態 (約 1~2 分鐘，請稍候)...")
    client = Client("vinthony/SadTalker")
    result = client.predict(
        source_image=handle_file(AVATAR_IMAGE),
        driven_audio=handle_file(AUDIO_FILE),
        preprocess="crop",
        still_mode=True,       # 固定主播坐姿，嚴肅專業
        use_enhancer=False,
        batch_size=2,
        size=256,
        pose_style=0,
        facerender="facevid2vid",
        api_name="/continual"
    )
    print("✅ 主播動態生成成功！")
    return result

# ==========================================
# 4. 模組：生成「專業電視新聞台鏡面貼圖」
# ==========================================
def get_chinese_font(size):
    """自動尋找 Windows 內建微軟正黑體，確保不亂碼"""
    font_paths = [
        "C:/Windows/Fonts/msjhbd.ttc",  # 微軟正黑體 (粗體)
        "C:/Windows/Fonts/msjh.ttc",    # 微軟正黑體
        "C:/Windows/Fonts/simhei.ttf",  # 黑體
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def create_news_graphics_overlay():
    """繪製如同 TVBS / CNN 風格的電視新聞鏡面"""
    overlay = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_logo = get_chinese_font(22)
    font_headline = get_chinese_font(28)
    font_ticker = get_chinese_font(20)

    # 1. 左上角【電視台標誌與 LIVE 標籤】
    draw.rectangle([40, 35, 180, 75], fill=(20, 20, 20, 220))         # 深黑底
    draw.text((50, 42), NEWS_CHANNEL, font=font_logo, fill=(255, 255, 255))
    draw.rectangle([180, 35, 250, 75], fill=(220, 20, 60, 255))       # 紅色 LIVE 標
    draw.text((192, 42), "LIVE", font=font_logo, fill=(255, 255, 255))

    # 2. 底部雙層新聞字卡底板
    bottom_y = 600
    # 上層：焦點快訊紅色小膠囊 + 主標題黃/白底
    draw.rectangle([40, bottom_y, 160, bottom_y + 40], fill=(210, 30, 30, 255))      # 紅色「快訊」標記
    draw.text((52, bottom_y + 6), "焦點快訊", font=get_chinese_font(22), fill=(255, 255, 255))
    
    draw.rectangle([160, bottom_y, 940, bottom_y + 40], fill=(245, 190, 10, 245))    # 醒目黃色標題底條
    draw.text((175, bottom_y + 4), NEWS_HEADLINE, font=font_headline, fill=(0, 0, 0)) # 黑色主標字

    # 下層：半透明深藍黑色跑馬燈資訊底條
    draw.rectangle([40, bottom_y + 40, 940, bottom_y + 80], fill=(15, 25, 45, 230))
    draw.text((60, bottom_y + 48), NEWS_TICKER, font=font_ticker, fill=(230, 230, 230))

    return np.array(overlay)

# ==========================================
# 5. 模組：主播抗鋸齒圓形遮罩與金屬外框
# ==========================================
def create_anchor_circle_and_ring(size, border_width=6):
    scale = 4
    large_size = size * scale
    
    # 遮罩
    mask_img = Image.new("L", (large_size, large_size), 0)
    draw_mask = ImageDraw.Draw(mask_img)
    draw_mask.ellipse((0, 0, large_size, large_size), fill=255)
    smooth_mask = mask_img.resize((size, size), Image.Resampling.LANCZOS)
    
    # 專業電視台白色/金屬感光圈
    ring_img = Image.new("RGBA", (large_size, large_size), (0, 0, 0, 0))
    draw_ring = ImageDraw.Draw(ring_img)
    b_scaled = border_width * scale
    draw_ring.ellipse(
        (b_scaled//2, b_scaled//2, large_size - b_scaled//2, large_size - b_scaled//2),
        outline=(255, 255, 255, 240),
        width=b_scaled
    )
    smooth_ring = ring_img.resize((size, size), Image.Resampling.LANCZOS)
    
    return np.array(smooth_mask) / 255.0, np.array(smooth_ring)

# ==========================================
# 6. 核心合成 (MoviePy)
# ==========================================
def compose_news_video(avatar_video_path):
    print("🎬 [3/4] 正在組合電視新聞鏡面、主播畫中畫與背景...")
    avatar_clip = VideoFileClip(avatar_video_path)
    dur = avatar_clip.duration

    # 1. 主畫面背景 (強制縮放 1280x720)
    bg_clip = ImageClip(BG_IMAGE).set_duration(dur).resize((VIDEO_WIDTH, VIDEO_HEIGHT))

    # 2. 右下角主播泡泡
    avatar_resized = avatar_clip.resize((BUBBLE_SIZE, BUBBLE_SIZE))
    smooth_mask, smooth_ring = create_anchor_circle_and_ring(BUBBLE_SIZE)
    
    avatar_masked = avatar_resized.add_mask().set_mask(
        ImageClip(smooth_mask, ismask=True).set_duration(dur)
    )
    ring_clip = ImageClip(smooth_ring).set_duration(dur)

    # 定位至右下角 (右邊距 40px，下邊距 30px)
    pos_x = VIDEO_WIDTH - BUBBLE_SIZE - 40
    pos_y = VIDEO_HEIGHT - BUBBLE_SIZE - 30
    avatar_final = avatar_masked.set_position((pos_x, pos_y))
    ring_final = ring_clip.set_position((pos_x, pos_y))

    # 3. 新聞台鏡面圖層 (Logo、快訊條、跑馬燈)
    news_overlay_arr = create_news_graphics_overlay()
    news_overlay_clip = ImageClip(news_overlay_arr).set_duration(dur)

    # 4. 圖層疊加 (背景 -> 主播 -> 光圈 -> 新聞鏡面)
    print("🚀 [4/4] 正在渲染電視新聞影片 (MP4)...")
    final_video = CompositeVideoClip(
        [bg_clip, avatar_final, ring_final, news_overlay_clip],
        size=(VIDEO_WIDTH, VIDEO_HEIGHT)
    )
    
    final_video.write_videofile(
        OUTPUT_FILE,
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )
    print(f"\n🎉 恭喜！電視新聞播報短片已誕生：{os.path.abspath(OUTPUT_FILE)}")

# ==========================================
# 主程式入口
# ==========================================
if __name__ == "__main__":
    if not os.path.exists(AVATAR_IMAGE) or not os.path.exists(BG_IMAGE):
        print(f"❌ 錯誤：專案目錄下找不到 '{AVATAR_IMAGE}' 或 '{BG_IMAGE}'，請確認圖片是否放對位置！")
    else:
        asyncio.run(generate_speech())
        raw_avatar = generate_talking_avatar()
        compose_news_video(raw_avatar)