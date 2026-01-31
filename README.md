# Future-Option-Trader

一個專注於期權交易的系統，包含回測以及券商API串接

## 📋 目錄

- [系統概述](#系統概述)
- [系統架構](#系統架構)
- [核心組件](#核心組件)
  - [數據獲取](#數據獲取)
  - [策略定義](#策略定義)
  - [回測引擎](#回測引擎)
  - [實盤執行](#實盤執行)
  - [報表與監控](#報表與監控)
- [安裝說明](#安裝說明)
- [使用方法](#使用方法)
- [系統流程](#系統流程)
- [開發計劃](#開發計劃)

## 系統概述

Future-Option-Trader 是一個完整的期權交易系統，旨在提供從策略開發、回測驗證到實盤交易的全流程解決方案。系統支援多種數據源、靈活的策略框架，以及完整的風險管理和報表功能。

### 主要功能

- 📊 **多源數據整合**：支援API與本地數據，靈活切換
- 🧪 **回測框架**：完整的歷史數據回測，包含交易成本計算
- 🤖 **策略擴展**：基於抽象類的策略模板，易於開發新策略
- 🚀 **實盤交易**：與券商API無縫對接，自動下單執行
- 📈 **績效分析**：豐富的統計指標與視覺化報表
- 📱 **即時通知**：透過Line Bot即時推送交易通知與帳戶狀態

## 系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                      數據層 (Data Layer)                      │
├─────────────────────────────────────────────────────────────┤
│  APIDataLoader          │         LocalDataLoader            │
│  - api_token            │         - data_folder              │
│  - timeout              │                                    │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
               ▼                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    策略層 (Strategy Layer)                    │
├─────────────────────────────────────────────────────────────┤
│                  Strategy (Abstract Class)                   │
│                  - strategy_name                             │
│                  - orders                                    │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────┐   ┌──────────────────────────────┐
│   回測層 (BackTest)       │   │   執行層 (Execution)          │
├──────────────────────────┤   ├──────────────────────────────┤
│      BackTest            │   │       Executor               │
│   - trader_fund          │   │   - trader_fund              │
│   - fee                  │   │   - fee                      │
│   - tax                  │   │   - tax                      │
│   - equity               │   │   - equity                   │
└──────────┬───────────────┘   └────────────┬─────────────────┘
           │                                │
           ▼                                ▼
┌─────────────────────────────────────────────────────────────┐
│                  報表層 (Reporting Layer)                     │
├─────────────────────────────────────────────────────────────┤
│  Report (Sync)           │      Report (Async)               │
│  - Sharpe Ratio          │      - Leverage Ratio             │
│  - MDD                   │      - Margin                     │
│  - Return                │      - Position                   │
│                          │      - Line Bot Integration       │
└─────────────────────────────────────────────────────────────┘
```

## 核心組件

### 數據獲取

#### APIDataLoader (Class)

從券商或數據提供商API獲取即時或歷史數據。

**職責**：
- 連接API服務，獲取市場數據
- 數據清洗與格式化
- 錯誤處理與重試機制

**關鍵屬性**：
- `api_token` (str): API認證令牌
- `timeout` (int): 請求超時時間（秒）

**主要方法**：
```python
def fetch_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame
def clean_data(raw_data: dict) -> pd.DataFrame
def validate_connection() -> bool
```

#### LocalDataLoader (Class)

從本地文件系統讀取歷史數據，用於回測或離線分析。

**職責**：
- 讀取本地CSV/Parquet等格式數據
- 數據驗證與完整性檢查
- 數據緩存管理

**關鍵屬性**：
- `data_folder` (str): 數據文件夾路徑

**主要方法**：
```python
def load_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame
def list_available_symbols() -> List[str]
def get_data_range(symbol: str) -> Tuple[str, str]
```

### 策略定義

#### Strategy (Abstract Class)

策略邏輯的抽象基類，定義所有交易策略必須實現的接口。

**職責**：
- 定義策略框架與執行流程
- 提供策略參數管理
- 生成交易信號與訂單

**關鍵屬性**：
- `strategy_name` (str): 策略名稱
- `orders` (List[Order]): 待執行訂單列表

**必須實現的方法**：
```python
@abstractmethod
def generate_signals(data: pd.DataFrame) -> pd.DataFrame
    """根據市場數據生成交易信號"""

@abstractmethod
def create_orders(signals: pd.DataFrame) -> List[Order]
    """將交易信號轉換為訂單"""

def on_bar(bar: dict) -> None
    """處理每個K線數據（可選實現）"""

def on_order_filled(order: Order) -> None
    """訂單成交回調（可選實現）"""
```

**使用範例**：
```python
class MovingAverageCrossStrategy(Strategy):
    def __init__(self, short_window=20, long_window=50):
        super().__init__("MA_Cross")
        self.short_window = short_window
        self.long_window = long_window
    
    def generate_signals(self, data):
        data['short_ma'] = data['close'].rolling(self.short_window).mean()
        data['long_ma'] = data['close'].rolling(self.long_window).mean()
        data['signal'] = 0
        data.loc[data['short_ma'] > data['long_ma'], 'signal'] = 1
        data.loc[data['short_ma'] < data['long_ma'], 'signal'] = -1
        return data
    
    def create_orders(self, signals):
        # 實現訂單生成邏輯
        pass
```

### 回測引擎

#### BackTest (Class)

模擬歷史交易，評估策略表現。

**職責**：
- 模擬訂單執行與成交
- 計算交易成本（手續費、稅金）
- 追蹤資金與持倉變化
- 計算績效指標

**關鍵屬性**：
- `trader_fund` (float): 初始資金
- `fee` (float): 手續費率
- `tax` (float): 交易稅率
- `equity` (List[float]): 權益曲線

**主要方法**：
```python
def run(strategy: Strategy, data: pd.DataFrame) -> BackTestResult
def calculate_pnl() -> float
def get_positions() -> Dict[str, Position]
def get_equity_curve() -> pd.Series
```

**回測流程**：
1. 載入歷史數據
2. 逐筆處理市場數據
3. 調用策略生成信號
4. 模擬訂單執行
5. 更新持倉與資金
6. 記錄交易明細
7. 計算績效指標

### 實盤執行

#### Executor (Class)

將策略應用於實盤交易，與券商API交互。

**職責**：
- 與券商API對接，實際下單
- 訂單管理與狀態追蹤
- 持倉與資金同步
- 風險控制與限制

**關鍵屬性**：
- `trader_fund` (float): 帳戶資金
- `fee` (float): 實際手續費率
- `tax` (float): 實際稅率
- `equity` (List[float]): 實時權益記錄

**主要方法**：
```python
def execute_strategy(strategy: Strategy) -> None
def place_order(order: Order) -> OrderResponse
def cancel_order(order_id: str) -> bool
def get_account_info() -> AccountInfo
def sync_positions() -> List[Position]
```

**風險控制**：
- 最大單筆下單金額限制
- 最大持倉比例控制
- 每日最大虧損停損機制
- 槓桿倍數監控

### 報表與監控

#### Report (Module - 同步版)

生成回測報表與視覺化圖表。

**職責**：
- 計算績效統計指標
- 生成權益曲線圖
- 分析交易明細
- 輸出報表文件

**關鍵指標**：
- `Sharpe Ratio`: 夏普比率，衡量風險調整後收益
- `MDD (Maximum Drawdown)`: 最大回撤，衡量最大虧損幅度
- `Return`: 總收益率與年化收益率

**其他指標**：
- 勝率 (Win Rate)
- 平均獲利/虧損比 (Avg Win/Loss Ratio)
- 最大連續盈利/虧損次數
- 月度/年度收益分佈

**主要方法**：
```python
def generate_report(backtest_result: BackTestResult) -> Report
def plot_equity_curve(equity: pd.Series) -> None
def plot_drawdown(equity: pd.Series) -> None
def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float
def calculate_max_drawdown(equity: pd.Series) -> Tuple[float, str, str]
def export_to_html(report: Report, output_path: str) -> None
```

#### Report (Async Module - 異步版)

實時監控帳戶狀態，通過Line Bot與使用者互動。

**職責**：
- 異步查詢帳戶資訊
- 實時推送交易通知
- Line Bot互動介面
- 風險警報通知

**監控指標**：
- `Leverage Ratio`: 槓桿倍數
- `Margin`: 保證金使用率
- `Position`: 當前持倉狀況

**通知事件**：
- 訂單成交通知
- 持倉達到止盈/止損
- 保證金不足警告
- 槓桿過高提醒
- 每日交易摘要

**主要方法**：
```python
async def check_account_status() -> AccountStatus
async def send_line_notification(message: str) -> bool
async def handle_line_command(command: str) -> str
async def monitor_positions() -> None
```

**Line Bot指令**：
- `/status` - 查詢帳戶狀態
- `/positions` - 查看當前持倉
- `/pnl` - 查看損益
- `/orders` - 查看訂單狀態
- `/stop` - 停止策略執行

## 安裝說明

### 環境需求

- Python 3.8+
- pip 或 poetry

### 安裝步驟

```bash
# 克隆專案
git clone https://github.com/a28218832/Future-Option-Trader.git
cd Future-Option-Trader

# 安裝依賴（使用 pip）
pip install -r requirements.txt

# 或使用 poetry
poetry install
```

### 主要依賴

```
pandas>=1.3.0
numpy>=1.21.0
matplotlib>=3.4.0
requests>=2.26.0
aiohttp>=3.8.0
line-bot-sdk>=2.0.0
```

## 使用方法

### 1. 回測範例

```python
from data_loader import LocalDataLoader
from strategy import MovingAverageCrossStrategy
from backtest import BackTest
from report import generate_report

# 載入數據
loader = LocalDataLoader(data_folder="./data")
data = loader.load_data("TX", "2023-01-01", "2023-12-31")

# 初始化策略
strategy = MovingAverageCrossStrategy(short_window=20, long_window=50)

# 執行回測
backtest = BackTest(
    trader_fund=1000000,
    fee=0.0002,
    tax=0.001
)
result = backtest.run(strategy, data)

# 生成報表
report = generate_report(result)
report.plot_equity_curve()
print(f"總收益率: {report.total_return:.2%}")
print(f"夏普比率: {report.sharpe_ratio:.2f}")
print(f"最大回撤: {report.max_drawdown:.2%}")
```

### 2. 實盤交易範例

```python
from data_loader import APIDataLoader
from strategy import YourCustomStrategy
from executor import Executor
import asyncio

# 初始化數據源
api_loader = APIDataLoader(
    api_token="YOUR_API_TOKEN",
    timeout=30
)

# 初始化執行器
executor = Executor(
    api_loader=api_loader,
    trader_fund=1000000,
    fee=0.0002,
    tax=0.001
)

# 初始化策略
strategy = YourCustomStrategy()

# 執行策略（同步方式）
executor.execute_strategy(strategy)

# 或使用異步監控
async def main():
    await executor.start_async_trading(strategy)

asyncio.run(main())
```

### 3. Line Bot監控範例

```python
from report_async import LineNotifier
import asyncio

async def monitor():
    notifier = LineNotifier(
        channel_secret="YOUR_CHANNEL_SECRET",
        channel_access_token="YOUR_ACCESS_TOKEN"
    )
    
    # 定期檢查帳戶狀態
    while True:
        status = await notifier.check_account_status()
        
        # 檢查風險指標
        if status.leverage_ratio > 3.0:
            await notifier.send_line_notification(
                f"⚠️ 警告：槓桿倍數過高 {status.leverage_ratio:.2f}x"
            )
        
        if status.margin_usage > 0.8:
            await notifier.send_line_notification(
                f"⚠️ 警告：保證金使用率過高 {status.margin_usage:.1%}"
            )
        
        await asyncio.sleep(300)  # 每5分鐘檢查一次

asyncio.run(monitor())
```

## 系統流程

### 回測流程

```
1. 準備數據
   ↓
2. 定義策略 (繼承 Strategy)
   ↓
3. 配置回測參數 (資金、費率等)
   ↓
4. 執行回測 (BackTest.run)
   ↓
5. 生成報表 (Report)
   ↓
6. 分析結果，優化策略
   ↓
7. 重複步驟 2-6 直到滿意
```

### 實盤交易流程

```
1. 回測驗證策略有效性
   ↓
2. 配置API連接 (APIDataLoader)
   ↓
3. 設置風險參數 (Executor)
   ↓
4. 啟動Line Bot監控 (Report Async)
   ↓
5. 執行策略 (Executor.execute_strategy)
   ↓
6. 即時監控 (檢查持倉、風險指標)
   ↓
7. 接收通知 (Line Bot)
   ↓
8. 定期檢視報表，調整策略
```

## 開發計劃

### Phase 1: 基礎架構 (已完成)
- [x] 專案結構規劃
- [x] README 文檔撰寫

### Phase 2: 數據層開發
- [ ] 實作 LocalDataLoader
- [ ] 實作 APIDataLoader
- [ ] 數據清洗與驗證功能
- [ ] 單元測試

### Phase 3: 策略層開發
- [ ] Strategy 抽象類定義
- [ ] 範例策略實作（移動平均、布林通道等）
- [ ] 策略回測介面
- [ ] 單元測試

### Phase 4: 回測引擎
- [ ] BackTest 核心功能
- [ ] 訂單模擬與成交邏輯
- [ ] 資金與持倉管理
- [ ] 交易成本計算
- [ ] 單元測試

### Phase 5: 報表系統
- [ ] 績效指標計算
- [ ] 視覺化圖表生成
- [ ] HTML報表輸出
- [ ] 單元測試

### Phase 6: 實盤執行
- [ ] Executor 核心功能
- [ ] 券商API對接
- [ ] 訂單管理系統
- [ ] 風險控制機制
- [ ] 整合測試

### Phase 7: 異步監控與通知
- [ ] Line Bot 整合
- [ ] 異步監控系統
- [ ] 即時通知功能
- [ ] 互動指令處理
- [ ] 整合測試

### Phase 8: 優化與部署
- [ ] 性能優化
- [ ] 錯誤處理完善
- [ ] 日誌系統
- [ ] 部署文檔
- [ ] 使用者手冊

## 貢獻指南

歡迎提交 Issue 和 Pull Request！

### 開發規範

- 遵循 PEP 8 代碼風格
- 編寫單元測試
- 更新相關文檔
- Commit message 使用中文或英文

## 授權

MIT License

## 聯絡方式

如有問題或建議，請開 Issue 或聯繫維護者。

---

**注意**：本系統僅供學習與研究使用，實盤交易請謹慎評估風險。
