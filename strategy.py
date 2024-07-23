# strategy.py

import backtrader as bt
from config import CONFIG
import pandas as pd

# 计算VWMA
class VolumeWeightedMovingAverage(bt.Indicator):
    lines = ('vwma',)
    params = (('period', CONFIG['strategy_params']['vad']['vwma_period']),)

    def __init__(self):
        self.addminperiod(self.params.period)

    def next(self):
        total_volume = 0
        total_price_volume = 0

        for i in range(-self.params.period + 1, 1):
            total_volume += self.data.volume[i]
            total_price_volume += self.data.close[i] * self.data.volume[i]

        self.lines.vwma[0] = total_price_volume / total_volume

# 记录交易过程中的数据
class TradeRecorder:
    # 初始化时接收一个策略对象，并存储记录
    def __init__(self, strategy):
        self.strategy = strategy
        self.data = []

    # 这个方法记录每个时间点的交易数据
    def record(self):
        self.data.append({
            'datetime': self.strategy.data.datetime.datetime(),
            'close': self.strategy.data.close[0],
            'vwma': getattr(self.strategy, 'vwma', [None])[0],
            'atr': getattr(self.strategy, 'atr', [None])[0],
            'position_size': self.strategy.position.size,
            'equity': self.strategy.broker.getvalue(),
            'buy_signal': self.strategy.buy_signal() if hasattr(self.strategy, 'buy_signal') else None,
            'sell_signal': self.strategy.sell_signal() if hasattr(self.strategy, 'sell_signal') else None
        })

    # 将记录的数据转换为pandas DataFrame格式
    def get_analysis(self):
        return pd.DataFrame(self.data)
    
class StrategyFactory:
    strategy_map = {
        'vad': 'VADStrategy',
        'buyandhold': 'BuyAndHoldStrategy'
    }

    @staticmethod
    def get_strategy(name, **kwargs):
        strategy_class_name = StrategyFactory.strategy_map.get(name)
        if strategy_class_name is None:
            raise ValueError(f"Strategy '{name}' not implemented")
        
        # 动态导入策略类
        module = __import__('strategy', fromlist=[strategy_class_name])
        strategy_class = getattr(module, strategy_class_name)

        class RecordingStrategy(strategy_class):
            def __init__(self):
                super(RecordingStrategy, self).__init__()
                self.trade_recorder = TradeRecorder(self)

            def notify_order(self, order):
                if order.status == order.Completed:
                    self.trade_recorder.record()

            def next(self):
                super(RecordingStrategy, self).next()

        return RecordingStrategy

class VADStrategy(bt.Strategy):
    params = CONFIG['strategy_params']['vad']

    def __init__(self):
        self.vwma = VolumeWeightedMovingAverage(self.data, period=self.p.vwma_period)
        self.atr = bt.indicators.ATR(self.data, period=self.p.atr_period)
        self.addition_count = 0
        self.last_entry_price = None
        self.total_position = 0
        self.total_amount = 0

    def next(self):
        long_signal = self.data.close < self.vwma - self.p.k * self.atr
        short_signal = self.data.close > self.vwma + self.p.k * self.atr

        if long_signal and self.addition_count == 0:
            size = self.p.base_order_amount / self.data.close[0]
            self.buy(size=size)
            self.last_entry_price = self.data.close[0]
            self.total_position = size
            self.addition_count = 1
            self.total_amount = self.p.base_order_amount
            print(f'开仓: 买入 {size} 股，价格: {self.data.close[0]}')

        elif long_signal and self.addition_count < self.p.max_additions and self.total_amount < self.p.max_amount:
            if self.data.close < self.last_entry_price - self.p.k * self.atr:
                add_amount = self.p.base_order_amount * (self.params.dca_multiplier ** self.addition_count)
                size = add_amount / self.data.close[0]
                self.buy(size=size)
                self.last_entry_price = self.data.close[0]
                self.addition_count += 1
                self.total_position += size
                self.total_amount += add_amount
                print(f'加仓: 买入 {size} 股，总持仓: {self.total_position} 股，价格: {self.data.close[0]}')

        elif short_signal and self.total_position > 0:
            price_change = self.data.close[0] - self.last_entry_price
            if price_change >= self.total_position * self.atr:
                self.sell(size=self.total_position)
                print(f'止盈: 卖出所有持仓，总持仓: {self.total_position} 股，价格: {self.data.close[0]}')
                self.reset_position()

            elif price_change <= -self.total_position * self.atr:
                self.sell(size=self.total_position)
                print(f'止损: 卖出所有持仓，总持仓: {self.total_position} 股，价格: {self.data.close[0]}')
                self.reset_position()

    def reset_position(self):
        self.addition_count = 0
        self.total_position = 0
        self.total_amount = 0
        self.last_entry_price = None

class BuyAndHoldStrategy(bt.Strategy):
    params = CONFIG['strategy_params']['vad']

    def __init__(self):
        self.order = None

    def next(self):
        if not self.position and not self.order:
            size = self.p.max_amount / self.data.close[0]
            self.order = self.buy(size=size)

    def buy_signal(self):
        return not self.position

    def sell_signal(self):
        return False