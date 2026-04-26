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
    conn.connect()
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
    times = [bar[0] for bar in rates]

    print("calculating indicators")
    # using existing classes
    tema20_full = indicators.indicator.TEMA(20).calculate(closes)
    tema60_full = indicators.indicator.TEMA(60).calculate(closes)
    rsi_full = indicators.indicator.RSI(10).calculate(closes)
    # --- DEBUG PRINTS ---
    print(f"Closes           : {len(closes)}")
    print(f"Length of TEMA 20: {len(tema20_full)}")
    print(f"Length of TEMA 60: {len(tema60_full)}")
    print(f"Length of RSI    :     {len(rsi_full)}")

    if not tema60_full or len(tema60_full) < 10:
        print("Critical Error: Indicators are not producing enough data.")
        return []
    # align tema20 to tema60
    diff = len(tema20_full) - len(tema60_full)
    tema20_aligned = tema20_full[diff:]
    # align closes and times to tema60
    offset = len(closes) - len(tema60_full)
    # align rsi to tema60
    rsi_diff = len(rsi_full) - len(tema60_full)
    
    hours =BacktestHours()
    trade_returns =[]

    print("Scanning for crossovers...")
    
    # Counter for diagnostics
    session_skipped = 0
    crosses_found = 0

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
        if tema20_full[i-1] <= tema60_full[i-1] and tema20_full[i] > tema60_full[i]:
            crosses_found+=1
            rsi_idx = i+rsi_diff
            if 0 <= rsi_idx < len(rsi_full) and rsi_full[rsi_idx] < 70:
                # Buy at current close, sell at next close
                # Return = (Exit - Entry) / Entry
                ret = (closes[idx+1]-closes[idx])/closes[idx]
                trade_returns.append(ret-0.0001) # spread
        # dead cross
        elif tema20_aligned[i-1] >= tema60_full[i-1] and tema20_aligned[i] < tema60_full[i]:
            crosses_found += 1
            rsi_idx = i + rsi_diff
            if 0 <= rsi_idx < len(rsi_full) and rsi_full[rsi_idx] > 30:
            # Short: Entry - Exit
             ret = (closes[idx]-closes[idx+1])/closes[idx]
             trade_returns.append(ret-0.0001)
    print(f"Debug: Total crosses found: {crosses_found}")
    print(f"Debug: Bars skipped by session filter: {session_skipped}")
    print(f"Debug: Trades that passed RSI filter: {len(trade_returns)}")
    print(f"trade after RSI filter              : {len(trade_returns)}")
    
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
    print(f"Median Final Bal        :    ${final_balances[num_sims//2]:.2f}")
    print(f"Probability of Profit   : {prob_profit:.2f}%")
    print(f"Max Final Balance       :   ${final_balances[-1]:.2f}")
    print(f"Min Final Balance       :   ${final_balances[0]:.2f}")
    print("="*40)

if __name__=="__main__":
    trade_outcomes = run_backtest()
    run_monte_carlo(trade_outcomes)


