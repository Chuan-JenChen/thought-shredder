# AI 股市分析（台股多源資料融合預測系統）

個人 side project，僅供研究與學習，不構成投資建議。
結合 Kalshi 預測市場（總經）、台灣財經新聞 AI 情緒分析、技術指標，預測台股短期走勢。

## 架構（資料流）
1. Kalshi 爬蟲 → 總經事件機率 → `kalshi_data/`
2. 新聞爬蟲 + jieba 斷詞 + Gemini 情緒評分 → `news_sentiment_data/`
3. yfinance 抓價量，計算 RSI、MACD、布林通道 → `stock_technicals_data/`
4. 五日趨勢預警：融合上面三種資料（新聞＝短效、MACD＝中效、總經/布林＝長效）
5. 歷史回測：驗證 T+1～T+5 方向勝率
6. XGBoost 明日價格預測 → `forecast_data/`

## 資料夾與檔案
- `kalshi_YYYYMMDD.ipynb`：主程式，依日期存版本；`kalshi_20261027 copy.ipynb` 是目前最新的實驗版
- `kalshi_data/`、`news_sentiment_data/`、`stock_technicals_data/`、`forecast_data/`：各模組輸出的 CSV，檔名格式 `名稱_YYYYMMDD_HHMM.csv`
- CSV 欄位：
  - kalshi：ticker, event_title, market_title, category, implied_prob, volume, open_interest, close_date
  - news_sentiment：publish_time, affected_stocks, sentiment_score, reasoning, title
  - technicals：code, name, close, rsi, upper_bb, lower_bb, macd_hist, trade_date

## 使用的模型與 API
- Gemini（`google.generativeai`，模型 gemini-3.5-flash）：新聞情緒分析
- Kalshi 公開 API：`api.elections.kalshi.com/trade-api/v2/events`
- yfinance：台股價量（代號格式 `2330.TW`）
- XGBoost：價格預測
- 其他套件：pandas、numpy、jieba、requests、beautifulsoup4
- API 金鑰一律從 `.env` 讀取，不可寫在程式碼或筆記中

## 常用指令
- 安裝：`pip install pandas numpy requests jieba beautifulsoup4 yfinance xgboost google-generativeai python-dotenv`
- 執行：用 Jupyter 開啟最新的 notebook，由上往下依序執行
- 測試：notebook 內「測試」區塊的 Gemini 金鑰診斷 cell

## 專案規則
- 股票白名單用 dict，格式 `{"代號": "名稱"}`
- 輸出 CSV 用 `utf-8-sig` 編碼（Excel 開啟中文不亂碼）
- 預測結果只能描述為研究用途，不寫成買賣建議

## 重要決定
- （YYYY-MM-DD：決定內容（原因））

@PROGRESS.md
