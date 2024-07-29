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
    # 初始化时接收一个策略对象，并存储记录
    def __init__(self, strategy):
        self.strategy = strategy
        self.data = []

    # 这个方法记录每个时间点的交易数据
    def record(self):
        current_value = self.strategy.broker.getvalue()
        initial_value = self.strategy.broker.startingcash
        pnl_pct = (current_value - initial_value) / initial_value * 100 if initial_value != 0 else 0

        self.data.append({
            'datetime': self.strategy.data.datetime.datetime(),
            'open': self.strategy.data.open[0],
            'high': self.strategy.data.high[0],
            'low': self.strategy.data.low[0],
            'close': self.strategy.data.close[0],
            'vwma': getattr(self.strategy, 'vwma', [None])[0],
            'atr': getattr(self.strategy, 'atr', [None])[0],
            'position_size': self.strategy.position.size,
            'equity': self.strategy.broker.getvalue(),
            'buy_signal': self.strategy.buy_signal() if hasattr(self.strategy, 'buy_signal') else None,
            'sell_signal': self.strategy.sell_signal() if hasattr(self.strategy, 'sell_signal') else None,
            'trade_count': getattr(self.strategy, 'trade_count', 0),
            'pnl_pct': pnl_pct if initial_value != 0 else None 
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
        commission = CONFIG['commission_rate']
        slippage = CONFIG['slippage'] 
        close_buy = self.data.close[0] * (1 + slippage)
        close_sell = self.data.close[0] * (1 - slippage)
        value = self.broker.getvalue() 

        if long_signal and self.addition_count == 0:
            self.first_order_amount = self.p.base_order_amount * (1 - commission)
            size = int(self.first_order_amount / close_buy)
            self.order = self.buy(size=size)
            self.last_entry_price = close_buy
            self.total_position = size
            self.addition_count = 1
            self.total_amount = self.first_order_amount
            
        elif long_signal and self.addition_count < self.p.max_additions and self.total_amount < value:
            if self.data.close < self.last_entry_price - self.p.k * self.atr:
                add_amount = self.first_order_amount * (self.params.dca_multiplier ** self.addition_count) * (1 - commission)
                size = int(add_amount / close_buy)
                self.order = self.buy(size=size)
                self.last_entry_price = close_buy
                self.addition_count += 1
                self.total_position += size
                self.total_amount += add_amount

        elif short_signal and self.total_position > 0:
            self.takeprofit = True
            price_change = self.data.close[0] - self.last_entry_price
            if price_change >= self.total_position * self.atr:
                self.order = self.sell(size=self.total_position, price = close_sell)
                self.reset_position()
                
            elif price_change <= -self.total_position * self.atr:
                self.takeprofit = False
                self.order = self.sell(size=self.total_position, price = close_sell)
                self.reset_position()

    def reset_position(self):
        self.addition_count = 0
        self.total_position = 0
        self.total_amount = 0
        self.last_entry_price = None

    def buy_signal(self):
        return self.data.close < self.vwma - self.p.k * self.atr

    def sell_signal(self):
        return self.data.close > self.vwma + self.p.k * self.atr
    
    # 计算盈亏利润
    def calculate_net_profit(self, sell_size):
        avg_buy_price = self.total_amount / self.total_position if self.total_position > 0 else 0
        sell_price = self.data.close[0] * (1 - CONFIG['slippage'])
        sell_amount = sell_size * sell_price * (1 - CONFIG['commission_rate'])
        buy_cost = sell_size * avg_buy_price
        net_profit = sell_amount - buy_cost
        
        return net_profit

    def notify_order(self, order):
        # 首先通知所有分析器
        for analyzer in self.analyzers:
            if hasattr(analyzer, 'notify_order'):
                analyzer.notify_order(order)

        # 处理订单状态
        if order.status in [order.Submitted, order.Accepted]:
            return  # 订单已提交或已接受，无需进一步处理

        if order.status == order.Completed:
            if order.ref not in self.processed_orders:
                self.processed_orders.add(order.ref)  # 标记订单为已处理
                self.trade_count += 1
                order_time = self.data.datetime.datetime() 
                if order.isbuy():
                    if self.addition_count == 1:
                        print(f'{order_time} 开仓: 买入 {order.executed.size} 股，价格: {order.executed.price}')
                    else:
                        print(f'{order_time} 加仓: 买入 {order.executed.size} 股，价格: {order.executed.price}')
                elif order.issell():
                    try:
                        net_profit = abs(self.calculate_net_profit(order.executed.size))
                        if self.takeprofit:
                            print(f'{order_time} 止盈：卖出 {order.executed.size} 股，价格: {order.executed.price}, 收益: {net_profit:.2f}')
                        else:
                            print(f'{order_time} 止损：卖出 {order.executed.size} 股，价格: {order.executed.price}, 亏损: {net_profit:.2f}')
                    except Exception as e:
                        print(f"计算净利润时出错: {e}")
                self.trade_recorder.record()
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f'订单被取消/保证金不足/被拒绝，订单状态: {order.status}')

        self.order = None  # 重置订单
                
class BuyAndHoldStrategy(bt.Strategy):
    params = (('timeframe', None),)

    def __init__(self):
        if self.p.timeframe not in CONFIG['strategies']['buyandhold']['enabled_timeframes']:
            raise ValueError(f"Unsupported timeframe: {self.p.timeframe}")
        
        self.order = None
        self.bought = False
        self.trade_count = 0
        self.trade_recorder = TradeRecorder(self)
        self.processed_orders = set()  # 新增：用于跟踪已处理的订单
        self.first_bar = True # 新增：第一根bar检查

    def next(self):
        cash = self.broker.getcash()
        slippage = CONFIG['slippage']
        commission = CONFIG['commission_rate']
        price = self.data.close[0] * (1 + slippage)

        if self.first_bar and not self.bought and not self.order:
            size = cash * (1 - commission) / price  # 买入所有可用资金对应的股数
            size = int(size) 
            
            if size > 0:
                self.order = self.buy(size=size)
                print(f'尝试买入: {size} 股，当前价格: {price}')
            else:
                print(f'可用资金不足，无法买入。现金: {cash}, 价格: {price}')
    
        self.first_bar = False
        self.trade_recorder.record()

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status == order.Completed and order.ref not in self.processed_orders:
            self.processed_orders.add(order.ref)
            self.trade_count += 1
            order_time = self.data.datetime.datetime() 
            if order.isbuy():
                print(f'{order_time} 买入并持有: 买入 {order.executed.size} 股，价格: {order.executed.price}')
                self.bought = True
            self.order = None
            self.trade_recorder.record()
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f'订单失败。状态: {order.status}')
            self.bought = False
            self.order = None

    def buy_signal(self):
        return not self.position and self.first_bar

    def sell_signal(self):
        return False