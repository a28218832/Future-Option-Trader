# Phase 2：Leg 連動與收益曲線

## 目標

完成關鍵互動：在 T 字報表勾選多個 Leg，立即更新下方組合收益曲線。

## 互動流程（核心）

1. 使用者在 AgGrid 勾選多個合約列（selected rows）
2. callback 收到每列的 `leg_id/買賣權/履約價/premium/side/qty/multiplier`
3. 產生標的價格網格 `S_grid`
4. 計算每個 Leg 的到期損益，做加總
5. 更新 `payoff_graph`（同時可顯示各 Leg 與總和）

## 損益計算模型（到期）

設每腿權重為 $w_i = side_i \times qty_i \times multiplier_i$：

- Call：$\Pi_i(S)=w_i\cdot(\max(S-K_i,0)-premium_i)$
- Put：$\Pi_i(S)=w_i\cdot(\max(K_i-S,0)-premium_i)$

總損益：

$$
\Pi_{total}(S)=\sum_{i=1}^{n}\Pi_i(S)
$$

## 實作重點

### 1) 表格列資料補強

每列需具備：

- `leg_id`（唯一）
- `option_type`（C/P）
- `strike`（履約價）
- `premium`（進場權利金）
- `side`（+1/-1）
- `qty`（口數）
- `multiplier`（乘數）

### 2) Callback 設計（建議）

- Inputs：
  - `t_table.selectedRows`
  - `underlying_price`（可選，作為參考線）
  - `s_grid_range`（可選，x 軸區間）
- Outputs：
  - `payoff_graph.figure`
  - `summary_metrics.children`（最大損失/損益平衡點）

### 3) 圖表可視化

- `go.Scatter` 畫總收益線
- 可選：每個 Leg 使用半透明線
- 以虛線標示現價 `S0`
- Hover 顯示 `S` 與 `P/L`

## 驗收標準

- 勾選/取消任一 Leg 後，收益曲線 < 200ms 更新
- Bull Spread、Straddle、Strangle 可正確呈現輪廓
- 0 筆選取時給出清楚空狀態提示

## 常見錯誤

- Call/Put payoff 公式方向寫反
- 權利金符號與 `side` 重複乘負號
- 未乘上契約乘數導致損益量級錯誤
