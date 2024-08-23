# strategy.py

import backtrader as bt
from config import CONFIG
import pandas as pd

# 计算VWMA
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



# 记录交易过程中的数据
class TradeRecorder:
    def __init__(self, strategy):
        self.strategy = strategy
        self.data = []
        self.current_trade = None

    def record(self, order=None): 
        current_cash = self.strategy.broker.getcash()
        current_position = self.strategy.position.size
        current_price = self.strategy.data.close[0]
        asset_value = current_position * current_price
        total_assets = current_cash + asset_value
        capital_utilization_rate = asset_value / total_assets
        initial_value = self.strategy.broker.startingcash
        net_value = total_assets / initial_value if initial_value != 0 else 0

        if order and order.status == order.Completed:
            if order.isbuy():
                buy_sell = '买' if self.strategy.position.size == order.size else '加'
            elif order.issell():
                buy_sell = '卖'
            trade_price = order.executed.price
            trade_size = order.executed.size
            trade_value = trade_price * trade_size
            trade_cost = trade_value * CONFIG['friction_cost']
        else:
            buy_sell = '无'
            trade_price = current_price
            trade_size = trade_value = trade_cost = 0

        unrealized_pnl = asset_value - (current_position * self.strategy.position.price) if current_position > 0 else 0

        self.data.append({
            '时间': self.strategy.data.datetime.datetime(),
            'open': self.strategy.data.open[0],
            'high': self.strategy.data.high[0],
            'low': self.strategy.data.low[0],
            'close': self.strategy.data.close[0],
            '交易状态': buy_sell,
            '交易价格': trade_price,
            '交易数量': trade_size,
            '交易金额': trade_value,
            '交易费用': trade_cost,
            '当前持仓': current_position,
            '可用资金': current_cash,
            '资金利用率':capital_utilization_rate,
            '资产价值':asset_value,
            '未实现盈亏': unrealized_pnl,
            '总资产': total_assets,
            '净值': round(net_value, 4)
        })
            
    def get_analysis(self):
        return pd.DataFrame(self.data)

    def record_trade(self):
        # 仅在有交易发生时调用
        if self.strategy.order:  # 检查当前是否有订单
            self.record(self.strategy.order)

    
class StrategyFactory:
    strategy_map = {
        # 'vad': 'VADStrategy',
        # 'buyandhold': 'BuyAndHoldStrategy',
        'SupertrendATR':'SupertrendATR',
        'SupertrendSd':'SupertrendSd',
        'SupertrendMf':'SupertrendMf'
    }

    @staticmethod
    def get_strategy(name, **kwargs):
        strategy_class_name = StrategyFactory.strategy_map.get(name)
        if strategy_class_name is None:
            raise ValueError(f"Strategy '{name}' not implemented")
        
        module = __import__('strategy', fromlist=[strategy_class_name])
        return getattr(module, strategy_class_name)



class VADStrategy(bt.Strategy):
    params = (
        ('timeframe', None),
        ('k', None),
        ('base_order_amount', None),
        ('dca_multiplier', None),
        ('max_additions', None),
        ('vwma_period', None),
        ('atr_period', None),
    )

    def __init__(self):
        if self.p.timeframe not in CONFIG['strategies']['vad']['enabled_timeframes']:
            raise ValueError(f"Unsupported timeframe: {self.p.timeframe}")

        # 使用传入的参数或默认值
        self.k = self.p.k
        self.base_order_amount = self.p.base_order_amount
        self.dca_multiplier = self.p.dca_multiplier
        self.max_additions = self.p.max_additions
        self.vwma_period = self.p.vwma_period
        self.atr_period = self.p.atr_period

        self.vwma = VolumeWeightedMovingAverage(self.data, period=self.vwma_period)
        self.atr = bt.indicators.ATR(self.data, period=self.atr_period)

        self.addition_count = 0
        self.takeprofit = False
        self.last_entry_price = None
        self.total_position = 0
        self.total_amount = 0
        self.trade_count = 0
        self.trade_recorder = TradeRecorder(self)
        self.processed_orders = set()  # 新增：用于跟踪已处理的订单
        self.first_order_amount = None # 新增：用于跟踪base_order_amount（考虑佣金）
        self.order = None # 用于记录交易

    def next(self):
        long_signal = self.data.close < self.vwma - self.p.k * self.atr
        short_signal = self.data.close > self.vwma + self.p.k * self.atr
        friction_cost = CONFIG['friction_cost']
        close_buy = self.data.close[0] * (1 + friction_cost)
        close_sell = self.data.close[0] * (1 - friction_cost)
        value = self.broker.getcash() 
        self.buy_signal_flag = False
        self.sell_signal_flag = False

        if long_signal and self.addition_count == 0:
            self.first_order_amount = self.p.base_order_amount * (1+friction_cost)
            size = int(self.first_order_amount / close_buy)
            self.order = self.buy(size=size)
            self.last_entry_price = close_buy
            self.total_position = size
            self.addition_count = 1
            self.total_amount = self.first_order_amount
            self.buy_signal_flag = True

        elif long_signal and 0 < self.addition_count < self.p.max_additions and self.total_amount < value:
            if self.data.close < self.last_entry_price - self.p.k * self.atr:
                add_amount = self.first_order_amount * (self.params.dca_multiplier ** self.addition_count) 
                size = int(add_amount / close_buy)
                self.order = self.buy(size=size)
                self.last_entry_price = close_buy
                self.addition_count += 1
                self.total_position += size
                self.total_amount += add_amount
                self.buy_signal_flag = True

        elif short_signal and self.total_position > 0:
            self.takeprofit = True
            price_change = self.data.close[0] - self.last_entry_price
            if price_change >= self.total_position * self.atr:
                self.order = self.sell(size=self.total_position, price = close_sell)
                self.reset_position()
                self.sell_signal_flag = True

            elif price_change <= -self.total_position * self.atr:
                self.takeprofit = False
                self.order = self.sell(size=self.total_position, price = close_sell)
                self.reset_position()
                self.sell_signal_flag = True
        
        self.trade_recorder.record()
    
    def reset_position(self):
        self.addition_count = 0
        self.total_position = 0
        self.total_amount = 0
        self.last_entry_price = None

    def buy_signal(self):
        return self.buy_signal_flag

    def sell_signal(self):
        return self.sell_signal_flag
    
    def calculate_net_profit(self, sell_size):
        avg_buy_price = self.total_amount / self.total_position if self.total_position > 0 else 0
        sell_price = self.data.close[0] * (1 - CONFIG['friction_cost'])
        sell_amount = sell_size * sell_price
        buy_cost = sell_size * avg_buy_price
        net_profit = sell_amount - buy_cost

        return net_profit

    def notify_order(self, order):
        for analyzer in self.analyzers:
            if hasattr(analyzer, 'notify_order'):
                analyzer.notify_order(order)

        if order.status in [order.Submitted, order.Accepted]:
            return  

        if order.status == order.Completed and order.ref not in self.processed_orders:
            self.processed_orders.add(order.ref)
            self.trade_count += 1
            
            self.trade_recorder.record(order)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f'订单被取消/保证金不足/被拒绝，订单状态: {order.status}')

        self.order = None  # 重置订单


