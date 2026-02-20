# Phase 1 Dash MVP

## 功能

- 即時 K 線圖（OHLC hover、縮放）
- 期權 T 字報表（含 Greeks 欄位）
- 基本篩選：交易日期、到期月份、買賣權、交易時段

## 安裝

```bash
pip install -r requirements.txt
```

## 執行

```bash
python app.py
```

啟動後開啟 `http://127.0.0.1:8050`。

## 資料讀取說明

- 期貨來源：`future_data/*_fut.csv`
- 選擇權來源：`option_data/**/*.csv`

預設只讀取最新 24 個選擇權 CSV（避免啟動過慢）。

可透過環境變數調整：

```bash
set OPTION_FILE_LIMIT=120
```

若要全量讀取，設定為 0：

```bash
set OPTION_FILE_LIMIT=0
```
