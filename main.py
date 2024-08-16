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

'''
方法 确保目录存在(file_path):
目录 = 获取file_path的目录
如果 目录不存在:
    创建目录

'''

def load_data(file_path):
    data = pd.read_csv(file_path, index_col='datetime', parse_dates=True)
    # print(data.head())
    return data

'''
方法 加载数据(file_path):
    数据 = 从CSV文件读取数据(文件路径, 将'datetime'列作为索引并解析日期)
    打印数据的前几行
    返回 数据
'''

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

'''
方法 运行策略（数据文件，策略名称，策略参数）:
    创建大脑
    设置 初始资金 = config设置

    数据 = 加载文件(file_path)
    开始日期 = 数据的第一个日期
    结束日期 = 数据的最后一个日期
    交易年数 = (结束日期 - 开始日期) / 365.25
    打印 交易年数

    添加分析器到Cerebro (夏普比率、自定义回撤、自定义收益、自定义交易分析)
    创建数据源并添加到Cerebro

    timeframe = 数据文件名称中提取
    策略类 = 策略工厂中（对应名称的策略）
    将策略添加到 大脑（策略类,timeframe,其他参数）

    打印初始资金
    运行回测
    获取并打印最终资金

    返回 Cerebro实例、回测结果、交易年数

'''

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

'''
方法 打印分析结果(回测结果, 交易年数, 策略名称, 数据名称):
    results = 策略实例

    夏普比率 = results中的夏普比率分析
    回撤分析 = results中的自定义回撤分析
    收益分析 = results中的自定义收益分析
    交易分析 = results中的自定义交易分析

    从自定义分析器中获取对应信息

    analysis_results = {
        "策略": 策略名称,
        "数据": 数据名称,

        "重要指标": {
            "总收益率": 格式化(总收益率),
            "年化收益率": 格式化(年化收益率),
            "最大回撤": 格式化(最大回撤百分比),
            "夏普比率": 格式化(夏普比率)
        },
        "其他指标": {
            "年均交易次数": 四舍五入(年均交易次数),
            "交易胜率": 胜率字符串,
            "盈亏比": 四舍五入(盈亏比),
            "最大回撤持续K线根数": 最大回撤持续期,
            "最大回撤金额": 格式化(最大回撤金额),
            "平均盈利": 计算平均盈利,
            "平均亏损": 计算平均亏损
        }
    }

    打印("\n重要指标：")
    对于 分析结果["重要指标"] 中的每个 键, 值:
        打印(f"    {键}: {值}")

    打印("\n其他指标：")
    对于 分析结果["其他指标"] 中的每个 键, 值:
        打印(f"    {键}: {值}")

    返回 分析结果
'''
def main():
    all_df = []       # 用于存储完整的数据
    all_filtered_df = []  # 用于存储交易记录

    # 运行所有策略组合
    for strategy_name, strategy_config in CONFIG['strategies'].items():
        for timeframe in strategy_config['enabled_timeframes']:
            data_file = CONFIG['data_files'][f'qqq_{timeframe}']
            strategy_params = strategy_config['params'][timeframe] if strategy_config['params'] else {}

            print(f"数据: {data_file} \n运行策略: {strategy_name}")
            cerebro, results, num_years= run_strategy(data_file, strategy_name, strategy_params)
        
            strategy = results[0]
            df = strategy.trade_recorder.get_analysis()
            filtered_df = df[df['交易状态'].isin(['买', '加', '卖'])].copy()
            filtered_df = filtered_df.reset_index(drop=True)
            filtered_df.index = filtered_df.index + 1

            df['策略'] = strategy_name
            df['时间框架'] = timeframe
            filtered_df['策略'] = strategy_name
            filtered_df['时间框架'] = timeframe
            
            all_df.append(df)
            all_filtered_df.append(filtered_df)

            # output_file = f"{CONFIG['output_dir']}{strategy_name}_{timeframe}_trades_all.csv"
            # ensure_dir(output_file)
            # df.to_csv(output_file, encoding='utf-8-sig')

            output_file = f"{CONFIG['output_dir']}{strategy_name}_{timeframe}_trades.csv"
            ensure_dir(output_file)
            filtered_df.to_csv(output_file, encoding='utf-8-sig')
            print(f"\n交易记录已保存到: {output_file}")
            
            print(f"——————————————————————————————————————————————————————————————")

    # 合并所有完整的交易记录
    combined_df = pd.concat(all_df, ignore_index=True)

    # 合并所有筛选后的交易记录
    combined_filtered_df = pd.concat(all_filtered_df, ignore_index=True)

    return combined_df, combined_filtered_df

if __name__ == '__main__':
    main()

'''
方法 主函数():
    所有结果 = 空列表

    对于 配置文件中的每个 策略名称, config策略配置:
        对于 每个 enabled_timeframes:
            data_file = cnofig设置[data_files][qqq_{timeframe}]
            strategy_params = 获取对应timeframe的策略参数（如果有）

            打印(f"\n运行策略: {策略名称} 数据: {数据文件}")
            Cerebro实例, 回测结果, 交易年数 = 运行策略(数据文件, 策略名称, 策略参数)
            
            analysis_results = 打印分析结果(results, num_years, strategy_name, data_file)
            analysis_results['时间间隔'] = f"{交易年数:.2f}年"
            将 分析结果 添加到 所有结果 列表中
            
            策略实例 = 回测结果[0]
            df = 获取策略实例的交易记录
            
            输出文件路径 = 构建交易记录输出文件路径
            确保输出目录存在(输出文件路径)
            将交易记录保存为CSV文件(输出文件路径)
            打印(f"交易记录已保存到: {输出文件路径}")

    all_results_df = 将所有结果转换为数据框
    列顺序 = ['策略', '数据', '时间间隔'] + [其他列]
    all_results_df = 根据新的列顺序重排列数据框

    合并结果输出文件 = 构建合并结果输出文件路径
    将所有结果数据框保存为CSV文件(合并结果输出文件)
    打印(f"合并的分析结果已保存到: {合并结果输出文件}")

如果 这是主程序:
    执行 主函数()

'''