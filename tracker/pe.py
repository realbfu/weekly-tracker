"""PE 取得。缺值一律回傳 None（頁面顯示 N/A），不以價格 × 現有 EPS 偽造。"""
from __future__ import annotations

import time
from typing import Optional

import yfinance as yf

# Yahoo 沒有指數本身的 PE，TWSE 官方也沒有公開的加權指數本益比端點（僅個股）
_NO_SOURCE = {
    "^TWII": "Yahoo 與 TWSE 皆無加權指數本益比",
}


def _positive(value) -> Optional[float]:
    # PE 為負值或 0 代表虧損／無意義
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def fetch_pe(symbol: str) -> dict:
    if symbol in _NO_SOURCE:
        return {"trailing": None, "forward": None, "note": _NO_SOURCE[symbol]}

    last: Exception | None = None
    for attempt in range(3):
        try:
            info = yf.Ticker(symbol).info
            note = ""
            trailing = _positive(info.get("trailingPE"))
            forward = _positive(info.get("forwardPE"))
            if trailing is None and forward is None:
                note = "Yahoo 未提供"
            return {"trailing": trailing, "forward": forward, "note": note}
        except Exception as exc:
            last = exc
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{symbol} PE 取得失敗：{last}")
