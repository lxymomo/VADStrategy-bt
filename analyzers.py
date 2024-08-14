# analyzer.py

import backtrader as bt
import math

# 计算交易
class CustomTradeAnalyzer(bt.Analyzer):
    # 初始化
    def __init__(self, num_years=None):
        self.trades = []
        self.total_trades = 0
        self.won = 0
        self.lost = 0
        self.total_profit = 0
        self.total_loss = 0
        self.current_trade = None
        self.equity_curve = []
        self.num_years = num_years

    # 记录数据
    def notify_order(self, order):

        # 如果订单完成，将当前净值添加到资金曲线中
        if order.status == order.Completed:
            self.equity_curve.append(self.strategy.broker.getvalue())

            # 如果是开仓
            if not self.current_trade and order.isbuy():
                self.current_trade = {
                    'entry_price': order.executed.price,
                    'size': order.executed.size,
                    'value': order.executed.value,
                    'entry_date': self.strategy.data.datetime.datetime(),
                    'entry_bar': len(self.equity_curve)  # 记录进入交易时的K线索引
                }

            # 如果是加仓
            elif self.current_trade and order.isbuy():
                total_size = self.current_trade['size'] + order.executed.size
                total_value = self.current_trade['value'] + order.executed.value
                self.current_trade['entry_price'] = total_value / total_size
                self.current_trade['size'] = total_size
                self.current_trade['value'] = total_value

            # 如果是平仓，记录价值，利润和亏损
            elif order.issell():
                exit_value = order.executed.price * order.executed.size
                entry_value = self.current_trade['entry_price'] * order.executed.size
                profit = exit_value - entry_value

                # 更新交易统计数据：总交易数量、盈亏交易数量、盈亏
                self.total_trades += 1
                if profit > 0:
                    self.won += 1
                    self.total_profit += profit
                else:
                    self.lost += 1
                    self.total_loss += abs(profit)

                # 更新交易字典
                self.trades.append({
                    'entry_price': self.current_trade['entry_price'],
                    'exit_price': order.executed.price,
                    'profit': profit,
                    'size': order.executed.size,
                    'bars_held': len(self.equity_curve) - self.current_trade['entry_bar']  # 使用 entry_bar 计算持有K线数
                })

                # 更新剩余仓位
                self.current_trade['size'] -= order.executed.size
                self.current_trade['value'] -= entry_value
                if self.current_trade['size'] <= 0:
                    self.current_trade = None  # 平仓后将current_trade设置为None

    def calculate_max_drawdown(self):
        peak = self.equity_curve[0]
        max_drawdown = 0
        drawdown_duration = 0
        max_drawdown_duration = 0
        for value in self.equity_curve:
            if value > peak:
                peak = value
                drawdown_duration = 0
            else:
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)
                drawdown_duration += 1
                max_drawdown_duration = max(max_drawdown_duration, drawdown_duration)
        return max_drawdown, max_drawdown_duration

    def get_analysis(self):
        total_trades = self.won + self.lost
        win_rate = self.won / total_trades if total_trades > 0 else 0
        loss_rate = self.lost / total_trades if total_trades > 0 else 0
        avg_profit = self.total_profit / self.won if self.won > 0 else 0
        avg_loss = self.total_loss / self.lost if self.lost > 0 else 0
        profit_factor = self.total_profit / self.total_loss if self.total_loss != 0 else float('inf')
        num_years = self.num_years if self.num_years else 1
        total_return = self.strategy.broker.getvalue() / self.strategy.broker.startingcash - 1
        annual_return = (1 + total_return) ** (1 / num_years) - 1
        max_drawdown, max_drawdown_duration = self.calculate_max_drawdown()

        return {
            '总交易次数': total_trades,
            '盈利次数': self.won,
            '亏损次数': self.lost,
            '交易胜率': f"{win_rate:.2%}",
            '亏损比率': f"{loss_rate:.2%}",
            '平均盈利': avg_profit,
            '平均亏损': -avg_loss,
            '盈亏比': profit_factor,
            '总利润': self.total_profit,
            '总亏损': -self.total_loss,
            '总收益': total_return,
            '年化收益': annual_return,
            '最大回撤': max_drawdown,
            '最长回撤期': max_drawdown_duration,
        }

'''
类 自定义交易分析器:
    方法 初始化(交易年数):
        初始化交易记录、统计数据和资金曲线
        记录交易年数

    方法 订单通知(订单):
        如果 订单已完成:
            更新资金曲线

            如果 是开仓订单:
                记录当前交易信息(入场价格、数量、价值、日期、入场K线索引)

            否则如果 是加仓订单:
                更新当前交易信息(平均入场价格、总数量、总价值)
            
            否则如果 是平仓订单:
                计算退出价值、入场价值和利润
                更新交易统计(总次数、盈亏次数、总盈亏)
                记录完整交易信息(入场价格,出场价格,盈亏,仓位,出场K线索引)
                更新剩余仓位
                如果 完全平仓:
                    重置当前交易为空

    方法 计算最大回撤():
        遍历资金曲线，计算最大回撤百分比和最长回撤期
        返回最大回撤和最长回撤期

    方法 获取分析结果():
        计算各项交易统计指标
        返回包含所有分析结果的字典
            总交易次数、盈亏次数、胜率、亏损率、平均盈利、平均亏损、盈亏比
            总利润、总亏损、总收益率、年化收益率、最大回撤、最长回撤期
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