import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def visualize_strategy_results(candlestick_data_path, trade_data_path):
    # 读取K线数据
    df_candlestick = pd.read_csv(candlestick_data_path)
    df_candlestick['datetime'] = pd.to_datetime(df_candlestick['datetime'])

    # 读取交易数据
    df_trades = pd.read_csv(trade_data_path)
    df_trades['datetime'] = pd.to_datetime(df_trades['datetime'])

    # 创建子图，指定2行1列布局
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.1, 
                        row_heights=[0.7, 0.3],
                        subplot_titles=('Candlestick Chart', 'Equity Curve'))

    # 添加K线图
    fig.add_trace(go.Candlestick(x=df_candlestick['datetime'],
                                 open=df_candlestick['open'],
                                 high=df_candlestick['high'],
                                 low=df_candlestick['low'],
                                 close=df_candlestick['close'],
                                 name='Candlestick'),
                  row=1, col=1)

    # 标记买入点和卖出点
    buy_signals = df_trades[df_trades['buy_signal']]
    sell_signals = df_trades[df_trades['sell_signal']]

    fig.add_trace(go.Scatter(x=buy_signals['datetime'], y=buy_signals['low'], mode='markers',
                             marker=dict(symbol='triangle-up', size=15, color='lime', line=dict(color='green', width=2)),
                             name='Buy Signal'), row=1, col=1)

    fig.add_trace(go.Scatter(x=sell_signals['datetime'], y=sell_signals['high'], mode='markers',
                             marker=dict(symbol='triangle-down', size=15, color='red', line=dict(color='darkred', width=2)),
                             name='Sell Signal'), row=1, col=1)

    # 添加equity曲线
    fig.add_trace(go.Scatter(x=df_trades['datetime'], y=df_trades['equity'], mode='lines', name='Equity', line=dict(color='navy', width=2)),
                  row=2, col=1)

    # 设置布局和标题
    fig.update_layout(
        title='Strategy Visualization',
        xaxis_title='Datetime',
        height=800,
        width=1200,
        xaxis_rangeslider_visible=False,  # 禁用范围滑动器
        hovermode='x',  # 设置hover模式为垂直线
        legend=dict(x=0.01, y=0.99)
    )

    # 显示图形
    fig.show()

# 使用示例
if __name__ == "__main__":
    candlestick_data_path = 'processed/BATS_QQQ_5min.csv'
    trade_data_path = 'results/vad_5min_trades.csv'
    visualize_strategy_results(candlestick_data_path, trade_data_path)
