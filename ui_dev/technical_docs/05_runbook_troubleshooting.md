# 運行手冊與排錯指南（Runbook & Troubleshooting）

## 1. 本機運行流程

## Step 1：安裝相依套件

```bash
pip install -r phase1_dash_mvp/requirements.txt
```

## Step 2：啟動應用

```bash
cd phase1_dash_mvp
python app.py
```

## Step 3：驗證

- 開啟 `http://127.0.0.1:8050`
- 檢查：
  1. K 線圖是否顯示
  2. T 字報表是否有資料
  3. 切換篩選器是否立即更新

## 2. 常見故障與處理

### 問題 A：`python app.py` 直接退出（Exit Code 1）

可能原因：

1. 套件缺失（`dash_ag_grid` / `dash_mantine_components`）
2. 資料路徑不存在（parquet 或 csv）
3. 欄位缺失或名稱不一致

排查順序：

1. 先重裝 requirements
2. 確認資料檔存在且可讀
3. 檢查 `app.py` 中資料路徑與欄位 drop 清單

### 問題 B：表格空白但無錯誤

可能原因：

1. 預設日期下沒有對應到期月份
2. `session-filter` 限制太窄
3. `cp-filter` 無選項

處理：

- 先切換為 `交易時段=全部`
- 檢查 callback 回傳 rowData 長度

### 問題 C：K 線圖空白

可能原因：

1. 期貨契約/到期組合無資料
2. OHLC 欄位被轉為 NaN

處理：

- 切換其他契約/到期
- 檢查 `filter_future_chart` 輸出筆數

## 3. 效能調校手冊

1. 先減少啟動讀檔量（優先 parquet）
2. 避免 callback 中做 I/O
3. 限制表格首屏行數與欄位
4. 優先優化 p95 延遲而非平均值

## 4. 日誌建議（待加）

建議新增：

- 每次 callback 入參摘要
- callback 執行耗時
- 回傳資料筆數
- 異常 traceback 與資料鍵值

## 5. 上線前最小檢查

- [ ] requirements 與實際 import 一致
- [ ] 資料路徑可在部署環境讀取
- [ ] callback 在空資料、缺值資料下不崩潰
- [ ] README 與實際啟動命令一致
