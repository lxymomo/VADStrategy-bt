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

    # 加载数据
    data = load_data(data_file)
    start_date = data.index[0].date()
    end_date = data.index[-1].date()
    num_years = (end_date - start_date).days / 365.25
    print(f"交易年数: {num_years:.2f}")

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(CustomDrawDown, _name='custom_drawdown')
    cerebro.addanalyzer(CustomReturns, _name='custom_returns', num_years=num_years)
    cerebro.addanalyzer(CustomTradeAnalyzer, _name='custom_trades')
    
    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)

    # 加载参数和策略
    timeframe = data_file.split('_')[-1].replace('.csv', '')
    strategy_class = StrategyFactory.get_strategy(strategy_name)
    cerebro.addstrategy(strategy_class, timeframe=timeframe, **strategy_params)

    # 运行回测
    initial_cash = CONFIG['initial_cash'] 
    print(f"初始资金: {initial_cash:.2f}")
    results = cerebro.run()
    final_value = cerebro.broker.get_value() 
    print(f"回测结束后的资金: {final_value:.2f}")

    return cerebro, results, num_years

# 打印策略结果
def print_analysis(results, num_years, strategy_name, data_name):
    results = results[0]

    # 获取分析结果
    sharpe_ratio = results.analyzers.sharpe.get_analysis().get('sharperatio', 0)
    custom_drawdown = results.analyzers.custom_drawdown.get_analysis()
    custom_returns = results.analyzers.custom_returns.get_analysis()
    custom_trade_analysis = results.analyzers.custom_trades.get_analysis()

    # 最大回撤
    max_drawdown = custom_drawdown.get('max', {}).get('drawdown', 0)
    max_drawdown_money = custom_drawdown.get('max', {}).get('moneydown', 0)
    max_drawdown_duration = custom_drawdown.get('max', {}).get('len', 0)

    # 收益率
    total_return = custom_returns.get('roi', 0)
    annual_return = custom_returns.get('annualized_roi', 0)

    # 交易胜率
    total_trades = custom_trade_analysis.get('total_trades', 0)
    winning_trades = custom_trade_analysis.get('won', 0)
    
    win_rate_str = f"{winning_trades}:{total_trades}" if total_trades > 0 else "0:0"

    # 盈亏比
    total_profit = custom_trade_analysis.get('total_profit', 0)
    total_loss = custom_trade_analysis.get('total_loss', 0)
    profit_factor = total_profit / total_loss if total_loss != 0 else float('inf')

    # 计算年均交易次数
    annual_trade_count = total_trades / num_years if num_years > 0 else 0

    # 创建结果字典
    analysis_results = {
        "策略": strategy_name,
        "数据": data_name,
        "重要指标":{
            "总收益率": f"{total_return:.2%}",
            "年化收益率": f"{annual_return:.2%}",
            "最大回撤": f"{max_drawdown:.2%}",
            "夏普比率": f"{sharpe_ratio:.2f}"
        },
        "其他指标":{
            "年均交易次数": round(annual_trade_count, 2),
            "交易胜率": win_rate_str,
            "盈亏比": round(profit_factor, 2),
            "最大回撤持续K线根数": max_drawdown_duration,
            "最大回撤金额": f"${max_drawdown_money:.2f}",
            "平均盈利": round(total_profit / winning_trades, 2) if winning_trades > 0 else 0,
            "平均亏损": round(total_loss / (total_trades - winning_trades), 2) if (total_trades - winning_trades) > 0 else 0
        }
    }

    # 打印结果
    print("\n重要指标：")
    for key, value in analysis_results["重要指标"].items():
        print(f"    {key}: {value}")

    print("\n其他指标：")
    for key, value in analysis_results["其他指标"].items():
        print(f"    {key}: {value}")

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