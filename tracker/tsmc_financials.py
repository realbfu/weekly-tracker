"""台積電（2330）月營收與季度損益。

資料來源：MOPS 公開資訊觀測站，透過 twmops 套件抓取。月營收由 twmops 直接算好
MoM%／YoY%。季度損益（營收／毛利／淨利／基本每股盈餘，Q1～Q3）twmops 已把累
計數字還原成單季數字；但 Q4 的 XBRL 年報揭露的是「全年累計」而非單季（年報
本身沒有單獨的 Q4 期間），須自行扣除同年 Q1+Q2+Q3 才是單季 Q4——這是台灣財報
揭露格式的已知特性，非 bug（EPS 採業界慣用的「全年 EPS 減前三季 EPS」估算單
季 EPS，嚴格來說會因加權股數些微差異而不完全精確，但這是通用作法）。
毛利率／淨利率、季增（QoQ%）／年增（YoY%）由我們自己算，需要比對前一季與去
年同季，故快取範圍會比實際顯示範圍多回補幾季（見 config.TSMC_QUARTERLY_FETCH_START，
且需從年初 Q1 開始才能在算 Q4 時取得同年前三季）。

歷史資料存在 data/ 下的 CSV 快取（透過 tracker.history.append_snapshot），之後
每次執行只補抓快取裡還沒有的期別；當月／當季尚未公布時 twmops 會丟例外，視為
「還沒補齊」，記一筆警告後停止往後嘗試即可，等下次執行再補。
"""
from __future__ import annotations

import contextlib
import io
from typing import List, Optional, Tuple

import pandas as pd
from twmops import FinancialFetcher, RevenueFetcher

from .config import TSMC_STOCK_ID
from .history import DATA_DIR

MONTHLY_FILE = "tsmc_monthly_revenue.csv"
QUARTERLY_FILE = "tsmc_quarterly_income.csv"

_revenue_fetcher = RevenueFetcher()
_financial_fetcher = FinancialFetcher()


def _roc_year(year: int) -> int:
    return year - 1911


def _next_month(year: int, month: int) -> Tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def _next_quarter(year: int, quarter: int) -> Tuple[int, int]:
    return (year + 1, 1) if quarter == 4 else (year, quarter + 1)


def fetch_monthly_revenue(year: int, month: int) -> dict:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        r = _revenue_fetcher.get_single_revenue(TSMC_STOCK_ID, year=_roc_year(year), month=month)
    return {
        "date": f"{year:04d}-{month:02d}",
        "revenue": r.revenue,
        "mom_pct": r.mom_change,
        "yoy_pct": r.yoy_change,
    }


def _find_basic_eps(facts: dict) -> Optional[float]:
    """XBRL 基本每股盈餘的標籤名稱在不同分類法版本間可能略有差異，多找幾種寫法。"""
    for key in ("BasicEarningsLossPerShare", "EarningsPerShareBasic", "BasicEarningsPerShare"):
        if key in facts:
            return facts[key]
    return next((v for k, v in facts.items() if "PerShare" in k and "Basic" in k), None)


def _fetch_statement_raw(year: int, quarter: int) -> dict:
    """單次 XBRL 查詢的原始結果；quarter=4 時這是「全年累計」，尚未扣除前三季。

    revenue／gross_profit／net_profit 的 XBRL 原始數字單位是新台幣元，換算成千元
    以對齊月營收（MOPS 開放資料慣例單位）——已用「單季營收加總 = 對應三個月月營收
    加總」交叉驗證換算正確。eps（每股盈餘）本身就是「元」，不需再換算。
    """
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        stmt = _financial_fetcher.get_simplified_statement(
            TSMC_STOCK_ID, year=_roc_year(year), quarter=quarter, statement_type="income_statement",
        )
    facts = {item.type: item.value for item in stmt.items}
    return {
        "revenue": facts["Revenue"] / 1000,
        "gross_profit": facts.get("GrossProfit", facts.get("GrossProfitLossFromOperations")) / 1000,
        "net_profit": facts["ProfitLoss"] / 1000,
        "eps": _find_basic_eps(facts),
    }


