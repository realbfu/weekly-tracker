"""Nasdaq-100 市場寬度。"""
from __future__ import annotations

import pandas as pd

from .breadth import breadth_series, latest_summary, us_zone
from .config import NDX_TICKERS, US_BREADTH_MA, US_MIN_VALID
from .prices import fetch_adjusted_closes


def compute_us_breadth() -> tuple[dict, pd.DataFrame]:
    # 2 年資料足夠 200 日均線，並保留約 1 年可畫趨勢圖
    closes = fetch_adjusted_closes(NDX_TICKERS, "2y")
    series = breadth_series(closes, US_BREADTH_MA, min_obs=max(US_BREADTH_MA))
    series = series.dropna(subset=[f"pct_{max(US_BREADTH_MA)}"])
    if series.empty:
        raise ValueError("Nasdaq-100 歷史資料不足，無法計算 200 日寬度")
    valid = int(series["valid"].iloc[-1])
    # 有效樣本明顯偏少通常是下載被限流，此時的寬度會失真，寧可失敗也不發佈
    if valid < US_MIN_VALID:
        raise ValueError(f"Nasdaq-100 有效樣本僅 {valid} 檔，低於 {US_MIN_VALID}，疑似下載不完整")
    return latest_summary(series, US_BREADTH_MA, us_zone), series
