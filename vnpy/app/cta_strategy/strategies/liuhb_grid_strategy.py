from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager
)
import json
import math
from vnpy.trader.constant import Direction


class LiuhbGridStrategy(CtaTemplate):
    Lot = 10  # 默认手数
    grid_ma_length = 30  # 均线周期
    grid_price = 0  # 开始价格
    grid_step = 50  # 止损步长
    Lot_max = 233  # 最大手数

    grid_ma = 0  # 均线

    parameters = ["Lot",
                  "grid_ma_length",
                  "grid_price",
                  "grid_step",
                  'Lot_max'
                  ]
    variables = ["grid_ma"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager()
        self.price = setting["grid_price"]
        self.step_price = setting["grid_step"]
        self.step_volume = setting["Lot"]
        self.pos = 0
        self.ask_price = 0.0  # 买入价
        self.bid_price = 0.0  # 卖出价
        self.vt_orderid = ""
        self.last_tick: TickData = None

    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")

        self.load_bar(self.grid_ma_length)

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.write_log("策略启动")

    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """
        Callback of new tick data update.
        """
        self.bg.update_tick(tick)
        self.last_tick = tick
        self.ask_price = tick.ask_price_1
        self.bid_price = tick.bid_price_1

        if abs(self.pos) >= self.Lot_max:
            return

        if self.vt_orderid:
            self.cancel_all()

        target_buy_distance = (self.price - self.last_tick.ask_price_1) / self.step_price
        target_buy_position = math.floor(target_buy_distance) * self.step_volume
        target_buy_volume = target_buy_position - self.pos

        # Calculate target volume to sell
        target_sell_distance = (self.price - self.last_tick.bid_price_1) / self.step_price
        target_sell_position = math.ceil(target_sell_distance) * self.step_volume
        target_sell_volume = self.pos - target_sell_position

        # Buy when price dropping
        if target_buy_volume > 0:
            print('current pos is {}'.format(self.pos))
            self.vt_orderid = self.buy(self.vt_symbol, self.last_tick.ask_price_1 - 0.5, min(target_buy_volume, self.last_tick.ask_volume_1))
        # Sell when price rising
        elif target_sell_volume > 0:
            print('current pos is {}'.format(self.pos))
            self.vt_orderid = self.sell(self.vt_symbol, self.last_tick.bid_price_1 + 0.5, min(target_sell_volume, self.last_tick.bid_volume_1))

    def on_bar(self, bar: BarData):

        am = self.am  # 转换为内部变量，增加查询速度
        am.update_bar(bar)  # m默认生成1分钟数据
        if not am.inited:
            return

        grid_array = am.sma(self.grid_ma_length, array=True)  # 计算均线
        self.grid_ma = grid_array[-1]  # 取均线最新值
        self.price = self.grid_ma
        self.put_event()

    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        if not order.is_active():
            self.vt_orderid = ""
            self.put_variables_event()

    def on_trade(self, trade: TradeData):  # 每笔成交调用一次
        """
        Callback of new trade data update.
        """
        self.write_log(trade)
        if trade.direction == Direction.LONG:
            self.pos += trade.volume
        else:
            self.pos -= trade.volume

        self.put_variables_event()


