import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import matplotlib.pyplot as plt

def create_interactive_chart(data, strategy_results):
    """
    创建交互式图表，显示价格、成交量和交易信号
    """
    # 创建一个包含两个子图的图表,共享 x 轴
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=('Price', 'Volume'),
                        row_width=[0.7, 0.3])

    # 添加价格蜡烛图
    fig.add_trace(go.Candlestick(x=data.index,
                                 open=data['open'], high=data['high'],
                                 low=data['low'], close=data['close'],
                                 name='Price'),
                  row=1, col=1)

    # 添加策略的买入卖出点
    fig.add_trace(go.Scatter(x=strategy_results['buy_dates'], 
                             y=strategy_results['buy_prices'],
                             mode='markers',
                             name='Buy Signal',
                             marker=dict(symbol='triangle-up', size=10, color='green')),
                  row=1, col=1)

    # 添加卖出信号
    fig.add_trace(go.Scatter(x=strategy_results['sell_dates'], 
                             y=strategy_results['sell_prices'],
                             mode='markers',
                             name='Sell Signal',
                             marker=dict(symbol='triangle-down', size=10, color='red')),
                  row=1, col=1)

    # 更新布局
    fig.update_layout(title='Trading Strategy Visualization',
                      xaxis_rangeslider_visible=False)

    # 显示图表
    fig.show()

def plot_performance_metrics(portfolio_stats, trade_stats):
    """
    绘制策略性能指标的条形图
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))

    # 绘制投资组合统计
    metrics = list(portfolio_stats.keys())
    values = list(portfolio_stats.values())
    ax1.bar(metrics, values)
    ax1.set_title('Portfolio Performance Metrics')
    ax1.set_ylabel('Value')
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # 绘制交易统计
    metrics = list(trade_stats.keys())
    values = list(trade_stats.values())
    ax2.bar(metrics, values)
    ax2.set_title('Trade Statistics')
    ax2.set_ylabel('Count')
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    plt.show()

def plot_equity_curve(returns):
    """
    绘制策略的权益曲线
    """
    cumulative_returns = (1 + returns).cumprod()
    plt.figure(figsize=(10, 6))
    plt.plot(cumulative_returns.index, cumulative_returns.values)
    plt.title('Strategy Equity Curve')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Returns')
    plt.grid(True)
    plt.show()

def analyze_strategy(cerebro, results):
    """
    分析策略性能并返回结果
    """
    strat = results[0]

    # 提取分析结果
    portfolio_stats = {}
    if hasattr(strat.analyzers, 'returns'):
        portfolio_stats['Total Return'] = strat.analyzers.returns.get_analysis().get('rtot', 0)
    if hasattr(strat.analyzers, 'sharpe'):
        portfolio_stats['Sharpe Ratio'] = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
    if hasattr(strat.analyzers, 'drawdown'):
        portfolio_stats['Max Drawdown'] = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)

    # 使用 cerebro 来获取额外的统计信息
    portfolio_stats['Final Portfolio Value'] = cerebro.broker.getvalue()
    portfolio_stats['Starting Portfolio Value'] = cerebro.broker.startingcash

    trade_stats = {}
    if hasattr(strat.analyzers, 'trades'):
        trade_analysis = strat.analyzers.trades.get_analysis()
        trade_stats['Total Trades'] = trade_analysis.get('total', {}).get('total', 0)
        trade_stats['Avg Trade Length'] = trade_analysis.get('len', {}).get('average', 0)
        trade_stats['Profitable Trades'] = trade_analysis.get('won', {}).get('total', 0)
        trade_stats['Loss Trades'] = trade_analysis.get('lost', {}).get('total', 0)

    # 使用 cerebro 来获取额外的交易统计
    trade_stats['Commission Paid'] = cerebro.broker.getcash() - cerebro.broker.startingcash + getattr(strat, 'pnl', 0)

    # 打印分析结果
    print("Portfolio Statistics:")
    for key, value in portfolio_stats.items():
        print(f"{key}: {value}")

    print("\nTrade Statistics:")
    for key, value in trade_stats.items():
        print(f"{key}: {value}")

    return portfolio_stats, trade_stats

def visualize_strategy(cerebro, results, data):
    """
    可视化策略结果
    """
    portfolio_stats, trade_stats = analyze_strategy(cerebro, results)
    
    # 获取策略的交易信号
    strat = results[0]
    buy_signals = pd.DataFrame({'date': getattr(strat, 'buy_dates', []), 'price': getattr(strat, 'buy_prices', [])})
    sell_signals = pd.DataFrame({'date': getattr(strat, 'sell_dates', []), 'price': getattr(strat, 'sell_prices', [])})
    
    strategy_results = {
        'buy_dates': buy_signals['date'],
        'buy_prices': buy_signals['price'],
        'sell_dates': sell_signals['date'],
        'sell_prices': sell_signals['price']
    }

    # 创建交互式图表
    create_interactive_chart(data, strategy_results)
    
    # 绘制性能指标
    plot_performance_metrics(portfolio_stats, trade_stats)
    
    # 绘制权益曲线
    if hasattr(strat.analyzers, 'returns'):
        returns = pd.Series(strat.analyzers.returns.get_analysis().get('rtot', 0))
        plot_equity_curve(returns)
    else:
        print("Returns data not available for equity curve plotting.")