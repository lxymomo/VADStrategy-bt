import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import os

app = dash.Dash(__name__)

# 定义数据目录
DATA_DIR = 'visual/'

def load_data(strategy, timeframe):
    filename = f"{strategy}_{timeframe}_all_trades.csv"
    file_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df['时间'] = pd.to_datetime(df['时间'])
        return df
    else:
        return pd.DataFrame()  # 返回空DataFrame如果文件不存在

'''
# 定义数据目录
数据目录 = 'visual/'

定义 加载数据(strategy, timeframe):
    文件名 = f"{策略}_{时间框架}_所有交易.csv"
    文件路径 = os.path.join(数据目录, 文件名)
    如果 os.path.exists(文件路径):
        数据框 = pd.read_csv(文件路径)
        数据框['时间'] = pd.to_datetime(数据框['时间'])
        返回 数据框
    否则:
        返回 空数据框()  # 如果文件不存在，返回空数据框

'''

def create_figure(strategy_df, benchmark_df, timeframe, strategy, benchmark):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        vertical_spacing=0.1, 
                        row_heights=[0.5, 0.25, 0.25],
                        subplot_titles=('Candlestick Chart', 'Equity Curve', 'Capital Utilization Rate'))

    # Add Candlestick chart
    fig.add_trace(go.Candlestick(x=strategy_df['时间'],
                                 open=strategy_df['open'],
                                 high=strategy_df['high'],
                                 low=strategy_df['low'],
                                 close=strategy_df['close'],
                                 name='Candlestick'),
                  row=1, col=1)

    # Mark buy and sell points
    buy_signals = strategy_df[strategy_df['交易状态'] == '买']
    add_signals = strategy_df[strategy_df['交易状态'] == '加']
    sell_signals = strategy_df[strategy_df['交易状态'] == '卖']

    fig.add_trace(go.Scatter(x=buy_signals['时间'], y=buy_signals['low'], mode='markers',
                             marker=dict(symbol='triangle-up', size=15, color='lime', line=dict(color='green', width=2)),
                             name='Buy Signal'), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=add_signals['时间'], y=add_signals['low'], mode='markers',
                             marker=dict(symbol='triangle-up', size=15, color='lime', line=dict(color='green', width=2)),
                             name='Add Signal'), row=1, col=1)

    fig.add_trace(go.Scatter(x=sell_signals['时间'], y=sell_signals['high'], mode='markers',
                             marker=dict(symbol='triangle-down', size=15, color='red', line=dict(color='darkred', width=2)),
                             name='Sell Signal'), row=1, col=1)

    # 资金曲线（策略）
    fig.add_trace(go.Scatter(x=strategy_df['时间'], y=strategy_df['总资产'], mode='lines+markers', 
                             name='Strategy Equity', marker=dict(color='red', size=1)),
                  row=2, col=1)

    # 资金曲线（基准）
    fig.add_trace(go.Scatter(x=benchmark_df['时间'], y=benchmark_df['总资产'], mode='lines+markers', 
                             name='Benchmark Equity', marker=dict(color='grey', size=1)),
                  row=2, col=1)

    # 资金利用率（柱状图）
    fig.add_trace(go.Scatter(x=strategy_df['时间'], y=strategy_df['资金利用率'], mode='markers', 
                         name='Capital Utilization Rate', marker=dict(color='orange', size=1)),
                  row=3, col=1)

    # 更新图表
    fig.update_layout(
        title=f'Strategy Visualization - {timeframe} {strategy} vs {benchmark}',
        height=1200,
        width=1200,
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        legend=dict(x=0.01, y=0.99)
    )

    # 更新Y轴
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Equity", row=2, col=1)
    fig.update_yaxes(title_text="Utilization Rate", row=3, col=1)

    # 更新X轴
    fig.update_xaxes(title_text="时间", row=3, col=1)

    return fig

'''
定义 创建图表(策略数据框, 基准数据框, 时间框架, 策略, 基准):
    创建子图，行数=3，列数=1，共享X轴，垂直间距=0.1, 每行高度=[], 子图标题=[],

    # 添加蜡烛图
    添加蜡烛图到子图（时间，开高收低，蜡烛图）第一行，第一列

    # 标记买入和卖出点
    买入信号 = 策略数据框[策略数据框['交易状态'] == '买']
    加信号 = 策略数据框[策略数据框['交易状态'] == '加']
    卖出信号 = 策略数据框[策略数据框['交易状态'] == '卖']

    添加买入信号到蜡烛图
    添加加信号到图表
    添加卖信号到图表

    # 资金曲线（策略）
    添加策略资金曲线到图表

    # 资金曲线（基准）
    添加基准资金曲线到图表

    # 资金利用率（柱状图）
    添加资金利用率柱状图到图表

    # 更新图表布局
    更新图表标题和尺寸
    更新Y轴和X轴标签

    返回 图表

'''

# 应用布局
app.layout = html.Div([
    html.H1("Strategy Visualization"),
    dcc.Dropdown(
        id='timeframe-dropdown',
        options=[
            {'label': '5分钟', 'value': '5min'},
            {'label': '240分钟', 'value': '240min'}
        ],
        value='240min'
    ),
    dcc.Dropdown(
        id='target-dropdown',
        options=[
            {'label': 'QQQ', 'value': 'QQQ'},
            {'label': 'BTC', 'value': 'BTC'},
            {'label': '600519', 'value': '600519'}
        ],
        value='BTC'
    ),
    dcc.Dropdown(
        id='benchmark-dropdown',
        options=[
            {'label': '买入并持有', 'value': 'buyandhold'},
            {'label': '国债', 'value': 'treasury'},
            {'label': 'BTC', 'value': 'btc'}
        ],
        value='buyandhold'
    ),
    dcc.Graph(id='strategy-graph')
])

@app.callback(
    Output('strategy-graph', 'figure'),
    [Input('timeframe-dropdown', 'value'),
     Input('benchmark-dropdown', 'value')]
)
def update_graph(timeframe, benchmark):
    strategy_df = load_data('vad', timeframe)
    benchmark_df = load_data(benchmark, timeframe)
    
    if strategy_df.empty or benchmark_df.empty:
        return go.Figure().add_annotation(text="No data available", showarrow=False, font=dict(size=20))
    
    return create_figure(strategy_df, benchmark_df, timeframe, 'vad', benchmark)

if __name__ == '__main__':
    app.run_server(debug=True)

'''
# 应用布局
应用布局 = html.Div([
    html.H1("策略可视化"),
    下拉菜单1：选择时间框架,
    下拉菜单2：选择目标,
    下拉菜单3：选择基准,
    图表组件
])

定义 更新图表(时间框架, 基准):
    策略数据框 = 加载数据('vad', 时间框架)
    基准数据框 = 加载数据(基准, 时间框架)
    
    如果 策略数据框为空 或 基准数据框为空:
        返回 显示无数据可用的图表
    
    返回 创建图表(策略数据框, 基准数据框, 时间框架, 'vad', 基准)

如果 __name__ 是 '__main__':
    运行应用服务器(调试模式=True)

'''