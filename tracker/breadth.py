"""市場寬度核心計算與分區規則（美股、台股共用）。"""
from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd


def own_sma(closes: pd.DataFrame, n: int) -> pd.DataFrame:
    """每檔以「自身有收盤價的日子」取最近 N 筆算均線，與 .gs 的 slice(-N) 一致。

    停牌日沒有收盤價，不會被當成一筆資料，也不會補值。
    """
    sma = {col: closes[col].dropna().rolling(n).mean() for col in closes.columns}
    return pd.DataFrame(sma).reindex(closes.index)


def breadth_series(
    closes: pd.DataFrame,
    periods: Iterable[int],
    min_obs: Optional[int] = None,
) -> pd.DataFrame:
    """回傳每日寬度：pct_N（%）、above_N（檔數）與 valid（有效樣本數）。

    當日有收盤價才算樣本。min_obs 不為 None 時，歷史筆數不足者不列入分母（美股：
    資料少於 200 筆略過）；為 None 時全部列入分母，歷史不足者視為未站上（台股）。
    """
    periods = tuple(periods)
    present = closes.notna()
    valid_mask = present if min_obs is None else present & (present.cumsum() >= min_obs)
    valid = valid_mask.sum(axis=1)

    out = pd.DataFrame({"valid": valid})
    for n in periods:
        sma = own_sma(closes, n)
        above = ((closes > sma) & valid_mask).sum(axis=1)
        # 尚無任何一檔算得出 N 日均線的日子（歷史不足 N 筆）不是 0%，而是沒有值
        ready = (sma.notna() & valid_mask).sum(axis=1) > 0
        out[f"above_{n}"] = above
        out[f"pct_{n}"] = (above / valid.where(valid > 0) * 100).where(ready)
    return out


def latest_summary(series: pd.DataFrame, periods: Iterable[int], zone_fn) -> dict:
    """取最新一日的寬度、分區標籤，以及相較約一週前（5 個交易日）的變化。"""
    last = series.iloc[-1]
    prev = series.iloc[-6] if len(series) > 5 else None
    values = {}
    for n in periods:
        pct = float(last[f"pct_{n}"])
        delta = None
        if prev is not None and pd.notna(prev[f"pct_{n}"]):
            delta = pct - float(prev[f"pct_{n}"])
        values[n] = {
            "pct": pct,
            "above": int(last[f"above_{n}"]),
            "zone": zone_fn(pct),
            "delta": delta,
        }
    return {
        "date": series.index[-1].strftime("%Y-%m-%d"),
        "valid": int(last["valid"]),
        "values": values,
    }


def us_zone(v: float) -> str:
    if v > 80:
        return "過熱"
    if v >= 50:
        return "多頭健康"
    if v >= 20:
        return "弱勢"
    return "超賣"


def tw_zone(v: float) -> str:
    if v >= 85:
        return "階段性頭部"
    if v >= 50:
        return "偏多"
    if v > 15:
        return "偏空"
    return "階段性底部"


def tw_long_term_signal(b20: float, b60: float, b240: float) -> str:
    if b20 >= 85 and b60 >= 85 and b240 >= 85:
        return "長期頭部"
    if b20 <= 15 and b60 <= 15 and b240 <= 15:
        return "長期底部"
    return ""


def zone_class(label: str) -> str:
    """分區標籤對應的樣式：hot 過熱／頭部、good 偏多、warn 偏空／弱勢、cold 超賣／底部。"""
    return {
        "過熱": "hot",
        "階段性頭部": "hot",
        "多頭健康": "good",
        "偏多": "good",
        "弱勢": "warn",
        "偏空": "warn",
        "超賣": "cold",
        "階段性底部": "cold",
    }.get(label, "")
