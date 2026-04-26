# EMA class
class EMA:
    def __init__(self, period):
        self.period = period

    def calculate(self,closes):
        if not closes:
            return None
        #SMA as ema seed
        SMA = sum(closes[:self.period])/self.period
        # define smoother factor
        k = 2/(self.period+1)
        ema = [SMA]
        for price in closes[self.period:]:
            new_ema = (price*k) + ema[-1]*(1-k)
            ema.append(new_ema)
        return ema
# calculate TEMA
class TEMA:
    def __init__(self,period):
        self.period=period
        self.ema=EMA(period) # TEMA uses EMA internally
    
    def calculate(self,closes):
        if not closes:
            return None
        ema1= self.ema.calculate(closes)
        ema2= self.ema.calculate(ema1)
        ema3= self.ema.calculate(ema2)
        # align ema1 and ema2 to ema3 length
        diff1 = len(ema1) - len(ema3)
        diff2 = len(ema2) - len(ema3)

        ema1_aligned = ema1[diff1:]
        ema2_aligned = ema2[diff2:]

        tema=[]
        for i in range (len(ema3)):
            tema.append(3*ema1_aligned[i] - 3*ema2_aligned[i] + ema3[i])
        return tema

# calculate ROC
class ROC:
    def __init__(self,period):
        self.period = period
    def calculate (self,closes):
        return ((closes[-1]-closes[-self.period])/closes[-self.period])*100

class RSI:
    def __init__(self,period):
        self.period=period

    def calculate(self,closes):
        # declare loses and gain since the RSI formula = 
        gains = []
        loses = []
        for i in range (1,len(closes)):
            change= closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                loses.append(0)
            else:
                gains.append (0)
                loses.append(abs(change))
        # calculate the avg gais and avg loses for calculate the RS
        # seed with first period
        avg_gains = sum(gains[:self.period])/self.period
        avg_loses = sum(loses[:self.period])/self.period
        rs = avg_gains/avg_loses
        rsi = []
        # roll forward with wilder smoothing
        for i in range (self.period, len(closes)-1):
            avg_gains = (avg_gains*(self.period-1) + gains[i])/self.period
            avg_loses = (avg_loses*(self.period-1)+loses[i])/self.period

            if avg_loses == 0:
                rsi.append(100) # no loses =overbought
            else:
                rs = avg_gains/avg_loses
                rsi.append(100-(100/(1+rs)))
        return rsi

# MACD indicator
class MACD:
    def __init__(self, fast=12, slow=26, signal=9):
        self.fast_ema=EMA(fast) # EMA 12
        self.slow_ema = EMA(slow) # EMA 26
        self.signal_ema= EMA(signal) # EMA 9 of MACD line
    def calculate(self,closes):
        if not closes:
            return None
        # 1. calculate fast and slow EMA
        ema12= self.fast_ema.calculate(closes)
        ema26 = self.slow_ema.calculate(closes)
        
        # 2. align the length of EMA 12 and ema 26 (ema 26 is shorter than ema 12)
        # trim ema 12 to match ema 26 lenth
        diff = len(ema12) - len(ema26)
        ema12_aligned = ema12[diff:]

        # MACD line
        macd_line = []
        for i in range (len(ema26)):
            macd_line.append(ema12_aligned[i]-ema26[i])
        
        # signal line 
        signal_line = self.signal_ema.calculate(macd_line)

        # create diff2 to calculate histogram
        diff2 = len(macd_line) - len(signal_line)
        macd_line_aligned = macd_line[diff2:]

        # calculate histogram 
        histogram=[]
        for i in range (len(signal_line)):
            histogram.append(macd_line_aligned[i]-signal_line[i])
        
        return macd_line,signal_line,histogram

# ATR
class ATR:
    def __init__(self,period):
        self.period=period
    
    def calculate(self,closes,highs,lows):
        # True range is the widest range of current period high-current period low
        # abs value of curr period high - previous period close
        # abs value of curr period low  - prev period close
        if not closes or not highs or not lows:
            return None
        true_range =[]
        for i in range (1,len(closes)):
            tr1= highs[i] - lows[i]
            tr2= abs(highs[i]-closes[i-1])
            tr3= abs(lows[i]-closes[i-1])

            true_range.append(max(tr1,tr2,tr3))
        # seed with SMA of first period atr
        avg_true_range_seed = sum(true_range[:self.period])/self.period
        atr = [avg_true_range_seed]
        for i in range (self.period,len(true_range)):
            new_atr = (atr[-1] * (self.period - 1) + true_range[i])/self.period
            atr.append(new_atr)
        return atr
    
if __name__ == "__main__":
    import MetaTrader5 as mt5
    from core.mt5_connector import MT5_connection

    conn = MT5_connection()
    try:
        conn.connect()

        # pull test data
        bars = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_H1, 0, 800)
        closes = [bar[4] for bar in bars]
        highs  = [bar[2] for bar in bars]
        lows   = [bar[3] for bar in bars]

        # test EMA
        ema = EMA(200)
        ema_result = ema.calculate(closes)
        print(f"EMA200     : {ema_result[-1]:.5f}")

        # test TEMA
        tema = TEMA(200)
        tema_result = tema.calculate(closes)
        print(f"TEMA200    : {tema_result[-1]:.5f}")

        # test ROC
        roc = ROC(12)
        roc_result = roc.calculate(closes)
        print(f"ROC12      : {roc_result:.4f}%")

        # test RSI
        rsi = RSI(14)
        rsi_result = rsi.calculate(closes)
        print(f"RSI14      : {rsi_result[-1]:.2f}")

        # test MACD
        macd = MACD()
        macd_line, signal_line, histogram = macd.calculate(closes)
        print(f"MACD Line  : {macd_line[-1]:.5f}")
        print(f"Signal     : {signal_line[-1]:.5f}")
        print(f"Histogram  : {histogram[-1]:.5f}")

        # test ATR
        atr = ATR(14)
        atr_result = atr.calculate(closes, highs, lows)
        print(f"ATR14      : {atr_result[-1]:.5f}")

    except ConnectionError as e:
        print(e)
    finally:
        conn.disconnect()


        
    