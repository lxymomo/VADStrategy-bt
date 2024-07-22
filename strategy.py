# strategy.py

import backtrader as bt
from config import CONFIG
import pandas as pd

class TradeRecorder:
    def __init__(self, strategy):
        self.strategy = strategy
        self.data = []

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

    def get_analysis(self):
        return pd.DataFrame(self.data)
    
class VolumeWeightedMovingAverage(bt.Indicator):
    lines = ('vwma',)
    params = (('period', 14),)

    def __init__(self):
        self.addminperiod(self.params.period)

    def next(self):
        total_volume = 0
        total_price_volume = 0

        for i in range(-self.params.period + 1, 1):
            total_volume += self.data.volume[i]
            total_price_volume += self.data.close[i] * self.data.volume[i]

        self.lines.vwma[0] = total_price_volume / total_volume

class StrategyFactory:
    @staticmethod
    def get_strategy(name, **kwargs):
        if name == 'vad':
            strategy_class = VADStrategy
        elif name == 'buyandhold':
            strategy_class = BuyAndHoldStrategy
        else:
            raise ValueError("Strategy not implemented")

        class RecordingStrategy(strategy_class):
            def __init__(self):
                super(RecordingStrategy, self).__init__()
                self.trade_recorder = TradeRecorder(self)

            def next(self):
                super(RecordingStrategy, self).next()
                self.trade_recorder.record()

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
    def __init__(self):
        self.order = None

    def next(self):
        if not self.position:
            self.buy()

    def buy_signal(self):
        return not self.position

    def sell_signal(self):
        return False
