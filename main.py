# main.py
import os
import pandas as pd
import backtrader as bt
import numpy as np
from config import CONFIG
from strategy import StrategyFactory

# 确保输出目录存在
def ensure_dir(file_path):
    directory = os.path.dirname(file_path) 
    if not os.path.exists(directory): 
        os.makedirs(directory)

# 加载数据
def load_data(file_path):
    data = pd.read_csv(file_path, index_col='datetime', parse_dates=True)
    return data

# 打印策略结果
def print_analysis(results, strategy_name, data_name):
    first_strat = results[0]

    # 获取分析结果
    sharpe_ratio = first_strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
    drawdown = first_strat.analyzers.drawdown.get_analysis()
    returns = first_strat.analyzers.returns.get_analysis()
    trade_analysis = first_strat.analyzers.trades.get_analysis()

    # 计算年化收益率
    total_return = returns.get('rtot', 0)
    num_years = len(first_strat.datas[0]) / (252 * 78)  # 假设一年252个交易日，每天78个5分钟K线
    annual_return = (1 + total_return) ** (1 / num_years) - 1 if total_return > -1 else -1

    # 创建结果字典
    analysis_results = {
        "策略": strategy_name,
        "数据": data_name,
        "夏普比率": sharpe_ratio,
        "总收益率": f"{total_return:.2%}",
        "年化收益率": f"{annual_return:.2%}",
        "最大回撤": f"{drawdown.get('max', {}).get('drawdown', 0):.2%}",
        "最大回撤持续期": drawdown.get('max', {}).get('len', 0),
        "总交易次数": trade_analysis.get('total', {}).get('total', 0),
        "交易胜率": f"{trade_analysis.get('won', {}).get('total', 0) / trade_analysis.get('total', {}).get('total', 1):.2%}" if trade_analysis.get('total', {}).get('total', 0) > 0 else "0.00%",
        "盈亏比": f"{trade_analysis.get('won', {}).get('pnl', {}).get('total', 0) / abs(trade_analysis.get('lost', {}).get('pnl', {}).get('total', 1)):.2f}" if abs(trade_analysis.get('lost', {}).get('pnl', {}).get('total', 0)) > 0 else "无穷大",
        "平均交易盈亏": f"${trade_analysis.get('pnl', {}).get('average', 0):.2f}"
    }

    # 打印结果
    for key, value in analysis_results.items():
        print(f"{key}: {value}")

    # 保存结果到文件
    output_file = f"{CONFIG['output_dir']}{strategy_name}_{data_name}_analysis.csv"
    pd.DataFrame([analysis_results]).to_csv(output_file, index=False)
    print(f"分析结果已保存到: {output_file}")

    return analysis_results

def run_strategy(cerebro, data_file, strategy_name, strategy_params):
    # 加载数据
    data = load_data(data_file)
    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)

    # 加载策略
    strategy_class = StrategyFactory.get_strategy(strategy_name)
    print(f"Using strategy class: {strategy_class.__name__}")
    cerebro.addstrategy(strategy_class, **strategy_params)

    # 设置初始现金、佣金率、滑点
    cerebro.broker.setcash(CONFIG['initial_cash'])
    cerebro.broker.setcommission(CONFIG['commission_rate'])
    cerebro.broker.set_slippage_perc(CONFIG['slippage'])

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    # 运行回测
    print(f"初始资金: {cerebro.broker.getvalue():.2f}")
    results = cerebro.run()
    print(f"回测结束后的资金: {cerebro.broker.getvalue():.2f}")

    # 输出结果
    data_name = os.path.basename(data_file).split('.')[0]
    analysis_results = print_analysis(results, strategy_name, data_name)

    # 导出交易记录
    strategy = results[0]
    df = strategy.trade_recorder.get_analysis()
    
    output_file = f"{CONFIG['output_dir']}{strategy_name}_{data_name}.csv"
    ensure_dir(output_file)
    df.to_csv(output_file)
    print(f"交易记录已保存到: {output_file}")

    return analysis_results

def main():
    cerebro = bt.Cerebro()

    # 运行所有策略组合
    for strategy_name, strategy_params in CONFIG['strategy_params'].items():
        for data_name, data_file in CONFIG['data_files'].items():
            print(f"\n运行策略: {strategy_name} 数据: {data_name}")
            run_strategy(cerebro, data_file, strategy_name, strategy_params)

if __name__ == '__main__':
    main()