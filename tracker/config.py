"""標的、均線週期、警示門檻等設定。數值沿用 marketbreath／BIAS 的既有 .gs 設定。"""
from __future__ import annotations

TIMEZONE = "Asia/Taipei"

# ---------- 市場寬度 ----------
# 與 marketbreath/nasdaq100_market_breadth.gs 的 getNasdaq100Tickers() 相同；
# 已下市或資料不足的代號會在計算時自動略過。
NDX_TICKERS = [
    "AAPL", "ABNB", "ADBE", "ADI", "ADP", "ADSK", "AEP", "AMAT", "AMD", "AMGN",
    "AMZN", "ANSS", "APP", "ARM", "ASML", "AVGO", "AZN", "BIIB", "BKNG", "BKR",
    "CCEP", "CDNS", "CDW", "CEG", "CHTR", "CMCSA", "COST", "CPRT", "CRWD", "CSCO",
    "CSGP", "CSX", "CTAS", "CTSH", "DASH", "DDOG", "DXCM", "EA", "EXC", "FANG",
    "FAST", "FTNT", "GEHC", "GFS", "GILD", "GOOG", "GOOGL", "HON", "IDXX", "INTC",
    "INTU", "ISRG", "KDP", "KHC", "KLAC", "LIN", "LRCX", "LULU", "MAR", "MCHP",
    "MDB", "MDLZ", "MELI", "META", "MNST", "MRVL", "MSFT", "MSTR", "MU", "NFLX",
    "NVDA", "NXPI", "ODFL", "ON", "ORLY", "PANW", "PAYX", "PCAR", "PDD", "PEP",
    "PLTR", "PYPL", "QCOM", "REGN", "ROP", "ROST", "SBUX", "SNPS", "TEAM", "TMUS",
    "TRI", "TSLA", "TTD", "TTWO", "TXN", "VRSK", "VRTX", "WBD", "WDAY", "XEL", "ZS",
]

US_BREADTH_MA = (20, 50, 200)
# 正常約 100 檔（清單含已下市的 ANSS），低於此數視為下載不完整
US_MIN_VALID = 90
TW_BREADTH_MA = (20, 60, 240)

# 穿越／分區門檻，僅用於趨勢圖的參考線
US_BREADTH_LEVELS = (20, 50, 80)
TW_BREADTH_LEVELS = (15, 50, 85)

# ---------- TWSE 價格庫 ----------
TWSE_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
TWSE_REQUEST_SLEEP_SEC = 2.0
# 低於此檔數視為回應格式異常（正常約 1,360 檔以上）
TWSE_MIN_STOCKS_SANITY = 1200
TW_HISTORY_KEEP_ROWS = 260
TW_BACKFILL_CALENDAR_DAYS = 400

# ---------- BIAS ----------
# (顯示名稱, Yahoo 代號)
BIAS_TARGETS = [
    ("加權指數", "^TWII"),
    ("台積電 2330", "2330.TW"),
    ("元大台灣50 0050", "0050.TW"),
    ("VOO", "VOO"),
    ("QQQ", "QQQ"),
    ("SOXX", "SOXX"),
    ("TSM", "TSM"),
    ("NVDA", "NVDA"),
]

DAILY_MA = (20, 60, 200)
DAILY_BIAS_THRESHOLDS = {20: 10.0, 60: 15.0, 200: 20.0}

WEEKLY_MA = (20, 60, 120, 240)
WEEKLY_BIAS_THRESHOLDS = {20: 15.0, 60: 30.0, 120: 50.0, 240: 80.0}

# 抓取範圍：日線 200 日均線約需 290 曆日；週線 240 週約需 4.6 年
DAILY_PERIOD = "2y"
WEEKLY_PERIOD = "6y"

# ---------- 價格走勢圖 ----------
CHART_TARGETS = [
    ("加權指數 TWSE", "^TWII"),
    ("VOO", "VOO"),
    ("QQQ", "QQQ"),
    ("SOXX", "SOXX"),
]
CHART_MA = (20, 60, 200)
