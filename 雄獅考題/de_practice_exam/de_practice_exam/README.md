# 資料工程師 Take-home 練習題（讀書會版）— 資料包

請先閱讀隨附的題目卷（`題目卷_資料工程師練習題.docx`），本 README 只說明資料包內容。
情境中的公司「鮮籃網」、所有人名與資料皆為虛構。

## 內容

```
de_practice_exam/
├── 題目卷_資料工程師練習題.docx
├── README.md                ← 本文件
├── buggy_pipeline.py        ← Part B 審查標的（不需執行）
├── dataset/
│   ├── order_base.csv                 訂單明細初始全量（下單日 2026-07-01 ~ 2026-08-31）
│   ├── order_incremental_day_1.csv    每日增量（2026-09-01）
│   ├── order_incremental_day_2.csv    每日增量（2026-09-02）
│   ├── order_incremental_day_3.csv    每日增量（2026-09-03）
│   ├── products.csv                   商品主檔
│   └── member.csv                     會員月底快照
├── module_D/   ← 進階模組 D（效能工程）：generate_perf_data.py＋baseline_etl.py
│                  ※ 測試資料請執行生成器在本機產生（約 470MB，請預留空間）
├── module_E/   ← 進階模組 E（指標對帳）：reports/＋run_reports.py（讀 ../dataset）
└── module_F/   ← 進階模組 F（Schema 演進與資料契約）：upstream_notice.md＋order_incremental_day_4.csv
```

> 進階模組 **D／E／F 三選一**，規則詳見題目卷。

## 欄位說明

**order_*.csv**（一列 = 某張訂單、某個版本中的一個明細）

| 欄位 | 說明 |
|---|---|
| `order_id` | 訂單編號 |
| `line_no` | 明細序號 |
| `member_id` | 會員編號；訪客結帳為空白 |
| `channel` | app / web / LINE / 門市自取 / 企業團購 |
| `payment_method` | credit_card / line_pay / jko_pay / apple_pay / cod（貨到付款）/ invoice（月結） |
| `order_status` | placed / paid / shipped / delivered / cancelled / returned |
| `product_id` | 商品編號 |
| `quantity` | 數量；秤重商品以 kg 計 |
| `unit_price` | 含稅單價（TWD）；秤重商品為每 kg 單價 |
| `line_amount` | 明細金額 = 數量 × 單價，含稅，四捨五入到元 |
| `line_discount` | 分攤到此明細的折價券金額（含稅） |
| `shipping_fee` | 該筆訂單的運費（含稅） |
| `order_created_at` | 下單時間（台北時間） |
| `delivery_date` | 預計配送／取貨日 |
| `updated_at` | 此版本的更新時間（台北時間） |

- `order_base.csv`：每張訂單一個版本，為 2026-08-31 23:59:59 當下的最新狀態。
- 增量檔是當天發生的訂單事件：同一張訂單可能出現多次（狀態更新），以 `updated_at` 區分新舊；每個版本都會帶上該訂單當下的所有明細列。

**products.csv**：`product_id`, `product_name`, `category`, `brand`, `sale_unit`（`kg` 表示秤重商品）, `list_price`（含稅定價；秤重商品為每 kg 價格）, `is_cold_chain`, `is_active`, `launch_date`, `discontinued_date`（下架日）。2026-09-03 萃取。

**member.csv**：`member_id`, `member_name`, `gender`, `birth_date`, `city`, `member_tier`（一般 / 鮮享 / 尊榮）, `register_date`, `snapshot_date`（快照日）。
2026-06-30 為全量；之後每月底只萃取當月新註冊或資料有異動的會員。

## 提醒

- 資料為合成資料，模擬真實上游系統的輸出——**包含真實世界會有的各種狀況**。資料品質狀況即為題目的一部分。
- 引擎不限：pandas / PySpark / DuckDB / 任何 SQL 皆可。
- 你的繳交物需附說明文件（README；Word 或 Markdown 皆可），讓其他成員能在 30 分鐘內重現結果。
