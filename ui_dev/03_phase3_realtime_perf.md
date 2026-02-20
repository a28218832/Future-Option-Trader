# Phase 3：即時更新與效能優化

## 目標

在高互動密度下維持低延遲，確保：

- 點選 Leg 到圖更新延遲穩定
- 大量合約列渲染不阻塞
- Greeks 計算不拖慢主流程

## 延遲預算（建議）

- UI 事件到 callback 進入：< 30ms
- payoff 計算：< 80ms
- figure 序列化 + 回傳：< 80ms
- 總體交互：< 200ms

## 優化策略

### 1) 資料層

- 由 CSV 轉 parquet，啟動時預載必要欄位
- 日期/到期月份建立索引（或預先分區）
- 對熱門查詢條件做 LRU 快取

### 2) 計算層（Greeks + Payoff）

- Greeks 預先批次計算並持久化（每日更新）
- 即時計算只做「選取 legs 的 payoff 向量化加總」
- 全程使用 NumPy 向量化，避免 Python for-loop 熱點

### 3) Callback 層

- 將重計算與輕更新分離：
  - `selectedRows` 只觸發 payoff
  - 篩選條件變更才重載 rowData
- 利用 `dcc.Store` 保存已過濾資料，減少重複查詢
- 避免在單一 callback 返回過大 payload

### 4) 前端渲染

- AgGrid 啟用虛擬滾動
- Payoff 線點數控制（如 200~600 點），避免過密
- 圖表 trace 數量限制：預設僅顯示總線，腿線按需開啟

## Greeks 計算建議

- 模型：Black-Scholes（歐式）作為基準
- `T = dT / 365`、波動率使用年化口徑
- 對深度價外、超短天期合約設數值保護（epsilon）
- 缺值策略：
  - 無成交但有報價時可用 mid-price 反推 IV
  - 完全缺報價則保留 NaN，不強行插值

## 監測指標（至少）

- callback p50/p95 延遲
- 每秒 callback 次數
- 前端渲染耗時（觀測）
- 資料快取命中率

## 驗收標準

- 常見操作（切日期、勾腿）p95 < 300ms
- 單頁 1,000+ 列資料可流暢操作
- Greeks 欄位顯示穩定，不因缺值造成崩潰
