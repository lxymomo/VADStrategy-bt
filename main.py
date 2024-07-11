import backtrader as bt
import config
from strategy import VADStrategy, BuyAndHoldStrategy
from texttable import Texttable
import pandas as pd
import os

# 确保结果目录存在
output_dir = 'data'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def get_csv_date_range(data_file):
    df = pd.read_csv(data_file, parse_dates=[0])
    return df.iloc[0, 0].date(), df.iloc[-1, 0].date()

def add_data_and_run_strategy(strategy_class, data_file, name):
    cerebro = bt.Cerebro()

    # 获取CSV文件的日期范围
    csv_start_date, csv_end_date = get_csv_date_range(data_file)

    # 比较CSV日期范围和配置的回测日期范围
    config_start_date = pd.to_datetime(config.backtest_params['start_date']).date()
    config_end_date = pd.to_datetime(config.backtest_params['end_date']).date()

    start_date = max(csv_start_date, config_start_date)
    end_date = min(csv_end_date, config_end_date)

    data = bt.feeds.GenericCSVData(
        dataname=data_file,
        dtformat='%Y/%m/%d %H:%M',
        datetime=0,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=-1,  # 如果没有 volume 列，设置为 -1
        openinterest=-1,  # 如果没有 openinterest 列，设置为 -1
        separator=',',  # 指定分隔符
    )
    
    # 添加数据、策略
    cerebro.adddata(data, name=name)
    cerebro.addstrategy(strategy_class)

    # 添加资金、佣金、滑点
    cerebro.broker.setcash(config.broker_params['initial_cash'])
    cerebro.broker.setcommission(commission=config.broker_params['commission_rate'])
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

    # 运行回测
    results = cerebro.run()
    return results, start_date, end_date

def run_backtest():
    for name, data_file in config.data_files:
        print(f"\n{name} 分析结果:")

        # 运行策略
        buy_and_hold_results, start_date, end_date = add_data_and_run_strategy(BuyAndHoldStrategy, data_file, name)
        buy_and_hold_strat = buy_and_hold_results[0]
        VADStrategy_results, start_date, end_date = add_data_and_run_strategy(VADStrategy, data_file, name)
        VADStrategy_strat = VADStrategy_results[0]

        # 获取 BuyAndHoldStrategy 的分析结果
        buy_and_hold_analysis = buy_and_hold_strat.analyzers.pyfolio.get_analysis()
        buy_and_hold_returns = list(buy_and_hold_analysis['returns'].values())
        buy_and_hold_sharpe = buy_and_hold_strat.analyzers.sharpe.get_analysis()['sharperatio']
        buy_and_hold_drawdown = buy_and_hold_strat.analyzers.drawdown.get_analysis()

        # 获取 VADStrategy 的分析结果
        VAD_analysis = VADStrategy_strat.analyzers.pyfolio.get_analysis()
        VAD_returns = list(VAD_analysis['returns'].values())
        VAD_sharpe = VADStrategy_strat.analyzers.sharpe.get_analysis()['sharperatio']
        VAD_drawdown = VADStrategy_strat.analyzers.drawdown.get_analysis()

        # 计算超额收益
        excess_total_returns = sum(VAD_returns) - sum(buy_and_hold_returns)
        excess_annual_returns = (pd.Series(VAD_returns).mean() * 252) - (pd.Series(buy_and_hold_returns).mean() * 252)

        # 打印
        print(f"回测时间：从 {start_date} 到 {end_date}")
        print(f'BuyAndHold 初始本金为 {config.broker_params["initial_cash"]:.2f}')
        print(f'BuyAndHold 最终本金为 {config.broker_params["initial_cash"] * (1 + sum(buy_and_hold_returns)):.2f}')
        print(f'VADStrategy 初始本金为 {config.broker_params["initial_cash"]:.2f}')
        print(f'VADStrategy 最终本金为 {config.broker_params["initial_cash"] * (1 + sum(VAD_returns)):.2f}')

        table = Texttable()
        table.add_rows([
            ["分析项目", "VADStrategy", "BuyAndHold", "超额收益"],
            ["总收益率", f"{sum(VAD_returns) * 100:.2f}%",
                        f"{sum(buy_and_hold_returns) * 100:.2f}%",
                        f"{excess_total_returns * 100:.2f}%"],
            ["年化收益率", f"{pd.Series(VAD_returns).mean() * 252 * 100:.2f}%",
                          f"{pd.Series(buy_and_hold_returns).mean() * 252 * 100:.2f}%", 
                          f"{excess_annual_returns * 100:.2f}%"],
            ["最大回撤", f"{VAD_drawdown.max.drawdown:.2f}%",
                         f"{buy_and_hold_drawdown.max.drawdown:.2f}%", 
                         " "],
            ["夏普比率", f"{VAD_sharpe:.2f}" if VAD_sharpe is not None else "N/A",
                         f"{buy_and_hold_sharpe:.2f}" if buy_and_hold_sharpe is not None else "N/A", 
                         " "]
        ])

        print(table.draw())

if __name__ == '__main__':
    run_backtest()
