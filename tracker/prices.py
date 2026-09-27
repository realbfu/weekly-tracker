"""透過 yfinance 抓取價格，含重試與退避。"""
from __future__ import annotations

import time
from typing import Iterable

import pandas as pd
import yfinance as yf

_RETRIES = 3


def _retry(fn, what: str):
    last: Exception | None = None
    for attempt in range(_RETRIES):
        try:
            return fn()
        except Exception as exc:  # yfinance 對限流與網路錯誤的例外型別不一
            last = exc
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{what} 失敗：{last}")


def fetch_close(symbol: str, period: str, interval: str) -> pd.Series:
    """回傳未還原收盤價（舊到新）。BIAS 與走勢圖沿用 .gs 的做法，使用原始收盤價。"""

    def _go() -> pd.Series:
        df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False)
        close = df["Close"].dropna()
        if close.empty:
            raise ValueError("沒有價格資料")
        close.index = close.index.tz_localize(None).normalize()
        return close

    return _retry(_go, f"{symbol} {interval} 價格")


def fetch_adjusted_closes(symbols: Iterable[str], period: str) -> pd.DataFrame:
    """一次抓多檔還原收盤價（欄為代號）。市場寬度沿用 .gs 使用還原價的做法。"""
    tickers = list(symbols)

    def _download(batch: list, threads: bool) -> pd.DataFrame:
        df = yf.download(
            batch,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            group_by="column",
            threads=threads,
        )
        if df.empty:
            raise ValueError("沒有價格資料")
        close = df["Close"]
        if isinstance(close, pd.Series):
            close = close.to_frame(batch[0])
        close.index = close.index.tz_localize(None).normalize()
        return close

    closes = _retry(lambda: _download(tickers, True), "Nasdaq-100 價格")

    # 多執行緒下載偶爾因 yfinance 的本機快取資料庫鎖定而漏抓個別代號，單獨重試一次；
    # 真的已下市的代號仍會失敗，屬正常，交由寬度計算略過
    missing = [t for t in tickers if t not in closes.columns or closes[t].dropna().empty]
    for ticker in missing:
        try:
            closes[ticker] = _download([ticker], False)[ticker].reindex(closes.index)
        except Exception:
            pass
    return closes
