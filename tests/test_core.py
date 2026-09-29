import numpy as np
import pandas as pd
import pytest

from tracker.bias import calc_bias
from tracker.breadth import breadth_series, tw_long_term_signal, tw_zone, us_zone
from tracker.breadth_tw import parse_mi_index
from tracker.business_cycle import parse_signal_history
from tracker.tsmc_financials import since, with_quarterly_growth


def _series(values):
    idx = pd.date_range("2026-01-01", periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype=float)


def test_bias_uses_latest_n_closes_and_flags_threshold():
    closes = _series([10] * 19 + [12])  # SMA20 = 10.1
    res = calc_bias(closes, (20,), {20: 10.0})
    assert res["bias"][20] == pytest.approx((12 - 10.1) / 10.1 * 100)
    assert res["alert"][20] == "hot"


def test_bias_negative_alert_and_insufficient_data():
    closes = _series([10] * 19 + [8])
    res = calc_bias(closes, (20, 60), {20: 5.0, 60: 5.0})
    assert res["alert"][20] == "cold"
    assert res["bias"][60] is None and res["alert"][60] is None


def test_breadth_is_strictly_greater_than_sma():
    # 三檔：A 站上均線、B 剛好等於均線（不算站上）、C 低於均線
    idx = pd.date_range("2026-01-01", periods=5, freq="D")
    closes = pd.DataFrame(
        {"A": [1, 1, 1, 1, 5], "B": [2, 2, 2, 2, 2], "C": [5, 5, 5, 5, 1]}, index=idx, dtype=float
    )
    out = breadth_series(closes, (3,), min_obs=None)
    last = out.iloc[-1]
    assert last["valid"] == 3
    assert last["above_3"] == 1
    assert last["pct_3"] == pytest.approx(100 / 3)


def test_breadth_min_obs_excludes_short_history_from_denominator():
    idx = pd.date_range("2026-01-01", periods=6, freq="D")
    closes = pd.DataFrame(
        {"OLD": [1, 1, 1, 1, 1, 9], "NEW": [np.nan, np.nan, np.nan, 1, 1, 9]}, index=idx, dtype=float
    )
    out = breadth_series(closes, (3,), min_obs=5)
    assert out.iloc[-1]["valid"] == 1  # NEW 只有 3 筆，不列入分母


def test_breadth_short_history_counts_as_not_above_when_no_min_obs():
    idx = pd.date_range("2026-01-01", periods=4, freq="D")
    closes = pd.DataFrame({"OLD": [1, 1, 1, 9], "NEW": [np.nan, np.nan, np.nan, 9]}, index=idx, dtype=float)
    out = breadth_series(closes, (3,), min_obs=None)
    assert out.iloc[-1]["valid"] == 2
    assert out.iloc[-1]["above_3"] == 1


def test_breadth_pct_is_nan_until_any_ticker_has_enough_history():
    idx = pd.date_range("2026-01-01", periods=4, freq="D")
    closes = pd.DataFrame({"A": [1, 2, 3, 4], "B": [4, 3, 2, 1]}, index=idx, dtype=float)
    out = breadth_series(closes, (3,), min_obs=None)
    assert out["pct_3"].iloc[:2].isna().all()  # 前 2 天不足 3 筆
    assert out["pct_3"].iloc[2:].notna().all()


def test_breadth_suspended_day_is_not_a_data_point():
    # B 在第 3 天停牌（NaN），均線應以自身最近 3 筆有價日計算
    idx = pd.date_range("2026-01-01", periods=5, freq="D")
    closes = pd.DataFrame({"B": [1, 1, np.nan, 1, 3]}, index=idx, dtype=float)
    out = breadth_series(closes, (3,), min_obs=None)
    assert out.iloc[-1]["above_3"] == 1  # 自身最近 3 筆為 1,1,3，均線 1.67，收盤 3 站上


def test_zone_boundaries_follow_gs_rules():
    assert us_zone(80.01) == "過熱" and us_zone(80) == "多頭健康"
    assert us_zone(50) == "多頭健康" and us_zone(49.9) == "弱勢" and us_zone(19.9) == "超賣"
    assert tw_zone(85) == "階段性頭部" and tw_zone(15) == "階段性底部" and tw_zone(15.1) == "偏空"
    assert tw_long_term_signal(90, 88, 86) == "長期頭部"
    assert tw_long_term_signal(10, 10, 15) == "長期底部"
    assert tw_long_term_signal(90, 88, 60) == ""


