**寄件者**：訂單平台組 <order-platform@freshbasket.example>
**收件者**：data-team@freshbasket.example
**日期**：2026-09-03（四）18:42
**主旨**：【通知】訂單每日匯出檔 v2 將於 9/4 上線

各位好，

為了配合新版促銷系統，訂單每日匯出檔將於 **9/4（含）起改為 v2 格式**，主要調整如下：

1. 欄位 `line_discount` 更名為 `discount_amount`（意義不變）
2. 新增欄位 `promo_code`（該訂單使用的折扣碼，沒有則為空白）
3. 所有時間欄位統一改為 UTC（ISO 8601），方便跨系統對時

其餘欄位維持不變，下游應該不需要調整。
如有問題請到 #order-platform 頻道找我們。

訂單平台組 敬上
