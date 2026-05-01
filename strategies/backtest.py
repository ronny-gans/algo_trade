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
def run_backtest():
    conn=MT5_connection()
    try:
        conn.connect()
    except ConnectionError as e:
        print(e)
        return []
    print("fetching 99,999 bars....")
    # mt 5 return numpy structured array but we treat as list of tupple
    rates = mt5.copy_rates_from_pos("EURUSD",mt5.TIMEFRAME_M15,0,99999)
    conn.disconnect()
    if rates is None:
        print("Error: No data received from MT5.")
        return []
    # extract closes into full list
    # Bar structure: (time, open, high, low, close, tick_volume, spread, real_volume)
    closes = [bar[4] for bar in rates]
    highs= [bar[2] for bar in rates]
    lows = [bar[3] for bar in rates]
    times = [bar[0] for bar in rates]
    atr_full = indicators.indicator.ATR(14).calculate(closes,highs,lows)

    print("calculating indicators")
    # using existing classes
    tema9_full = indicators.indicator.TEMA(9).calculate(closes)
    tema20_full = indicators.indicator.TEMA(20).calculate(closes)
    rsi_full = indicators.indicator.RSI(7).calculate(closes)
    tema60_full = indicators.indicator.TEMA(60).calculate(closes)
    # --- DEBUG PRINTS ---
    print(f"Closes           :  {len(closes)}")
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
    offset = len(closes) - len(tema60_full)
    # align rsi to tema60
    rsi_diff = len(rsi_full) - len(tema60_full)
    # atr diff
    atr_diff = len(atr_full) - len(tema60_full)

    hours =BacktestHours()
    trade_returns =[]

    print("Scanning for crossovers...")
    
    # Counter for diagnostics
    session_skipped = 0
    crosses_found = 0
    time_stop_hitted = 0
    print("simulating trade...")
    for i in range(1,len(tema60_full)-1):
        # index in closes list
        idx= i + offset

        #check session
        if not hours.is_active(times[idx]):
            session_skipped+=1
            continue
        # crossover logic
        # golden cross
        
        if tema9_aligned[i-1] <= tema20_aligned[i-1] and tema9_aligned[i] > tema20_aligned[i]:
            if tema60_full[i] < closes[idx]: # mean
                crosses_found+=1
                rsi_idx = i+rsi_diff
                if 0 <= rsi_idx < len(rsi_full) and rsi_full[rsi_idx] > 50:
                    entry = closes[idx]
                    atr_idx = i +atr_diff
                    atr = atr_full[atr_idx]
                    sl = atr*1.5 #stoploss 1.5x ATR
                    tp = sl *2 # TP at 2 times SL
                    result = None 
                    for j in range (idx+1, min(idx+48, len(closes)-1)): # max 48 bars = 12 hour
                        high_j = highs[j]
                        low_j = lows[j]
                        if high_j >= entry + tp:
                            result = tp / entry    # TP hit 
                            break
                        if low_j <= entry - sl:
                            result = -(sl / entry) # SL hit 
                            break
                    if result is None:
                        exit_idx = min(idx+48, len(closes)-1)
                        result = (closes[exit_idx]-entry)/entry # time stop
                        time_stop_hitted+=1
                    trade_returns.append(result-0.0001) # spread
        # dead cross
        elif tema9_aligned[i-1] >= tema20_aligned[i-1] and tema9_aligned[i] < tema20_aligned[i]:
            if tema60_full[i] > closes[idx]: # mean reversion
                crosses_found += 1
                rsi_idx = i + rsi_diff
                if 0 <= rsi_idx < len(rsi_full) and rsi_full[rsi_idx] < 50: 
                # Short: Entry - Exit
                    entry = closes[idx]
                    atr_idx = i +atr_diff
                    atr = atr_full[atr_idx]
                    sl = atr*1.5 #stoploss 1.5x ATR
                    tp = sl *2 # TP at 2 times SL
                    result = None 
                    for j in range (idx+1, min(idx+48, len(closes)-1)): # max 48 bars = 12 hour
                        high_j = highs[j]
                        low_j = lows[j]
                        if low_j <= entry - tp:
                            result = tp / entry    # TP hit 
                            break
                        if high_j >= entry + sl:
                            result = -(sl / entry) # SL hit 
                            break
                    if result is None:
                        exit_idx = min(idx+48, len(closes)-1)
                        result = (entry-closes[exit_idx])/entry # time stop
                        time_stop_hitted+=1
                    trade_returns.append(result-0.0001) # spread
    print(f"Debug: Total crosses found           : {crosses_found}")
    print(f"Debug: Bars skipped by session filter: {session_skipped}")
    print(f"Debug: Trades that passed RSI filter : {len(trade_returns)}")
    print(f"time stop hitted                     : {time_stop_hitted}")
    print(f"trade after RSI filter               : {len(trade_returns)}")
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
        # simulate random sequence of the trades we found
        for _ in range(num_trades):
            # random.choice picks one trade return from our list
            r=random.choice(returns)
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


