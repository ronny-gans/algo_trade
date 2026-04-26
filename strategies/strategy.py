from indicators import indicator
from datetime import datetime, timezone

# Trading hours
class trading_hours:
    def is_active(self):
        now_utc = datetime.now(timezone.utc)
        hour_utc = now_utc.hour
        weekday_utc = now_utc.weekday() # 0 = monday, 6 = sunday
        if weekday_utc == 5 or weekday_utc == 6: # close at weekend
            return False, "WEEKEND"
        # london session: 07-11 utc
        if 7 <= hour_utc < 11:
            return True, "LONDON"
        # new york session 12-16 UTC
        elif 12 <= hour_utc < 16:
            return True, "NEW YORK"
         # friday after 20.00 UTC --liquidity drop, spread wider
        elif weekday_utc == 4 and hour_utc >= 20:
            return False, "FRIDAY CLOSE"
        else:
            return False, "OFF SESSION"
       
# TEMA cross (golden cross and dead cross)
class TEMA_CROSS:
    def __init__(self,fast = 20, slow = 60):
        self.tema_fast = indicator.TEMA(fast)
        self.tema_slow = indicator.TEMA(slow)
    def calculate(self,closes):
        if not closes:
            return None
        # calculate tema 20 and tema 60
        tema20 = self.tema_fast.calculate(closes)
        tema60 = self.tema_slow.calculate(closes)
        # align tema 20 (tema 20 is longer than tema 60)
        diff = len(tema20) - len(tema60)
        tema20_aligned = tema20[diff:]
        
        # check only last two bars for crossover
        if tema20_aligned [-2] <= tema60[-2] and tema20_aligned[-1] > tema60[-1]:
            signal = "GOLDEN CROSS" # bearish

        elif tema20_aligned [-2] >= tema60[-2] and tema20_aligned[-1] < tema60[-1]:
            signal = "DEAD CROSS" #Bearish
        else:
            signal=None
        return signal, tema20_aligned[-1], tema60[-1]
# RSI cross
class RSI_signal:
    # 10 period for H1 and M15 timeframe
    def __init__(self, period = 10):
        self.rsi =indicator.RSI(period)
    def calculate(self,closes):
        if not closes:
            return None
        # RSI values
        rsi_values = self.rsi.calculate(closes)
        current_rsi = rsi_values[-1]
        if current_rsi > 70:
            return "OVERBOUGHT", current_rsi
        elif current_rsi < 30:
            return "OVERSOLD", current_rsi
        else:
            return "NEUTRAL", current_rsi
# MACD cross
class MACD_cross:
    def __init__(self):
        self.macd = indicator.MACD()
    
    def calculate(self,closes):
        if not closes:
            return None
        macd_line,signal_line,histogram = self.macd.calculate(closes)

        # crossover signal
        if macd_line[-2] <= signal_line[-2] and macd_line[-1] > signal_line[-1]:
            crossover = "BULLSIH"
        elif macd_line[-2] >= signal_line[-2] and macd_line[-1] < signal_line[-1]:
            crossover = "BEARISH"
        else:
            crossover="NEUTRAL"
        
        # macd direction
        if macd_line[-1] > 0:
            momentum = "ABOVE ZERO"
        else:
            momentum="BELOW ZERO"
        
        # histogram strength
        histogram_strength = histogram[-1]
        
        return crossover, momentum, histogram_strength

if __name__ == "__main__":
    
    import MetaTrader5 as mt5
    from core.mt5_connector import MT5_connection

    conn = MT5_connection()
    try:
        conn.connect()

        bars = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H1, 0, 800)
        closes = [bar[4] for bar in bars]

        # test TEMA cross
        tema_cross = TEMA_CROSS()
        signal, fast, slow = tema_cross.calculate(closes)
        print(f"TEMA Cross : {signal}")
        print(f"TEMA Fast  : {fast:.5f}")
        print(f"TEMA Slow  : {slow:.5f}")

        # test RSI signal
        rsi_signal = RSI_signal()
        rsi_status, rsi_val = rsi_signal.calculate(closes)
        print(f"RSI Signal : {rsi_status} ({rsi_val:.2f})")

        # test MACD signal
        macd_signal = MACD_cross()
        crossover, momentum, hist = macd_signal.calculate(closes)
        print(f"MACD Cross : {crossover}")
        print(f"MACD Moment: {momentum}")
        print(f"Histogram  : {hist:.5f}")

        # test trading hours
        hours = trading_hours()
        active, session = hours.is_active()
        print(f"Session    : {session} | Active: {active}")

    except ConnectionError as e:
        print(e)
    finally:
        conn.disconnect()