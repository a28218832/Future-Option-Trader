# Future-Option-Trader
一個專注於期權交易的系統，包含回測以及券商API串接

---



回測邏輯為：**「只在換倉日進行動作」**。即：在上個月的換倉日平倉舊部位、並同時建立下個月的新部位（Bear Call Spread）。中間持有期間不進行停損或停利（因為需求未提及），直到下個換倉日才結算。
逐日回測，這代表架構將轉變為「事件驅動 (Event-Driven)」的形式。這種方式雖然運算較慢，但優點是能精確模擬真實交易情境（每天檢查訊號、計算每日市值變化），且非常適合未來擴充（例如加入停損、動態調整倉位）。
> 
> > 1. **資料清洗**：新增過濾期貨價差單（含 `/` 符號）的步驟。
> > 2. **核心驅動**：廢除原本的「跳躍式」迴圈，改為 `market_stream_generator`。
> > 3. **狀態管理**：因為是逐日讀取，策略函式需要一個「狀態機 (State Machine)」來記憶目前手上的部位。
> > 
> > 
> 
> 

以下是修訂後的技術規格書：

---

# Bear Call Spread 策略回測技術規格書 (v2.0 - Generator 版)

## 1. 系統架構變更 (Architecture Shift)

原先架構是「鎖定特定日期 -> 計算 -> 跳至下個特定日期」。
新架構將分為三個層次：

1. **Data Layer (Generator)**: 負責清洗資料、逐日計算 Greeks、拋出當日市場快照 (Snapshot)。
2. **Strategy Layer (Consumer)**: 接收快照，判斷是否為換倉日，決定是否交易。
3. **State Layer (Portfolio)**: 記錄當前持倉狀態、計算已實現損益。

---

## 2. 新增與修改的功能模組

### 2.1 資料前處理模組 (Data Cleaning)

需修改 `get_now_price` 並增加期貨清洗邏輯，確保不抓到價差單。

#### `clean_futures_data(df_fut)` **(New)**

* **目標**：移除期貨資料中的價差組合單（Spread Orders）。
* **輸入**：原始 `df_fut`。
* **輸出**：乾淨的 `df_fut`。
* **邏輯**：
1. 移除 `到期月份(週別)` 欄位中包含 `/` 字元的資料列 (例如 "202205/202206")。
2. 移除 `契約` 欄位中包含 `/` 字元的資料列 (雙重確認)。
3. 確保 `交易日期` 為 datetime 格式並排序。



#### `get_target_contract_price(df_fut_clean, date, contract_month)` **(Refined)**

* **目標**：取得特定日期、特定合約月份的期貨開盤/收盤價 (用於計算 Greeks 的 Underlying S)。
* **輸入**：清洗後的期貨資料, 日期, 目標合約月份 (e.g., '202205')。
* **輸出**：價格 (float)。
* **注意**：若該遠月合約當日無成交，需有 fallback 機制 (抓當日近月價格調整或抓結算價)。

---

### 2.2 市場資料生成器 (The Generator)

這是本次修改的核心。此 Generator 會「懶惰執行 (Lazy Execution)」，只有在迴圈跑到那一天時才計算那天的 Greeks。

#### `market_data_generator(start_date, end_date, df_opt, df_fut, risk_free_rate)`

* **目標**：按交易日序，逐日回傳當天的完整市場資訊。
* **輸入**：回測區間、原始資料表、利率參數。
* **輸出 (Yield)**：Tuple `(current_date, future_price, call_df_daily, put_df_daily)`。
* **邏輯流程**：
1. **Init**: 呼叫 `clean_futures_data`。
2. **Timeline**: 找出 `df_fut` 與 `df_opt` 交集的「所有唯一交易日」列表，範圍限制在 `start_date` 到 `end_date`。
3. **Loop**: 遍歷每一個 `trade_date`：
* **Get Future Price (S)**: 取得當日「台指期近月」開盤價或收盤價 (作為 Greeks 計算基準)。若當日無期貨價格，跳過該日 (yield None or continue)。
* **Filter Option**: 篩選出 `df_opt` 中 `交易日期 == trade_date` 的資料。
* **Calc Greeks**: 呼叫既有的 `get_greeks(df_opt_daily, trade_date, S, risk_free_rate)`。
* *註：這一步最耗時，但能確保策略端拿到的是有 Delta 的資料。*


