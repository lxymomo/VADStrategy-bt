import plotly.graph_objects as go
import pandas as pd
import backtrader as bt
from datetime import datetime
from strategy import VADStrategy
import config

# 检查并打印数据文件内容
data_file = r"C:\github\VADStrategy-bt-\data\BATS_QQQ_5.csv"
df = pd.read_csv(data_file, parse_dates=[0])
print("CSV Data Head:")
print(df.head())  # 打印前几行数据

# 定义函数以加载数据并运行策略
def load_data_and_run_strategy(strategy_class, data_file):
    cerebro = bt.Cerebro()

    # 获取CSV文件的日期范围
    def get_csv_date_range(data_file):
        df = pd.read_csv(data_file, parse_dates=[0])
        return df.iloc[0, 0].date(), df.iloc[-1, 0].date()

    csv_start_date, csv_end_date = get_csv_date_range(data_file)

    # 比较CSV日期范围和配置的回测日期范围
    config_start_date = pd.to_datetime(config.backtest_params['start_date']).date()
    config_end_date = pd.to_datetime(config.backtest_params['end_date']).date()

    start_date = max(csv_start_date, config_start_date)
    end_date = min(csv_end_date, config_end_date)

    data = bt.feeds.GenericCSVData(
        dataname=data_file,
        dtformat='%Y/%m/%d %H:%M',  # 根据数据文件中的日期格式
        datetime=0,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=-1,  # 没有 volume 列，设置为 -1
        openinterest=-1,  # 没有 openinterest 列，设置为 -1
        separator=',',  # 指定分隔符
        fromdate=start_date,
        todate=end_date
    )

    # 添加数据、策略
    cerebro.adddata(data)
    cerebro.addstrategy(strategy_class)

    # 添加资金、佣金、滑点
    cerebro.broker.setcash(config.broker_params['initial_cash'])
    cerebro.broker.setcommission(commission=config.broker_params['commission_rate'])

    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='time_return')

    # 运行回测
    results = cerebro.run()
    return results[0] 

# 运行策略并获取数据
strategy = load_data_and_run_strategy(VADStrategy, data_file)

print("Strategy type:", type(strategy))
print("Strategy attributes:", dir(strategy))

# 检查数据长度
print("Data length:", strategy.data.buflen())
print("Close data length:", len(strategy.data.close))
print("Prices length:", len(strategy.prices))
print("VWMA14 values length:", len(strategy.vwma14_values))
print("ATR values length:", len(strategy.atr_values))

# 获取策略运行的数据长度
data_length = min(strategy.data.buflen(), len(strategy.prices), len(strategy.vwma14_values), len(strategy.atr_values))

# 提取日期时间和其他数据
dates = []
closes = []
vwma14s = []
atrs = []

for i in range(data_length):
    dates.append(bt.num2date(strategy.data.datetime.array[i]).replace(tzinfo=None))
    closes.append(strategy.prices[i])
    vwma14s.append(strategy.vwma14_values[i])
    atrs.append(strategy.atr_values[i])

# 将策略数据转换为 Pandas DataFrame
df_result = pd.DataFrame({
    'Date': dates,
    'Close': closes,
    'VWMA14': vwma14s,
    'ATR': atrs
})

print("Result Data Head:")
print(df_result.head()) 

# 运行策略并获取数据
strategy = load_data_and_run_strategy(VADStrategy, data_file)

print("Strategy type:", type(strategy))
print("Strategy attributes:", dir(strategy))

# 检查数据长度
print("Data length:", strategy.data.buflen())
print("Close data length:", len(strategy.data.close))
print("Prices length:", len(strategy.prices))
print("VWMA14 values length:", len(strategy.vwma14_values))
print("ATR values length:", len(strategy.atr_values))

# 获取策略运行的数据长度
data_length = min(strategy.data.buflen(), len(strategy.prices), len(strategy.vwma14_values), len(strategy.atr_values))

# 提取日期时间和其他数据
dates = []
closes = []
vwma14s = []
atrs = []

for i in range(data_length):
    dates.append(bt.num2date(strategy.data.datetime.array[i]).replace(tzinfo=None))
    closes.append(strategy.prices[i])
    vwma14s.append(strategy.vwma14_values[i])
    atrs.append(strategy.atr_values[i])

# 将策略数据转换为 Pandas DataFrame
df_result = pd.DataFrame({
    'Date': dates,
    'Close': closes,
    'VWMA14': vwma14s,
    'ATR': atrs
})

print("Result Data Head:")
print(df_result.head())  # 打印结果数据的前几行

# 创建折线图
fig = go.Figure()

# 添加收盘价线
fig.add_trace(go.Scatter(x=df_result['Date'], y=df_result['Close'], mode='lines', name='Close', 
                         line=dict(color='blue', width=2)))

# 添加VWMA14线
fig.add_trace(go.Scatter(x=df_result['Date'], y=df_result['VWMA14'], mode='lines', name='VWMA14', 
                         line=dict(color='red', width=2, dash='dash')))

# 标记买入点
buy_dates = [date for date in strategy.buy_dates if date is not None]
buy_prices = []
for date in buy_dates:
    matching_rows = df_result[df_result['Date'].dt.date == date]
    if not matching_rows.empty:
        buy_prices.append(matching_rows['Close'].values[0])
    else:
        print(f"Warning: No matching data for buy date {date}")

if buy_dates and buy_prices:
    fig.add_trace(go.Scatter(x=buy_dates, y=buy_prices, mode='markers', name='Buy', 
                             marker=dict(color='green', size=12, symbol='triangle-up')))

# 标记卖出点
sell_dates = [date for date in strategy.sell_dates if date is not None]
sell_prices = []
for date in sell_dates:
    matching_rows = df_result[df_result['Date'].dt.date == date]
    if not matching_rows.empty:
        sell_prices.append(matching_rows['Close'].values[0])
    else:
        print(f"Warning: No matching data for sell date {date}")

if sell_dates and sell_prices:
    fig.add_trace(go.Scatter(x=sell_dates, y=sell_prices, mode='markers', name='Sell', 
                             marker=dict(color='red', size=12, symbol='triangle-down')))
# 设置图表布局
fig.update_layout(
    title={
        'text': 'VAD Strategy Backtest',
        'y':0.5,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'
    },
    xaxis_title="Date",
    yaxis_title="Price",
    legend=dict(
        x=0,
        y=1,
        traceorder="normal",
        font=dict(family="sans-serif", size=12, color="black"),
        bgcolor="LightSteelBlue",
        bordercolor="Black",
        borderwidth=2
    ),
    hovermode="x unified",
    plot_bgcolor='white',
    xaxis=dict(
        showline=True,
        showgrid=True,
        showticklabels=True,
        linecolor='rgb(204, 204, 204)',
        linewidth=2,
        ticks='outside',
        tickfont=dict(
            family='Arial',
            size=12,
            color='rgb(82, 82, 82)',
        ),
    ),
    yaxis=dict(
        showgrid=True,
        zeroline=False,
        showline=True,
        showticklabels=True,
    ),
)

# 展示图表
fig.show()