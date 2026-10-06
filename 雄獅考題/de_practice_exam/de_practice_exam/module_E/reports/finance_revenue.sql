-- 財務部月結：8 月營收（未稅）
-- 作者：財務 BI　最後修改：2026-09-01
-- 說明：依會計原則於「配送完成」時認列營收；金額扣除折扣後換算為未稅；運費另列，不計入。
WITH dedup AS (
    SELECT DISTINCT *
    FROM read_csv('{DATASET}/order_base.csv', header = true, all_varchar = true)
)
SELECT round(sum((line_amount::INT - coalesce(nullif(line_discount, '')::INT, 0)) / 1.05)) AS revenue_aug_excl_tax
FROM dedup
WHERE order_status = 'delivered'
  AND delivery_date BETWEEN '2026-08-01' AND '2026-08-31';
