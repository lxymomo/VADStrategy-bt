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

    
# 计算收益
class CustomReturns(bt.Analyzer):
    params = (('timeframe', bt.TimeFrame.Days), ('num_years', 1.0),)  # 添加num_years参数

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
        self.annualized_roi = math.pow(1.0 + self.roi, 1 / self.params.num_years) - 1.0  # 使用实际的交易年数

    def get_analysis(self):
        return {
            'roi': self.roi,
            'annualized_roi': self.annualized_roi,
        }

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