def _load(filename: str) -> pd.DataFrame:
    path = DATA_DIR / filename
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def update_monthly_revenue(
    end_year: int, end_month: int, start: Tuple[int, int],
) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    """回傳（含本次新抓資料的完整月營收歷史, 本次新抓的列, 警告訊息）。

    只抓快取裡還沒有的月份；是否要把新抓的列寫回 CSV 由呼叫端決定（比照
    breadth／PE 快照的慣例：只有整批執行都成功才落盤，避免不完整資料進版控）。
    """
    existing = _load(MONTHLY_FILE)
    have = set(existing["date"]) if not existing.empty else set()
    new_rows: list = []
    warnings: list = []
    y, m = start
    while (y, m) <= (end_year, end_month):
        key = f"{y:04d}-{m:02d}"
        if key not in have:
            try:
                new_rows.append(fetch_monthly_revenue(y, m))
            except Exception as exc:
                warnings.append(f"台積電 {key} 月營收取得失敗：{exc}")
                break  # 通常代表尚未公布，之後月份也還沒有，停止往後嘗試
        y, m = _next_month(y, m)
    new_df = pd.DataFrame(new_rows)
    combined = pd.concat([existing, new_df], ignore_index=True) if new_rows else existing
    return combined.sort_values("date").reset_index(drop=True), new_df, warnings


def update_quarterly_income(
    end_year: int, end_quarter: int, start: Tuple[int, int],
) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    """回傳（含本次新抓資料的完整季度損益歷史（單季，未含衍生指標）, 本次新抓的列, 警告訊息）。

    只抓快取裡還沒有的季別；落盤時機比照 update_monthly_revenue。start 建議從某年
    Q1 開始，確保算 Q4 時同年前三季已在快取或本次已抓過。
    """
    existing = _load(QUARTERLY_FILE)
    cache: dict = {
        (int(row.year), int(row.quarter)): {
            "revenue": row.revenue, "gross_profit": row.gross_profit, "net_profit": row.net_profit,
            "eps": getattr(row, "eps", None),
        }
        for row in existing.itertuples()
    }
    new_rows: list = []
    warnings: list = []
    y, q = start
    while (y, q) <= (end_year, end_quarter):
        if (y, q) not in cache:
            try:
                raw = _fetch_statement_raw(y, q)
                if q == 4:
                    # 年報揭露全年累計，扣除前三季（已是單季）才是單季 Q4；
                    # 正常情況下前三季在本次迴圈已依序抓過，這裡的 fetch 只是防呆備援
                    prior = []
                    for pq in (1, 2, 3):
                        if (y, pq) not in cache:
                            cache[(y, pq)] = _fetch_statement_raw(y, pq)
                        prior.append(cache[(y, pq)])
                    prior_eps = [p["eps"] for p in prior]
                    row = {
                        "revenue": raw["revenue"] - sum(p["revenue"] for p in prior),
                        "gross_profit": raw["gross_profit"] - sum(p["gross_profit"] for p in prior),
                        "net_profit": raw["net_profit"] - sum(p["net_profit"] for p in prior),
                        "eps": (
                            None if raw["eps"] is None or any(e is None for e in prior_eps)
                            else raw["eps"] - sum(prior_eps)
                        ),
                    }
                else:
                    row = raw
                cache[(y, q)] = row
                new_rows.append({"year": y, "quarter": q, **row})
            except Exception as exc:
                warnings.append(f"台積電 {y}Q{q} 季報取得失敗：{exc}")
                break
        y, q = _next_quarter(y, q)
    new_df = pd.DataFrame(new_rows)
    combined = pd.concat([existing, new_df], ignore_index=True) if new_rows else existing
    return combined.sort_values(["year", "quarter"]).reset_index(drop=True), new_df, warnings


def with_quarterly_growth(quarterly: pd.DataFrame) -> pd.DataFrame:
    """加上毛利率／淨利率／季增（QoQ%）／年增（YoY%）。輸入須已依年季由舊到新排序。"""
    out = quarterly.copy()
    out["gross_margin_pct"] = out["gross_profit"] / out["revenue"] * 100
    out["net_margin_pct"] = out["net_profit"] / out["revenue"] * 100
    out["qoq_pct"] = out["revenue"].pct_change(1) * 100
    out["yoy_pct"] = out["revenue"].pct_change(4) * 100
    return out


def since(df: pd.DataFrame, year: int, quarter: int) -> pd.DataFrame:
    """篩選出 year-quarter（含）之後的列，df 須含 year／quarter 欄位。"""
    key = df["year"] * 4 + df["quarter"]
    return df[key >= year * 4 + quarter].reset_index(drop=True)