class BuyAndHoldStrategy(bt.Strategy):
    params = (('timeframe', None),)

    def __init__(self):
        if self.p.timeframe not in CONFIG['strategies']['buyandhold']['enabled_timeframes']:
            raise ValueError(f"不支持的timeframe: {self.p.timeframe}")
        
        self.order = None
        self.bought = False
        self.trade_count = 0
        self.trade_recorder = TradeRecorder(self)
        self.processed_orders = set()
        self.first_bar = True

    def next(self):
        cash = self.broker.getcash()
        friction_cost = CONFIG['friction_cost']
        price = self.data.close[0] * (1 + friction_cost)

        if self.first_bar and not self.bought and not self.order:
            size =  int(cash / price) 

            if size > 0:
                self.order = self.buy(size=size)
                # print(f'尝试买入: {size} 股，当前价格: {price}')
            else:
                print(f'可用资金不足，无法买入。现金: {cash}, 价格: {price}')
    
        self.first_bar = False
        self.trade_recorder.record()

    def notify_order(self, order):
        for analyzer in self.analyzers:
            if hasattr(analyzer, 'notify_order'):
                analyzer.notify_order(order)

        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status == order.Completed and order.ref not in self.processed_orders:
            self.processed_orders.add(order.ref)
            self.trade_count += 1
            order_time = self.data.datetime.datetime() 

            if order.isbuy():
                # print(f'{order_time} 买入并持有: 买入 {order.executed.size} 股，价格: {order.executed.price}')
                self.bought = True
            self.order = None
            self.trade_recorder.record(order)
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f'订单失败。状态: {order.status}')
            self.bought = False
            self.order = None

    def buy_signal(self):
        return not self.position and self.first_bar

    def sell_signal(self):
        return False


class SupertrendATR(bt.Strategy):
    params = (
        ('timeframe', None),
        ('vwma_period', None),
        ('atr_period', None),
        ('k', None)
    )

    def __init__(self):
        if self.p.timeframe not in CONFIG['strategies']['SupertrendATR']['enabled_timeframes']:
            raise ValueError(f"不支持的timeframe: {self.p.timeframe}")

        self.k = self.p.k
        self.close = self.datas[0].close
        self.order = None
        self.trade_recorder = TradeRecorder(self)

        self.vwma_period = self.p.vwma_period
        self.vwma = VolumeWeightedMovingAverage(self.data, period=self.vwma_period)

        self.atr_period = self.p.atr_period
        self.atr = bt.indicators.ATR(self.data, period=self.atr_period)

    def next(self):
        long_signal = self.data.close < self.vwma - self.p.k * self.atr
        short_signal = self.data.close > self.vwma + self.p.k * self.atr
        friction_cost = CONFIG['friction_cost']
        close_buy = self.data.close[0] * (1 + friction_cost)
        close_sell = self.data.close[0] * (1 - friction_cost)
        cash = self.broker.getcash() 
        self.buy_signal_flag = False
        self.sell_signal_flag = False

        # 检查是否有待处理的订单
        if self.order:
            return

        # 检查是否已经持仓
        if not self.position:
            if long_signal:
                size = cash / close_buy
                self.order = self.buy(size=size)
                self.buy_signal_flag = True
        else:
            if short_signal:
                size = self.position.size
                self.order = self.sell(size=size, price=close_sell)
                self.sell_signal_flag = True
    
        self.trade_recorder.record()

    def notify_order(self, order):
        for analyzer in self.analyzers:
            if hasattr(analyzer, 'notify_order'):
                analyzer.notify_order(order)

        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            self.trade_recorder.record(order)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f'订单失败。状态: {order.status}')

        self.order = None

    def buy_signal(self):
        return self.buy_signal_flag

    def sell_signal(self):
        return self.sell_signal_flag

