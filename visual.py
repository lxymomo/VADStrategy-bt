import plotly.graph_objs as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from dash import Dash, dcc, html
from dash.dependencies import Input, Output

def visualize_strategy(cerebro, strategy, data, start_date, end_date):
    # 调试信息
    print("数据行:", data.lines.getlinealiases())
    print("数据长度:", len(data))
    print("策略:", type(strategy))
    print(f"时间范围: {start_date} to {end_date}")

    # 检查数据长度
    print(f"data.datetime.array length: {len(data.datetime.array)}")
    print(f"data length: {len(data)}")

    # 将Backtrader的数据转换为pandas DataFrame
    df = pd.DataFrame({
        'close': data.lines.close.array,
        'low': data.lines.low.array,
        'high': data.lines.high.array,
        'open': data.lines.open.array
    })

    # 获取所有数据点的日期时间信息
    datetime_values = [data.datetime.array[i] for i in range(len(data.datetime.array))]  # 直接使用 data.datetime.array 的索引

    # 将 "datetime" 列设置为索引并转换为 DatetimeIndex
    df.index = pd.to_datetime(datetime_values)

    # 过滤日期范围
    df = df[(df.index.date >= start_date) & (df.index.date <= end_date)]  # 使用 to_pydatetime() 获取日期信息
    
    print("DataFrame info:")
    print(df.info())
    print("DataFrame head:")
    print(df.head())

    # 创建Plotly图表
    fig = make_subplots(rows=1, cols=1, shared_xaxes=True, subplot_titles=('Price',))

    # 添加K线图
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'))

    # 添加VWMA指标线
    if hasattr(strategy, 'vwma14'):
        vwma_values = np.array(strategy.vwma14.array)
        vwma_values = vwma_values[-len(df):]  # 确保VWMA长度与df相同
        vwma_line = go.Scatter(x=df.index, y=vwma_values, name='VWMA', line=dict(color='blue'))
        fig.add_trace(vwma_line)
    else:
        print("Warning: VWMA14 not found in strategy")

    # 处理买卖点
    if hasattr(strategy, 'buy_dates') and hasattr(strategy, 'sell_dates'):
        buy_dates = pd.to_datetime(strategy.buy_dates, format='%Y/%m/%d %H:%M')
        sell_dates = pd.to_datetime(strategy.sell_dates, format='%Y/%m/%d %H:%M')
        
        buy_dates = buy_dates[(buy_dates.date >= start_date) & (buy_dates.date <= end_date)]
        sell_dates = sell_dates[(sell_dates.date >= start_date) & (sell_dates.date <= end_date)]
        
        buy_prices = df.loc[buy_dates, 'close']
        sell_prices = df.loc[sell_dates, 'close']

        buy_points = go.Scatter(x=buy_dates, y=buy_prices, mode='markers', name='Buy', marker=dict(color='green', size=10, symbol='triangle-up'))
        sell_points = go.Scatter(x=sell_dates, y=sell_prices, mode='markers', name='Sell', marker=dict(color='red', size=10, symbol='triangle-down'))
        
        fig.add_trace(buy_points)
        fig.add_trace(sell_points)
    else:
        print("Warning: Buy/Sell dates not found in strategy")

    # 设置图表布局
    fig.update_layout(title='Strategy Visualization', xaxis_rangeslider_visible=False)

    # 创建Dash应用
    app = Dash(__name__)

    app.layout = html.Div([
        dcc.Graph(id='graph', figure=fig),
        html.Div([
            html.Label('Date Range:'),
            dcc.DatePickerRange(
                id='date-range',
                start_date=df.index.min().date(),
                end_date=df.index.max().date(),
                display_format='YYYY-MM-DD'
            )
        ])
    ])

    @app.callback(
        Output('graph', 'figure'),
        Input('date-range', 'start_date'),
        Input('date-range', 'end_date')
    )
    def update_graph(start_date, end_date):
        print(f"Updating graph: start_date={start_date}, end_date={end_date}")
        
        start_date = pd.to_datetime(start_date).date()
        end_date = pd.to_datetime(end_date).date()

        mask = (df.index.date >= start_date) & (df.index.date <= end_date)  # 使用 to_pydatetime() 获取日期信息
        df_filtered = df[mask]

        fig = make_subplots(rows=1, cols=1, shared_xaxes=True, subplot_titles=('Price',))
        fig.add_trace(go.Candlestick(x=df_filtered.index, open=df_filtered['open'], high=df_filtered['high'], low=df_filtered['low'], close=df_filtered['close'], name='Price'))

        if hasattr(strategy, 'vwma14'):
            vwma_values = np.array(strategy.vwma14.array)
            vwma_values = vwma_values[-len(df):]  # 确保VWMA长度与df相同
            vwma_filtered = vwma_values[mask]
            fig.add_trace(go.Scatter(x=df_filtered.index, y=vwma_filtered, name='VWMA', line=dict(color='blue')))

        if hasattr(strategy, 'buy_dates') and hasattr(strategy, 'sell_dates'):
            buy_dates = pd.to_datetime(strategy.buy_dates)
            sell_dates = pd.to_datetime(strategy.sell_dates)
            
            buy_dates = buy_dates[(buy_dates.date >= start_date) & (buy_dates.date <= end_date)]
            sell_dates = sell_dates[(sell_dates.date >= start_date) & (sell_dates.date <= end_date)]
            
            buy_prices = df_filtered.loc[buy_dates, 'close']
            sell_prices = df_filtered.loc[sell_dates, 'close']

            fig.add_trace(go.Scatter(x=buy_dates, y=buy_prices, mode='markers', name='Buy', marker=dict(color='green', size=10, symbol='triangle-up')))
            fig.add_trace(go.Scatter(x=sell_dates, y=sell_prices, mode='markers', name='Sell', marker=dict(color='red', size=10, symbol='triangle-down')))

        fig.update_layout(title='Strategy Visualization', xaxis_rangeslider_visible=False)
        return fig

    return app