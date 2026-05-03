import MetaTrader5 as mt5
from core.mt5_connector import MT5_connection
import random
import math
import indicators.indicator 
from strategies.strategy import RSI_signal, MACD_cross, TEMA_CROSS
from datetime import datetime, timezone

# -- Manual trading hours --
class BacktestHours:
    def is_active(self, unix_timestamp):
        dt = datetime.fromtimestamp(unix_timestamp,tz=timezone.utc)
        hour = dt.hour
        weekday=dt.weekday()

        if weekday>=5: return False # weekend
        if 7<=hour<11: return True # london
        if 12<= hour<16: return True # NY
        return False
def get_htf_index(m15_time,times_h1):
    for i in range (len(times_h1)-1):
        if times_h1[i] <= m15_time < times_h1[i+1]:
            return i
    return None

def run_backtest():
    conn=MT5_connection()
    try:
        conn.connect()
    except ConnectionError as e:
        print(e)
        return []
    print("fetching 99,999 bars....")
    # mt 5 return numpy structured array but we treat as list of tupple
    rates_m15 = mt5.copy_rates_from_pos("EURUSD",mt5.TIMEFRAME_M15,0,99999)
    rates_h1 = mt5.copy_rates_from_pos("EURUSD",mt5.TIMEFRAME_H1,0,99999)
    conn.disconnect()
    if rates_m15 is None:
        print("Error: No data received from MT5.")
        return []
    # extract closes into full list
    # Bar structure: (time, open, high, low, close, tick_volume, spread, real_volume)
    closes_m15 = [bar[4] for bar in rates_m15]
    highs_m15= [bar[2] for bar in rates_m15]
    lows_m15 = [bar[3] for bar in rates_m15]
    times_m15 = [bar[0] for bar in rates_m15]
    closes_h1 = [bar[4] for bar in rates_h1]
    times_h1 = [bar[0] for bar in rates_h1]
    atr_full = indicators.indicator.ATR(14).calculate(closes_m15,highs_m15,lows_m15)
    tema_60_h1 = indicators.indicator.TEMA(60).calculate(closes_h1)
    adx = indicators.indicator.ADX(14).calculate(closes_m15,highs_m15,lows_m15)
    print("calculating indicators")
    # using existing classes
    tema9_full = indicators.indicator.TEMA(9).calculate(closes_m15)
    tema20_full = indicators.indicator.TEMA(20).calculate(closes_m15)
    rsi_full = indicators.indicator.RSI(14).calculate(closes_m15)
    tema60_full = indicators.indicator.TEMA(60).calculate(closes_m15)
    # --- DEBUG PRINTS ---
    print(f"Closes           :  {len(closes_m15)}")
    print(f"Length of TEMA 9 :  {len(tema9_full)}")
    print(f"Length of TEMA 20:  {len(tema20_full)}")
    print(f"Length of RSI    :  {len(rsi_full)}")

    if not tema9_full or len(tema20_full) < 10:
        print("Critical Error: Indicators are not producing enough data.")
        return []
    # align tema to ema 200
    tema20_diff = len(tema20_full) - len(tema60_full)
    tema20_aligned = tema20_full[tema20_diff:]
    diff = len(tema9_full) - len(tema60_full)
    tema9_aligned = tema9_full[diff:]
    # align closes and times to tema60
    offset = len(closes_m15) - len(tema60_full)
    h1_offset = len(closes_h1) - len(tema_60_h1)
    # align rsi to tema60
    rsi_diff = len(rsi_full) - len(tema60_full)
    # atr diff
    atr_diff = len(atr_full) - len(tema60_full)
    atr_aligned = atr_full[atr_diff:]
    # adx aligned 
    adx_diff = len(adx) - len(tema60_full)
    adx_aligned = adx[adx_diff:]
    hours =BacktestHours()
    trade_returns =[]
    

    print("Scanning for crossovers...")
    
    # Counter for diagnostics
    session_skipped = 0
    crosses_found = 0
    time_stop_hitted = 0
    htf_none = 0
    trend_up_count = 0
    trend_down_count = 0
    rsi_fail = 0 
    print("simulating trade...")
    for i in range(1,len(tema60_full)-1):
        # index in closes list
        idx= i + offset

        #check session
        if not hours.is_active(times_m15[idx]):
            session_skipped+=1
            continue
        # Get HTF index for M15 time frame
        htf_idx = get_htf_index(times_m15[idx],times_h1)
        if htf_idx is None:
            htf_none+=1
            continue
        tema_idx = htf_idx-h1_offset
        if tema_idx < 0 or tema_idx >= len(tema_60_h1):
            continue
        if htf_idx < 1 or tema_idx < 1:
            continue
        trend_up = closes_h1[htf_idx-1] > tema_60_h1[tema_idx-1]
        trend_down = closes_h1[htf_idx-1] < tema_60_h1[tema_idx-1]
        
        # crossover logic
        # golden cross
        #if tema9_aligned[i-1] <= tema20_aligned[i-1] and tema9_aligned[i] > tema20_aligned[i]:
        if trend_up: #and adx_aligned[i]>=0.25:
            trend_up_count+=1
            if tema60_full[i] < closes_m15[idx]: 
                #if tema60_full[i] < tema20_aligned[i] and tema20_aligned[i] < tema9_aligned[i]: 
                    if closes_m15[idx] < closes_m15[idx-1]: #pullback
                        crosses_found+=1
                        #rsi_idx = i+rsi_diff
                        #if 0 <= rsi_idx < len(rsi_full) and rsi_full[rsi_idx] < 45:
                        if True:
                            entry = closes_m15[idx+1]
                            atr = atr_aligned[i]
                            sl = atr*1.5 #stoploss 1.5x ATR
                            tp = sl *3 # TP at 2 times SL
                            result = None 
                            for j in range (idx+2,min(idx+48, len(closes_m15)-1)): # max 48 bars = 12 hour
                                high_j = highs_m15[j]
                                low_j = lows_m15[j]
                                if high_j >= entry + tp:
                                    result = tp / entry    # TP hit 
                                    break
                                if low_j <= entry - sl:
                                    result = -(sl / entry) # SL hit 
                                    break
                            if result is None:
                                exit_idx = min(idx+48, len(closes_m15)-1)
                                result = (closes_m15[exit_idx]-entry)/entry # time stop
                                time_stop_hitted+=1
                            spread = random.uniform(0.00005, 0.0002)
                            slippage = random.uniform(0, 0.0001)
                            trade_returns.append(result-spread-slippage) # spread
                    #else:
                        #rsi_fail+=1
        # dead cross
        #elif tema9_aligned[i-1] >= tema20_aligned[i-1] and tema9_aligned[i] < tema20_aligned[i]:
        elif trend_down: #and adx_aligned[i]>=0.25:
            trend_down_count+=1
            if tema60_full[i] > closes_m15[idx]: # 
                #if tema60_full[i] > tema20_aligned[i] and tema20_aligned[i] > tema9_aligned[i]:
                    if closes_m15[idx] > closes_m15 [idx-1]: #pullback
                        crosses_found += 1
                        #rsi_idx = i + rsi_diff
                        #if 0 <= rsi_idx < len(rsi_full) and rsi_full[rsi_idx] > 55: 
                        if True:
                        # Short: Entry - Exit
                            entry = closes_m15[idx+1]
                            atr = atr_aligned[i]
                            sl = atr*1.5 #stoploss 1.5x ATR
                            tp = sl *3 # TP at 2 times SL
                            result = None 
                            for j in range (idx+2, min(idx+48, len(closes_m15)-1)): # max 48 bars = 12 hour
                                high_j = highs_m15[j]
                                low_j = lows_m15[j]
                                if low_j <= entry - tp:
                                    result = tp / entry    # TP hit 
                                    break
                                if high_j >= entry + sl:
                                    result = -(sl / entry) # SL hit 
                                    break
                            if result is None:
                                exit_idx = min(idx+48, len(closes_m15)-1)
                                result = (entry-closes_m15[exit_idx])/entry # time stop
                                time_stop_hitted+=1
                            spread = random.uniform(0.00005, 0.0002)
                            slippage = random.uniform(0, 0.0001)
                            trade_returns.append(result-spread-slippage) # spread
                    #else:
                        #rsi_fail+=1
    print(f"Debug: Total crosses found           : {crosses_found}")
    print(f"Debug: Bars skipped by session filter: {session_skipped}")
    print(f"Debug: Trades that passed RSI filter : {len(trade_returns)}")
    print(f"time stop hitted                     : {time_stop_hitted}")
    print(f"trade after RSI filter               : {len(trade_returns)}")
    print(f"HTF None                             : {htf_none}")
    print(f"trend up                             : {trend_up_count}")
    print(f"trend down count                     : {trend_down_count}")
    print(f"RSI fail                             :  {rsi_fail}")
    if trade_returns:
        winning_trades = len([r for r in trade_returns if r > 0])
        losing_trades = len([r for r in trade_returns if r <= 0])
        win_rate = (winning_trades / len(trade_returns)) * 100
        avg_win = sum([r for r in trade_returns if r > 0]) / max(1, winning_trades)
        avg_loss = sum([r for r in trade_returns if r <= 0]) / max(1, losing_trades)
        
        print(f"\n--- STRATEGY STATISTICS ---")
        print(f"Total Trades        : {len(trade_returns)}")
        print(f"Winning Trades      : {winning_trades}")
        print(f"Losing Trades       : {losing_trades}")
        print(f"Win Rate            : {win_rate:.2f}%")
        print(f"Avg Win             : {avg_win:.4f} ({avg_win*100:.2f}%)")
        print(f"Avg Loss            : {avg_loss:.4f} ({avg_loss*100:.2f}%)")
        print(f"Profit Factor       : {abs(sum([r for r in trade_returns if r > 0]) / sum([r for r in trade_returns if r <= 0])):.2f}")
        print("---\n")
    
    return trade_returns

