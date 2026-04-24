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

        tema=[]
        for i in range (len(ema3)):
            tema.append(3*ema1[i] - 3*ema2[i] + ema3[i])
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


        
    