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
    'start_date': '2010-6-30',
    'end_date': '2024-06-30'
}

# 资金、佣金、滑点设置
broker_params = {
    'initial_cash': 100000,
    'commission_rate': 5/10000,
    'slippage': 1/1000
}

'''
策略 Strategy 参数设置
'''

# VADStrategy参数
vad_strategy_params = {
    'k': 2,
    'base_order_amount': 10000,
    'dca_multiplier': 1.5,
    'number_of_dca_orders': 3
}


'''
指标 Indicator 参数设置
'''
# VWMA
indicator_params = {
    'vwma_period': 14
}