def run_monte_carlo(returns, num_sims=100000, start_bal=10000):
    if not returns:
        print("no trade to simulate")
        return None
    print(f"starting {num_sims} monte carlo simulations...")
    final_balances = []
    num_trades=len(returns)
    # this loops will be the slowest part without numpy
    for _ in range(num_sims):
        current_balances = start_bal
        shuffled = returns[:]
        random.shuffle(shuffled)
        # simulate random sequence of the trades we found
        for r in shuffled:
            # random.choice picks one trade return from our list
            current_balances*=(1+r)
        final_balances.append(current_balances)
    # -- Manual statistics--
    final_balances.sort()
    avg_balances = sum(final_balances)/num_sims
    profitable_sims = len([b for b in final_balances if b>start_bal])
    prob_profit = (profitable_sims/num_sims)*100

    print("\n"+"="*40)
    print("MONTE CARLO RESULTS")
    print("="*40)
    print(f"Total trades fund       : {num_trades}")
    print(f"Average Final Balances  : {avg_balances}")
    print(f"Median Final Bal        : ${final_balances[num_sims//2]:.2f}")
    print(f"Probability of Profit   : {prob_profit:.2f}%")
    print(f"Max Final Balance       : ${final_balances[-1]:.2f}")
    print(f"Min Final Balance       : ${final_balances[0]:.2f}")
    print("="*40)

if __name__=="__main__":
    trade_outcomes = run_backtest()
    run_monte_carlo(trade_outcomes)


