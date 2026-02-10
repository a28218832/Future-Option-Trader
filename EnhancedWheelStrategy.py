from utils import *
class EnhancedWheelStrategy(BaseStrategy):
    def __init__(self, 
                 leverage: float = 3.0, 
                 target_delta: float = 0.20,
                 stop_loss_delta: float = 0.60,
                 profit_take_pct: float = 0.80,
                 gamma_risk_days: int = 5):
        self.leverage = leverage
        self.target_delta = target_delta
        self.stop_loss_delta = stop_loss_delta
        self.profit_take_pct = profit_take_pct
        self.gamma_risk_days = gamma_risk_days
        
        # 狀態變數
        self.mode = 'PUT'  # 'PUT' (收租) or 'CALL' (救援)
        self.virtual_cost = 0.0 

    def _calculate_position_size(self, balance, spot_price) -> int:
        """
        [資金管理核心]
        根據當前餘額與槓桿計算口數。
        公式: (餘額 * 槓桿) / (指數 * 50)
        """
        if spot_price <= 0: return 1
        raw_qty = (balance * self.leverage) / (spot_price * 50)
        return max(1, int(raw_qty)) # 至少下1口

    def on_bar(self, context, market_data) -> List[TradeSignal]:
        """日內監控：風控與停利"""
        date, S, calls, puts = market_data
        position = context.get('position')
        print("position", position)
        signals = []

        if not position or not position.get('legs'):
            return []

        # 取得持倉資訊
        my_leg = position['legs'][0]
        qty = position['qty'] # 從 executor 讀取當前口數
        strike = my_leg['strike']
        opt_type = my_leg['type']
        contract = position['contract'] # 修正：從 position 讀取 contract
        # print(f">> [{date}] {opt_type.capitalize()} {strike}, Qty={qty}")
        # 查報價與 Greeks
        df_chain = calls if opt_type == 'call' else puts
        try:
            row = df_chain[df_chain['履約價'] == strike].iloc[0]
            current_price = row['收盤價']
            current_delta = abs(row['Delta'])
            current_dt = row['dT'] * 252 # 年化轉天數
            
        except:
            return [] 

        entry_price = my_leg['entry_price']

        # 1. 提早獲利 (Profit Take)
        if current_price <= entry_price * (1 - self.profit_take_pct):
            signals.append(TradeSignal('CLOSE', contract, [Leg(my_leg['side'], strike, opt_type)], 
                                     f"TakeProfit_{int(self.profit_take_pct*100)}%", quantity=qty))
            return signals

        # 2. Delta 止損 (Stop Loss)
        if current_delta > self.stop_loss_delta:
            signals.append(TradeSignal('CLOSE', contract, [Leg(my_leg['side'], strike, opt_type)], 
                                     f"StopLoss_Delta_{current_delta:.2f}", quantity=qty))
            return signals

        # 3. Gamma 避險 (Risk Aversion)
        if current_dt < self.gamma_risk_days and current_delta > 0.4:
            signals.append(TradeSignal('CLOSE', contract, [Leg(my_leg['side'], strike, opt_type)], 
                                     "Gamma_Risk", quantity=qty))
            print(f">> [{date}] Gamma Risk triggered for {opt_type.capitalize()} {strike}: Delta={current_delta:.2f}, dT={current_dt:.2f}年, Qty={qty}")
            return signals

        return signals

    def on_rollover(self, context, market_data, rollover_info) -> List[TradeSignal]:
        """換倉日邏輯：結算舊倉，建立新倉"""
        is_rollover, close_contract, open_contract = rollover_info
        date, S, calls, puts = market_data
        balance = context['balance']
        position = context.get('position')
        
        signals = []

        # --- A. 處理舊倉 (結算/轉狀態) ---
        if position:
            leg_info = position['legs'][0]
            qty = position['qty']
            strike = leg_info['strike']
            
            # 發出平倉訊號 (Executor 會處理損益)
            signals.append(TradeSignal(
                'CLOSE', position['contract'], 
                [Leg(leg_info['side'], strike, leg_info['type'])], 
                "Rollover_Expiry", quantity=qty
            ))
            
            # 判斷是否 ITM 決定下期模式
            is_itm = (leg_info['type'] == 'put' and S < strike) or \
                     (leg_info['type'] == 'call' and S > strike)

            if self.mode == 'PUT':
                if is_itm:
                    self.mode = 'CALL'
                    self.virtual_cost = strike
                # else: 保持 PUT
            elif self.mode == 'CALL':
                if is_itm:
                    self.mode = 'PUT' # 救援失敗或成功被call走，回歸原點
                    self.virtual_cost = 0
                # else: 繼續 CALL (可選擇調整 virtual_cost)

        # --- B. 建立新倉 ---
        # 根據最新餘額計算口數
        new_qty = self._calculate_position_size(balance, S)
        target_leg = None
        
        # 預先過濾合約月份 (假設資料有此欄位，若無則忽略)
        # target_puts = puts[puts['到期月份'] == open_contract]
        target_puts = puts 
        target_calls = calls

        if self.mode == 'PUT':
            # 策略：賣出 Delta ~ 0.2 的 Put
            try:
                # 使用 iloc 找最接近的
                idx = (target_puts['Delta'] - (-self.target_delta)).abs().argsort().iloc[0]
                row = target_puts.iloc[idx]
                target_leg = Leg('sell', row['履約價'], 'put')
            except:
                pass # 找不到適合的
                
        elif self.mode == 'CALL':
            # 策略：賣出 Strike > Virtual Cost 的 Call
            candidates = target_calls[target_calls['履約價'] >= self.virtual_cost]
            if not candidates.empty:
                # 找最接近 ATM 的 (權利金較高)
                candidates = candidates.sort_values('履約價')
                row = candidates.iloc[0] # 取最小的履約價 (最接近成本)
                target_leg = Leg('sell', row['履約價'], 'call')
            else:
                # 找不到 (成本太高)，防禦性策略：賣最高履約價
                if not target_calls.empty:
                    row = target_calls.sort_values('履約價').iloc[-1]
                    target_leg = Leg('sell', row['履約價'], 'call')

        if target_leg:
            signals.append(TradeSignal(
                'OPEN', open_contract, [target_leg], 
                f"Wheel_{self.mode}", quantity=new_qty
            ))
            
        return signals