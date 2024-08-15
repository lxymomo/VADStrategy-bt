# config.py

CONFIG = {
    'initial_cash': 100000,
    'friction_cost': 1/1000,

    # ↓ 调整策略适用的、不同时间周期的参数
    'strategies': {  
        'vad': {
            # ↓ 准许适用5min, 240min参数，这一步是为了以后能放入更多数据
            'enabled_timeframes': ['5min', '240min'],  
            'params': { 
                '5min': {
                    'k': 1.6,
                    'base_order_amount': 10000,
                    'dca_multiplier': 1.5,
                    'max_additions': 4,
                    'vwma_period': 14,
                    'atr_period': 14
                },
                '240min': {
                    'k': 0.7,
                    'base_order_amount': 10000,
                    'dca_multiplier': 1.5,
                    'max_additions': 4,
                    'vwma_period': 14,
                    'atr_period': 14
                }
            }
        },
        'buyandhold': {
            'enabled_timeframes': ['5min', '240min'],
            'params': None
        }
    },
    'data_files': {
        'qqq_5min': 'processed/BATS_QQQ_5min.csv',   # 数据文件 QQQ 5min
        'qqq_240min': 'processed/BATS_QQQ_240min.csv' # 数据文件 QQQ 240min
    },
    'output_dir': 'results/', # 输出文件夹位置
    'visualization': {
        'data_path': 'results/vad_5min_trades.csv'  # 需要可视化的文件
    }
}