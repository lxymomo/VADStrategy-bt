import backtrader as bt
import config
from indicators import VWMA

'''
策略
'''

class VADStrategy(bt.Strategy):
    params = (
        ('k', config.vad_strategy_params['k']),
        ('base_order_amount', config.vad_strategy_params['base_order_amount']),
        ('dca_multiplier', config.vad_strategy_params['dca_multiplier']),
        ('number_of_dca_orders', config.vad_strategy_params['number_of_dca_orders'])
    )

    def __init__(self):
        self.atr = bt.indicators.ATR(self.data, period=14)
        self.vwma = VWMA(self.data, period=config.indicator_params['vwma_period'])
        self.add_long_counter = 1
        self.last_dca_price = 0.0
        self.total_long_trades = 0
        self.buy_count = 0
        self.sell_count = 0

    def next(self):
        # 确保ATR指标已计算出有效值
        if len(self) < 14:
            return
        
        k_atr = self.params.k * self.atr[0]
        take_profit_percent = self.params.k * self.atr[0]
        stop_loss_percent = self.params.k * self.atr[0]

        vwma_above = self.vwma.vwma[0] + k_atr
        vwma_below = self.vwma.vwma[0] - k_atr
        long_signal = self.data.close[0] < vwma_below
        short_signal = self.data.close[0] > vwma_above

        self.log(f'Close={self.data.close[0]}, VWMA={self.vwma.vwma[0]}, Long Signal={long_signal}, Short Signal={short_signal}')

        # 开仓逻辑
        if long_signal and self.total_long_trades == 0:
            self.open_long_position()
        elif long_signal and self.total_long_trades > 0 and self.total_long_trades < self.params.number_of_dca_orders:
            self.add_to_long_position()

        # 计算未平仓利润
        if self.position.size > 0:
            self.check_profit_and_loss(take_profit_percent, stop_loss_percent, short_signal)

    # 开仓逻辑
    def open_long_position(self):
        size = self.params.base_order_amount / self.data.close[0]
        self.buy(size=size)
        self.last_dca_price = self.params.base_order_amount
        self.total_long_trades += 1
        self.buy_count += 1
        self.log(f'Open order: Size={size}, Price={self.data.close[0]}')

    # 加仓逻辑
    def add_to_long_position(self):
        if self.data.close[0] <= (self.position.price - self.params.k * self.atr[0]):
            self.last_dca_price *= self.params.dca_multiplier
            size = self.last_dca_price / self.data.close[0]
            self.buy(size=size)
            self.add_long_counter += 1
            self.total_long_trades += 1
            self.buy_count += 1
            self.log(f'Add order: Size={size}, Price={self.data.close[0]}')

    def check_profit_and_loss(self, take_profit_percent, stop_loss_percent, short_signal):
        cost_basis = self.position.price
        current_price = self.data.close[0]
        position_size = self.position.size

        # 止盈逻辑
        if short_signal and (current_price - cost_basis) >= take_profit_percent * position_size:
            self.sell(size=position_size)
            self.sell_count += 1
            self.total_long_trades = 0
            self.add_long_counter = 0
            self.log(f'Take Profit: Size={position_size}, Price={current_price}')

        # 止损逻辑
        elif short_signal and (current_price - cost_basis) <= -stop_loss_percent * position_size:
            self.sell(size=position_size)
            self.sell_count += 1
            self.total_long_trades = 0
            self.add_long_counter = 0
            self.log(f'Stop Loss: Size={position_size}, Price={current_price}')

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')

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
