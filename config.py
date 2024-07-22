import glob
import os
import re

'''
用于修改参数
'''

# 获取 data 文件夹中的所有 CSV 文件
data_dir = 'data'
data_files = sorted(
    [(os.path.splitext(os.path.basename(file))[0], file) for file in glob.glob(os.path.join(data_dir, '*.csv'))],
    key=lambda x: int(re.search(r'\d+', x[0]).group())
)
# 回测时间参数
backtest_params = {
    'start_date': '2023/06/30 12:00',
    'end_date': '2024/06/30 20:00'
}

# 资金、佣金、滑点设置
broker_params = {
    'initial_cash': 1000000,
    'commission_rate': 5/10000,
    'slippage': 1/1000
}

'''
策略 Strategy 参数设置
'''

# VADStrategy参数
vad_strategy_params = {
    'k': 1.6,
    'base_order_amount': 10000,
    'dca_multiplier': 1.5,
    'number_of_dca_orders': 3
}

# BuyAndHoldStrategy参数
buy_and_hold_strategy_params = {}

'''
指标 Indicator 参数设置
'''
# VWMA
indicator_params = {
    'vwma_period': 14
}

# 整合所有策略参数
strategy_params = {
    'VAD': vad_strategy_params,
    'BuyAndHold': buy_and_hold_strategy_params
}

# 整合所有配置
config = {
    'data_files': data_files,
    'backtest_params': backtest_params,
    'broker_params': broker_params,
    'strategy_params': strategy_params,
    'indicator_params': indicator_params
}