"""把 LINE 文字訊息轉成記帳動作，回傳要回覆的文字。"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select

from .calc import calc_wage
from .db import Material, SessionLocal, WorkLog

TW = timezone(timedelta(hours=8))

HELP = (
    "📒 水電記帳機器人\n"
    "工時 姓名 小時 [時薪]\n  例：工時 阿明 10 250\n"
    "  （時薪沒寫就用該員工上次的時薪）\n"
    "材料 品名 金額\n  例：材料 電線 1500\n"
    "今日／本月：看統計\n"
    "說明：看這份說明"
)


def today() -> date:
    return datetime.now(TW).date()


def _num(s: str) -> Decimal:
    try:
        v = Decimal(s.replace(",", ""))
    except InvalidOperation:
        raise ValueError(f"「{s}」不是數字")
    if v < 0:
        raise ValueError("數字不能是負的")
    return v


def handle(owner: str, text: str, on: date | None = None) -> str:
    on = on or today()
    parts = text.strip().split()
    if not parts:
        return HELP
    cmd, args = parts[0], parts[1:]
    try:
        if cmd == "工時":
            return _work(owner, args, on)
        if cmd == "材料":
            return _material(owner, args, on)
        if cmd in ("今日", "今天"):
            return _summary(owner, on, on, "今日")
        if cmd == "本月":
            return _summary(owner, on.replace(day=1), on, "本月")
    except ValueError as e:
        return f"⚠️ {e}\n\n輸入「說明」看格式"
    return HELP


def _work(owner: str, args: list[str], on: date) -> str:
    if len(args) not in (2, 3):
        raise ValueError("格式：工時 姓名 小時 [時薪]")
    name, hours = args[0], _num(args[1])
    if hours > 24:
        raise ValueError("一天工時不能超過 24 小時")
    with SessionLocal() as s:
        if len(args) == 3:
            hourly = _num(args[2])
        else:
            hourly = s.scalar(
                select(WorkLog.hourly)
                .where(WorkLog.owner == owner, WorkLog.worker == name)
                .order_by(WorkLog.id.desc()).limit(1)
            )
            if hourly is None:
                raise ValueError(f"第一次記錄「{name}」，請附上時薪，例：工時 {name} {args[1]} 250")
        w = calc_wage(hours, hourly)
        s.add(WorkLog(owner=owner, worker=name, work_date=on, hours=hours,
                      hourly=hourly, wage=w["total"]))
        s.commit()
    lines = [f"✅ {name} {on:%m/%d} {hours:g} 小時（時薪 {hourly:g}）",
             f"正常 {w['normal']:g}h = {w['normal_pay']:,} 元"]
    if w["ot1"] or w["ot2"]:
        lines.append(f"加班 {w['ot1'] + w['ot2']:g}h = {w['ot_pay']:,} 元")
    lines.append(f"合計 {w['total']:,} 元")
    return "\n".join(lines)


def _material(owner: str, args: list[str], on: date) -> str:
    if len(args) != 2:
        raise ValueError("格式：材料 品名 金額")
    item, amount = args[0], _num(args[1]).quantize(Decimal("1"))
    with SessionLocal() as s:
        s.add(Material(owner=owner, item=item, spend_date=on, amount=amount))
        s.commit()
    return f"✅ 材料 {item} {amount:,} 元（{on:%m/%d}）"


def _summary(owner: str, start: date, end: date, label: str) -> str:
    with SessionLocal() as s:
        rows = s.execute(
            select(WorkLog.worker, func.sum(WorkLog.hours), func.sum(WorkLog.wage))
            .where(WorkLog.owner == owner, WorkLog.work_date.between(start, end))
            .group_by(WorkLog.worker).order_by(WorkLog.worker)
        ).all()
        mat = s.scalar(
            select(func.coalesce(func.sum(Material.amount), 0))
            .where(Material.owner == owner, Material.spend_date.between(start, end))
        )
    wage_total = sum((Decimal(r[2]) for r in rows), Decimal(0))
    out = [f"📊 {label}統計（{start:%m/%d}–{end:%m/%d}）"]
    out += [f"{n}：{Decimal(h).normalize():f}h，{Decimal(w):,.0f} 元" for n, h, w in rows] or ["（沒有工時紀錄）"]
    out.append(f"人事 {wage_total:,.0f} 元")
    out.append(f"材料 {Decimal(mat):,.0f} 元")
    out.append(f"總成本 {wage_total + Decimal(mat):,.0f} 元")
    return "\n".join(out)
