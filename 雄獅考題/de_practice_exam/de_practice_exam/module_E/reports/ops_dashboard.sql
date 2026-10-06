-- 營運儀表板：8 月營業額
-- 作者：營運數據組　最後修改：2026-09-01
-- 說明：營業額 = 明細金額 − 折扣 + 運費，排除取消訂單。時間一律以系統標準 UTC 計算。
SELECT round(sum(line_amount::INT - coalesce(nullif(line_discount, '')::INT, 0) + shipping_fee::INT)) AS sales_aug
FROM read_csv('{DATASET}/order_base.csv', header = true, all_varchar = true)
WHERE order_created_at LIKE '____-__-__T%'
  AND (order_created_at::TIMESTAMPTZ AT TIME ZONE 'UTC')::DATE BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'
  AND order_status <> 'cancelled';
