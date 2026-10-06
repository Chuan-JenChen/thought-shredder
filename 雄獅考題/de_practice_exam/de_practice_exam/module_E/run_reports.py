# -*- coding: utf-8 -*-
"""執行三份報表 SQL，印出各自的「8 月」數字。用法：python run_reports.py [dataset 資料夾，預設 ../dataset]"""
import pathlib
import sys

import duckdb

dataset = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "../dataset").resolve().as_posix()
con = duckdb.connect()
con.execute("SET TimeZone = 'Asia/Taipei'")
for f in sorted(pathlib.Path(__file__).with_name("reports").glob("*.sql")):
    sql = f.read_text(encoding="utf-8").replace("{DATASET}", dataset)
    value = con.sql(sql).fetchone()[0]
    print(f"{f.stem:<18} {value:>16,.0f}")
