import pandas as pd
import numpy as np
from typing import List, Dict, Optional

# 沿用之前的 Leg 與 TradeSignal 定義
class Leg:
    def __init__(self, side: str, strike: float, opt_type: str):
        self.side = side
        self.strike = strike
        self.opt_type = opt_type
    def __repr__(self):
        return f"{self.side} {self.opt_type} {self.strike}"

class TradeSignal:
    def __init__(self, action: str, contract: str, legs: List[Leg], reason: str, quantity: int = 1):
        self.action = action
        self.contract = contract
        self.legs = legs
        self.reason = reason
        self.quantity = quantity

class BaseStrategy:
    def on_bar(self, context, market_data) -> List[TradeSignal]: pass
    def on_rollover(self, context, market_data, rollover_info) -> List[TradeSignal]: pass

class EnhancedWheelStrategy(BaseStrategy):
    def __init__(self, 
                 leverage: float = 3.0, 
                 target_delta: float = 0.20,
                 stop_loss_delta: float = 0.60,
                 profit_take_pct: float = 0.80):
        self.leverage = leverage
        self.target_delta = target_delta
        self.stop_loss_delta = stop_loss_delta
        self.profit_take_pct = profit_take_pct
        
        # 狀態變數
        self.mode = 'PUT' 
        self.virtual_cost = 0.0 

    def _calculate_qty(self, balance, spot) -> int:
        return max(1, int((balance * self.leverage) / (spot * 50)))

    def _get_exact_quote(self, df_chain, contract, strike, opt_type):
        """
        [核心修正] 精準查價函式
        強制要求：月份、履約價、類型 必須完全吻合
        """
        # 1. 篩選合約月份
        mask_contract = df_chain['到期月份(週別)'] == contract
        
        # 2. 篩選履約價 (浮點數可能有誤差，使用 np.isclose 或小範圍)
        mask_strike = (df_chain['履約價'] - strike).abs() < 0.1
        
        # 3. 買賣權已由傳入的 df_chain 分流，但保險起見可再確認
        
        target_row = df_chain[mask_contract & mask_strike]
        
        if target_row.empty:
            return None
        
        # 回傳 Series (該行資料)
        return target_row.iloc[0]

    def on_bar(self, context, market_data) -> List[TradeSignal]:
        date, S, calls, puts = market_data
        position = context.get('position')
        signals = []

        if not position:
            return []

        # 取得持倉的「關鍵身分證」
        my_leg = position['legs'][0]
        contract = position['contract'] # 這是最關鍵的修正：必須知道是哪個月的合約
        strike = my_leg['strike']
        opt_type = my_leg['type']
        qty = position['qty']
        
        # 選擇正確的報價表
        df_chain = calls if opt_type == 'call' else puts
        
        # --- 精準查價 ---
        row = self._get_exact_quote(df_chain, contract, strike, opt_type)
        
        if row is None:
            # 這是正常的，可能今天資料缺失，或該合約已結算
            # print(f">> [監控警告] {date.date()} 查無報價: {contract} {opt_type} {strike}")
            return []

        # 讀取數值
        curr_price = row['收盤價']
        curr_delta = abs(row['Delta']) # 取絕對值避免負號干擾
        curr_dt = row['dT'] * 252
        
        # --- 顯式打印判斷 (Explicit Logging) ---
        # 這裡不隨便平倉，除非觸發條件
        # print(f">> [監控] {date.date()} 持倉: {contract} {opt_type} {strike} | 現價: {curr_price:.1f} | Delta: {curr_delta:.2f} | 剩餘: {curr_dt:.1f}天")

        entry_price = my_leg['entry_price']

        # 1. 提早獲利判斷
        target_price = entry_price * (1 - self.profit_take_pct)
        if curr_price <= target_price:
            print(f">> [信號] {date.date()} 觸發停利! 進場: {entry_price}, 現價: {curr_price}, 目標: {target_price}")
            signals.append(TradeSignal('CLOSE', contract, [Leg(my_leg['side'], strike, opt_type)], "TakeProfit", qty))
            return signals

        # 2. Delta 風控判斷
        if curr_delta > self.stop_loss_delta:
            print(f">> [信號] {date.date()} 觸發 Delta 止損! 當前 Delta {curr_delta:.2f} > 閾值 {self.stop_loss_delta}")
            signals.append(TradeSignal('CLOSE', contract, [Leg(my_leg['side'], strike, opt_type)], "StopLoss_Delta", qty))
            return signals

        # 3. Gamma 風控 (僅在剩下 5 天內且 Delta 變大時)
        if curr_dt < 5 and curr_delta > 0.4:
            print(f">> [信號] {date.date()} 觸發 Gamma 避險! 剩餘 {curr_dt:.1f} 天且 Delta {curr_delta:.2f} 偏高")
            signals.append(TradeSignal('CLOSE', contract, [Leg(my_leg['side'], strike, opt_type)], "Gamma_Risk", qty))
            return signals

        return signals

    def on_rollover(self, context, market_data, rollover_info) -> List[TradeSignal]:
        is_rollover, close_contract, open_contract = rollover_info
        date, S, calls, puts = market_data
        position = context.get('position')
        balance = context['balance']
        signals = []

        print(f"\n=== {date.date()} 換倉日 / 結算日 ===")
        print(f">> 預計結算合約: {close_contract} -> 預計開倉合約: {open_contract}")

        # 1. 處理舊倉 (平倉/結算)
        if position:
            leg = position['legs'][0]
            strike = leg['strike']
            # 無論是否 ITM，先執行平倉 (Executor 會算損益)
            signals.append(TradeSignal('CLOSE', position['contract'], 
                                     [Leg(leg['side'], strike, leg['type'])], "Rollover_Expiry", position['qty']))
            
            # 判斷 ITM (用當天收盤價 S)
            is_itm = (leg['type'] == 'put' and S < strike) or (leg['type'] == 'call' and S > strike)
            
            if is_itm:
                print(f">> [結算] 舊倉 ITM 被穿價 (S={S}, K={strike})")
                if self.mode == 'PUT':
                    self.mode = 'CALL'
                    self.virtual_cost = strike
                    print(f">> [模式切換] 進入 CALL 救援模式. 虛擬成本: {self.virtual_cost}")
                elif self.mode == 'CALL':
                    self.mode = 'PUT'
                    self.virtual_cost = 0
                    print(f">> [模式切換] 救援結束/失敗. 回歸 PUT 模式.")
            else:
                print(f">> [結算] 舊倉 OTM 安全下莊. 保持 {self.mode} 模式.")

        # 2. 建立新倉
        qty = self._calculate_qty(balance, S)
        target_leg = None

        if self.mode == 'PUT':
            # --- Put 選股 (嚴格篩選) ---
            # 步驟 1: 鎖定合約月份
            candidates = puts[puts['到期月份(週別)'] == open_contract].copy()
            
            if candidates.empty:
                print(f">> [錯誤] 找不到月份為 {open_contract} 的 Put 資料!")
            else:
                # 步驟 2: 計算 Delta 差距 (強制取絕對值)
                # 我們要找 Delta 接近 0.2 的 Put (通常 Put Delta 是負的，但資料庫可能是正或負)
                candidates['abs_delta'] = candidates['Delta'].abs()
                
                # 步驟 3: 設定合理範圍 (避免選到 0.02)
                # 篩選 Delta 在 0.10 ~ 0.30 之間的
                valid_candidates = candidates[
                    (candidates['abs_delta'] >= 0.10) & 
                    (candidates['abs_delta'] <= 0.30)
                ].copy()
                
                if not valid_candidates.empty:
                    # 在合理範圍內找最接近 0.2 的
                    valid_candidates['diff'] = (valid_candidates['abs_delta'] - self.target_delta).abs()
                    best_row = valid_candidates.sort_values('diff').iloc[0]
                    
                    target_leg = Leg('sell', best_row['履約價'], 'put')
                    print(f">> [開倉選擇] PUT | 合約: {open_contract} | 履約價: {best_row['履約價']} | Delta: {best_row['abs_delta']:.2f}")
                else:
                    print(f">> [放棄] 找不到 Delta 在 0.1~0.3 之間的 Put (可能市場極端)")
                
                del valid_candidates  # 釋放記憶體
                
        elif self.mode == 'CALL':
            # --- Call 選股 (救援模式) ---
            # 步驟 1: 鎖定合約
            candidates = calls[calls['到期月份(週別)'] == open_contract].copy()
            
            # 步驟 2: 篩選 履約價 >= 虛擬成本 (這是硬指標)
            candidates = candidates[candidates['履約價'] >= self.virtual_cost]
            
            if not candidates.empty:
                # 步驟 3: 找最接近價平 (ATM) 的那一檔，權利金最肥
                # 因為已經篩選過 >= Cost，所以最小的履約價就是最接近 Cost 的
                best_row = candidates.sort_values('履約價').iloc[0].copy()              
                
                # 檢查 Delta 是否太小 (例如 < 0.05 沒肉吃)
                if abs(best_row['Delta']) < 0.05:
                     print(f">> [放棄] 符合成本的 Call Delta 過小 ({abs(best_row['Delta']):.2f})，不交易")
                else:
                    target_leg = Leg('sell', best_row['履約價'], 'call')
                    print(f">> [開倉選擇] CALL (救援) | 合約: {open_contract} | 履約價: {best_row['履約價']} (Cost: {self.virtual_cost}) | Delta: {best_row['Delta']:.2f}")
            else:
                print(f">> [放棄] 市場價格遠低於虛擬成本 {self.virtual_cost}，找不到上方 Call")

        if target_leg:
            signals.append(TradeSignal('OPEN', open_contract, [target_leg], f"Wheel_{self.mode}", qty))

        return signals