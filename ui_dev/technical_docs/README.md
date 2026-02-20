# 交易輔助平台技術文檔總索引

更新日期：2026-02-20

本資料夾提供可直接交接、維運、擴充的技術文檔，涵蓋：

- 開發流程（從需求到上線）
- 系統運行流程（啟動、互動、回呼）
- 各模組邏輯與資料契約
- 故障排查與效能調校

## 文件地圖

1. `01_system_architecture.md`：整體架構、元件責任、資料流
2. `02_development_workflow.md`：分階段開發流程與交付標準
3. `03_runtime_sequence.md`：系統啟動與 UI 互動時序
4. `04_module_spec.md`：程式模組規格（函式級）
5. `05_runbook_troubleshooting.md`：執行、部署、排錯與監控

## 目前實作範圍（對應程式）

- 程式入口：`phase1_dash_mvp/app.py`
- 資料服務：`phase1_dash_mvp/services/data_service.py`
- 套件需求：`phase1_dash_mvp/requirements.txt`
- 使用說明：`phase1_dash_mvp/README.md`

## 與產品需求對應

- K 線圖：已完成（Plotly Candlestick + hover）
- T 字報表：已完成（Dash AG Grid + Greeks 欄位）
- Leg 點選連動 Payoff：規劃完成，尚待 Phase 2 實作
