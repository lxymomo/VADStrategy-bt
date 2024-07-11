import backtrader as bt
import config

class VWMA(bt.Indicator):
    lines = ('vwma',)
    params = dict(period=config.indicator_params['vwma_period'])

    def __init__(self):
        self.addminperiod(self.params.period)
        volume_price = self.data.close * self.data.volume
        self.lines.vwma = bt.indicators.SumN(volume_price, period=self.params.period) / bt.indicators.SumN(self.data.volume, period=self.params.period)
