"""每週主流程：抓資料 → 計算 → 存快照 → 產生 site/index.html。

單一標的失敗只顯示警告；市場寬度整段失敗視為致命，頁面仍會產生，但程式以非 0 結束，
讓 workflow 不發佈、保留上次成功的頁面。
"""
import datetime as dt
import sys
from zoneinfo import ZoneInfo

import pandas as pd

from tracker.bias import calc_bias
from tracker.breadth_tw import compute_tw_breadth, load_history, update_history
from tracker.breadth_us import compute_us_breadth
from tracker.business_cycle import fetch_history
from tracker.config import (
    BIAS_TARGETS,
    CHART_TARGETS,
    DAILY_BIAS_THRESHOLDS,
    DAILY_MA,
    DAILY_PERIOD,
    TIMEZONE,
    TW_BREADTH_LEVELS,
    TW_BREADTH_MA,
    US_BREADTH_LEVELS,
    US_BREADTH_MA,
)
from tracker.history import append_snapshot
from tracker.pe import fetch_pe
from tracker.prices import fetch_close
from tracker.site import breadth_chart_json, business_cycle_chart_json, price_chart_json, render


def main() -> int:
    now = dt.datetime.now(ZoneInfo(TIMEZONE))
    today = now.date()
    fatal: list = []
    warnings: list = []
    breadth: list = []
    snapshot_rows: list = []

    # ---- 市場寬度 ----
    try:
        summary, series = compute_us_breadth()
        breadth.append({
            "id": "chart-us", "title": "Nasdaq-100 市場寬度", "summary": summary,
            "chart": breadth_chart_json(series, US_BREADTH_MA, US_BREADTH_LEVELS, "站上均線比例（近一年）"),
            "note": "參考線：20／50／80%。使用還原收盤價，資料不足 200 筆或當日無報價者不計入。",
        })
        snapshot_rows.append(("us", summary, US_BREADTH_MA))
    except Exception as exc:
        fatal.append(f"Nasdaq-100 市場寬度計算失敗：{exc}")

    try:
        hist = update_history(load_history(), today)
        summary, series = compute_tw_breadth(hist)
        breadth.append({
            "id": "chart-tw", "title": "台股上市 市場寬度", "summary": summary,
            "chart": breadth_chart_json(series, TW_BREADTH_MA, TW_BREADTH_LEVELS, "站上均線比例"),
            "note": "參考線：15／50／85%。母體為 TWSE 每日收盤行情全部證券，未還原價；240 日線需累積 240 筆後才有值。",
        })
        snapshot_rows.append(("tw", summary, TW_BREADTH_MA))
    except Exception as exc:
        fatal.append(f"台股上市市場寬度計算失敗：{exc}")

    # ---- 景氣對策信號 ----
    business_cycle, business_cycle_chart = None, None
    try:
        bc_history = fetch_history()
        latest = bc_history.iloc[-1]
        business_cycle = {
            "date": latest["date"].strftime("%Y-%m"),
            "score": float(latest["score"]),
            "light": latest["light"],
        }
        business_cycle_chart = {
            "id": "chart-business-cycle",
            "json": business_cycle_chart_json(bc_history.tail(12)),
        }
    except Exception as exc:
        warnings.append(f"景氣對策信號取得失敗：{exc}")

    # ---- BIAS／PE ----
    daily_rows, daily_closes, pe_snapshot = [], {}, []
    for name, symbol in BIAS_TARGETS:
        try:
            closes = fetch_close(symbol, DAILY_PERIOD, "1d")
            daily_closes[symbol] = closes
            bias_data = calc_bias(closes, DAILY_MA, DAILY_BIAS_THRESHOLDS)
        except Exception as exc:
            warnings.append(f"{name} 日線 BIAS 取得失敗：{exc}")
            bias_data = None

        try:
            pe = fetch_pe(symbol)
        except Exception as exc:
            warnings.append(f"{name} PE 取得失敗：{exc}")
            pe = {"trailing": None, "forward": None, "note": "取得失敗"}

        daily_rows.append({"name": name, "data": bias_data, "pe": pe})
        pe_snapshot.append({
            "date": today.isoformat(), "symbol": symbol,
            "trailing_pe": pe["trailing"], "forward_pe": pe["forward"],
        })

    bias_tables = [
        {"title": "日線 BIAS／PE", "unit": "日", "periods": DAILY_MA, "thresholds": DAILY_BIAS_THRESHOLDS, "rows": daily_rows},
    ]

    # ---- 價格走勢圖 ----
    price_charts = []
    for i, (name, symbol) in enumerate(CHART_TARGETS):
        closes = daily_closes.get(symbol)
        if closes is None:
            continue
        price_charts.append({"id": f"chart-price-{i}", "json": price_chart_json(closes, name)})

    path = render({
        "updated_at": now.strftime("%Y-%m-%d %H:%M"),
        "breadth": breadth,
        "business_cycle": business_cycle,
        "business_cycle_chart": business_cycle_chart,
        "bias_tables": bias_tables,
        "price_charts": price_charts,
        "warnings": warnings,
        "fatal": fatal,
    })
    print(f"已產生 {path}")
    for msg in warnings + fatal:
        print(msg, file=sys.stderr)

    if fatal:
        return 1

    # 只有整體成功才存快照，避免不完整的資料進版控
    breadth_snapshot = []
    for market, summary, periods in snapshot_rows:
        row = {"date": today.isoformat(), "market": market, "valid": summary["valid"]}
        for n in periods:
            row[f"pct_{n}"] = round(summary["values"][n]["pct"], 2)
        breadth_snapshot.append(row)
    if breadth_snapshot:
        append_snapshot("breadth_history.csv", pd.DataFrame(breadth_snapshot), ["date", "market"])
    append_snapshot("pe_history.csv", pd.DataFrame(pe_snapshot), ["date", "symbol"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
