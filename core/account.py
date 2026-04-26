import MetaTrader5 as mt5

# class account contains username and balance
class Account:
    def __init__(self):
        self.logged_in = False
    def is_login(self,user,password,server):
        # Convert user to int if it's a string, MT5 requires int for the account number
        authorized=mt5.login(int(user),password=password, server=server)
        if authorized:
            self.logged_in=True
            print("login successful")
        else:
            self.logged_in=False
            # Fixed the missing print here
            print(f"Login failed. Error code: {mt5.last_error()}")
        return self.logged_in
    def get_info (self):
        if self.logged_in==True:
            account_info = mt5.account_info()
            return account_info if account_info else None
        else:
            print("Not logged in. Error code",mt5.last_error())
        return None
    def get_balance(self):
        if self.logged_in==True:
            account_info = mt5.account_info()
            return account_info.balance # access directly from object
        else:
            print("Not logged in, error code=",mt5.last_error())
        return None
    # prevent duplicate trades on same pair
    def get_open_position(self, pair=None):
        if not self.logged_in:
            return None
        if pair:
            positions= mt5.positions_get(symbol=pair)
        else:
            positions=mt5.positions_get() # all open positions
        return positions if positions else []
    def get_trade_history(self, days=7):
        if not self.logged_in:
            return None
        from datetime import datetime,timedelta
        date_from = datetime.now() - timedelta(days=days)
        date_to = datetime.now()
        history = mt5.history_deals_get(date_from,date_to)
        return history if history else []
if __name__=="__main__":
    from core.mt5_connector import MT5_connection
    import os
    from dotenv import load_dotenv
    # connect to MT 5
    conn= MT5_connection()
    load_dotenv()
    try:
        conn.connect()
        # test class
        acc = Account()
        # call method and provide credentials
        user_name=os.getenv("MT5_USER")
        password=os.getenv("MT5_PASSWORD")
        server= os.getenv("MT5_SERVER") #server
        if acc.is_login(user_name,password,server):
            info=acc.get_info()
            balance=acc.get_balance()
            print(f"user    : {info.name}")
            print(f"company : {info.company}")
            print(f"equity  : USD {info.equity:.2f}")
            print(f"balance : USD {balance:.2f}")
        else:
            print("Could not proceed because login failed.")
    except ConnectionError as e:
        print(e)
    finally:
        conn.disconnect()



