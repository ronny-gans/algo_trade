import MetaTrader5 as mt5

# class account contains username and balance
class Account:
    def __init__(self,user,password):
        self.user=user
        self.password=password
    def authentication (self):
        authorized = mt5.login(self.user,self.password)
        if authorized:
            account_info = mt5.account_info()._asdict()
            return account_info
        else:
            print("failed to connect to account, error code=",mt5.last_error())
        mt5.shutdown()