def _payload(n_rows, stat="OK", extra_row=None):
    data = [[f"{1000 + i}", "測試", "1", "1", "1", "1", "1", "1", "1,234.50"] for i in range(n_rows)]
    if extra_row:
        data.append(extra_row)
    return {
        "stat": stat,
        "tables": [
            {"title": "價格指數", "fields": ["指數"], "data": []},
            {
                "title": "115年09月24日 每日收盤行情(全部)",
                "fields": ["證券代號", "證券名稱", "成交股數", "成交筆數", "成交金額", "開盤價", "最高價", "最低價", "收盤價"],
                "data": data,
            },
        ],
    }


def test_parse_mi_index_ok_parses_commas_and_skips_dashes():
    closes = parse_mi_index(_payload(1300, extra_row=["9999", "停牌", "0", "0", "0", "--", "--", "--", "--"]))
    assert len(closes) == 1300
    assert closes["1000"] == 1234.5
    assert "9999" not in closes


def test_parse_mi_index_holiday_returns_none():
    assert parse_mi_index({"stat": "很抱歉，沒有符合條件的資料!"}) is None


def test_parse_mi_index_other_errors_raise_instead_of_looking_like_holiday():
    with pytest.raises(RuntimeError):
        parse_mi_index({"stat": "查詢過於頻繁"})
    with pytest.raises(RuntimeError):
        parse_mi_index(_payload(10))  # 檔數過少，疑似格式異常


def test_parse_signal_history_skips_unpublished_latest_month():
    csv_text = (
        "Date,領先指標綜合指數,景氣對策信號綜合分數,景氣對策信號\n"
        "202606,135.79,39,紅\n"
        "202607,138.63,41,紅\n"
        "202608,140.0,-,-\n"  # 當月尚未公布
    )
    df = parse_signal_history(csv_text.encode("utf-8-sig"))
    assert len(df) == 2
    last = df.iloc[-1]
    assert last["date"].strftime("%Y-%m") == "2026-07"
    assert last["score"] == 41.0 and last["light"] == "紅"


def test_parse_signal_history_all_missing_raises():
    csv_text = "Date,景氣對策信號綜合分數,景氣對策信號\n202608,-,-\n"
    with pytest.raises(RuntimeError):
        parse_signal_history(csv_text.encode("utf-8-sig"))


def test_with_quarterly_growth_computes_margins_and_changes():
    df = pd.DataFrame([
        {"year": 2024, "quarter": 4, "revenue": 100.0, "gross_profit": 60.0, "net_profit": 40.0},
        {"year": 2025, "quarter": 1, "revenue": 110.0, "gross_profit": 66.0, "net_profit": 44.0},
        {"year": 2025, "quarter": 2, "revenue": 121.0, "gross_profit": 72.6, "net_profit": 48.4},
        {"year": 2025, "quarter": 3, "revenue": 100.0, "gross_profit": 60.0, "net_profit": 40.0},
        {"year": 2025, "quarter": 4, "revenue": 150.0, "gross_profit": 90.0, "net_profit": 60.0},
    ])
    out = with_quarterly_growth(df)
    last = out.iloc[-1]
    assert last["gross_margin_pct"] == pytest.approx(60.0)
    assert last["net_margin_pct"] == pytest.approx(40.0)
    assert last["qoq_pct"] == pytest.approx(50.0)  # 150 對比前一季（2025Q3）100
    assert last["yoy_pct"] == pytest.approx(50.0)  # 150 對比去年同季（2024Q4）100
    assert pd.isna(out.iloc[0]["yoy_pct"])  # 第一列沒有去年同季資料可比


def test_since_filters_by_year_quarter():
    df = pd.DataFrame([
        {"year": 2024, "quarter": 4, "v": 1},
        {"year": 2025, "quarter": 1, "v": 2},
        {"year": 2025, "quarter": 4, "v": 3},
    ])
    out = since(df, 2025, 1)
    assert list(out["v"]) == [2, 3]
