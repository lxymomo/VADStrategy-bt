# config.py

CONFIG = {
    'initial_cash': 100000,
    'commission_rate': 5 / 10000,
    'slippage': 1 / 1000,
    'strategy_params': {
        'vad': {
            'k': 1.6,
            'base_order_amount':10000,
            'dca_multiplier':1.5,
            'max_additions':4,
            'vwma_period':14,
            'atr_period':14,
        },
        'buyandhold': {
        }
    },
    'data_files': {
        'qqq_5min': 'processed/BATS_QQQ_5min.csv',
        'qqq_240min': 'processed/BATS_QQQ_240min.csv'
    },
    'output_dir': 'results/'
}
