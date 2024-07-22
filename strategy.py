# strategy.py
import backtrader as bt

class StrategyFactory:
    @staticmethod
    def get_strategy(strategy_name, params):
        if strategy_name == "VAD":
            return VADStrategy
        elif strategy_name == "BuyAndHold":
            return BuyAndHoldStrategy
        else:
            raise ValueError("Unknown strategy")

class VADStrategy(bt.Strategy):
    params = (
        ('k', 1.6),
        ('base_order_amount', 10000),
        ('dca_multiplier', 1.5),
        ('number_of_dca_orders', 3),
    )

    def __init__(self):
        pass

    def next(self):
        pass

class BuyAndHoldStrategy(bt.Strategy):
    def __init__(self):
        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            self.order = self.buy()

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                print(f"BUY EXECUTED, {order.executed.price}")
            elif order.issell():
                print(f"SELL EXECUTED, {order.executed.price}")

        self.order = None
