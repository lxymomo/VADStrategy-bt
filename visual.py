import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from config import CONFIG  # 导入配置
from main import main

def visualize_strategy_results():
    combined_df, combined_filtered_df = main()
    combined_df['datetime'] = pd.to_datetime(combined_df['datetime'])

    # 创建子图，指定2行1列布局
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.1, 
                        row_heights=[0.7, 0.3],
                        subplot_titles=('Candlestick Chart', 'Equity Curve'))

    # 添加K线图
    fig.add_trace(go.Candlestick(x=df['datetime'],
                                 open=df['open'],
                                 high=df['high'],
                                 low=df['low'],
                                 close=df['close'],
                                 name='Candlestick'),
                  row=1, col=1)

    # 标记买入点和卖出点
    buy_signals = df[df['buy_signal'] == 1]
    sell_signals = df[df['sell_signal'] == 1]

    fig.add_trace(go.Scatter(x=buy_signals['datetime'], y=buy_signals['low'], mode='markers',
                             marker=dict(symbol='triangle-up', size=15, color='lime', line=dict(color='green', width=2)),
                             name='Buy Signal'), row=1, col=1)

    fig.add_trace(go.Scatter(x=sell_signals['datetime'], y=sell_signals['high'], mode='markers',
                             marker=dict(symbol='triangle-down', size=15, color='red', line=dict(color='darkred', width=2)),
                             name='Sell Signal'), row=1, col=1)

    # 添加equity曲线
    fig.add_trace(go.Scatter(x=df['datetime'], y=df['equity'], mode='lines', name='Equity', line=dict(color='navy', width=2)),
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
    visualize_strategy_results()

'''
方法 可视化策略结果() 
    数据路径 = CONFIG['visualization']['data_path']
    df['日期时间'] = 转换为日期时间(数据框['日期时间'])

    图形 = 创建子图(行数=2, 列数=1, 共享X轴=True,
                    垂直间距=0.1, 
                    行高=[0.7, 0.3],
                    子图标题=('K线图', '权益曲线'))

    添加追踪(图形, K线图, x=数据框['日期时间'],
              开盘=数据框['开盘'],
              最高=数据框['最高'],
              最低=数据框['最低'],
              收盘=数据框['收盘'],
              名称='K线',
              行=1, 列=1)

    买入信号 = df[数据框['买入信号'] == 1]
    卖出信号 = df[数据框['卖出信号'] == 1]

    添加追踪(图形, 散点图, x=买入信号['日期时间'], y=买入信号['最低'], 模式='标记',
              标记=设置标记(符号='三角形向上', 尺寸=15, 颜色='青柠', 边线=设置边线(颜色='绿色', 宽度=2)),
              名称='买入信号', 行=1, 列=1)

    添加追踪(图形, 散点图, x=卖出信号['日期时间'], y=卖出信号['最高'], 模式='标记',
              标记=设置标记(符号='三角形向下', 尺寸=15, 颜色='红色', 边线=设置边线(颜色='深红', 宽度=2)),
              名称='卖出信号', 行=1, 列=1)

    添加追踪(图形, 散点图, x=数据框['日期时间'], y=数据框['权益'], 模式='线', 名称='权益', 线=设置线(颜色='海军蓝', 宽度=2),
              行=2, 列=1)

    更新布局(图形,
        标题='策略可视化',
        X轴标题='日期时间',
        高度=800,
        宽度=1200,
        X轴范围滑块可见=False,  // 禁用范围滑动器
        悬停模式='x',  // 设置悬停模式为垂直线
        图例=设置图例(x=0.01, y=0.99)
    )

    显示图形(图形)
}

if __name__ 等于 "__main__" {
    可视化策略结果()
}


'''