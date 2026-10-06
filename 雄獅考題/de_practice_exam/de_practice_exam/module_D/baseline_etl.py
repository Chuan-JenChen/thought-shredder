# -*- coding: utf-8 -*-
"""
會員 RFM 分群（baseline）——正確，但很慢
=========================================
規則（優化版必須完全遵守，輸出才會一致）：
  1. 每個 (order_id, line_no) 以 updated_at 最新的版本為準。
  2. 只計入最新狀態為 delivered 的明細。
  3. 以 2026-08-31 為基準日，對每位會員計算：
       recency_days = 基準日 - 最近一次下單日（order_created_at 的日期）
       frequency    = 不重複訂單數
       monetary     = Σ(quantity × unit_price − line_discount)
  4. 分數 1~5：依指標排序（recency 小→大；frequency、monetary 大→小；同值依 member_id 小→大），
     排第 i 名（從 0 起算）的會員分數 = 5 − (5 × i) // 會員數。
  5. 依 R/F/M 分數給分群標籤（見 segment()）。
  6. 依 member_id 排序輸出 rfm_result.csv，並印出檔案的 md5 作為 [CHECKSUM]。

用法：python baseline_etl.py [資料夾，預設 perf_data]
"""
import csv
import glob
import hashlib
import sys
import time
from datetime import date, datetime

import pandas as pd

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else "perf_data"
AS_OF = date(2026, 8, 31)
OUTPUT = "rfm_result.csv"


def load_orders():
    all_df = pd.DataFrame()
    for path in sorted(glob.glob(f"{DATA_DIR}/orders_*.csv")):
        df = pd.read_csv(path)
        all_df = pd.concat([all_df, df], ignore_index=True)
    return all_df


def latest_versions(df):
    latest = {}
    for _, row in df.iterrows():
        key = (row["order_id"], row["line_no"])
        ts = datetime.strptime(row["updated_at"], "%Y-%m-%dT%H:%M:%S%z")
        if key not in latest or ts > latest[key][0]:
            latest[key] = (ts, row["order_status"], row["member_id"], row["order_id"], row["order_created_at"],
                           row["quantity"], row["unit_price"], row["line_discount"])
    return list(latest.values())


def member_stats(rows):
    stats = {}
    for _, status, member_id, order_id, created_at, qty, price, disc in rows:
        if status != "delivered":
            continue
        order_date = datetime.strptime(created_at[:10], "%Y-%m-%d").date()
        s = stats.setdefault(member_id, {"last": order_date, "orders": set(), "monetary": 0})
        s["last"] = max(s["last"], order_date)
        s["orders"].add(order_id)
        s["monetary"] += int(qty) * int(price) - int(disc)
    return stats


def score(member_ids, value, descending):
    ranked = sorted(member_ids, key=lambda m: (-value(m) if descending else value(m), m))
    n = len(ranked)
    return {m: 5 - (5 * ranked.index(m)) // n for m in member_ids}


def segment(r, f, m):
    if r >= 4 and f >= 4 and m >= 4:
        return "冠軍會員"
    if r >= 3 and f >= 3:
        return "忠誠會員"
    if r >= 4 and f <= 2:
        return "新進會員"
    if r <= 2 and f >= 3:
        return "流失風險"
    if r <= 2 and f <= 2:
        return "沉睡會員"
    return "一般會員"


def main():
    t_start = time.time()
    df = load_orders()
    print(f"讀檔完成：{len(df):,} 列（{time.time() - t_start:.1f}s）")
    rows = latest_versions(df)
    stats = member_stats(rows)
    members = pd.read_csv(f"{DATA_DIR}/members_perf.csv")

    ids = list(stats)
    recency = {m: (AS_OF - stats[m]["last"]).days for m in ids}
    freq = {m: len(stats[m]["orders"]) for m in ids}
    monetary = {m: stats[m]["monetary"] for m in ids}
    r_score = score(ids, lambda m: recency[m], descending=False)
    f_score = score(ids, lambda m: freq[m], descending=True)
    m_score = score(ids, lambda m: monetary[m], descending=True)

    with open(OUTPUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["member_id", "member_tier", "recency_days", "frequency", "monetary",
                    "r_score", "f_score", "m_score", "segment"])
        for m in sorted(ids):
            tier = members[members["member_id"] == m]["member_tier"].values[0]
            w.writerow([m, tier, recency[m], freq[m], monetary[m], r_score[m], f_score[m], m_score[m],
                        segment(r_score[m], f_score[m], m_score[m])])

    with open(OUTPUT, "rb") as f:
        checksum = hashlib.md5(f.read()).hexdigest()
    print(f"會員數：{len(ids):,}")
    print(f"[CHECKSUM] {checksum}")
    print(f"[ELAPSED] {time.time() - t_start:.1f}s")


if __name__ == "__main__":
    main()
