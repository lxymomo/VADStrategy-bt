import pandas as pd
from bokeh.plotting import figure, curdoc
from bokeh.models import ColumnDataSource, HoverTool, CrosshairTool, WheelZoomTool
from bokeh.layouts import column
from bokeh.embed import components
import dash
from dash import dcc, html

def create_figure(title, x_axis_type="datetime", tools="pan,box_zoom,reset,save,wheel_zoom"):
    return figure(x_axis_type=x_axis_type, width=1200, height=800, title=title, tools=tools)

def add_equity_curve(p, source):
    p.line('date', 'equity', line_width=2, color='navy', alpha=0.8, source=source)
    p.yaxis.axis_label = 'Equity'

def add_candlestick(p, df, source):
    inc = df.close > df.open
    dec = df.open > df.close
    w = 12*60*60*1000  # 半天的宽度（毫秒）

    p.segment('date', 'high', 'date', 'low', color="black", source=source)
    p.vbar('date', w, 'open', 'close', fill_color="green", line_color="black", source=source, selection_color="green")
    p.vbar('date', w, 'open', 'close', fill_color="red", line_color="black", source=source, selection_color="red")

def add_signals(p, df):
    buy_df = df[df['buy_signal']]
    sell_df = df[df['sell_signal']]
    
    p.scatter('date', 'low', marker='triangle', size=10, color="green", alpha=0.5, source=ColumnDataSource(buy_df))
    p.scatter('date', 'high', marker='inverted_triangle', size=10, color="red", alpha=0.5, source=ColumnDataSource(sell_df))

def add_vwma(p, source):
    p.line('date', 'vwma', color='blue', alpha=0.5, line_width=2, source=source, legend_label="VWMA")

def add_hover_tool(p, tooltips):
    hover = HoverTool(tooltips=tooltips, formatters={'@date': 'datetime'}, mode='vline')
    p.add_tools(hover)
    return hover

def add_crosshair_tool(p):
    crosshair = CrosshairTool()
    p.add_tools(crosshair)
    return crosshair

def visualize_strategy_results(df):
    df['date'] = pd.to_datetime(df['datetime'])
    source = ColumnDataSource(df)

    p = create_figure("Strategy Visualization")
    add_candlestick(p, df, source)
    add_signals(p, df)
    add_vwma(p, source)
    hover = add_hover_tool(p, [
        ('Date', '@date{%F}'),
        ('Open', '@open{0.00}'),
        ('High', '@high{0.00}'),
        ('Low', '@low{0.00}'),
        ('Close', '@close{0.00}'),
        ('Equity', '@equity{0.00}')
    ])

    p2 = create_figure("Equity Curve")
    add_equity_curve(p2, source)
    p2.add_tools(hover)

    crosshair = add_crosshair_tool(p)
    add_crosshair_tool(p2)

    p.toolbar.active_scroll = WheelZoomTool()
    p2.toolbar.active_scroll = WheelZoomTool()

    return p, p2

# 在 Dash 应用中使用 Bokeh 可视化
app = dash.Dash(__name__)

df = pd.read_csv('results/vad_5min_trades.csv')
p, p2 = visualize_strategy_results(df)

# 获取图形的 HTML 和 JavaScript 片段
script_p, div_p = components(p)
script_p2, div_p2 = components(p2)

app.layout = html.Div([
    html.H1("Strategy Visualization"),
    html.Div([
        html.Div([html.Div(id='plot1-div', style={'width': '100%', 'height': '600px'})], id='plot1-container'),
        html.Script(script_p)
    ]),
    html.H1("Equity Curve"),
    html.Div([
        html.Div([html.Div(id='plot2-div', style={'width': '100%', 'height': '600px'})], id='plot2-container'),
        html.Script(script_p2)
    ]),
])

if __name__ == '__main__':
    app.run_server(debug=True)