* **Yield**: `yield trade_date, S, call_df_with_greeks, put_df_with_greeks`。





---

### 2.3 策略邏輯與狀態管理 (Strategy Consumer)

因為改成逐日接收資料，我們需要一個變數來記住「我現在什麼時候要換倉？」以及「我現在手上有沒有單？」。

#### 輔助函式：`get_rollover_info(current_date, contract_list)`

* **目標**：判斷 `current_date` 是否為某個合約的換倉日。
* **邏輯**：
* 輸入當前日期，檢查它是否為「近月合約」的「倒數第 N 個交易日」。
* 這需要預先建立一個 `TradingCalendar` (交易日曆表)，才能反推倒數日。
* 回傳：`(is_rollover_day: bool, target_contract_to_close: str, target_contract_to_open: str)`。
* *例如：如果是 5月的倒數第三天，回傳 (True, '202205', '202206')。*



#### `run_backtest_generator(generator, params)`

* **目標**：主程式，消耗 generator 並執行交易。
* **變數 (State)**：
* `current_position`: Dict (紀錄目前持有的 Short Call & Long Call 資訊，若無則為 None)。
* `pnl_history`: List (交易紀錄)。


* **邏輯流程**：
1. 建立 `calendar` (所有交易日列表)，用於判斷換倉日。
2. **For** `date, S, calls, puts` **in** `generator`:
* 若資料為 None，continue。
* **Check Rollover**: 呼叫 `get_rollover_info(date)`。
* **情境 A：是換倉日 (Rollover Day)**
1. **平倉 (Close)**: 若 `current_position` 不為空：
* 從 `calls` 中找到持有履約價的現在價格。
* 計算損益，寫入 `pnl_history`。
* 清空 `current_position`。


2. **建倉 (Open)**:
* 目標合約 = `target_contract_to_open` (下個月)。
* 篩選 `calls` 中 `到期月份 == 目標合約` 的資料。
* 依據 `TARGET_DELTA` 尋找 Short Leg。
* 依據 `FIX_WIDTH` 尋找 Long Leg。
* 記錄進場價格與履約價，更新 `current_position`。




* **情境 B：非換倉日**
* (可選) 更新每日市值 (Mark-to-Market) 至權益曲線。
* 目前僅需 pass，等待下一次換倉訊號。







---

## 3. 修改後的資料結構 (Data Structures)

### 3.1 Yield 的資料格式

Generator 每天吐出的資料：

```python
(
    pd.Timestamp('2022-01-05'),  # Date
    18200.0,                     # Underlying Future Price (S)
    pd.DataFrame(...),           # Call DF (含 Greeks)
    pd.DataFrame(...)            # Put DF (含 Greeks)
)

```

### 3.2 持倉狀態 (Current Position State)

在 Loop 內維護的字典：

```python
current_position = {
    "contract_month": "202206",
    "short_strike": 18500,
    "long_strike": 18700,
    "entry_price_short": 150.0,
    "entry_price_long": 20.0,
    "entry_date": pd.Timestamp('2022-05-18')
}

```

---

## 4. 總結開發步驟 (Development Roadmap)

1. **Data Cleaning**: 優先實作 `clean_futures_data`，這是基礎。
2. **Calendar Utils**: 實作「判斷某天是否為倒數第 N 個交易日」的邏輯，這需要先掃描一次所有日期建立索引。
3. **Generator**: 實作 `market_data_generator`，並確認它能正確呼叫 `get_greeks` 且效能可接受（每秒可能只能跑幾天，取決於您的電腦與資料量）。
4. **Loop & Trade**: 撰寫 `run_backtest_generator` 迴圈邏輯。

這樣改動後，您的程式碼結構會更清晰，且未來要加入「停損監控 (每分鐘/每日)」時，只需要在 **情境 B** 裡面加入判斷邏輯即可，擴充性極佳。



















