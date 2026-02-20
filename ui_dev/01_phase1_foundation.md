# Phase 1：基礎框架與核心元件落地（MVP）

## 目標

建立可運作的單頁交易介面，完成：

1. K 線圖（基於 `df_fut`）
2. T 字報表（基於 `df_opt` + Greeks 欄）
3. 基本篩選（交易日期、到期月份、買賣權、交易時段）

## 工作項目

### 1) 專案骨架

- 建立 `app.py`（Dash 入口）
- 建立 `layout/`（版面）與 `callbacks/`（互動）模組
- 建立 `services/`（資料清洗、Greeks、Payoff 計算）

### 2) 資料預處理

- 將 `-`、空字串統一轉為 NaN
- 日期欄位統一為 `datetime64`
- `履約價/開高低收/成交量/Greeks` 轉為數值型
- 同一履約價區分 `交易時段`（一般/盤後）

### 3) K 線圖

- 使用 `go.Candlestick`
- Hover 顯示 `Open/High/Low/Close/Volume`
- 新增 `rangeslider` 與拖曳縮放

### 4) T 字報表

- 使用 `dash-ag-grid`
- 欄位至少包含：
  - `履約價`、`買賣權`、`收盤價`、`成交量`
  - `Implied_Volatility`、`Delta`、`Gamma`、`Theta`、`Vega`、`Itm_Prob`
- 先啟用列選取（single/multi 均可，建議直接 multi）

## Callback 最小集合

1. `Input: 篩選器值` -> `Output: K線 figure`
2. `Input: 篩選器值` -> `Output: T字 rowData`

## 驗收標準

- 畫面載入 < 2 秒（本機 parquet）
- K 線 hover 正確顯示 OHLC
- T 字報表可流暢捲動與排序
- 篩選後資料同步更新且不報錯

## 風險與建議

- 原始 CSV 格式不一致：先建立欄位映射表再轉型
- 先不做即時串流，優先完成單次查詢流暢度
