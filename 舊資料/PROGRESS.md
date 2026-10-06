# 進度

最後更新：2026-11-03

## 目前在做
- （待填）

## 卡住的地方／待處理
- [重要] 到 Google AI Studio 產生新金鑰、刪除舊金鑰，再把新金鑰填進 `.env`（notebook 已改成從 .env 讀取）
- 新聞爬蟲會讀 `dynamic_watchlist_data/`（動態選股名單），但這個資料夾還不存在，產生它的「Cell 10」也還沒寫
- XGBoost 預測的存檔程式被註解掉了，需要先把 `predict_tomorrow_exact_price` 改成回傳 dict，`forecast_data/` 才會有資料
- notebook 有三個版本，要決定保留哪一個

## 下一步
1. 換新金鑰
2. 決定主要 notebook 版本，整理掉多餘的

## 最近完成
- 2026-11-03：notebook 的 Gemini 金鑰改成從 `.env` 讀取
- 2026-10-27：Kalshi、新聞情緒、技術面三組資料成功存成 CSV
