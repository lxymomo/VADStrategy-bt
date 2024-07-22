# main.py

import pandas as pd
import backtrader as bt
from config import CONFIG
from strategy import StrategyFactory

def load_data(file_path):
    """加载数据函数"""
    data = pd.read_csv(file_path, index_col='datetime', parse_dates=True)
    return data

def main():
    # 加载数据
    data_file = CONFIG['data_files']['qqq_5min']  # 可以根据需要更改
    data = load_data(data_file)

    # 初始化Cerebro引擎
    cerebro = bt.Cerebro()

    # 加载策略
    strategy_name = 'vad'  # 替换为需要的策略名称，如 'vad' 或 'buyandhold'
    strategy_class = StrategyFactory.get_strategy(strategy_name)
    cerebro.addstrategy(strategy_class)

    # 加载数据
    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)

    # 设置初始现金、佣金率、滑点
    cerebro.broker.setcash(CONFIG['initial_cash'])
    cerebro.broker.setcommission(CONFIG['commission_rate'])
    cerebro.broker.set_slippage_perc(CONFIG['slippage'])

    # 运行回测
    print(f"初始资金: {cerebro.broker.getvalue():.2f}")
    results = cerebro.run()
    print(f"回测结束后的资金: {cerebro.broker.getvalue():.2f}")

    # 输出结果
    port_value = cerebro.broker.getvalue()
    total_return = port_value - CONFIG['initial_cash']
    annual_return = (port_value / CONFIG['initial_cash']) ** (1 / (len(data) / (252 * 78))) - 1  # 假设一年252个交易日，每天78个5分钟K线

    print("Final Portfolio Value: {:.2f}".format(port_value))
    print("Total Return: {:.2f}".format(total_return))
    print("Annual Return: {:.2%}".format(annual_return))

if __name__ == '__main__':
    main()
