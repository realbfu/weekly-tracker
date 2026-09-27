"""BIAS（乖離率）計算與警示判定。"""
from __future__ import annotations

from typing import Dict, Iterable, Optional

import pandas as pd


def calc_bias(
    closes: pd.Series,
    periods: Iterable[int],
    thresholds: Dict[int, float],
) -> dict:
    """BIAS(N) = (收盤 - SMA(N)) / SMA(N) * 100。

    序列須為舊到新；資料不足 N 筆的週期回傳 None，不硬算。
    alert 為 "hot"（正乖離過大）、"cold"（負乖離過大）或 None。
    """
    close = float(closes.iloc[-1])
    ma: Dict[int, Optional[float]] = {}
    bias: Dict[int, Optional[float]] = {}
    alert: Dict[int, Optional[str]] = {}
    for n in periods:
        if len(closes) < n:
            ma[n] = bias[n] = alert[n] = None
            continue
        avg = float(closes.tail(n).mean())
        ma[n] = avg
        bias[n] = (close - avg) / avg * 100
        limit = thresholds.get(n)
        if limit is not None and abs(bias[n]) >= limit:
            alert[n] = "hot" if bias[n] > 0 else "cold"
        else:
            alert[n] = None
    return {
        "date": closes.index[-1].strftime("%Y-%m-%d"),
        "close": close,
        "ma": ma,
        "bias": bias,
        "alert": alert,
    }
