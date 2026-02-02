# Future-Option-Trader
一個專注於期權交易的系統，包含回測以及券商API串接

---



> > 根據目前提供的程式碼與需求，我觀察到您的 `get_greeks` 是針對「單一日期」進行計算的。若直接對 20 年的資料逐日計算 Greeks 可能會非常耗時。此外，資料中包含「一般」與「盤後」交易時段，且欄位格式（如千分位逗號）需要全域清洗。
> > 我預設回測邏輯為：**「只在換倉日進行動作」**。即：在上個月的換倉日平倉舊部位、並同時建立下個月的新部位（Bear Call Spread）。中間持有期間不進行停損或停利（因為需求未提及），直到下個換倉日才結算。
> 
> 

以下為您規劃的 Bear Call Spread 策略回測技術文檔。

---

# 🐻 Bear Call Spread 策略回測技術規格書

## 1. 系統概述 (System Overview)

本系統旨在回測台指選擇權 (TXO) 的「空頭價差策略 (Bear Call Spread)」。系統將依據設定的 Delta 值選取賣方履約價，並依據固定點數寬度選取買方保護履約價。回測將模擬每月換倉邏輯，計算長期累積損益與交易明細。

### 核心策略參數 (Parameters)

| 參數名稱 | 變數名稱 | 預設值 | 說明 |
| --- | --- | --- | --- |
| 起始日期 | `START_DATE` | '2001-12-24' | 回測開始的時間點 |
| 目標 Delta | `TARGET_DELTA` | 0.2 | 賣方 (Short Call) 尋找最接近此 Delta 的履約價 |
| 價差寬度 | `FIX_WIDTH` | 200 | 買方 (Long Call) 履約價 = Short Strike + Width |
| 換倉偏移天數 | `ROLLOVER_OFFSET` | 3 | 契約到期日前 N 個交易日進行換倉 |
| 無風險利率 | `RISK_FREE_RATE` | 0.01 | 用於計算 BS Model 與 Greeks |
| 合約乘數 | `MULTIPLIER` | 50 | 台指選擇權每一點的價值 |

---

## 2. 資料結構定義 (Data Structures)

### 2.1 交易紀錄 (pnl_history)

`pnl_history` 將作為主要輸出結果，格式為 List of Dictionaries 或 DataFrame，每一列代表一次完整的「月合約操作損益」。

| 欄位名稱 | 類型 | 說明 |
| --- | --- | --- |
| `trade_id` | int | 交易序號 |
| `entry_date` | datetime | 進場日期 (即上個月的換倉日) |
| `exit_date` | datetime | 出場日期 (即當月的換倉日) |
| `contract_month` | str | 交易的合約月份 (e.g., '202206') |
| `short_strike` | int | 賣出買權 (Sell Call) 的履約價 |
| `long_strike` | int | 買進買權 (Buy Call) 的履約價 |
| `short_entry_price` | float | 進場時 Short Call 價格 |
| `long_entry_price` | float | 進場時 Long Call 價格 |
| `short_exit_price` | float | 出場時 Short Call 價格 |
| `long_exit_price` | float | 出場時 Long Call 價格 |
| `entry_delta` | float | 進場時 Short Call 的實際 Delta |
| `pnl_points` | float | 損益點數 = (建倉價差收點 - 平倉價差付點) |
| `pnl_amount` | float | 實際損益金額 = pnl_points * MULTIPLIER |
| `balance` | float | 策略累積權益數 |

---

## 3. 功能模組設計 (Function Modules)

為了達成回測目標，除了既有的 `get_greeks`、`weekday_count` 等工具外，需要新增以下功能函式：

### 3.1 資料前處理模組

**目標**：確保全域資料格式統一，過濾掉不必要的盤後資料，並建立日期索引。

#### `preprocess_option_data(df_opt)`

* **功能**：清洗選擇權資料，移除逗號，轉換數值型別，過濾非一般交易時段。
* **輸入**：原始 `df_opt` (DataFrame)。
* **輸出**：清洗後的 `df_opt` (DataFrame)。
* **邏輯**：
1. 篩選 `交易時段 == '一般'`。
2. 將 `收盤價`, `履約價` 等欄位去除 ',' 並轉為 float/int。
3. 將 `交易日期` 轉為 datetime 物件。
4. 排序資料。



#### `get_all_settlement_months(df_fut, start_date)`

* **功能**：從期貨資料中找出所有需要交易的「合約月份」列表。
* **輸入**：`df_fut`, `start_date`。
* **輸出**：List (如 `['200201', '200202', ...]`)。
* **邏輯**：從 `start_date` 開始，找出期貨資料中存在的所有近月合約代碼。

