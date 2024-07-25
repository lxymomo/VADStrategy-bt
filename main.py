# main.py
import os
import pandas as pd
import backtrader as bt
from config import CONFIG
from strategy import StrategyFactory
from analyzers import CustomDrawDown, CustomReturns, CustomTradeAnalyzer

# 确保输出目录存在
def ensure_dir(file_path):
    directory = os.path.dirname(file_path) 
    if not os.path.exists(directory): 
        os.makedirs(directory)

# 加载数据
def load_data(file_path):
    data = pd.read_csv(file_path, index_col='datetime', parse_dates=True)
    print(data.head())
    return data

def run_strategy(data_file, strategy_name, strategy_params):
    # 创建新的 Cerebro 实例
    cerebro = bt.Cerebro()

    # 设置初始现金、佣金率、滑点
    cerebro.broker.setcash(CONFIG['initial_cash'])

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(CustomDrawDown, _name='custom_drawdown')
    cerebro.addanalyzer(CustomReturns, _name='custom_returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='custom_trades')

    # 加载数据
    data = load_data(data_file)
    start_date = data.index[0].date()
    end_date = data.index[-1].date()
    num_years = (end_date - start_date).days / 365.25
    print(f"交易年数: {num_years:.2f}")
    
    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)

    # 加载参数和策略
    timeframe = '5min' if '5min' in data_file else '240min'
    strategy_class = StrategyFactory.get_strategy(strategy_name)
    cerebro.addstrategy(strategy_class, timeframe=timeframe, **strategy_params)

    # 运行回测
    print(f"初始资金: {cerebro.broker.getvalue():.2f}")
    results = cerebro.run()
    print(f"回测结束后的资金: {cerebro.broker.getvalue():.2f}")

    return cerebro, results, num_years

# 打印策略结果
def print_analysis(results, num_years, strategy_name, data_name):
    results = results[0]
    num_years = num_years

    # 获取分析结果
    sharpe_ratio = results.analyzers.sharpe.get_analysis().get('sharperatio', 0)
    custom_drawdown = results.analyzers.custom_drawdown.get_analysis()
    custom_returns = results.analyzers.custom_returns.get_analysis()
    trade_analysis = results.analyzers.custom_trades.get_analysis()

    max_drawdown = custom_drawdown.get('max', {}).get('drawdown', 0)
    max_drawdown_money = custom_drawdown.get('max', {}).get('moneydown', 0)
    max_drawdown_duration = custom_drawdown.get('max', {}).get('len', 0)

    total_return = custom_returns.get('roi', 0)
    annual_return = custom_returns.get('annualized_roi', 0)

    total_trades = trade_analysis.get('total', {}).get('total', 0)
    winning_trades = trade_analysis.get('won', {}).get('total', 0)
    
    if total_trades > 0:
        win_rate = winning_trades / total_trades
    else:
        win_rate = 0

    total_won = trade_analysis.get('won', {}).get('pnl', {}).get('total', 0)

    avg_profit = trade_analysis.get('won', {}).get('pnl', {}).get('average', 0)
    avg_loss = abs(trade_analysis.get('lost', {}).get('pnl', {}).get('average', 0))


    # 创建结果字典
    analysis_results = {
        "策略": strategy_name,
        "数据": data_name,
        "总收益率": f"{total_return:.2%}",
        "年化收益率": f"{annual_return:.2%}",
        "最大回撤": f"{max_drawdown:.2%}",
        "最大回撤金额": f"${max_drawdown_money:.2f}",
        "最大回撤持续期": max_drawdown_duration,
        "总交易次数": total_trades,
        "盈利交易次数": winning_trades,
        "交易胜率": f"{win_rate:.2%}",
        "平均盈利": f"${avg_profit:.2f}",
        "平均亏损": f"${avg_loss:.2f}",
        "夏普比率": f"{sharpe_ratio:.2f}"
    }

    # 打印结果
    for key, value in analysis_results.items():
        print(f"{key}: {value}")

    return analysis_results

def main():
    all_results = []  # 用于存储所有分析结果的列表

    # 运行所有策略组合
    for strategy_name, strategy_config in CONFIG['strategies'].items():
        for timeframe in strategy_config['enabled_timeframes']:
            data_file = CONFIG['data_files'][f'qqq_{timeframe}']
            strategy_params = strategy_config['params'][timeframe] if strategy_config['params'] else {}

            print(f"\n运行策略: {strategy_name} 数据: {data_file}")
            cerebro, results, num_years = run_strategy(data_file, strategy_name, strategy_params)
            
            analysis_results = print_analysis(results, num_years, strategy_name, data_file)
            analysis_results['时间间隔'] = f"{num_years:.2f}年"
            all_results.append(analysis_results)
            
            strategy = results[0]
            df = strategy.trade_recorder.get_analysis()
            
            output_file = f"{CONFIG['output_dir']}{strategy_name}_{timeframe}_trades.csv"
            ensure_dir(output_file)
            df.to_csv(output_file)
            print(f"交易记录已保存到: {output_file}")

    # 合并结果数据，调整顺序
    all_results_df = pd.DataFrame(all_results)
    columns_order = ['策略', '数据', '时间间隔'] + [col for col in all_results_df.columns if col not in ['策略', '数据', '时间间隔']]
    all_results_df = all_results_df[columns_order]

    # 保存合并后的结果到一个CSV文件
    combined_output_file = f"{CONFIG['output_dir']}combined_analysis_results.csv"
    all_results_df.to_csv(combined_output_file, index=False)
    print(f"合并的分析结果已保存到: {combined_output_file}")

if __name__ == '__main__':
    main()