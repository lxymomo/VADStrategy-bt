# analyzer.py

import backtrader as bt
import numpy as np

class CustomAnalyzer(bt.Analyzer):
    def __init__(self):
        self.trades = []
        self.current_trade = None
        self.peak = 0
        self.drawdown = 0
        self.max_drawdown = 0
        self.drawdown_start = None
        self.drawdown_duration = 0
        self.max_drawdown_duration = 0
        self.returns = []
        self.win_streak = 0
        self.lose_streak = 0
        self.max_win_streak = 0
        self.max_lose_streak = 0

    def next(self):
        # 更新回撤
        value = self.strategy.broker.getvalue()
        self.peak = max(self.peak, value)
        
        if value < self.peak:
            self.drawdown = (self.peak - value) / self.peak
            if self.drawdown > self.max_drawdown:
                self.max_drawdown = self.drawdown
                self.drawdown_duration = len(self.data) - self.drawdown_start if self.drawdown_start else 0
                self.max_drawdown_duration = max(self.max_drawdown_duration, self.drawdown_duration)
        else:
            self.drawdown = 0
            self.drawdown_start = len(self.data)

        # 计算收益率
        if len(self.data) > 1:
            daily_return = (value / self.strategy.broker.getvalue(self.data.datetime.date(-1))) - 1
            self.returns.append(daily_return)

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trades.append(trade)
            
            # 更新连续盈亏次数
            if trade.pnl > 0:
                self.win_streak += 1
                self.lose_streak = 0
            else:
                self.lose_streak += 1
                self.win_streak = 0
            
            self.max_win_streak = max(self.max_win_streak, self.win_streak)
            self.max_lose_streak = max(self.max_lose_streak, self.lose_streak)

    def stop(self):
        # 最终计算
        pass

    def get_analysis(self):
        total_trades = len(self.trades)
        winning_trades = sum(1 for trade in self.trades if trade.pnl > 0)
        losing_trades = total_trades - winning_trades
        
        total_profit = sum(trade.pnl for trade in self.trades if trade.pnl > 0)
        total_loss = sum(trade.pnl for trade in self.trades if trade.pnl <= 0)
        
        return {
            'sharpe_ratio': np.sqrt(252) * np.mean(self.returns) / np.std(self.returns) if self.returns else 0,
            'total_return': (self.strategy.broker.getvalue() / self.strategy.broker.startingcash) - 1,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_duration': self.max_drawdown_duration,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
            'profit_factor': abs(total_profit / total_loss) if total_loss != 0 else float('inf'),
            'average_trade': np.mean([trade.pnl for trade in self.trades]) if self.trades else 0,
            'max_win_streak': self.max_win_streak,
            'max_lose_streak': self.max_lose_streak
        }