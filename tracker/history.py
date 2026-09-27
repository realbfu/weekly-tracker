"""每週快照存檔（CSV）。同一天同一 key 重跑時覆蓋，不重複累加。"""
from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def append_snapshot(filename: str, rows: pd.DataFrame, key_cols: List[str]) -> None:
    path = DATA_DIR / filename
    if path.exists():
        old = pd.read_csv(path, dtype={"date": str})
        merged = pd.concat([old, rows], ignore_index=True)
        merged = merged.drop_duplicates(subset=key_cols, keep="last")
    else:
        merged = rows
    path.parent.mkdir(parents=True, exist_ok=True)
    merged.sort_values(key_cols).to_csv(path, index=False)
