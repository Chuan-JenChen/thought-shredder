"""薪資計算：依台灣勞基法加班費規則（平日）。"""
from decimal import Decimal, ROUND_HALF_UP

NORMAL_HOURS = Decimal("8")
OT1_HOURS = Decimal("2")          # 第 9–10 小時
OT1_RATE = Decimal("4") / 3       # ×1.34
OT2_RATE = Decimal("5") / 3       # 第 11 小時起 ×1.67


def split_hours(hours: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    """回傳 (正常工時, 加班前2小時, 加班第3小時起)。"""
    if hours < 0:
        raise ValueError("工時不能是負數")
    normal = min(hours, NORMAL_HOURS)
    ot1 = min(max(hours - NORMAL_HOURS, Decimal(0)), OT1_HOURS)
    ot2 = max(hours - NORMAL_HOURS - OT1_HOURS, Decimal(0))
    return normal, ot1, ot2


def calc_wage(hours: Decimal, hourly: Decimal) -> dict:
    normal, ot1, ot2 = split_hours(hours)
    normal_pay = normal * hourly
    ot1_pay = ot1 * hourly * OT1_RATE
    ot2_pay = ot2 * hourly * OT2_RATE
    total = (normal_pay + ot1_pay + ot2_pay).quantize(Decimal("1"), ROUND_HALF_UP)
    return {
        "normal": normal, "ot1": ot1, "ot2": ot2,
        "normal_pay": normal_pay.quantize(Decimal("1"), ROUND_HALF_UP),
        "ot_pay": (ot1_pay + ot2_pay).quantize(Decimal("1"), ROUND_HALF_UP),
        "total": total,
    }
