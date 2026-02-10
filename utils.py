import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional



import pandas as pd
import numpy as np

def clean_numeric_col(series):
    """
    輔助函式：清洗含有逗號的數字字串，並處理 '-' 為 NaN
    """
    return pd.to_numeric(
        series.astype(str).str.replace(',', '').str.strip().replace('-', np.nan), 
        errors='coerce'
    )

def clean_futures_data(df_raw):
    """
    清洗期貨資料
    1. 轉換日期格式
    2. 排除價差單 (含有 '/' 的合約)
    3. 轉換價格欄位為浮點數
    """
    print("--- 開始清洗期貨資料 (Futures) ---")
    df = df_raw.copy()
    
    # 1. 日期標準化
    df['交易日期'] = pd.to_datetime(df['交易日期'])
    
    # 2. 排除價差單 (Spread Orders)
    # 檢查 '到期月份(週別)' 和 '契約' 是否含有 '/'
    mask_spread_month = df['到期月份(週別)'].astype(str).str.contains('/')
    mask_spread_contract = df['契約'].astype(str).str.contains('/')
    
    before_len = len(df)
    df = df[~(mask_spread_month | mask_spread_contract)]
    after_len = len(df)
    print(f">> 已排除價差單: {before_len - after_len} 筆")

    # 3. 數值欄位清洗 (去除逗號, 轉 float)
    target_cols = ['開盤價', '最高價', '最低價', '收盤價', '結算價']
    for col in target_cols:
        if col in df.columns:
            df[col] = clean_numeric_col(df[col])
            
    # 4. 排序與重設索引
    df.sort_values(by=['交易日期', '契約', '到期月份(週別)'], inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    print(f">> 期貨資料清洗完成，共 {len(df)} 筆。")
    return df

def clean_options_data(df_raw):
    """
    清洗選擇權資料
    1. 過濾非一般交易時段
    2. 轉換日期與履約價格式
    3. 轉換價格欄位
    """
    print("--- 開始清洗選擇權資料 (Options) ---")
    df = df_raw.copy()
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].astype(str).str.strip()
    
    # 1. 過濾交易時段 (只留 '一般')
    if '交易時段' in df.columns:
        before_len = len(df)
        df = df[df['交易時段'] == '一般']
        print(f">> 已過濾盤後資料: {before_len - len(df)} 筆")
    
    # 2. 日期標準化
    df['交易日期'] = pd.to_datetime(df['交易日期'])
    
    # 3. 履約價轉數值 (重要：用於排序與查找)
    df['履約價'] = clean_numeric_col(df['履約價'])
    
    # 4. 價格欄位清洗
    target_cols = ['開盤價', '最高價', '最低價', '收盤價', '結算價']
    for col in target_cols:
        if col in df.columns:
            df[col] = clean_numeric_col(df[col])
            
    # 5. 確保到期月份格式乾淨 (去除空格)
    df['到期月份(週別)'] = df['到期月份(週別)'].astype(str).str.strip()

    # 6. 排序
    # 注意：履約價排序對於尋找價差組合(Spread)很重要
    df.sort_values(by=['交易日期', '到期月份(週別)', '履約價'], inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    print(f">> 選擇權資料清洗完成，共 {len(df)} 筆。")
    return df





# --- 資料結構定義 ---
class Leg:
    def __init__(self, side: str, strike: float, opt_type: str):
        self.side = side        # 'buy' or 'sell'
        self.strike = strike
        self.opt_type = opt_type # 'call' or 'put'

    def __repr__(self):
        return f"{self.side.upper()} {self.opt_type.upper()} @ {self.strike}"

class TradeSignal:
    def __init__(self, action: str, contract: str, legs: List[Leg], reason: str, quantity: int = 1):
        self.action = action    # 'OPEN' or 'CLOSE'
        self.contract = contract
        self.legs = legs
        self.reason = reason
        self.quantity = quantity # [新增] 明確指定口數

class BaseStrategy(ABC):
    @abstractmethod
    def on_bar(self, context, market_data) -> List[TradeSignal]:
        pass
    @abstractmethod
    def on_rollover(self, context, market_data, rollover_info) -> List[TradeSignal]:
        pass

# --- 輔助函式 ---
def get_rollover_info(date, rollover_map):
    """從 map 取得換倉資訊，確保回傳 3 個值"""
    if date in rollover_map:
        info = rollover_map[date]
        return True, info['close'], info['open']
    else:
        return False, None, None


import pandas as pd
import numpy as np


from datetime import datetime, timedelta
def weekday_count(y,m,weekday="Wed",count=3):
    weekday_map = {"Mon":0, "Tue":1, "Wed":2, "Thu":3, "Fri":4, "Sat":5, "Sun":6}
    target_weekday = weekday_map.get(weekday, 2)  # Default to Wednesday if not found
    first_day = datetime(y, m, 1)
    weekday_count = 0
    temp = first_day
    while weekday_count < count:
        if temp.weekday() == target_weekday:
            weekday_count += 1
        if weekday_count < count:
            temp += timedelta(days=1)
    return temp
    
def get_expiry_date(contract_str):
    try:
        s = str(contract_str).split('.')[0].strip()

        y = int(s[:4])
        m = int(s[4:6])
        if len(s) > 6: 
            weekSymbol = s[6]
            count = int(s[7])
            if weekSymbol in ['W','w']:
                return weekday_count(y, m, "Wed", count)
            elif weekSymbol in ['F','f']:
                return weekday_count(y, m, "Fri", count)
            else:
                return pd.NaT
        return weekday_count(y, m, "Wed", 3)
    except:
        return pd.NaT
import numpy as np
import pandas as pd
import py_lets_be_rational as lj

def get_greeks(df_opt, nowDate, S, R):
    now_df = df_opt[df_opt['交易日期'] == nowDate]
    call_df = now_df[now_df['買賣權']=='買權']
    put_df  = now_df[now_df['買賣權']=='賣權']
    
    
    """
    1. 先計算 Implied Volatility (IV)
    2. 再使用 IV 計算 Greeks
    """
    # 避免 SettingWithCopyWarning
    call_df = call_df.copy()
    put_df = put_df.copy()

    # ==========================================
    # 1. 時間前處理 (T & dT)
    # ==========================================
    # 假設 get_expiry_date 函式已定義
    call_df['T'] = call_df['到期月份(週別)'].apply(get_expiry_date)
    put_df['T'] = put_df['到期月份(週別)'].apply(get_expiry_date)

    # 計算年化剩餘時間，並設定極小值避免除以零
    call_df['dT'] = ((call_df['T'] - call_df['交易日期']).dt.days / 365.0).clip(lower=1e-5)
    put_df['dT'] = ((put_df['T'] - put_df['交易日期']).dt.days / 365.0).clip(lower=1e-5)

    # ==========================================
    # 2. 定義 IV 計算函式
    # ==========================================
    def calculate_iv(row, option_type_flag):
        """
        option_type_flag: 1.0 for Call, -1.0 for Put
        """
        price = row['收盤價']
        K = row['履約價']
        T = row['dT']
        
        # 簡易檢查：價格異常或時間歸零直接回傳 0
        if price <= 0 or T <= 0:
            return 0.0

        # 計算遠期價格 F = S * exp(R*T)
        F = S * np.exp(R * T)

        # 檢查內含價值 (Intrinsic Value) 防止套利違規導致錯誤
        intrinsic = max(0, F - K) if option_type_flag == 1 else max(0, K - F)
        if price <= intrinsic:
            return 0.0  # 價格低於內含價值，理論上 IV 為 0 或無解

        try:
            # 使用 py_lets_be_rational 反推 IV
            # 參數順序: price, F, K, T, q
            iv = lj.implied_volatility_from_a_transformed_rational_guess(
                price, F, K, T, option_type_flag
            )
            return iv
        except:
            return 0.0

    # ==========================================
    # 3. 執行 IV 計算
    # ==========================================
    # Call: q = 1.0
    call_df['Implied_Volatility'] = call_df.apply(lambda row: calculate_iv(row, 1.0), axis=1)
    
    # Put: q = -1.0
    put_df['Implied_Volatility'] = put_df.apply(lambda row: calculate_iv(row, -1.0), axis=1)

    # ==========================================
    # 4. 定義 Greeks 計算函式 (Black-Scholes)
    # ==========================================
    def calculate_bs_greeks(row, option_type_str):
        K = row['履約價']
        T = row['dT']
        sigma = row['Implied_Volatility']
        
        if sigma <= 0 or T <= 0:
            return 0.0, 0.0, 0.0, 0.0, 0.0
            
        sqrt_T = np.sqrt(T)
        d1 = (np.log(S / K) + (R + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T

        # 使用 lj.norm_cdf
        nd1 = lj.norm_cdf(d1)
        nd2 = lj.norm_cdf(d2)
        n_prime_d1 = (1.0 / np.sqrt(2 * np.pi)) * np.exp(-0.5 * d1 ** 2)

        # Delta, Itm Probability
        if option_type_str == 'call':
            delta = nd1
            itm_prob = nd2
        else:
            delta = nd1 - 1.0
            itm_prob = 1.0 - nd2
        # Gamma
        gamma = n_prime_d1 / (S * sigma * sqrt_T)

        # Vega
        vega = S * sqrt_T * n_prime_d1

        # Theta
        theta_common = -(S * sigma * n_prime_d1) / (2 * sqrt_T)
        if option_type_str == 'call':
            theta = theta_common - R * K * np.exp(-R * T) * nd2
        else:
            n_neg_d2 = 1.0 - nd2
            theta = theta_common + R * K * np.exp(-R * T) * n_neg_d2
            
        return delta, gamma, theta, vega, itm_prob

    # ==========================================
    # 5. 執行 Greeks 計算
    # ==========================================
    # Call Greeks
    greeks_call = call_df.apply(lambda row: calculate_bs_greeks(row, 'call'), axis=1, result_type='expand')
    call_df[['Delta', 'Gamma', 'Theta', 'Vega', 'Itm_Prob']] = greeks_call

    # Put Greeks
    greeks_put = put_df.apply(lambda row: calculate_bs_greeks(row, 'put'), axis=1, result_type='expand')
    put_df[['Delta', 'Gamma', 'Theta', 'Vega', 'Itm_Prob']] = greeks_put
    
    return call_df, put_df


def market_data_generator(start_date, end_date, df_opt, df_fut, risk_free_rate=0.01):
    """
    逐日生成市場資料生成器 (Generator)
    
    Yields:
        tuple: (current_date, S, call_df, put_df)
        
        - current_date (pd.Timestamp): 當前交易日
        - S (float): 當日標的價格 (使用近月期貨價格)
        - call_df (pd.DataFrame): 當日 Call 資料表 (含 Greeks)
        - put_df (pd.DataFrame): 當日 Put 資料表 (含 Greeks)
    """
    
    print(f"--- 初始化市場資料生成器 ({start_date} to {end_date}) ---")
    
    # 1. 建立交易日曆 (只取期貨有資料的日子，並限制在回測區間內)
    # 確保 index 重設，方便後續操作
    all_dates = df_fut['交易日期'].unique()
    # all_dates = pd.to_datetime(all_dates).sort_values()
    all_dates = all_dates[pd.to_datetime(all_dates).argsort()]
    # all_dates = pd.DataFrame(all_dates).sort_values(by=0)[0]
    
    mask_date = (all_dates >= pd.to_datetime(start_date)) & (all_dates <= pd.to_datetime(end_date))
    trade_dates = all_dates[mask_date]
    
    print(f">> 預計執行交易日數: {len(trade_dates)} 天")

    # 2. 逐日迴圈
    for current_date in trade_dates:
        
        # ==========================================
        # A. 取得當日標的價格 S (Near Month Future)
        # ==========================================
        # 篩選當日期貨資料
        daily_fut = df_fut[df_fut['交易日期'] == current_date]
        
        if daily_fut.empty:
            continue
            
        # 找出「近月合約」：排序「到期月份」，取第一筆
        # 假設資料已清洗過，無價差單，且格式正確
        daily_fut_sorted = daily_fut.sort_values(by='到期月份(週別)')
        
        # 取最近月合約
        near_month_row = daily_fut_sorted.iloc[0]
        
        # 決定價格 (Open > Close > Settlement)
        S = near_month_row['開盤價']
        if pd.isna(S) or S <= 0:
            S = near_month_row['收盤價']
        if pd.isna(S) or S <= 0:
            S = near_month_row['結算價']
            
        # 若仍無價格，跳過該日
        if pd.isna(S) or S <= 0:
            # print(f"Warning: {current_date.date()} 查無有效標的價格 S，跳過。")
            continue

        # ==========================================
        # B. 準備當日選擇權資料
        # ==========================================
        # 為了效能，先從大表切出當日資料
        daily_opt = df_opt[df_opt['交易日期'] == current_date]
        
        if daily_opt.empty:
            continue

        # ==========================================
        # C. 計算 Greeks
        # ==========================================
        # 呼叫您提供的 get_greeks 函式
        # 注意：get_greeks 會回傳 (call_df, put_df)
        try:
            # 這裡傳入 daily_opt，get_greeks 內部會再 filter 一次 date，這沒問題
            call_greeks, put_greeks = get_greeks(daily_opt, current_date, S, risk_free_rate)
            
            # 簡單防呆：確保回傳不是空的
            if call_greeks.empty and put_greeks.empty:
                continue
                
            # ==========================================
            # D. Yield 結果
            # ==========================================
            yield current_date, S, call_greeks, put_greeks
            
        except Exception as e:
            print(f"Error on {current_date.date()}: {e}")
            continue


def build_rollover_map(df_fut, start_date, end_date, offset=3):
    """建立換倉日曆 (簡易模擬: 每月第3個週三為結算日)"""
    dates = sorted(df_fut['交易日期'].unique())
    rollover_map = {}
    
    for d in dates:
        # 判斷標準：週三且日期在 15~21 之間
        if d.weekday() == 2 and 15 <= d.day <= 21:
            m_str = d.strftime('%Y%m')
            # 假設下個月合約
            next_m = (d + pd.DateOffset(months=1)).strftime('%Y%m')
            
            rollover_map[d] = {
                'close': m_str, 
                'open': next_m, 
                'is_expiry': True
            }
    return rollover_map


# class BacktestExecutor:
#     def __init__(self, strategy, start_date, end_date, df_opt, df_fut, balance=2_000_000):
#         self.strategy = strategy
#         self.start_date = pd.Timestamp(start_date)
#         self.end_date = pd.Timestamp(end_date)
#         self.df_opt = df_opt
#         self.df_fut = df_fut
        
#         self.current_position = None 
#         self.history = []
#         self.balance = balance # 初始資金
        
#     def run(self):
#         print(f"--- Executor Start: {self.start_date.date()} ~ {self.end_date.date()} | Init Balance: {self.balance} ---")
        
#         rollover_map = build_rollover_map(self.df_fut, self.start_date, self.end_date)
#         market_gen = market_data_generator(self.start_date, self.end_date, self.df_opt, self.df_fut)
        
#         for date, S, calls, puts in market_gen:
#             # print(f"\n[{date.date()}] S={S:.1f} | Balance: {self.balance:.0f}")
#             print(date.date(), end=' ')
#             market_data = (date, S, calls, puts)
            
#             context = {
#                 'position': self.current_position,
#                 'balance': self.balance # 傳入當前餘額供策略計算口數
#             }
            
#             is_rollover, close_contract, open_contract = get_rollover_info(date, rollover_map)
#             rollover_info = (is_rollover, close_contract, open_contract)
            
#             signals = []
#             if is_rollover:
#                 print(">> 換倉日觸發!")
#                 signals = self.strategy.on_rollover(context, market_data, rollover_info)
#             else:
#                 print(">> 一般交易日")
#                 signals = self.strategy.on_bar(context, market_data)
                
#             for sig in signals:
#                 self._execute_signal(sig, market_data)
                
#         return pd.DataFrame(self.history)

#     def _execute_signal(self, signal, market_data):
#         date, S, calls, puts = market_data
#         df_prices = pd.concat([calls, puts])
        
#         # 若資料有月份欄位，建議過濾
#         if '到期月份(週別)' in df_prices.columns:
#             df_prices = df_prices[df_prices['到期月份(週別)'] == signal.contract]

#         # --- 建倉 (OPEN) ---
#         if signal.action == 'OPEN':
#             net_cash_flow = 0.0
#             legs_record = []
#             qty = signal.quantity # 讀取策略計算的口數
            
#             for leg in signal.legs:
#                 try:
#                     cond = (df_prices['履約價'] == leg.strike) & \
#                            (df_prices['買賣權'] == ('買權' if leg.opt_type == 'call' else '賣權'))
                    
#                     if cond.sum() == 0: continue
#                     price = df_prices[cond].iloc[0]['收盤價']
                    
#                     direction = 1 if leg.side == 'sell' else -1
#                     net_cash_flow += (price * direction)
                    
#                     legs_record.append({
#                         'side': leg.side, 'type': leg.opt_type, 
#                         'strike': leg.strike, 'entry_price': price
#                     })
#                 except: pass

#             if not legs_record: return # 建倉失敗

#             total_premium = net_cash_flow * 50 * qty
#             self.balance += total_premium
            
#             self.current_position = {
#                 'contract': signal.contract,
#                 'legs': legs_record,
#                 'qty': qty, # 紀錄口數
#                 'total_premium': total_premium,
#                 'entry_date': date,
#                 'entry_index': S,
#                 'strategy_mode': getattr(self.strategy, 'mode', 'N/A')
#             }
#             # print(f"[{date.date()}] OPEN {qty} lots. Balance: {self.balance:.0f}")

#         # --- 平倉 (CLOSE) ---
#         elif signal.action == 'CLOSE' and self.current_position:
#             close_cash_flow = 0.0
#             legs_detail_str = []
#             qty = self.current_position['qty'] # 使用建倉時的口數平倉
            
#             for leg_data in self.current_position['legs']:
#                 try:
#                     # 查平倉價
#                     cond = (df_prices['履約價'] == leg_data['strike']) & \
#                            (df_prices['買賣權'] == ('買權' if leg_data['type'] == 'call' else '賣權'))
                    
#                     if cond.sum() > 0:
#                         exit_price = df_prices[cond].iloc[0]['收盤價']
#                     else:
#                         # 結算備案
#                         strike = leg_data['strike']
#                         if leg_data['type'] == 'call': exit_price = max(0, S - strike)
#                         else: exit_price = max(0, strike - S)
                        
#                     direction = -1 if leg_data['side'] == 'sell' else 1
#                     close_cash_flow += (exit_price * direction)
                    
#                     detail = f"{leg_data['type'].upper()} {int(leg_data['strike'])} ({leg_data['entry_price']:.1f}->{exit_price:.1f})"
#                     legs_detail_str.append(detail)
#                 except: pass
            
#             # 結算損益
#             close_amount = close_cash_flow * 50 * qty
#             pnl = self.current_position['total_premium'] + close_amount
#             self.balance += close_amount
            
#             self.history.append({
#                 'entry_date': self.current_position['entry_date'],
#                 'exit_date': date,
#                 'mode': self.current_position['strategy_mode'],
#                 'reason': signal.reason,
#                 'qty': qty,
#                 'pnl': pnl,
#                 'balance': self.balance,
#                 'trade_detail': " | ".join(legs_detail_str),
#                 'entry_index': self.current_position['entry_index'],
#                 'exit_index': S
#             })
#             self.current_position = None
#             # print(f"[{date.date()}] CLOSE {qty} lots. Balance: {self.balance:.0f}")


class BacktestExecutor:
    def __init__(self, strategy, start_date, end_date, df_opt, df_fut, balance=2_000_000):
        self.strategy = strategy
        self.start_date = pd.Timestamp(start_date)
        self.end_date = pd.Timestamp(end_date)
        self.df_opt = df_opt
        self.df_fut = df_fut
        
        self.current_position = None 
        self.history = []
        self.balance = balance 
        
    def run(self):
        print(f"--- Executor Start | Balance: {self.balance} ---")
        
        # 建立換倉地圖
        rollover_map = build_rollover_map(self.df_fut, self.start_date, self.end_date)
        # 資料生成器
        market_gen = market_data_generator(self.start_date, self.end_date, self.df_opt, self.df_fut)
        
        for date, S, calls, puts in market_gen:
            market_data = (date, S, calls, puts)
            
            # Context 傳遞
            context = {
                'position': self.current_position,
                'balance': self.balance
            }
            
            # 取得換倉資訊
            is_rollover, close_contract, open_contract = get_rollover_info(date, rollover_map)
            rollover_info = (is_rollover, close_contract, open_contract)
            
            signals = []
            if is_rollover:
                signals = self.strategy.on_rollover(context, market_data, rollover_info)
            else:
                signals = self.strategy.on_bar(context, market_data)
                
            for sig in signals:
                self._execute_signal(sig, market_data)
                
        return pd.DataFrame(self.history)

    def _execute_signal(self, signal, market_data):
        date, S, calls, puts = market_data
        df_prices = pd.concat([calls, puts])
        
        # [關鍵修正] 這裡必須先過濾出正確的合約月份，避免查到週選
        # 如果 signal 有指定 contract (通常都有)，就只看那個 contract
        if signal.contract:
            df_prices = df_prices[df_prices['到期月份(週別)'] == signal.contract]

        if df_prices.empty:
            print(f">> [下單失敗] {date.date()} 找不到月份為 {signal.contract} 的報價資料")
            return

        if signal.action == 'OPEN':
            net_cash_flow = 0.0
            legs_record = []
            qty = signal.quantity
            
            for leg in signal.legs:
                # 精準查價：履約價 + 買賣權
                mask = (df_prices['履約價'] == leg.strike) & \
                       (df_prices['買賣權'] == ('買權' if leg.opt_type == 'call' else '賣權'))
                
                target_rows = df_prices[mask]
                
                if target_rows.empty:
                    print(f">> [缺資料] 無法建倉: {leg}")
                    continue
                    
                price = target_rows.iloc[0]['收盤價']
                
                direction = 1 if leg.side == 'sell' else -1
                net_cash_flow += (price * direction)
                
                legs_record.append({
                    'side': leg.side, 'type': leg.opt_type, 
                    'strike': leg.strike, 'entry_price': price
                })

            if not legs_record: return 

            total_premium = net_cash_flow * 50 * qty
            self.balance += total_premium
            
            self.current_position = {
                'contract': signal.contract, # 記住這個合約月份！
                'legs': legs_record,
                'qty': qty,
                'total_premium': total_premium,
                'entry_date': date,
                'entry_index': S,
                'strategy_mode': getattr(self.strategy, 'mode', 'N/A')
            }
            print(f">> [成交 OPEN] {date.date()} {signal.contract} | 口數: {qty} | 收權利金: {total_premium:.0f}")

        elif signal.action == 'CLOSE' and self.current_position:
            # 確保平倉也是平同一個合約
            if self.current_position['contract'] != signal.contract:
                 # 若換倉日時，signal.contract 可能是新合約，但我們要平的是舊合約
                 # 這裡為了查價，我們應該要查 "持倉的合約"
                 # 所以即使 signal 寫的是 open_contract，我們查價要用 current_position['contract']
                 # 但這需要重新抓取該舊合約的報價 (可能不在 df_prices 篩選範圍內)
                 # 解決方案：重新從 calls/puts 篩選舊合約
                 df_prices_close = pd.concat([calls, puts])
                 df_prices_close = df_prices_close[df_prices_close['到期月份(週別)'] == self.current_position['contract']]
            else:
                 df_prices_close = df_prices

            close_cash_flow = 0.0
            legs_detail_str = []
            qty = self.current_position['qty']
            
            for leg_data in self.current_position['legs']:
                # 精準查價
                mask = (df_prices_close['履約價'] == leg_data['strike']) & \
                       (df_prices_close['買賣權'] == ('買權' if leg_data['type'] == 'call' else '賣權'))
                
                exit_price = 0
                if not mask.empty and mask.sum() > 0:
                    exit_price = df_prices_close[mask].iloc[0]['收盤價']
                else:
                    # 結算或查無報價，使用內含價值計算
                    strike = leg_data['strike']
                    if leg_data['type'] == 'call': exit_price = max(0, S - strike)
                    else: exit_price = max(0, strike - S)
                    # print(f">> [平倉提示] {date.date()} 查無報價，使用結算價: {exit_price}")

                direction = -1 if leg_data['side'] == 'sell' else 1
                close_cash_flow += (exit_price * direction)
                
                legs_detail_str.append(f"{leg_data['type']} {leg_data['strike']} ({leg_data['entry_price']}->{exit_price})")

            close_amount = close_cash_flow * 50 * qty
            pnl = self.current_position['total_premium'] + close_amount
            self.balance += close_amount
            
            self.history.append({
                'entry_date': self.current_position['entry_date'],
                'exit_date': date,
                'pnl': pnl,
                'roi': pnl / abs(self.current_position['total_premium']) if self.current_position['total_premium']!=0 else 0,
                'trade_detail': " | ".join(legs_detail_str),
                'balance': self.balance
            })
            
            print(f">> [成交 CLOSE] {date.date()} PnL: {pnl:.0f} | Detail: {legs_detail_str}")
            self.current_position = None



