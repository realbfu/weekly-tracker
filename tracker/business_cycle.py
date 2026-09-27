"""景氣對策信號（燈號、綜合判斷分數）。

資料來源：政府資料開放平台「景氣指標及燈號」資料集（國家發展委員會，每月更新）。
先呼叫 data.gov.tw 的資料集 API 取得目前的下載連結（連結每月會換），再下載其中
的 ZIP 取出「景氣指標與燈號.csv」。當月尚未公布時該筆為 "-"，取最近一筆有值的資料。
"""
from __future__ import annotations

import io
import zipfile

import pandas as pd
import requests

from .config import NDC_DATASET_API, NDC_ECO_CSV_NAME

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def parse_signal_csv(csv_bytes: bytes) -> dict:
    df = pd.read_csv(io.BytesIO(csv_bytes), dtype=str, encoding="utf-8-sig")
    df = df[df["景氣對策信號"].notna() & (df["景氣對策信號"] != "-")]
    if df.empty:
        raise RuntimeError("景氣對策信號資料皆為缺值")
    last = df.iloc[-1]
    date = last["Date"]
    return {
        "date": f"{date[:4]}-{date[4:]}",
        "score": float(last["景氣對策信號綜合分數"]),
        "light": last["景氣對策信號"],
    }


def fetch_signal() -> dict:
    meta = requests.get(NDC_DATASET_API, headers=_HEADERS, timeout=30).json()
    dist = meta["result"]["distribution"][0]
    if dist["resourceFormat"] != "ZIP":
        raise RuntimeError(f"景氣對策信號資料格式非預期：{dist['resourceFormat']!r}")
    zip_bytes = requests.get(dist["resourceDownloadUrl"], headers=_HEADERS, timeout=30).content
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        csv_bytes = z.read(NDC_ECO_CSV_NAME)
    return parse_signal_csv(csv_bytes)
