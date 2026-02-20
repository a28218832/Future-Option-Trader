from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import os

import numpy as np
import pandas as pd


OPTION_COLUMNS = [
    "交易日期",
    "契約",
    "到期月份(週別)",
    "履約價",
    "買賣權",
    "開盤價",
    "最高價",
    "最低價",
    "收盤價",
    "成交量",
    "結算價",
    "未沖銷契約數",
    "最後最佳買價",
    "最後最佳賣價",
    "歷史最高價",
    "歷史最低價",
    "是否因訊息面暫停交易",
    "交易時段",
    "T",
    "dT",
    "Implied_Volatility",
    "Delta",
    "Gamma",
    "Theta",
    "Vega",
    "Itm_Prob",
]

FUTURE_COLUMNS = [
    "交易日期",
    "契約",
    "到期月份(週別)",
    "開盤價",
    "最高價",
    "最低價",
    "收盤價",
    "漲跌價",
    "漲跌%",
    "成交量",
    "結算價",
    "未沖銷契約數",
    "最後最佳買價",
    "最後最佳賣價",
    "歷史最高價",
    "歷史最低價",
]

NUMERIC_OPTION_COLUMNS = [
    "履約價",
    "開盤價",
    "最高價",
    "最低價",
    "收盤價",
    "成交量",
    "結算價",
    "未沖銷契約數",
    "最後最佳買價",
    "最後最佳賣價",
    "歷史最高價",
    "歷史最低價",
    "T",
    "dT",
    "Implied_Volatility",
    "Delta",
    "Gamma",
    "Theta",
    "Vega",
    "Itm_Prob",
]

NUMERIC_FUTURE_COLUMNS = [
    "開盤價",
    "最高價",
    "最低價",
    "收盤價",
    "成交量",
    "結算價",
    "未沖銷契約數",
    "最後最佳買價",
    "最後最佳賣價",
    "歷史最高價",
    "歷史最低價",
]


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.replace("-", np.nan), errors="coerce")


def _ensure_columns(df: pd.DataFrame, required_columns: list[str]) -> pd.DataFrame:
    for col in required_columns:
        if col not in df.columns:
            df[col] = np.nan
    return df[required_columns]


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def load_future_data() -> pd.DataFrame:
    root = _workspace_root()
    future_dir = root / "future_data"
    files = sorted(future_dir.glob("*_fut.csv"))
    if not files:
        return pd.DataFrame(columns=FUTURE_COLUMNS + ["交易日期_dt"])

    frames = []
    for path in files:
        try:
            frame = pd.read_csv(path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            frame = pd.read_csv(path, encoding="big5", errors="ignore")
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)
    df = _ensure_columns(df, FUTURE_COLUMNS)
    df["交易日期_dt"] = pd.to_datetime(df["交易日期"], errors="coerce")
    for col in NUMERIC_FUTURE_COLUMNS:
        df[col] = _to_numeric(df[col])
    df = df.dropna(subset=["交易日期_dt"]).sort_values("交易日期_dt")
    return df


@lru_cache(maxsize=1)
def load_option_data() -> pd.DataFrame:
    root = _workspace_root()
    option_dir = root / "option_data"
    files = sorted(option_dir.glob("**/*.csv"))
    limit = int(os.getenv("OPTION_FILE_LIMIT", "24"))
    if limit > 0:
        files = files[-limit:]

    if not files:
        return pd.DataFrame(columns=OPTION_COLUMNS + ["交易日期_dt"])

    frames = []
    for path in files:
        try:
            frame = pd.read_csv(path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            frame = pd.read_csv(path, encoding="big5", errors="ignore")
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)
    df = _ensure_columns(df, OPTION_COLUMNS)
    df["交易日期_dt"] = pd.to_datetime(df["交易日期"], errors="coerce")
    for col in NUMERIC_OPTION_COLUMNS:
        df[col] = _to_numeric(df[col])
    df["交易時段"] = df["交易時段"].fillna("一般")
    df = df.dropna(subset=["交易日期_dt"]).sort_values(["交易日期_dt", "履約價"])
    return df


def get_option_filter_values(df_opt: pd.DataFrame) -> dict:
    dates = sorted(df_opt["交易日期"].dropna().unique().tolist())
    cp_values = sorted(df_opt["買賣權"].dropna().unique().tolist())
    sessions = sorted(df_opt["交易時段"].dropna().unique().tolist())
    return {
        "dates": dates,
        "cp_values": cp_values,
        "sessions": sessions,
    }


def get_future_filter_values(df_fut: pd.DataFrame) -> dict:
    contracts = sorted(df_fut["契約"].dropna().unique().tolist())
    expiries = sorted(df_fut["到期月份(週別)"].dropna().unique().tolist())
    return {
        "contracts": contracts,
        "expiries": expiries,
    }


def get_expiries_by_date(df_opt: pd.DataFrame, trade_date: str | None) -> list[str]:
    if not trade_date:
        return []
    data = df_opt[df_opt["交易日期"] == trade_date]
    return sorted(data["到期月份(週別)"].dropna().unique().tolist())


def filter_option_table(
    df_opt: pd.DataFrame,
    trade_date: str | None,
    expiry: str | None,
    cp_values: list[str] | None,
    session: str | None,
) -> pd.DataFrame:
    data = df_opt
    if trade_date:
        data = data[data["交易日期"] == trade_date]
    if expiry:
        data = data[data["到期月份(週別)"] == expiry]
    if cp_values:
        data = data[data["買賣權"].isin(cp_values)]
    if session and session != "全部":
        data = data[data["交易時段"] == session]

    display_columns = [
        "交易日期",
        "契約",
        "到期月份(週別)",
        "履約價",
        "買賣權",
        "交易時段",
        "收盤價",
        "成交量",
        "Implied_Volatility",
        "Delta",
        "Gamma",
        "Theta",
        "Vega",
        "Itm_Prob",
    ]
    data = data.reindex(columns=display_columns).copy()
    data = data.sort_values(["履約價", "買賣權", "交易時段"], na_position="last")
    return data


def filter_future_chart(df_fut: pd.DataFrame, contract: str | None, expiry: str | None) -> pd.DataFrame:
    data = df_fut
    if contract:
        data = data[data["契約"] == contract]
    if expiry:
        data = data[data["到期月份(週別)"] == expiry]
    data = data.dropna(subset=["開盤價", "最高價", "最低價", "收盤價"])
    data = data.sort_values("交易日期_dt")
    return data
