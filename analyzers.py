# analyzer.py

import backtrader as bt
import math

# 计算交易
class CustomTradeAnalyzer(bt.Analyzer):
    def __init__(self):
        self.trades = []
        self.total_trades = 0
        self.won = 0
        self.lost = 0
        self.total_profit = 0
        self.total_loss = 0

    def notify_trade(self, trade):
        if trade.isclosed:
            self.total_trades += 1
            if trade.pnl > 0:
                self.won += 1
                self.total_profit += trade.pnl
            else:
                self.lost += 1
                self.total_loss += trade.pnl
            self.trades.append(trade)

    def get_analysis(self):
        win_rate = self.won / self.total_trades if self.total_trades > 0 else 0
        loss_rate = self.lost / self.total_trades if self.total_trades > 0 else 0
        avg_profit = self.total_profit / self.won if self.won > 0 else 0
        avg_loss = self.total_loss / self.lost if self.lost > 0 else 0
        profit_factor = abs(self.total_profit / self.total_loss) if self.total_loss != 0 else float('inf')

        return {
            '总交易次数': self.total_trades,
            '盈利次数': self.won,
            '亏损次数': self.lost,
            '盈利比率': win_rate,
            '亏损比率': loss_rate,
            '平均盈利': avg_profit,
            '平均亏损': avg_loss,
            '盈利因子': profit_factor,
            '总利润': self.total_profit,
            '总亏损': self.total_loss
        }

# 计算收益
class CustomReturns(bt.Analyzer):
    params = (('timeframe', bt.TimeFrame.Days),)

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
        self.annualized_roi = math.pow(1.0 + self.roi, 252.0 / len(self.returns)) - 1.0

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

    def next(self):
        # 使用策略的 broker 来获取当前的投资组合价值
        value = self.strategy.broker.getvalue()
        
        if value > self.peak:
            self.peak = value
        else:
            drawdown = (self.peak - value) / self.peak
            self.drawdown = drawdown
            self.max_drawdown = max(self.max_drawdown, drawdown)

    def get_analysis(self):
        return {
            'max': {
                'drawdown': self.max_drawdown,
                'moneydown': self.peak * self.max_drawdown
            }
        }


