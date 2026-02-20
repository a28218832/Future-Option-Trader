from __future__ import annotations

import logging
import os

import dash
from dash import dcc, html, Input, Output
import dash_ag_grid as dag
import dash_mantine_components as dmc
import plotly.graph_objects as go

from services.data_service import (
    filter_future_chart,
    filter_option_table,
    get_expiries_by_date,
    get_future_filter_values,
    get_option_filter_values,
    load_future_data,
    load_option_data,
)


import glob
DEBUG_LOG = os.getenv("APP_DEBUG_LOG", "0").lower() in {"1", "true", "yes", "on"}
logging.basicConfig(level=logging.DEBUG if DEBUG_LOG else logging.INFO)
logger = logging.getLogger(__name__)

futureList = glob.glob('C:/my_file/0_research/20250908_FutureStrategy/future_data/processed_parquet/*.parquet')
logger.debug("Loaded future parquet files: %s", futureList)

import pandas as pd

df_fut = pd.read_parquet(futureList[0])

for future_file in futureList[1:]:
    df_future = pd.read_parquet(future_file)
    
    df_fut = pd.concat([df_fut, df_future], axis=0, ignore_index=True)

if "交易日期_dt" not in df_fut.columns:
    df_fut["交易日期_dt"] = pd.to_datetime(df_fut["交易日期"], errors="coerce")


# 檢查結果
# print(df_opt.info())
logger.debug("Future dataframe columns: %s", list(df_fut.columns))


df_opt = pd.read_parquet("C:/my_file/0_research/20250908_FutureStrategy/option_data/processed_parquet/opt_all.parquet")
df_opt = df_opt.drop(columns=['漲跌價', '漲跌%', 'Unnamed: 20', '契約到期日', 'Unnamed: 21'])
logger.debug("Option dataframe columns: %s", list(df_opt.columns))

opt_values = get_option_filter_values(df_opt)
fut_values = get_future_filter_values(df_fut)

default_trade_date = opt_values["dates"][-1] if opt_values["dates"] else None
default_expiries = get_expiries_by_date(df_opt, default_trade_date)
default_opt_expiry = default_expiries[0] if default_expiries else None

default_fut_contract = "TX" if "TX" in fut_values["contracts"] else (fut_values["contracts"][0] if fut_values["contracts"] else None)
default_fut_expiry = fut_values["expiries"][-1] if fut_values["expiries"] else None

app = dash.Dash(__name__)
app.title = "Phase 1 - Trading UI MVP"


