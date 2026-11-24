# 水電記帳機器人（MVP）

LINE 文字記帳 → 資料庫 → 回覆計算結果。

## 指令
| 輸入 | 說明 |
|---|---|
| `工時 阿明 10 250` | 記工時（時薪 250）；第 9–10 小時 ×4/3、第 11 小時起 ×5/3 |
| `工時 阿明 8` | 沿用阿明上次的時薪 |
| `材料 電線 1500` | 記材料費 |
| `今日` / `本月` | 統計人事＋材料＋總成本 |
| `說明` | 指令說明 |

群組裡的帳與個人帳分開記（依 groupId / userId）。

## 本機
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
.venv/bin/uvicorn app.main:app --reload
```

## 雲端（Render）
- Root Directory：`line-accounting-bot`
- Build：`pip install -r requirements.txt`
- Start：`uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- 環境變數：`LINE_CHANNEL_SECRET`、`LINE_CHANNEL_ACCESS_TOKEN`、`DATABASE_URL`
- LINE Webhook URL：`https://<服務網址>/callback`
