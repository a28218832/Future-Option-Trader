# 系統運行流程（Runtime Sequence）

## 1. 啟動流程

### Step 1：載入模組

- `app.py` 載入 Dash / Plotly / AG Grid 元件
- 匯入 `data_service.py` 篩選函式

### Step 2：載入資料

- 讀入期貨資料集（目前版本可使用 parquet）
- 讀入選擇權資料集
- 建立 `交易日期_dt` 欄位（若缺少）

### Step 3：建立初始狀態

- 計算篩選器選項（交易日、到期、契約、交易時段）
- 計算預設值（最新日期、預設契約）
- 生成第一版 K 線圖 figure

### Step 4：掛載 callback

註冊三組 callback，等待 UI 事件。

## 2. 互動流程（Callback）

## A. 交易日期切換

輸入：`trade-date.value`

流程：

1. 查詢該日可用到期月份
2. 更新 `opt-expiry.data`
3. 更新 `opt-expiry.value` 為第一個可用值

輸出：`opt-expiry` 下拉選單內容與預設值

## B. T 字報表更新

輸入：

- `trade-date.value`
- `opt-expiry.value`
- `cp-filter.value`
- `session-filter.value`

流程：

1. 套用日期/到期/月別/交易時段條件
2. 取顯示欄位（價量 + Greeks）
3. 回傳 `rowData`

輸出：`t-table.rowData`

## C. K 線圖更新

輸入：

- `fut-contract.value`
- `fut-expiry.value`

流程：

1. 篩選期貨資料
2. 移除 OHLC 缺值列
3. 建立 candlestick trace

輸出：`kline-graph.figure`

## 3. 資料生命週期

1. 原始資料（CSV/parquet）
2. DataFrame 清洗（日期/數值）
3. callback 條件篩選（子集）
4. 轉換為前端可用結構（`dict records` / `figure`）

## 4. 目前已知流程限制

1. 啟動時一次性載入較大資料可能影響 cold start
2. 目前尚未加入 Payoff callback（Phase 2）
3. 尚未對 callback 延遲做顯式監控

## 5. Phase 2 接入點

新增流程：

1. 使用者勾選 `t-table.selectedRows`
2. callback 計算 $\Pi_{total}(S)$
3. 更新 `payoff-graph.figure`
