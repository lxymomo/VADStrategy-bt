# visual.py

import pandas as pd
from bokeh.plotting import figure, show
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, HoverTool, CrosshairTool

def visualize_strategy_results(df):
    # 准备数据
    df['date'] = pd.to_datetime(df['datetime'])
    source = ColumnDataSource(df)

    # 创建主图形
    p = figure(x_axis_type="datetime", width=1200, height=800, title="Strategy Visualization")
    p.xaxis.axis_label = 'Date'
    p.yaxis.axis_label = 'Price'

    # 添加K线图
    inc = df.close > df.open
    dec = df.open > df.close
    w = 12*60*60*1000 # 半天的宽度（毫秒）

    p.segment('date', 'high', 'date', 'low', color="black", source=source)
    inc_source = ColumnDataSource(df[inc])
    dec_source = ColumnDataSource(df[dec])

    p.vbar('date', w, 'open', 'close', fill_color="green", line_color="black", source=inc_source)
    p.vbar('date', w, 'open', 'close', fill_color="red", line_color="black", source=dec_source)

    # 添加买入和卖出点
    buy_df = df[df['buy_signal'] == True]
    sell_df = df[df['sell_signal'] == True]
    
    p.triangle('date', 'low', size=10, color="green", alpha=0.5, source=ColumnDataSource(buy_df))
    p.inverted_triangle('date', 'high', size=10, color="red", alpha=0.5, source=ColumnDataSource(sell_df))

    # 添加VWMA线
    p.line('date', 'vwma', color='blue', alpha=0.5, line_width=2, source=source, legend_label="VWMA")

    # 添加equity曲线
    p2 = figure(x_axis_type="datetime", width=1200, height=400, title="Equity Curve")
    p2.line('date', 'equity', line_width=2, color='navy', alpha=0.8, source=source)
    p2.yaxis.axis_label = 'Equity'

    # 添加交互工具
    hover = HoverTool(
        tooltips=[
            ('Date', '@date{%F}'),
            ('Open', '@open{0.00}'),
            ('High', '@high{0.00}'),
            ('Low', '@low{0.00}'),
            ('Close', '@close{0.00}'),
            ('Equity', '@equity{0.00}')
        ],
        formatters={'@date': 'datetime'},
        mode='vline'
    )
    p.add_tools(hover)
    p2.add_tools(hover)

    crosshair = CrosshairTool()
    p.add_tools(crosshair)
    p2.add_tools(crosshair)

    # 显示图形
    show(column(p, p2))

# 使用示例
if __name__ == "__main__":
    # 假设您有一个包含策略结果的DataFrame
    df = pd.read_csv('results/vad_5min_trades.csv')
    visualize_strategy_results(df)