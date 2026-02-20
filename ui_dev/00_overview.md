# 交易輔助平台 UI 開發總覽（Dash 架構）

更新日期：2026-02-20

## 1. 目標與需求對應

本規劃對應三個核心能力：

1. 即時 K 線圖（OHLC Hover、縮放、平移）
2. 期權 T 字報表（Greeks + 合約選擇）
3. 點選多個 Leg 後，即時更新收益曲線（Payoff Curve）

## 2. 技術選型（建議採用）

- UI / App Framework：`dash` + `dash-mantine-components`
- 高密度表格：`dash-ag-grid`
- 圖表：`plotly`（`go.Candlestick` + `go.Scatter`）
- 數值計算：`numpy` + `scipy`
- 資料層：`pandas` + `pyarrow`（parquet）
- 快取：`flask-caching`（可選：Redis 作為共享快取）

## 3. 為何此組合適合你的場景

- Dash callback 天然支援「多輸入 -> 多輸出」交互，適合交易台工作流。
- `dash-ag-grid` 可做大表格虛擬化渲染、欄位固定、條件格式化，適合 Greeks 高密度數據。
- Plotly 對金融圖表成熟：K 線 + 多 trace 疊加 + 高品質 hover。

## 4. 系統邏輯（高階）

1. 從 `df_opt` / `df_fut` 清理欄位（`-` 轉 NaN、數值型別、日期型別）
2. 先計算或快取 Greeks 欄位（`Delta/Gamma/Theta/Vega`；若需再擴充 `Rho`）
3. 將 `df_fut` 綁定至 K 線圖，`df_opt` 綁定至 T 字報表
4. 使用者在表格選取 Legs 後觸發 callback
5. callback 計算組合收益：

$$
\Pi_{total}(S) = \sum_{i=1}^{n} w_i \cdot \Pi_i(S)
$$

6. 回傳新 Figure 更新 Payoff Curve

## 5. 資料欄位契約（建議）

為了 callback 簡化，建議在 T 字報表資料中補齊：

- `leg_id`: 唯一鍵（日期_到期_履約價_CP_時段）
- `side`: `+1`（買進）/ `-1`（賣出）
- `qty`: 口數（預設 1）
- `premium`: 建議使用進場價格（例如中間價或收盤價）
- `multiplier`: 乘數（台指選擇權常見 50）

## 6. 開發階段總覽

- Phase 1：基礎框架 + K 線 + T 字報表
- Phase 2：Leg 選取連動 + Payoff Curve
- Phase 3：即時資料與效能優化
- Phase 4：測試、部署、監控與風險治理

詳見同資料夾內 `01~04` 文件。