class SupertrendSd(bt.Strategy):
    params = (
        ('timeframe', None),
        ('k', None)
    )

    def __init__(self):
        if self.p.timeframe not in CONFIG['strategies']['SupertrendSd']['enabled_timeframes']:
            raise ValueError(f"不支持的timeframe: {self.p.timeframe}")

        self.k = self.p.k
        self.std = bt.indicators.StandardDeviation(self.data.close, period=len(self.data))
        self.close = self.datas[0].close
        self.order = None
        self.trade_recorder = TradeRecorder(self)
        
    def next(self):
        friction_cost = CONFIG['friction_cost']
        close_buy = self.data.close[0] * (1 + friction_cost)
        close_sell = self.data.close[0] * (1 - friction_cost)
        cash = self.broker.getcash() 
        self.buy_signal_flag = False
        self.sell_signal_flag = False

        # 如果数据不足，不进行操作
        if len(self) <= self.std.period:
            return
    
        # 检查是否有待处理的订单
        if self.order:
            return

        # 检查是否已经持仓
        if not self.position:
            if self.close[0] > self.close[-1] + self.p.k * self.std[0]:
                size = cash / close_buy
                self.order = self.buy(size=size)
        else:
            if self.close[0] < self.close[-1] - self.p.k * self.std[0]:
                size = self.position.size
                self.order = self.sell(size=size, price=close_sell)
    
        self.trade_recorder.record()

    def notify_order(self, order):
        for analyzer in self.analyzers:
            if hasattr(analyzer, 'notify_order'):
                analyzer.notify_order(order)

        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            self.trade_recorder.record(order)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f'订单失败。状态: {order.status}')

        self.order = None

    def buy_signal(self):
        return self.buy_signal_flag

    def sell_signal(self):
        return self.sell_signal_flag

class SupertrendMf(bt.Strategy):
    params = (
        ('timeframe', None),
        ('p', None),
        ('k', None),
        ('vwma_period', None),
        ('atr_period', None),
    )

    def __init__(self):
        if self.p.timeframe not in CONFIG['strategies']['SupertrendMf']['enabled_timeframes']:
            raise ValueError(f"不支持的timeframe: {self.p.timeframe}")

        self.k = self.p.k
        self.p = self.p.p
        self.close = self.datas[0].close
        self.order = None
        self.trade_recorder = TradeRecorder(self)

        self.vwma_period = self.p.vwma_period
        self.vwma = VolumeWeightedMovingAverage(self.data, period=self.vwma_period)

        self.atr_period = self.p.atr_period
        self.atr = bt.indicators.ATR(self.data, period=self.atr_period)

    def next(self):
        ATR_long_signal = self.data.close < self.vwma - self.p.p * self.atr
        ATR_short_signal = self.data.close > self.vwma + self.p.p * self.atr

        SD_long_signal = self.close[0] > self.close[-1] + self.p.k * self.std[0]
        SD_short_signal = self.close[0] < self.close[-1] - self.p.k * self.std[0]

        long_signal = ATR_long_signal or SD_long_signal
        strong_long_signal = ATR_long_signal and SD_long_signal
        short_signal = ATR_short_signal or  SD_short_signal

        friction_cost = CONFIG['friction_cost']
        close_buy = self.data.close[0] * (1 + friction_cost)
        close_sell = self.data.close[0] * (1 - friction_cost)
        cash = self.broker.getcash() 
        self.buy_signal_flag = False
        self.sell_signal_flag = False

        # 检查是否有待处理的订单
        if self.order:
            return

        # 检查是否已经持仓
        if not self.position:
            if long_signal:
                size = cash / close_buy
                self.order = self.buy(size=size)
            elif strong_long_signal:
                size = (cash / close_buy) * 1.5
                self.order = self.buy(size=size)
        else:
            if short_signal:
                size = self.position.size
                self.order = self.sell(size=size, price=close_sell)
    
        self.trade_recorder.record()

    def notify_order(self, order):
        for analyzer in self.analyzers:
            if hasattr(analyzer, 'notify_order'):
                analyzer.notify_order(order)

        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            self.trade_recorder.record(order)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f'订单失败。状态: {order.status}')

        self.order = None

    def buy_signal(self):
        return self.buy_signal_flag

    def sell_signal(self):
        return self.sell_signal_flag