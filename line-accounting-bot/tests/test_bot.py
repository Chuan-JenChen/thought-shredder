import base64, hashlib, hmac, json, os
from datetime import date
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["LINE_CHANNEL_SECRET"] = "test-secret"

import pytest
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app import db
db.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
db.SessionLocal.configure(bind=db.engine)

from app.bot import handle
from app.calc import calc_wage

D = date(2026, 11, 24)


@pytest.fixture(autouse=True)
def fresh_db():
    db.Base.metadata.drop_all(db.engine)
    db.init_db()


def test_normal_day():
    w = calc_wage(Decimal(8), Decimal(250))
    assert w["total"] == 2000 and w["ot_pay"] == 0


def test_overtime_split():
    # 8h*250 + 2h*250*4/3 + 1h*250*5/3 = 2000 + 666.67 + 416.67 = 3083
    w = calc_wage(Decimal(11), Decimal(250))
    assert (w["normal"], w["ot1"], w["ot2"]) == (8, 2, 1)
    assert w["total"] == 3083


def test_work_log_remembers_wage():
    assert "合計 2,000" in handle("u1", "工時 阿明 8 250", D)
    assert "合計 2,500" in handle("u1", "工時 阿明 9.5", D)  # 2000 + 1.5*250*4/3


def test_first_time_needs_wage():
    assert "請附上時薪" in handle("u1", "工時 新人 8", D)


def test_bad_input():
    assert "不是數字" in handle("u1", "工時 阿明 八 250", D)
    assert "說明" in handle("u1", "亂打", D) or "記帳" in handle("u1", "亂打", D)


def test_summary_and_isolation():
    handle("u1", "工時 阿明 8 250", D)
    handle("u1", "材料 電線 1,500", D)
    handle("u2", "材料 水管 999", D)
    out = handle("u1", "今日", D)
    assert "阿明：8h，2,000 元" in out
    assert "材料 1,500 元" in out and "總成本 3,500 元" in out


def test_webhook_signature():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    body = json.dumps({"events": []}).encode()
    sig = base64.b64encode(hmac.new(b"test-secret", body, hashlib.sha256).digest()).decode()
    assert c.post("/callback", content=body, headers={"X-Line-Signature": sig}).status_code == 200
    assert c.post("/callback", content=body, headers={"X-Line-Signature": "bad"}).status_code == 400
