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



def load_data(file_path):
    data = pd.read_csv(file_path, index_col='datetime', parse_dates=True)
    # print(data.head())
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
    print(f'回测开始时间：{start_date}')
    print(f'回测结束时间：{end_date}')
    print(f"交易年数: {num_years:.2f} 年")

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

    # 从分析器获取数据
    # 重要指标
    total_return = custom_returns.get('roi', 0)
    annual_return = custom_returns.get('annualized_roi', 0)
    max_drawdown = custom_drawdown.get('max', {}).get('drawdown', 0)

    # 其他指标
    annual_trade_count = custom_trade_analysis.get('annual_trade_count',0)
    win_rate = custom_trade_analysis.get('win_rate',0)
    profit_factor = custom_trade_analysis.get('profit_factor',0)
    max_drawdown_duration = custom_drawdown.get('max', {}).get('len', 0)
    max_drawdown_start = custom_drawdown.get('max', {}).get('datetime', 'N/A')
    max_drawdown_end = custom_drawdown.get('max', {}).get('recovery', 'N/A')
    avg_winning_trade_bars = custom_trade_analysis.get('avg_winning_trade_bars', 0)

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
            "年均交易次数": annual_trade_count,
            "胜率": win_rate,
            "盈亏比": profit_factor,
            "最大回撤持续K线根数": max_drawdown_duration,
            "最大回撤开始时间": max_drawdown_start,
            "最大回撤结束时间": max_drawdown_end,
            "盈利交易的平均持仓K线根数": avg_winning_trade_bars
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
    # 运行所有策略组合
    for strategy_name, strategy_config in CONFIG['strategies'].items():
        for timeframe in strategy_config['enabled_timeframes']:
            data_file = CONFIG['data_files'][f'qqq_{timeframe}']
            
            target = data_file.split('_')[1]
            
            strategy_params = strategy_config['params'][timeframe] if strategy_config['params'] else {}

            print(f"数据: {data_file} \n运行策略: {strategy_name}")
            cerebro, results, num_years = run_strategy(data_file, strategy_name, strategy_params)
        
            strategy = results[0]
            df = strategy.trade_recorder.get_analysis()
            filtered_df = df[df['交易状态'].isin(['买', '加', '卖'])].copy()
            filtered_df = filtered_df.reset_index(drop=True)
            filtered_df.index = filtered_df.index + 1

            columns_to_drop = ['open', 'high', 'low', 'close','资金利用率']
            filtered_df = filtered_df.drop(columns=columns_to_drop, errors='ignore')

            df['策略'] = strategy_name
            df['时间框架'] = timeframe
            filtered_df['策略'] = strategy_name
            filtered_df['时间框架'] = timeframe

            output_file = f"{CONFIG['output_dir']}{strategy_name}_{timeframe}_{target}_trades.csv"
            ensure_dir(output_file)
            filtered_df.to_csv(output_file, encoding='utf-8-sig')
            print(f"\n交易记录已保存到: {output_file}")

            output_df = f"{CONFIG['df_dir']}{strategy_name}_{timeframe}_{target}_all_trades.csv"
            ensure_dir(output_df)
            df.to_csv(output_df, encoding='utf-8-sig')
            print(f"可视化数据已保存到: {output_df}")
            
            print(f"——————————————————————————————————————————————————————————————")

if __name__ == '__main__':
    main()
