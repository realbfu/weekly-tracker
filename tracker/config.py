"""標的、均線週期、警示門檻等設定。數值沿用 marketbreath／BIAS 的既有 .gs 設定。"""
from __future__ import annotations

TIMEZONE = "Asia/Taipei"

# ---------- 市場寬度 ----------
# 與 marketbreath/nasdaq100_market_breadth.gs 的 getNasdaq100Tickers() 相同；
# 來源：Nasdaq 官方 API（2026-09-24，101 檔）。已下市或資料不足 200 筆的代號（如新上市的 HONA、SPCX）會在計算時自動略過。
NDX_TICKERS = [
    "AAPL", "ABNB", "ADBE", "ADI", "ADP", "ADSK", "AEP", "ALAB", "ALNY", "AMAT",
    "AMD", "AMGN", "AMZN", "APP", "ARM", "ASML", "AVGO", "AXON", "BKNG", "BKR",
    "CCEP", "CDNS", "CEG", "CMCSA", "COST", "CPRT", "CRWD", "CRWV", "CSCO", "CSX",
    "CTAS", "DASH", "DDOG", "DXCM", "EXC", "FANG", "FAST", "FER", "FTNT", "GEHC",
    "GILD", "GOOG", "GOOGL", "HON", "HONA", "IDXX", "INTC", "INTU", "ISRG", "KDP",
    "KLAC", "LIN", "LITE", "LRCX", "MAR", "MCHP", "MDLZ", "MELI", "META", "MNST",
    "MPWR", "MRVL", "MSFT", "MSTR", "MU", "NBIS", "NFLX", "NVDA", "NXPI", "ODFL",
    "ORLY", "PANW", "PAYX", "PCAR", "PDD", "PEP", "PLTR", "PYPL", "QCOM", "REGN",
    "RKLB", "ROP", "ROST", "SBUX", "SHOP", "SNDK", "SNPS", "SPCX", "STX", "TER",
    "TMUS", "TRI", "TSLA", "TTWO", "TXN", "VRTX", "WBD", "WDAY", "WDC", "WMT",
    "XEL",
]

US_BREADTH_MA = (20, 50, 200)
# 正常約 99 檔（HONA、SPCX 上市未滿 200 日不計入），低於此數視為下載不完整
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

# 抓取範圍：日線 200 日均線約需 290 曆日
DAILY_PERIOD = "2y"

# ---------- 價格走勢圖 ----------
CHART_TARGETS = [
    ("加權指數 TWSE", "^TWII"),
    ("VOO", "VOO"),
    ("QQQ", "QQQ"),
    ("SOXX", "SOXX"),
]
CHART_MA = (20, 60, 200)

# 疊加在加權指數走勢圖上的匯率（副座標軸）
FX_OVERLAY_SYMBOL = "^TWII"
FX_TARGET = ("USD/TWD", "USDTWD=X")

# ---------- 景氣對策信號 ----------
# 政府資料開放平台「景氣指標及燈號」資料集（國家發展委員會提供，每月更新）
NDC_DATASET_API = "https://data.gov.tw/api/v2/rest/dataset/6099"
NDC_ECO_CSV_NAME = "景氣指標與燈號.csv"

# ---------- 台積電營運（月營收／季度損益） ----------
# 資料來源：MOPS 公開資訊觀測站，透過 twmops 套件抓取
TSMC_STOCK_ID = "2330"
TSMC_MONTHLY_START = (2025, 10)  # 月營收回補／顯示起點
# 季報回補起點：從 2024 Q1 開始，一方面才夠算 2025 Q4 的年增（YoY%），
# 一方面 Q4 的單季數字需扣除同年 Q1~Q3（年報揭露全年累計），須有完整年度
TSMC_QUARTERLY_FETCH_START = (2024, 1)
TSMC_QUARTERLY_DISPLAY_START = (2025, 4)  # 顯示起點：2025 Q4（對應 2025-10 之後）
