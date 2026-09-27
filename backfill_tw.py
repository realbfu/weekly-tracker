"""一次性回補 TWSE 歷史收盤價（約 10 分鐘）。可中斷，重跑會從斷點續補。"""
import datetime as dt
from zoneinfo import ZoneInfo

from tracker.breadth_tw import load_history, update_history
from tracker.config import TIMEZONE

if __name__ == "__main__":
    today = dt.datetime.now(ZoneInfo(TIMEZONE)).date()
    hist = update_history(load_history(), today)
    print(f"完成：共 {len(hist)} 個交易日，{hist.index.min().date()} ~ {hist.index.max().date()}")
