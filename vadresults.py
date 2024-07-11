import os
import pandas as pd
import backtrader as bt

# 确保结果目录存在
output_dir = 'results'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 定义VWMA指标（不使用volume）
class VWMA(bt.Indicator):
    lines = ('vwma',)
    params = (('period', 20),)

    def __init__(self):
        self.addminperiod(self.params.period)
        self.vwma = self.lines.vwma

    def next(self):
        total_price = 0
        for i in range(-self.params.period + 1, 1):
            total_price += self.data.close[i]
        self.vwma[0] = total_price / self.params.period if self.params.period != 0 else 0

# 定义VAD策略所需的指标计算类
class VADStrategy(bt.Strategy):
    params = dict(period=14, k=1.6, vwma_period=20)

    def __init__(self):
        self.atr = bt.indicators.ATR(self.data, period=self.params.period)
        self.vwma = VWMA(self.data, period=self.params.vwma_period)
        self.k_atr = self.params.k * self.atr
        self.vwma_k_atr_up = self.vwma + self.k_atr
        self.vwma_k_atr_down = self.vwma - self.k_atr
        self.addminperiod(max(self.params.period, self.params.vwma_period))

    def next(self):
        # 这里不需要实现任何交易逻辑，只需要指标计算
        pass

# 定义函数来处理CSV文件并计算指标
def process_csv(input_file, output_file):
    df = pd.read_csv(input_file, parse_dates=['time'])

    # 转换数据到Backtrader格式（删除volume列）
    data = bt.feeds.PandasData(dataname=df, datetime='time', open='open', high='high', low='low', close='close', volume=None, openinterest=None)

    # 创建Cerebro引擎
    cerebro = bt.Cerebro()
    cerebro.adddata(data)

    # 添加VADStrategy
    cerebro.addstrategy(VADStrategy)

    # 运行Cerebro引擎
    strategies = cerebro.run()
    strategy = strategies[0]

    # 获取计算后的指标数据
    indicators_df = df.copy()
    min_period = max(strategy.params.period, strategy.params.vwma_period)
    
    indicators_df['atr'] = [getattr(strategy.atr, 'array', [None])[i] if i >= min_period - 1 else None for i in range(len(df))]
    indicators_df['k_atr'] = [getattr(strategy.k_atr, 'array', [None])[i] if i >= min_period - 1 else None for i in range(len(df))]
    indicators_df['vwma'] = [getattr(strategy.vwma, 'array', [None])[i] if i >= min_period - 1 else None for i in range(len(df))]
    indicators_df['vwma_k_atr_up'] = [getattr(strategy.vwma_k_atr_up, 'array', [None])[i] if i >= min_period - 1 else None for i in range(len(df))]
    indicators_df['vwma_k_atr_down'] = [getattr(strategy.vwma_k_atr_down, 'array', [None])[i] if i >= min_period - 1 else None for i in range(len(df))]

    # 保存结果到新的CSV文件
    indicators_df.to_csv(output_file, index=False)

# 获取data文件夹中的所有CSV文件
input_folder = 'data'
for filename in os.listdir(input_folder):
    if filename.endswith('.csv'):
        input_file_path = os.path.join(input_folder, filename)
        output_file_path = os.path.join(output_dir, filename)
        process_csv(input_file_path, output_file_path)
        print(f'成功处理并保存文件: {filename}')
