# 系統架構設計（System Architecture）

## 1. 目標

建置一套高資訊密度、低互動延遲的交易輔助平台，核心能力：

1. 即時 K 線圖（OHLC）
2. 期權 T 字報表（Greeks）
3. 多 Leg 組合損益連動（Phase 2）

## 2. 技術棧

- 應用框架：Dash
- UI 元件：dash-mantine-components
- 表格引擎：dash-ag-grid
- 圖表引擎：plotly
- 數據處理：pandas + numpy
- 數值計算：scipy（供 Greeks / IV 延伸）

## 3. 邏輯分層

### A. 展示層（Presentation Layer）

- `app.py` 內定義 Layout：篩選器 + K 線圖 + T 字報表
- 只負責顯示與事件綁定，不負責資料清洗

### B. 互動層（Interaction Layer）

- Dash callback 負責「輸入事件 -> 輸出更新」
- 目前三組 callback：
  1. 交易日期 -> 更新可選到期月份
  2. 篩選條件 -> 更新 T 字報表
  3. 期貨契約/到期 -> 更新 K 線

### C. 資料服務層（Data Service Layer）

- `data_service.py` 提供資料讀取、型別清洗、條件篩選函式
- `load_future_data` / `load_option_data` 使用快取避免重複 I/O
- `filter_*` 函式提供 callback 可重用查詢邏輯

### D. 資料層（Data Layer）

- 原始來源：`future_data`、`option_data`
- 目前 `app.py` 可讀取 parquet（使用者已調整）
- 資料服務保留 csv 路徑兼容能力

## 4. 核心資料流

### 啟動階段

1. 載入期貨與選擇權資料
2. 正規化欄位（日期、數值）
3. 推導預設篩選值
4. 建立初始 K 線與空表格

### 互動階段

1. 使用者調整篩選器
2. callback 觸發對應 `filter_*` 函式
3. 以新的 rowData/figure 回填元件

## 5. 擴充邊界（Phase 2+）

- 新增 `payoff_service.py`：專責計算單腿與組合收益
- 新增 callback：`selectedRows -> payoff figure`
- 保持原有資料清洗與篩選層不變，降低改動風險

## 6. 設計原則

1. 先保證資料一致性，再追求視覺豐富度
2. 回呼應單一責任，避免超大型 callback
3. 計算採向量化，降低 Python loop 延遲
4. 使用欄位契約避免前後端語意漂移
