"""台股上市市場寬度：以 TWSE 每日收盤行情自建價格庫。

母體為每日收盤行情表中所有有數字收盤價的證券（含 ETF、特別股等，不濾成只剩個股），
這樣才能對齊玩股網的口徑。價格為未還原價。
"""
from __future__ import annotations

import datetime as dt
import time
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
import requests

from .breadth import breadth_series, latest_summary, tw_long_term_signal, tw_zone
from .config import (
    TW_BACKFILL_CALENDAR_DAYS,
    TW_BREADTH_MA,
    TW_HISTORY_KEEP_ROWS,
    TWSE_MIN_STOCKS_SANITY,
    TWSE_REQUEST_SLEEP_SEC,
    TWSE_URL,
)

HISTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "tw_close_history.csv.gz"
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def parse_mi_index(payload: dict) -> Optional[dict]:
    """解析 MI_INDEX 回應為 {證券代號: 收盤價}。休市日回傳 None，其餘異常一律 raise。

    只有「沒有符合條件」才視為休市；被限流或格式變動若也回傳 None，會造成靜默漏日。
    """
    stat = payload.get("stat", "")
    if "沒有符合條件" in stat:
        return None
    if stat != "OK":
        raise RuntimeError(f"TWSE 回應異常：{stat!r}")

    table = next(
        (t for t in payload.get("tables", []) if "每日收盤行情" in (t.get("title") or "")),
        None,
    )
    if table is None:
        raise RuntimeError("TWSE 回應找不到「每日收盤行情」表")
    fields = table["fields"]
    code_idx, close_idx = fields.index("證券代號"), fields.index("收盤價")

    closes: dict = {}
    for row in table["data"]:
        try:
            closes[str(row[code_idx]).strip()] = float(str(row[close_idx]).replace(",", ""))
        except ValueError:
            continue  # 停牌或無成交時收盤價為 "--"
    if len(closes) < TWSE_MIN_STOCKS_SANITY:
        raise RuntimeError(f"TWSE 證券檔數僅 {len(closes)}，低於 {TWSE_MIN_STOCKS_SANITY}，疑似格式異常")
    return closes


def fetch_day(day: dt.date, session: requests.Session) -> Optional[dict]:
    resp = session.get(
        TWSE_URL,
        params={"date": day.strftime("%Y%m%d"), "type": "ALLBUT0999", "response": "json"},
        headers=_HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    return parse_mi_index(resp.json())


def load_history(path: Path = HISTORY_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, index_col=0, parse_dates=True)


def save_history(hist: pd.DataFrame, path: Path = HISTORY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    hist.tail(TW_HISTORY_KEEP_ROWS).to_csv(path, float_format="%.2f", compression="gzip")


def _merge(hist: pd.DataFrame, pending: dict) -> pd.DataFrame:
    if not pending:
        return hist
    new = pd.DataFrame.from_dict(pending, orient="index")
    new.index = pd.DatetimeIndex(new.index)
    merged = pd.concat([hist, new]).sort_index()
    return merged[~merged.index.duplicated(keep="last")]


def update_history(
    hist: pd.DataFrame,
    end: dt.date,
    log: Callable[[str], None] = print,
    save_every: int = 10,
) -> pd.DataFrame:
    """從價格庫最後一天的隔天補到 end；價格庫為空則回補 TW_BACKFILL_CALENDAR_DAYS 天。

    每累積 save_every 個交易日就存檔，中斷後重跑會從斷點續補。
    """
    if hist.empty:
        day = end - dt.timedelta(days=TW_BACKFILL_CALENDAR_DAYS)
    else:
        day = hist.index.max().date() + dt.timedelta(days=1)

    session = requests.Session()
    pending: dict = {}
    while day <= end:
        if day.weekday() < 5:
            closes = fetch_day(day, session)
            if closes is None:
                log(f"{day} 休市")
            else:
                pending[pd.Timestamp(day)] = closes
                log(f"{day} 收盤價 {len(closes)} 檔")
                if len(pending) >= save_every:
                    hist = _merge(hist, pending)
                    pending = {}
                    save_history(hist)
            time.sleep(TWSE_REQUEST_SLEEP_SEC)
        day += dt.timedelta(days=1)

    hist = _merge(hist, pending)
    save_history(hist)
    return hist.tail(TW_HISTORY_KEEP_ROWS)


def compute_tw_breadth(hist: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    longest = max(TW_BREADTH_MA)
    if len(hist) < longest:
        raise RuntimeError(
            f"台股價格庫僅 {len(hist)} 筆，少於 {longest} 筆，請先執行 backfill_tw.py"
        )
    series = breadth_series(hist, TW_BREADTH_MA, min_obs=None)
    summary = latest_summary(series, TW_BREADTH_MA, tw_zone)
    v = summary["values"]
    summary["long_term"] = tw_long_term_signal(
        v[TW_BREADTH_MA[0]]["pct"], v[TW_BREADTH_MA[1]]["pct"], v[TW_BREADTH_MA[2]]["pct"]
    )
    return summary, series