---

### 3.2 訊號與選股模組 (Signal & Selection)

**目標**：根據策略參數挑選具體的履約價。

#### `identify_rollover_date(year, month, offset, trading_calendar)`

* **功能**：計算指定合約月份的「換倉日」。
* **輸入**：年份, 月份, `ROLLOVER_OFFSET`, 交易日曆 (從資料中提取的日期列表)。
* **輸出**：`Target Date` (datetime)。
* **邏輯**：
1. 利用現有的 `weekday_count` 算出該月結算日 (第三個週三)。
2. 在交易日曆中，往前推算 `offset` 個交易日 (排除非交易日)。



#### `select_strategy_legs(df_opt_daily, target_delta, width, risk_free_rate, future_price)`

* **功能**：在特定日期，挑選 Bear Call Spread 的兩隻腳。
* **輸入**：
* `df_opt_daily`: 當日的選擇權資料 (需包含 Call)。
* `target_delta`: 目標 Delta (e.g., 0.2)。
* `width`: 價差寬度 (e.g., 200)。
* `future_price`: 當時期貨價格 (用於 Greeks 計算)。


* **輸出**：Dictionary `{'short_k': ..., 'long_k': ..., 'short_price': ..., 'long_price': ..., 'actual_delta': ...}`
* **邏輯**：
1. 呼叫 `get_greeks` 計算當日所有 Call 的 Delta。
2. **Short Leg**: 找到 `abs(Delta - target_delta)` 最小的履約價 ()。
3. **Long Leg**: 計算 。
4. 搜尋  的價格，若無精確履約價，則找最接近的。
5. 回傳兩者的價格與履約價。



---

### 3.3 回測執行模組 (Execution & PnL)

**目標**：串接時間軸，計算損益。

#### `calculate_period_pnl(entry_info, exit_info)`

* **功能**：計算單次交易的損益。
* **輸入**：
* `entry_info`: 進場時的部位資訊 (價格、履約價)。
* `exit_info`: 出場時的部位資訊 (價格)。


* **輸出**：損益點數 (float)。
* **邏輯**：
* **Credit Received (進場收權利金)** = 
* **Cost to Close (出場付權利金)** = 
* **PnL** = Credit Received - Cost to Close
* *註：Bear Call Spread 進場是 Credit Strategy，希望價差縮小。*



#### `run_backtest(df_opt, df_fut, params)`

* **功能**：主控制迴圈。
* **輸入**：原始資料表, 參數字典。
* **輸出**：`pnl_history` (List of dicts), `equity_curve` (DataFrame)。
* **邏輯流程**：
1. **Init**: 呼叫 `preprocess_option_data`。
2. **Calendar**: 建立交易日曆與合約月份列表。
3. **Loop**: 遍歷每一個合約月份 。
* **決定日期**:
* 本次進場日 () = 上個月 () 的換倉日。
* 本次出場日 () = 本月 () 的換倉日。


* **進場 (Open Position)**:
* 在 ，針對合約 ，呼叫 `select_strategy_legs` 取得  及進場價。


* **出場 (Close Position)**:
* 在 ，針對合約 ，查詢  的收盤價。


* **記錄**:
* 呼叫 `calculate_period_pnl`。
* 將結果存入 `pnl_history`。




4. **Finalize**: 將 `pnl_history` 轉為 DataFrame 並計算累積損益。



---

## 4. 技術注意事項 (Technical Constraints)

1. **Greeks 計算效能**：
* 由於 `get_greeks` 包含數值解法 (Implied Volatility)，在迴圈中對整個 DataFrame 運算極慢。
* **優化方案**：在 `select_strategy_legs` 中，只針對當天、特定到期月的 Call 進行 Greeks 計算，而非全歷史資料。


2. **資料缺失處理**：
* 若換倉日當天某個履約價無成交 (Volume=0 或 Price=NaN)，應優先使用「結算價」，若無結算價則使用「最後最佳買賣價平均」，若仍無則標記為異常交易或以前一日價格填充。


3. **合約月份代碼匹配**：
* 需小心處理台指選的週選 (e.g., '202205W1') 與月選 ('202205')。策略指定為「月選」，需明確過濾掉含有 'W' 的合約代碼。



---

## 5. 下一步建議 (Next Steps)

這份文檔確認後，我將開始撰寫程式碼。實作順序如下：

1. 實作 `preprocess_data` 與 `get_rollover_dates` 確保時間軸正確。
2. 優化 `get_greeks` 的呼叫方式以適配單日篩選。
3. 組合主迴圈 `run_backtest` 產出 `pnl_history`。





















