import MetaTrader5 as mt5

# connect to mt5
class MT5_connection:
    def __init__(self):
        self.connected = False
    def connect(self):
        if not mt5.initialize():
            raise ConnectionError(f"MT 5 initialization failed: {mt5.last_error()}")
        self.connected=True
        print("MT 5 connected successfully")
    def disconnect(self):
        mt5.shutdown()
        self.connected=False
        print("MT 5 disconnected")