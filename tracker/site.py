"""產生靜態儀表板 site/index.html（Jinja2 + Plotly）。"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .breadth import zone_class
from .config import CHART_MA

ROOT = Path(__file__).resolve().parent.parent

# 兩種佈景都看得清楚的中間色調
_COLORS = {"close": "#7f8c9b", 20: "#2f7de1", 50: "#e08a00", 60: "#e08a00", 120: "#2aa876", 200: "#c2408b", 240: "#c2408b"}


def _base_layout(title: str) -> dict:
    return dict(
        title=dict(text=title, x=0.01, font=dict(size=15)),
        margin=dict(l=48, r=16, t=48, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.15),
        hovermode="x unified",
        xaxis=dict(showgrid=False),
        yaxis=dict(zeroline=False),
    )


def breadth_chart_json(series: pd.DataFrame, periods: Iterable[int], levels, title: str) -> str:
    fig = go.Figure()
    for n in periods:
        col = f"pct_{n}"
        data = series[col].dropna().tail(260)
        fig.add_trace(go.Scatter(
            x=data.index, y=data.round(2), mode="lines", name=f"{n} 日",
            line=dict(color=_COLORS[n], width=2),
            hovertemplate="%{y:.1f}%",
        ))
    for lv in levels:
        fig.add_hline(y=lv, line=dict(dash="dot", width=1, color="#8a8f98"))
    fig.update_layout(**_base_layout(title))
    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    return pio.to_json(fig)


def price_chart_json(closes: pd.Series, title: str) -> str:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=closes.index, y=closes.round(2), mode="lines", name="收盤價",
        line=dict(color=_COLORS["close"], width=2),
    ))
    for n in CHART_MA:
        ma = closes.rolling(n).mean().dropna()
        fig.add_trace(go.Scatter(
            x=ma.index, y=ma.round(2), mode="lines", name=f"MA{n}",
            line=dict(color=_COLORS[n], width=1.3),
        ))
    fig.update_layout(**_base_layout(title))
    fig.update_layout(margin=dict(t=78), title=dict(y=0.97))
    # 按鈕移到左側、標題正下方；Plotly 工具列固定在右上角，左右錯開就不會重疊
    fig.update_xaxes(rangeselector=dict(
        x=0, xanchor="left", y=0.86, yanchor="top",
        buttons=[
            dict(count=3, label="3M", step="month", stepmode="backward"),
            dict(count=6, label="6M", step="month", stepmode="backward"),
            dict(count=1, label="1Y", step="year", stepmode="backward"),
            dict(step="all", label="全部"),
        ],
    ))
    return pio.to_json(fig)


def _fmt(value: Optional[float], digits: int = 2, signed: bool = False) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:+,.{digits}f}" if signed else f"{value:,.{digits}f}"


def render(context: dict, out_dir: Path = ROOT / "site") -> Path:
    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        autoescape=select_autoescape(["html", "j2"]),
    )
    env.filters["fmt"] = _fmt
    env.filters["zone_class"] = zone_class
    html = env.get_template("index.html.j2").render(**context)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "index.html"
    path.write_text(html, encoding="utf-8")
    return path
