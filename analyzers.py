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
        self.max_drawdown_start = None
        self.max_drawdown_end = None

    def next(self):
        value = self.strategy.broker.getvalue()
        current_date = self.data.datetime.date(0)
        
        if value > self.peak:
            if self.drawdown > 0:
                if self.drawdown == self.max_drawdown:
                    self.max_drawdown_end = current_date
            self.peak = value
            self.drawdown_start = len(self.data)
            self.current_drawdown_length = 0
            self.drawdown = 0
        else:
            drawdown = (self.peak - value) / self.peak
            self.drawdown = drawdown
            self.current_drawdown_length += 1
            
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
                self.drawdown_length = self.current_drawdown_length
                self.max_drawdown_length = max(self.max_drawdown_length, self.drawdown_length)
                self.max_drawdown_start = self.data.datetime.date(-self.current_drawdown_length)
                self.max_drawdown_end = None

    def get_analysis(self):
        return {
            'max': {
                'drawdown': self.max_drawdown,
                'moneydown': self.peak * self.max_drawdown,
                'len': self.max_drawdown_length,
                'datetime': self.max_drawdown_start,
                'recovery': self.max_drawdown_end
            }
        }

