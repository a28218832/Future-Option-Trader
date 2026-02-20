# 模組邏輯規格（Module Specification）

## 1. `app.py`

### 1.1 模組責任

- 組裝 UI Layout
- 註冊 callback
- 啟動 Dash app

### 1.2 主要區塊

1. **資料初始化區塊**
   - 載入 `df_fut`、`df_opt`
   - 準備預設篩選值

2. **圖表建構區塊**
   - `create_candlestick_figure(contract, expiry)`
   - 將 DataFrame 轉成 Plotly figure

3. **表格欄位區塊**
   - `get_column_defs()`
   - 定義 T 字報表欄位、寬度、型別

4. **UI 版面區塊**
   - 篩選器 + `dcc.Graph` + `AgGrid`

5. **callback 區塊**
   - `refresh_option_expiry`
   - `refresh_option_table`
   - `refresh_kline`

### 1.3 輸入/輸出契約

- K 線 callback：
  - Input：`contract`, `expiry`
  - Output：Plotly figure

- T 字 callback：
  - Input：日期、到期、買賣權、時段
  - Output：`list[dict]` rowData

## 2. `services/data_service.py`

### 2.1 模組責任

- 資料載入（CSV）
- 欄位正規化（缺值、型別）
- 提供可重用篩選函式

### 2.2 函式規格

#### `_to_numeric(series)`

- 目的：將 `-` 及無效值轉為 NaN，回傳數值 Series

#### `_ensure_columns(df, required_columns)`

- 目的：補齊缺少欄位，避免 schema 不一致

#### `load_future_data()`

- 來源：`future_data/*_fut.csv`
- 處理：欄位補齊、日期轉換、數值轉換、排序
- 快取：`@lru_cache(maxsize=1)`

#### `load_option_data()`

- 來源：`option_data/**/*.csv`
- 特色：可由 `OPTION_FILE_LIMIT` 限制讀取筆數
- 處理：欄位補齊、日期轉換、Greeks 數值化、排序

#### `get_option_filter_values(df_opt)`

- 產出：日期清單、買賣權清單、交易時段清單

#### `get_future_filter_values(df_fut)`

- 產出：契約清單、到期清單

#### `get_expiries_by_date(df_opt, trade_date)`

- 產出：指定交易日期的可用到期月份

#### `filter_option_table(...)`

- 目的：依條件生成 T 字報表子集
- 回傳：含 Greeks 的顯示欄位 DataFrame

#### `filter_future_chart(df_fut, contract, expiry)`

- 目的：依條件生成 K 線資料集
- 回傳：可直接餵給 candlestick 的 DataFrame

## 3. Phase 2 建議新增模組

### `services/payoff_service.py`

建議函式：

- `build_price_grid(s0, min_ratio, max_ratio, points)`
- `payoff_call(S, K, premium, side, qty, multiplier)`
- `payoff_put(S, K, premium, side, qty, multiplier)`
- `payoff_portfolio(S, legs)`
- `break_even_points(S, pnl)`

## 4. 非功能性需求對應

1. 可維護性：模組責任單一
2. 可擴充性：callback 與 service 解耦
3. 可觀測性：建議新增 callback 延遲日志