def create_candlestick_figure(contract: str | None, expiry: str | None) -> go.Figure:
    data = filter_future_chart(df_fut, contract, expiry)
    fig = go.Figure()
    if data.empty:
        fig.update_layout(title="K 線圖（無資料）")
        return fig

    fig.add_trace(
        go.Candlestick(
            x=data["交易日期"],
            open=data["開盤價"],
            high=data["最高價"],
            low=data["最低價"],
            close=data["收盤價"],
            name="OHLC",
            increasing_line_color="#e03131",
            decreasing_line_color="#1864ab",
            hovertemplate=(
                "日期: %{x|%Y-%m-%d}<br>"
                "開: %{open:.2f}<br>"
                "高: %{high:.2f}<br>"
                "低: %{low:.2f}<br>"
                "收: %{close:.2f}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title=f"即時 K 線圖 - {contract or ''} {expiry or ''}",
        xaxis_rangeslider_visible=True,
        xaxis_title="交易日期",
        yaxis_title="價格",
        template="plotly_white",
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
        height=420,
    )
    return fig


def get_column_defs() -> list[dict]:
    return [
        {"field": "交易日期", "pinned": "left", "minWidth": 120},
        {"field": "契約", "width": 70},
        {"field": "到期月份(週別)", "width": 110},
        {"field": "履約價", "type": "numericColumn", "width": 90},
        {"field": "買賣權", "width": 80},
        {"field": "交易時段", "width": 90},
        {"field": "收盤價", "type": "numericColumn", "width": 90},
        {"field": "成交量", "type": "numericColumn", "width": 90},
        {"field": "Implied_Volatility", "headerName": "IV", "type": "numericColumn", "width": 90},
        {"field": "Delta", "type": "numericColumn", "width": 90},
        {"field": "Gamma", "type": "numericColumn", "width": 90},
        {"field": "Theta", "type": "numericColumn", "width": 90},
        {"field": "Vega", "type": "numericColumn", "width": 90},
        {"field": "Itm_Prob", "headerName": "ITM Prob", "type": "numericColumn", "width": 100},
    ]


app.layout = dmc.MantineProvider(
    [
        dmc.Container(
            [
                dmc.Title("Phase 1：交易 UI MVP", order=2, mb="sm"),
                dmc.Text("K 線圖 + T 字報表（含 Greeks）", c="dimmed", mb="md"),
                dmc.SimpleGrid(
                    cols=6,
                    spacing="md",
                    children=[
                        dmc.Select(
                            id="trade-date",
                            label="交易日期",
                            data=[{"value": d, "label": d} for d in opt_values["dates"]],
                            value=default_trade_date,
                            clearable=False,
                        ),
                        dmc.Select(
                            id="opt-expiry",
                            label="選擇權到期",
                            data=[{"value": e, "label": e} for e in default_expiries],
                            value=default_opt_expiry,
                            clearable=False,
                        ),
                        dmc.MultiSelect(
                            id="cp-filter",
                            label="買賣權",
                            data=[{"value": v, "label": v} for v in opt_values["cp_values"]],
                            value=opt_values["cp_values"],
                        ),
                        dmc.Select(
                            id="session-filter",
                            label="交易時段",
                            data=[{"value": "全部", "label": "全部"}] + [{"value": s, "label": s} for s in opt_values["sessions"]],
                            value="一般" if "一般" in opt_values["sessions"] else "全部",
                            clearable=False,
                        ),
                        dmc.Select(
                            id="fut-contract",
                            label="期貨契約",
                            data=[{"value": c, "label": c} for c in fut_values["contracts"]],
                            value=default_fut_contract,
                            clearable=False,
                        ),
                        dmc.Select(
                            id="fut-expiry",
                            label="期貨到期",
                            data=[{"value": e, "label": e} for e in fut_values["expiries"]],
                            value=default_fut_expiry,
                            clearable=False,
                        ),
                    ],
                ),
                dmc.Space(h="md"),
                dcc.Graph(id="kline-graph", figure=create_candlestick_figure(default_fut_contract, default_fut_expiry)),
                dmc.Space(h="md"),
                dmc.Title("期權 T 字報表", order=4, mb="xs"),
                dag.AgGrid(
                    id="t-table",
                    columnDefs=get_column_defs(),
                    rowData=[],
                    columnSize="sizeToFit",
                    dashGridOptions={
                        "rowSelection": "multiple",
                        "animateRows": True,
                        "pagination": True,
                        "paginationPageSize": 40,
                        "defaultColDef": {
                            "sortable": True,
                            "filter": True,
                            "resizable": True,
                        },
                    },
                    style={"height": "520px", "width": "100%"},
                ),
            ],
            fluid=True,
            pt="md",
            pb="xl",
        )
    ]
)


@app.callback(
    Output("opt-expiry", "data"),
    Output("opt-expiry", "value"),
    Input("trade-date", "value"),
)
def refresh_option_expiry(trade_date: str | None):
    expiries = get_expiries_by_date(df_opt, trade_date)
    options = [{"value": x, "label": x} for x in expiries]
    value = expiries[0] if expiries else None
    return options, value


@app.callback(
    Output("t-table", "rowData"),
    Input("trade-date", "value"),
    Input("opt-expiry", "value"),
    Input("cp-filter", "value"),
    Input("session-filter", "value"),
)
def refresh_option_table(trade_date: str | None, expiry: str | None, cp_values: list[str] | None, session: str | None):
    data = filter_option_table(df_opt, trade_date, expiry, cp_values, session)
    return data.to_dict("records")


@app.callback(
    Output("kline-graph", "figure"),
    Input("fut-contract", "value"),
    Input("fut-expiry", "value"),
)
def refresh_kline(contract: str | None, expiry: str | None):
    return create_candlestick_figure(contract, expiry)


if __name__ == "__main__":
    app.run(debug=True)
