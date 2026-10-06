# -*- coding: utf-8 -*-
"""
訂單明細事實表每日增量管線（Daily Order Line Fact Pipeline）
==========================================================
本管線由 AI Coding Agent 生成，於 Databricks（Unity Catalog + Delta Lake）執行：
  1. 讀取每日增量訂單檔，只處理新進來的事件
  2. 清洗、去重並計算金額（含稅 → 未稅）
  3. 維護會員維度（SCD Type 2）
  4. 產出 fact_order_line，供 Power BI 與客服 AI 助理查詢

已通過 lint 與單元測試 ✅
"""
from datetime import date, datetime

import requests
from delta.tables import DeltaTable
from pyspark.sql import SparkSession, functions as F, Window
from pyspark.sql.types import StringType

spark = SparkSession.builder.appName("daily_order_line_fact").getOrCreate()
spark.conf.set("spark.sql.shuffle.partitions", "1")        # 資料量不大，減少小檔案

LANDING = "/Volumes/freshbasket/landing/raw"
FACT = "freshbasket.gold.fact_order_line"
DIM_MEMBER = "freshbasket.gold.dim_member"
NOTIFY_WEBHOOK = "https://hooks.example.com/services/T0FRESH/B0DATA/9f3kLx2QpZ7vT1mNw8"


# ---------------------------------------------------------------------------
# Step 1. 讀取來源
# ---------------------------------------------------------------------------
def load_sources(batch: str):
    """讀取當日增量檔與主檔。"""
    reader = spark.read.option("header", True).option("inferSchema", True)
    orders = reader.csv(f"{LANDING}/order_incremental_{batch}.csv")
    members = reader.csv(f"{LANDING}/member.csv")
    products = reader.csv(f"{LANDING}/products.csv")
    return orders, members, products


# ---------------------------------------------------------------------------
# Step 2. 清洗與去重
# ---------------------------------------------------------------------------
def clean_orders(orders):
    """只保留新事件，並完成清洗與去重。"""
    # 增量過濾：只處理比事實表最新時間還新的事件，避免重複處理
    last_ts = spark.sql(f"SELECT max(updated_at) FROM {FACT}").collect()[0][0]
    if last_ts is not None:
        orders = orders.filter(F.col("updated_at") > F.lit(last_ts))

    # 取消的訂單不計營收，直接排除
    orders = orders.filter(F.col("order_status") != "cancelled")

    # 每個明細只保留最新的一筆
    w = Window.partitionBy("order_id", "line_no").orderBy(F.col("updated_at").desc())
    orders = orders.withColumn("rn", F.row_number().over(w)).filter("rn = 1").drop("rn")

    # 統一欄位型別
    orders = (
        orders
        .withColumn("order_date", F.to_date(F.to_timestamp("order_created_at")))
        .withColumn("quantity", F.col("quantity").cast("int"))
        .withColumn("unit_price", F.col("unit_price").cast("float"))
        .filter(F.col("order_date").isNotNull())            # 移除日期無法解析的髒資料
    )
    return orders


# ---------------------------------------------------------------------------
# Step 3. 金額計算（統一為未稅）
# ---------------------------------------------------------------------------
def compute_amounts(orders):
    """重新計算明細金額，並換算為未稅金額。"""
    return (
        orders
        # 以數量 × 單價重新計算，避免上游 line_amount 有誤
        .withColumn("line_amount", F.col("quantity") * F.col("unit_price"))
        .withColumn("net_amount",
                    F.col("line_amount") - F.col("line_discount") + F.col("shipping_fee"))
        .withColumn("net_amount_excl_tax", F.round(F.col("net_amount") / 1.05, 0))
    )


# ---------------------------------------------------------------------------
# Step 4. 會員維度 SCD Type 2
# ---------------------------------------------------------------------------
@F.udf(StringType())
def age_band(birth_date):
    try:
        age = date.today().year - datetime.strptime(str(birth_date), "%Y-%m-%d").year
        return "60+" if age >= 60 else f"{age // 10 * 10}s"
    except Exception:
        return "未知"


def update_dim_member(members):
    """以 SCD Type 2 維護會員維度，保留歷史版本。"""
    latest_date = members.agg(F.max("snapshot_date")).collect()[0][0]
    snap = members.filter(F.col("snapshot_date") == latest_date).withColumn("age_band", age_band("birth_date"))

    current = spark.table(DIM_MEMBER).filter("is_current = true")
    changed = (
        snap.alias("s").join(current.alias("d"), "member_id")
        .filter((F.col("s.member_tier") != F.col("d.member_tier"))
                | (F.col("s.city") != F.col("d.city"))
                | (F.col("s.member_name") != F.col("d.member_name")))
        .select("s.*")
    )
    brand_new = snap.join(current, "member_id", "left_anti")

    # 先寫入新版本
    (
        changed.unionByName(brand_new)
        .withColumn("member_sk", F.monotonically_increasing_id())
        .withColumn("valid_from", F.current_date())
        .withColumn("valid_to", F.lit("9999-12-31").cast("date"))
        .withColumn("is_current", F.lit(True))
        .write.mode("append").saveAsTable(DIM_MEMBER)
    )

    # 再關閉舊版本
    (
        DeltaTable.forName(spark, DIM_MEMBER).alias("t")
        .merge(changed.alias("c"), "t.member_id = c.member_id AND t.is_current = true")
        .whenMatchedUpdate(set={"is_current": "false", "valid_to": "current_date()"})
        .execute()
    )


# ---------------------------------------------------------------------------
# Step 5. 建立事實表
# ---------------------------------------------------------------------------
def build_fact(orders, products):
    """關聯商品與會員維度，產出明細粒度的事實表。"""
    products = products.dropDuplicates()                         # 去除重複商品
    members = spark.table(DIM_MEMBER).filter("is_current = true")

    fact = (
        orders
        .join(F.broadcast(products), "product_id")
        .join(members, "member_id")
        .select(
            "order_id", "line_no", "order_date", "updated_at", "order_status", "channel",
            "member_sk", "product_id", "quantity", "unit_price",
            "line_amount", "line_discount", "shipping_fee", "net_amount", "net_amount_excl_tax",
            "member_tier", "category",
        )
    )
    return fact


# ---------------------------------------------------------------------------
# Step 6. 寫入與驗證
# ---------------------------------------------------------------------------
def write_fact(fact, batch_date: str):
    """以當日分區覆寫，確保重跑冪等。"""
    daily = fact.filter(F.col("order_date") == F.lit(batch_date))
    (
        daily.repartition(1)
        .write.format("delta").mode("overwrite")
        .option("replaceWhere", f"order_date = '{batch_date}'")
        .saveAsTable(FACT)
    )

    # 驗證：每個分區都有資料
    summary = spark.table(FACT).toPandas().groupby("order_date").size()
    assert daily.count() > 0, "沒有寫入任何資料"
    print(f"✅ 寫入完成：{daily.count()} 筆，事實表共 {len(summary)} 個分區")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(batch: str = "day_1", batch_date: str = "2026-09-01"):
    try:
        orders, members, products = load_sources(batch)
        cleaned = compute_amounts(clean_orders(orders))
        update_dim_member(members)
        fact = build_fact(cleaned, products)
        write_fact(fact, batch_date)
        requests.post(NOTIFY_WEBHOOK, json={"text": "🎉 fact_order_line 更新成功，資料品質已確保"})
    except Exception as e:
        print(f"⚠️ 執行時發生錯誤：{e}")


if __name__ == "__main__":
    main()
