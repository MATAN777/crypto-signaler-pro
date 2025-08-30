from __future__ import annotations
import io, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def _candles(ax, df: pd.DataFrame):
    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    x = np.arange(len(df))
    up = c >= o
    dn = ~up
    w = 0.6
    for i in range(len(df)):
        ax.vlines(x[i], l[i], h[i], linewidth=0.8, alpha=0.7)
    ax.bar(x[up], (c - o)[up], bottom=o[up], width=w, alpha=0.85)
    ax.bar(x[dn], (o - c)[dn], bottom=c[dn], width=w, alpha=0.85)

def _hband(ax, ylow: float, yhigh: float, x0: float, x1: float, alpha: float = 0.12, lw: float = 1.0):
    ax.axhspan(ylow, yhigh, xmin=0, xmax=1, alpha=alpha)
    ax.hlines([ylow, yhigh], x0, x1, linewidth=lw, alpha=0.8)

def plot_chart(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    fib: dict | None = None,
    zones: dict | None = None,
) -> bytes:
    data = df.tail(200).reset_index(drop=True) if len(df) > 200 else df.copy().reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(11, 5.2), dpi=140)
    ax.set_title(f"{symbol} · {timeframe}")

    _candles(ax, data)

    for col, lw in [("ema_fast", 1.2), ("ema_mid", 1.4), ("ema_slow", 1.6)]:
        if col in data:
            ax.plot(data.index, data[col].values, linewidth=lw, alpha=0.95, label=col)

    x0, x1 = 0, len(data) - 1 if len(data) else 1

    if zones and isinstance(zones, dict):
        dem = zones.get("demand") or {}
        sup = zones.get("supply") or {}
        if dem.get("low") is not None and dem.get("high") is not None:
            _hband(ax, float(dem["low"]), float(dem["high"]), x0, x1, alpha=0.16, lw=1.0)
            ax.text(x1, (dem["low"] + dem["high"]) / 2.0, "Demand", va="center", ha="right", fontsize=9, alpha=0.9)
        if sup.get("low") is not None and sup.get("high") is not None:
            _hband(ax, float(sup["low"]), float(sup["high"]), x0, x1, alpha=0.16, lw=1.0)
            ax.text(x1, (sup["low"] + sup["high"]) / 2.0, "Supply", va="center", ha="right", fontsize=9, alpha=0.9)

    if fib and isinstance(fib, dict) and fib.get("level") is not None:
        lvl = float(fib["level"])
        ax.hlines(lvl, x0, x1, linewidth=1.6, alpha=0.95, linestyles="--")
        dir_txt = fib.get("direction", "")
        ax.text(x0, lvl, f"Fib 0.31 {lvl:.2f} ({dir_txt})", va="bottom", ha="left", fontsize=9, alpha=0.95)

    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left")
    ax.set_xlim(0, max(x1, 1))
    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf.read()