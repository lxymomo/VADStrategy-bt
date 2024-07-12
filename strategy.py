import backtrader as bt
import config
from indicators import VWMA

'''
策略
'''

class VADStrategy(bt.Strategy):
    params = (
        ('k', 1.6),
        ('base_order_amount', 100000),
        ('DCAmultiplier', 1.5),
        ('max_dca_count', 4),
        ('profit_atr_multiplier', 1),  # 止盈ATR乘数
        ('loss_atr_multiplier', 1),    # 止损ATR乘数
    )

    def __init__(self):
        self.vwma200 = bt.indicators.WeightedMovingAverage(
            self.data.close, period=200, subplot=False
        )
        self.atr = bt.indicators.ATR(self.data, period=14)
        
        self.long_signal = self.data.close < self.vwma200 - self.p.k * self.atr
        self.short_signal = self.data.close > self.vwma200 + self.p.k * self.atr
        
        self.order = None
        self.dca_count = 0
        self.last_buy_price = 0
        self.buy_count = 0
        self.sell_count = 0

    def next(self):
        if self.order:
            return

        #开仓逻辑
        if not self.position:
            if self.long_signal:
                size = self.p.base_order_amount / self.data.close
                self.order = self.buy(size=size)
                self.dca_count = 1
                self.last_buy_price = self.data.close[0]
        
        elif self.position.size > 0:
            # 加仓逻辑
            if self.long_signal and self.data.close < (self.last_buy_price - self.p.k * self.atr) and self.dca_count < self.p.max_dca_count:
                dca_amount = self.p.base_order_amount * (self.p.DCAmultiplier ** (self.dca_count - 1))
                size = dca_amount / self.data.close
                self.order = self.buy(size=size)
                self.dca_count += 1
                self.last_buy_price = self.data.close[0]
            
            # 止盈止损逻辑
            total_profit = (self.data.close[0] - self.position.price) * self.position.size 
            if self.short_signal or total_profit >= self.position.size * self.atr[0] * self.p.profit_atr_multiplier or total_profit <= -self.position.size * self.atr[0] * self.p.loss_atr_multiplier:
                self.order = self.close()

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.buy_count += 1
            elif order.issell():
                self.sell_count += 1
                self.dca_count = 0

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} {txt}')

class BuyAndHoldStrategy(bt.Strategy):
    def __init__(self):
        self.buy_count = 0
        self.sell_count = 0
        self.order = None  
        self.buy_executed = False
        self.sell_executed = False
        # self.log(f'Initial Cash: {self.broker.get_cash()}')

    def next(self):
        # 在第一个可交易的 bar 买入
        if len(self) == 1 and not self.position and not self.buy_executed:
            cash = self.broker.get_cash()
            close_price = self.data.close[0]
            commission_rate = config.broker_params['commission_rate']
            slippage_rate = config.broker_params['slippage']

            # 计算总成本
            size = int(cash / (close_price * (1 + commission_rate + slippage_rate)))
            total_cost = size * close_price * (1 + commission_rate + slippage_rate)
            
            # self.log(f'Trying to buy: Cash={cash}, Close={close_price}, Size={size}, Total Cost={total_cost}')
            if total_cost <= cash and size > 0:
                self.order = self.buy(size=size)
                self.buy_executed = True
                # self.log(f'Buy order created: Size={size}')

        # 判断是否达到最后一个bar
        if len(self) == len(self.data) - 1 and self.position and not self.sell_executed:
            self.log(f'Trying to sell: Position Size={self.position.size}')
            self.order = self.sell(size=self.position.size)
            self.sell_executed = True

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                # self.log(f'BUY COMPLETED, Price: {order.executed.price}, Size: {order.executed.size}')
                self.buy_count += 1
            elif order.issell():
                # self.log(f'SELL COMPLETED, Price: {order.executed.price}, Size: {order.executed.size}')
                self.sell_count += 1
            self.order = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # self.log(f'Order Canceled/Margin/Rejected: Status={order.status}, Ref={order.ref}')
            self.order = None

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')
