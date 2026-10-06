# -*- coding: utf-8 -*-
"""
模組 D 測試資料生成器
=====================
在本機產生一年份（2025-09-01 ~ 2026-08-31）的訂單明細事件：
  perf_data/orders_YYYYMMDD.csv   365 個每日小檔，合計約 510 萬列、約 470MB
  perf_data/members_perf.csv      5 萬名會員的等級

每張訂單會產生兩個版本：下單時的 placed，以及 1~3 天後的最終狀態
（delivered / cancelled / returned）。最終狀態可能落在隔天或之後的檔案。

用法：python generate_perf_data.py [輸出資料夾，預設 perf_data]
"""
import bisect
import csv
import math
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from itertools import accumulate

OUT = sys.argv[1] if len(sys.argv) > 1 else "perf_data"
R = random.Random(42)
rnd = R.random
TPE = timezone(timedelta(hours=8))
START = datetime(2025, 9, 1, tzinfo=TPE)
DAYS = 365
N_MEMBERS, N_PRODUCTS, ORDERS_PER_DAY = 50_000, 400, 2_400
COLS = ["order_id", "line_no", "member_id", "order_status", "product_id", "quantity",
        "unit_price", "line_discount", "order_created_at", "updated_at"]


def randint(a, b):
    return a + int(rnd() * (b - a + 1))


def fmt(t):
    return t.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def main():
    os.makedirs(OUT, exist_ok=True)
    prices = [randint(3, 120) * 5 - 1 for _ in range(N_PRODUCTS)]
    tiers = ["一般"] * 70 + ["鮮享"] * 22 + ["尊榮"] * 8
    with open(f"{OUT}/members_perf.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["member_id", "member_tier"])
        for i in range(1, N_MEMBERS + 1):
            w.writerow([f"C{i:06d}", tiers[int(rnd() * len(tiers))]])
    cum = list(accumulate(math.exp(0.7 * R.gauss(0, 1)) for _ in range(N_MEMBERS)))   # 會員購買頻率不均

    pending = {}                                              # 檔案日期 -> 之後才到的最終狀態列
    seq, total = 0, 0
    for day in range(DAYS):
        d = START + timedelta(days=day)
        key = d.strftime("%Y%m%d")
        rows = pending.pop(key, [])
        for _ in range(ORDERS_PER_DAY + randint(-200, 200)):
            seq += 1
            oid = f"PO{seq:08d}"
            t0 = d + timedelta(seconds=randint(0, 86399))
            member = f"C{bisect.bisect_left(cum, rnd() * cum[-1]) + 1:06d}"
            u = rnd()
            final = "delivered" if u < 0.90 else "cancelled" if u < 0.96 else "returned"
            t1 = t0 + timedelta(seconds=randint(20 * 3600, 72 * 3600))
            n_lines = 1 + int(rnd() ** 1.5 * 6)
            products = set()
            while len(products) < n_lines:
                products.add(int(rnd() ** 1.3 * N_PRODUCTS))
            for ln, p in enumerate(sorted(products), 1):
                qty = 1 + int(rnd() ** 3 * 4)
                disc = min(randint(1, 10) * 5, qty * prices[p] // 2) if rnd() < 0.2 else 0
                base = [oid, ln, member, None, f"G{p + 1:05d}", qty, prices[p], disc, fmt(t0), None]
                rows.append(base[:3] + ["placed"] + base[4:9] + [fmt(t0)])
                k1 = t1.strftime("%Y%m%d")
                if (t1 - START).days < DAYS:
                    pending.setdefault(k1, []).append(base[:3] + [final] + base[4:9] + [fmt(t1)])
        with open(f"{OUT}/orders_{key}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(COLS)
            w.writerows(rows)
        total += len(rows)
        if day % 30 == 0:
            print(f"  {key}：累計 {total:,} 列")
    print(f"完成：{DAYS} 個檔、{total:,} 列，輸出於 {OUT}/")


if __name__ == "__main__":
    main()
