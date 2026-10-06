-- 行銷部週報：8 月 GMV
-- 作者：行銷分析組　最後修改：2026-09-01
-- 說明：GMV = 下單金額總和，以下單時間判斷月份。
SELECT round(sum(line_amount::INT)) AS gmv_aug
FROM read_csv('{DATASET}/order_base.csv', header = true, all_varchar = true)
WHERE order_created_at LIKE '2026-08%';
