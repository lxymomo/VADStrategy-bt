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

    '''
计算VWMA类
    定义属性(vwma, 14周期)
    
    初始化构造函数
        确保在计算前，至少有period根数据
    
    在每根bar计算
        总成交量 = 0
        加权价格 = 0

        遍历最近的period根数据:
            更新 总成交量 += 总成交量
            更新 加权价格 = close * 成交量

        vwma = 加权价格 / 总成交量
    '''

# 记录交易过程中的数据
class TradeRecorder:
    def __init__(self, strategy):
        self.strategy = strategy
        self.data = []
        self.current_trade = None

    def record(self, order):
        # 检查订单状态并记录
        if order.status == order.Completed:
            current_value = self.strategy.broker.getvalue()
            initial_value = self.strategy.broker.startingcash
            pnl = current_value - initial_value
            net_value = current_value / initial_value if initial_value != 0 else 0

            self.data.append({
                '时间': self.strategy.data.datetime.datetime(),
                '交易计数': getattr(self.strategy, 'trade_count', 0),
                '开盘价': self.strategy.data.open[0],
                '最高价': self.strategy.data.high[0],
                '最低价': self.strategy.data.low[0],
                '收盘价': self.strategy.data.close[0],
                '交易量': self.strategy.data.volume[0],
                '持仓': self.strategy.position.size,
                '当前余额': current_value,
                '净值': round(net_value, 4),
                '盈亏': pnl
            })

    def get_analysis(self):
        return pd.DataFrame(self.data)

    def record_trade(self):
        # 仅在有交易发生时调用
        if self.strategy.order:  # 检查当前是否有订单
            self.record(self.strategy.order)

    '''
类 TradeRecorder:
    初始化(策略):
        设置策略为输入的策略
        初始化数据列表为空
        当前交易设置为 None

    方法 记录(订单):
        如果 订单状态 为 完成:
            当前价值 = 策略的经纪人获取价值()
            初始价值 = 策略的经纪人获取初始现金()
            盈亏 = 当前价值 - 初始价值
            净值 = 当前价值 / 初始价值 如果 初始价值 不等于 0 否则 0

            将以下信息添加到数据列表:
                时间: 策略的数据时间
                交易计数: 策略的交易计数
                开盘价: 策略的数据开盘价
                最高价: 策略的数据最高价
                最低价: 策略的数据最低价
                收盘价: 策略的数据收盘价
                交易量: 策略的数据交易量
                持仓: 策略的当前持仓
                当前余额: 当前价值
                净值: 净值四舍五入到小数点后四位
                盈亏: 盈亏

    方法 获取分析():
        返回数据列表转换为数据框

    方法 记录交易():
        如果 策略的当前订单 存在:
            调用 记录(策略的当前订单)
    '''
    
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
    
    '''
类 策略工厂（用于增减策略）
    策略映射 = {
        vad: vad策略类
        bnh：bnh策略类    
    }    

    静态方法 获取策略（策略名称，**额外参数）
        策略类名称 = 从策略映射中获取
        if 策略名称 不存在：
        抛出错误
    
        策略模块 = 从 strategy 导入
        返回 从strategy中返回对应名称的类
    '''

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
        value = self.broker.getcash() 
        self.buy_signal_flag = False
        self.sell_signal_flag = False

        if long_signal and self.addition_count == 0:
            self.first_order_amount = self.p.base_order_amount * (1+commission)
            size = int(self.first_order_amount / close_buy)
            self.order = self.buy(size=size)
            self.last_entry_price = close_buy
            self.total_position = size
            self.addition_count = 1
            self.total_amount = self.first_order_amount # 总投入金额更新
            self.buy_signal_flag = True

        elif long_signal and 0 < self.addition_count < self.p.max_additions and self.total_amount < value:
            if self.data.close < self.last_entry_price - self.p.k * self.atr:
                add_amount = self.first_order_amount * (self.params.dca_multiplier ** self.addition_count) * (1+commission)
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

        '''
    方法 每根bar执行：
        long信号 = close < vwma - k*atr
        short信号 = close > vwma + k*atr
        佣金 = config设置
        滑点 = config设置
        买入价 = close * (1+滑点)
        卖出价 = close * (1-滑点)
        value = 总现金
        买入标记 = False
        卖出标记 = False

        if long信号且还未加仓，则开仓：
            首次花费金额 = 设定花费金额 * （1+佣金）
            交易量 = 首次花费金额 / 滑点调整后的close，向下取整
            根据算出的交易量进行买卖
            （更新数据）
            更新 最新买入价 = 滑点调整后的close
            更新 总仓位 = 交易量
            更新 加仓次数
            更新 总投入金额
            更新 买入信号标志 = True

        elif 如果有long信号 且 0<开仓次数<最大开仓 且 总投入金额<当前总现金，则加仓：
            if close < 最新买入价 - k * atr,
            加仓金额 = 首次花费金额 * ( dca倍数 ** 加仓次数) * (1+佣金)
            交易量 = 加仓金额 / 滑点调整后的close，向下取整
            根据算出的交易量进行买卖
            （更新数据）
            更新 最新买入价 = 滑点调整后的close
            更新 加仓次数
            更新 总仓位 = 交易量 + 当前仓位
            更新 总投入金额 = 当前投入金额 + 加仓金额
            更新 买入信号标志 = True

        elif 如果有short信号 且 当前有仓位，则平仓：
            止盈 = True
            价格变化 = close - 上次买入价

            if 价格变化 >总仓位 * atr:
                平仓，价格 = 滑点调整后的价格
                重置数据()
                更新 卖出信号标志 = True
            
            elif 价格变化 <= -总仓位 * atr:
                止盈 = False
                平仓，价格 = 滑点调整后的价格
                重置数据()
                更新 卖出信号标志 = True

        记录数据()

        '''
    
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
        sell_price = self.data.close[0] * (1 - CONFIG['slippage'])
        sell_amount = sell_size * sell_price * (1 - CONFIG['commission_rate'])
        buy_cost = sell_size * avg_buy_price
        net_profit = sell_amount - buy_cost

        '''
    方法 重置数据():
        清空 加仓次数
        清空 总仓位
        清空 总投入金额
        清空 上次买入价

    方法 买入信号():
        返回 卖出买入标志

    方法 卖出信号():
        返回 卖出信号标志
        
    方法 计算利润():
        if总仓位>0, 平均买入价=总投入金额 / 总仓位 else 平均买入价=0
        卖出价格 = 滑点调整后的close
        卖出金额 = 卖出仓位 * 卖出价格 * (1-佣金)
        买入成本 = 仓位 * 均价
        净利润 = 卖出价格 - 买入成本
        
        返回 净利润
        '''        
        
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
            order_time = self.data.datetime.datetime() 

            if order.isbuy():
                if self.addition_count == 1:
                    print(f'{order_time} 开仓: 买入 {order.executed.size} 股，价格: {order.executed.price}')
                    self.trade_recorder.record_trade()
                else:
                    print(f'{order_time} 加仓: 买入 {order.executed.size} 股，价格: {order.executed.price}')
                    self.trade_recorder.record_trade()
                    
            elif order.issell():
                try:
                    net_profit = abs(self.calculate_net_profit(order.executed.size))
                    if self.takeprofit:
                        print(f'{order_time} 止盈：卖出 {order.executed.size} 股，价格: {order.executed.price}, 收益: {net_profit:.2f}')
                        self.trade_recorder.record_trade()
                    else:
                        print(f'{order_time} 止损：卖出 {order.executed.size} 股，价格: {order.executed.price}, 亏损: {net_profit:.2f}')
                        self.trade_recorder.record_trade()
                except Exception as e:
                    print(f"计算净利润时出错: {e}")
            

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f'订单被取消/保证金不足/被拒绝，订单状态: {order.status}')

        self.order = None  # 重置订单

        '''
        遍历所有的analyzer
            if 分析器有 notify_order方法
            将当前订单信息，传递给所有分析器进行处理

        if 订单状态已提交或接受，不处理

        if 订单状态已完成 且 订单标识 不在 已处理订单
            标记订单处理
            交易次数 += 1
            订单时间= 当前时间

                if 订单是买入
                    if 加仓次数 == 1:
                        print 开仓信息
                    else: 
                        print 加仓信息

                elif 订单是卖出
                    try:
                        净利润 = 计算出的利润
                        if 止盈
                            print 止盈信息
                        else:
                            pinrt 止损信息
                    except 有错误
                        print 错误信息
                记录()

        elif 订单状态有问题
            print 有问题的状态
        '''

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
                print(f'{order_time} 买入并持有: 买入 {order.executed.size} 股，价格: {order.executed.price}')
                self.bought = True
            self.order = None
            self.trade_recorder.record_trade()

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f'订单失败。状态: {order.status}')
            self.bought = False
            self.order = None

        '''
类 Buyandhold策略
    参数 timeframe

    初始化构造函数
        if timeframe不在准许的timeframe:
            警告
        
        交易 = 无
        买入 = 无
        交易次数 = 0
        交易记录 = TradeRecorder()
        已完成订单 = set()
        第一根bar = True

    方法 next():
        cash = 当前现金
        滑点 = config设置
        佣金 = config设置
        滑点调整后价格 = close * (1+滑点)

        if 有一根bar 且 尚未买入 且 尚未交易:
            交易量 = 现金*(1-佣金) / 滑点调整后价格
            向下取整

            if 交易量>0:
                买入
                print 买入信息
            else:
                print 无法买入信息
            
        第一根bar = False
        记录数据()

    方法 notify_order()
        遍历所有的analyzer
            if 分析器有 notify_order方法
            将当前订单信息，传递给所有分析器进行处理

        if 订单状态已提交或接受，不处理

        if 订单状态已完成 且 订单标识 不在 已处理订单:
            标记订单处理
            交易次数 += 1
            订单时间= 当前时间

            if 订单是买入：
                print 买入信息
                已有买入
            无挂单
            记录数据()

        elif 订单状态有问题
            print 有问题的状态

    方法 buy_signal():
        返回  无仓位 and 第一根bar，返回True（只在第一根bar买入）

    方法 sell_signal():
        返回 false（不发出卖出信号）
        '''

    def buy_signal(self):
        return not self.position and self.first_bar

    def sell_signal(self):
        return False
    
