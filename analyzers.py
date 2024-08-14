# analyzer.py

import backtrader as bt
import math

# 计算交易
class CustomTradeAnalyzer(bt.Analyzer):
    params = (
        ('num_years', 1.0),
    )

    def start(self):
        self.trades = []
        self.total_trades = 0
        self.winning_trades = 0
        self.total_profit = 0
        self.total_loss = 0
        self.winning_trade_bars = 0

    def notify_trade(self, trade):
        if trade.isclosed:
            self.total_trades += 1
            
            if trade.pnl > 0:
                self.winning_trades += 1
                self.total_profit += trade.pnl
                self.winning_trade_bars += trade.barlen
            else:
                self.total_loss -= trade.pnl  # 注意：亏损的trade.pnl是负数

            self.trades.append(trade)

    def stop(self):
        self.annual_trade_count = self.total_trades / self.p.num_years
        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        self.profit_factor = self.total_profit / self.total_loss if self.total_loss != 0 else float('inf')
        self.avg_winning_trade_bars = self.winning_trade_bars / self.winning_trades if self.winning_trades > 0 else 0

    def get_analysis(self):
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'annual_trade_count': self.annual_trade_count,
            'win_rate': self.win_rate,
            'total_profit': self.total_profit,
            'total_loss': self.total_loss,
            'profit_factor': self.profit_factor,
            'winning_trade_bars': self.winning_trade_bars,
            'avg_winning_trade_bars': self.avg_winning_trade_bars,
            'num_years': self.p.num_years,
        }
    
'''
类 自定义交易分析器(CustomTradeAnalyzer):
    参数:
        num_years: 1.0

    方法 开始(start):
        初始化 交易列表(trades)为空
        初始化 总交易数(total_trades)为0
        初始化 赢利交易数(winning_trades)为0
        初始化 总利润(total_profit)为0
        初始化 总亏损(total_loss)为0
        初始化 赢利交易的条数(winning_trade_bars)为0

    方法 通知交易(notify_trade, trade):
        如果 交易闭合(trade.isclosed):
            总交易数增加1
            
            如果 交易利润大于0(trade.pnl > 0):
                赢利交易数增加1
                总利润增加交易利润(trade.pnl)
                赢利交易的条数增加交易的条数(trade.barlen)
            否则:
                总亏损减少交易利润(-trade.pnl)  # 亏损的交易利润是负数

            将当前交易添加到交易列表(trades)

    方法 停止(stop):
        年度交易数量(annual_trade_count) = 总交易数 / 年数
        胜率(win_rate) = 赢利交易数 / 总交易数 如果 总交易数 > 0 否则 0
        利润因子(profit_factor) = 总利润 / 总亏损 如果 总亏损 != 0 否则 无限大(float('inf'))
        平均赢利交易条数(avg_winning_trade_bars) = 赢利交易的条数 / 赢利交易数 如果 赢利交易数 > 0 否则 0

    方法 获取分析结果(get_analysis):
        返回 {
            '总交易数': 总交易数,
            '赢利交易数': 赢利交易数,
            '年度交易数量': 年度交易数量,
            '胜率': 胜率,
            '总利润': 总利润,
            '总亏损': 总亏损,
            '利润因子': 利润因子,
            '赢利交易条数': 赢利交易的条数,
            '平均赢利交易条数': 平均赢利交易条数,
            '年数': 年数,
        }
'''    
# 计算收益
class CustomReturns(bt.Analyzer):
    params = (('num_years', 1.0),)  

    def start(self):
        self.start_value = self.strategy.broker.getvalue()
        self.current_value = self.start_value
        self.returns = []

    def next(self):
        self.current_value = self.strategy.broker.getvalue()
        returns = (self.current_value / self.start_value) - 1.0
        self.returns.append(returns)

    def stop(self):
        self.roi = (self.current_value / self.start_value) - 1.0
        self.annualized_roi = math.pow(1.0 + self.roi, 1 / self.params.num_years) - 1.0

    def get_analysis(self):
        return {
            'roi': self.roi,
            'annualized_roi': self.annualized_roi,
        }
'''
类 自定义收益分析器:
    参数 = 使用 num_years

    方法 开始():
        初始资金 = 获取策略当前总资产
        当前资产 = 初始资金
        收益列表 = 空列表

    方法 每次迭代():
        当前资产 = 获取策略当前总资产
        收益率 = (当前资产 / 初始资金) - 1.0
        将收益率添加到收益列表

    方法 结束():
        总收益率 = (当前资产 / 初始资金) - 1.0
        年化收益率 = (1.0 + 总收益率) 的 (1 / 交易年数) 次方 - 1.0

    方法 获取分析结果():
        返回 {
            '总收益率': 总收益率,
            '年化收益率': 年化收益率
        }
'''

# 最大回撤
class CustomDrawDown(bt.Analyzer):
    params = (('fund', None),)

    def start(self):
        self.drawdown = 0.0
        self.max_drawdown = 0.0
        self.peak = float('-inf')
        self.drawdown_start = 0
        self.drawdown_length = 0
        self.max_drawdown_length = 0
        self.current_drawdown_length = 0

    def next(self):
        value = self.strategy.broker.getvalue()
        
        if value > self.peak:
            self.peak = value
            self.drawdown_start = len(self.data)
            self.current_drawdown_length = 0
        else:
            drawdown = (self.peak - value) / self.peak
            self.drawdown = drawdown
            self.current_drawdown_length += 1
            
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
                self.drawdown_length = self.current_drawdown_length
                self.max_drawdown_length = max(self.max_drawdown_length, self.drawdown_length)

    def get_analysis(self):
        return {
            'max': {
                'drawdown': self.max_drawdown,
                'moneydown': self.peak * self.max_drawdown,
                'len': self.max_drawdown_length
            }
        }


'''
类 自定义回撤分析器:
    参数 = (('资金', 无),)

    函数 开始():
        self.当前回撤 = 0.0
        self.最大回撤 = 0.0
        self.峰值 = 负无穷大
        self.回撤开始时间 = 0
        self.回撤持续时间 = 0
        self.最大回撤持续时间 = 0
        self.当前回撤持续时间 = 0

    函数 下一步():
        当前价值 = self.策略.经纪人.获取价值()
        
        如果 当前价值 > self.峰值:
            self.峰值 = 当前价值
            self.回撤开始时间 = 数据长度
            self.当前回撤持续时间 = 0
        否则:
            回撤 = (self.峰值 - 当前价值) / self.峰值
            self.当前回撤 = 回撤
            self.当前回撤持续时间 += 1
            
            如果 回撤 > self.最大回撤:
                self.最大回撤 = 回撤
                self.回撤持续时间 = self.当前回撤持续时间
                self.最大回撤持续时间 = 最大值(self.最大回撤持续时间, self.回撤持续时间)

    函数 获取分析结果():
        返回 {
            '最大': {
                '回撤率': self.最大回撤,
                '回撤金额': self.峰值 * self.最大回撤,
                '持续时间': self.最大回撤持续时间
            }
        }
'''