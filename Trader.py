# coding=utf-8
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant
import xtquant.xtdata as xtdata
import time
import pandas as pd
import json
from datetime import datetime

class MyXtQuantTraderCallback(XtQuantTraderCallback):
    """交易回调类"""
    def on_disconnected(self):
        print("连接断开")
        
    def on_connected(self):
        print("连接成功")
        
    def on_stock_order(self, order):
        print(f"委托回报: {order.stock_code} {order.order_status}")
        
    def on_stock_trade(self, trade):
        print(f"成交回报: {trade.stock_code} {trade.traded_volume}股")
        
    def on_stock_asset(self, asset):
        print(f"资金变动: 现金{asset.cash} 总资产{asset.total_asset}")
        
    def on_stock_position(self, position):
        print(f"持仓变动: {position.stock_code} {position.volume}股")
        
    def on_order_error(self, order_error):
        print(f"委托失败: {order_error.error_msg}")
        
    def on_cancel_error(self, cancel_error):
        print(f"撤单失败: {cancel_error.error_msg}")

class Trader:
    """QMT交易器封装类"""
    
    def __init__(self, qmt_path, account_id, account_type='STOCK', session_id=None):
        """
        初始化交易器
        
        Args:
            qmt_path: QMT安装路径下的userdata_mini目录
            account_id: 资金账号
            account_type: 账号类型，默认STOCK
            session_id: 会话ID，默认使用时间戳
        """
        self.qmt_path = qmt_path
        self.account_id = account_id
        self.account_type = account_type
        self.session_id = session_id or int(time.time())
        
        # 创建账号对象
        self.account = StockAccount(account_id, account_type)
        
        # 创建交易器和回调
        self.xt_trader = XtQuantTrader(qmt_path, self.session_id)
        self.callback = MyXtQuantTraderCallback()
        
        # 连接状态
        self.is_connected = False
        self.is_subscribed = False
    
    def connect(self):
        """连接交易系统"""
        try:
            # 注册回调
            self.xt_trader.register_callback(self.callback)
            
            # 启动交易线程
            self.xt_trader.start()
            
            # 建立连接
            connect_result = self.xt_trader.connect()
            if connect_result == 0:
                self.is_connected = True
                print("QMT交易系统连接成功")
                
                # 订阅账号
                subscribe_result = self.xt_trader.subscribe(self.account)
                if subscribe_result == 0:
                    self.is_subscribed = True
                    print("账号订阅成功")
                else:
                    print(f"账号订阅失败: {subscribe_result}")
                    
                return True
            else:
                print(f"连接失败，错误码: {connect_result}")
                return False
                
        except Exception as e:
            print(f"连接异常: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        try:
            self.xt_trader.stop()
            self.is_connected = False
            self.is_subscribed = False
            print("已断开连接")
        except Exception as e:
            print(f"断开连接异常: {e}")
    
    # ==================== 查询方法 ====================
    
    def get_account_info(self):
        """查询账户资产信息"""
        if not self._check_connection():
            return None
            
        try:
            asset = self.xt_trader.query_stock_asset(self.account)
            if asset:
                value = pd.DataFrame({
                    '账户ID': asset.account_id,
                    '现金': asset.cash,  # 现金
                    '总资产': asset.total_asset,  # 总资产
                    '股票市值': asset.market_value,  # 市值
                    '冻结资金': asset.frozen_cash,  # 冻结资金
                },index = [0])
                return value
            return None
        except Exception as e:
            print(f"查询资产信息失败: {e}")
            return None
    
    def get_positions(self, stock_code=None):
        """查询持仓信息
        
        Args:
            stock_code: 股票代码，如'600000.SH'，为None时查询所有持仓
        """
        if not self._check_connection():
            return None
            
        try:
            if stock_code:
                # 查询指定股票持仓
                position = self.xt_trader.query_stock_position(self.account, stock_code)
                if position:
                    return pd.DataFrame([self._format_position(position)])
                return []
            else:
                # 查询所有持仓
                positions = self.xt_trader.query_stock_positions(self.account)
                return pd.DataFrame([self._format_position(pos) for pos in positions]) if positions else []
        except Exception as e:
            print(f"查询持仓失败: {e}")
            return None
    
    def get_orders(self, cancelable_only=False):
        """查询当日委托
        
        Args:
            cancelable_only: 是否只查询可撤单委托
        """
        if not self._check_connection():
            return None
            
        try:
            orders = self.xt_trader.query_stock_orders(self.account, cancelable_only)
            return [self._format_order(order) for order in orders] if orders else []
        except Exception as e:
            print(f"查询委托失败: {e}")
            return None
    
    def get_trades(self):
        """查询当日成交"""
        if not self._check_connection():
            return None
            
        try:
            trades = self.xt_trader.query_stock_trades(self.account)
            return [self._format_trade(trade) for trade in trades] if trades else []
        except Exception as e:
            print(f"查询成交失败: {e}")
            return None
    def is_limit_up(self, stock_code):
        """查询股票是否涨停
        Args:
            stock_code: 6位股票代码，如'600000'
        Returns:
            bool: True表示涨停，False表示未涨停
        """
        try:
            # 补全股票代码后缀
            full_code = f"{stock_code}.SH" if stock_code.startswith('6') else f"{stock_code}.SZ"
            
            # 获取股票实时行情
            tick_data = xtdata.get_full_tick([full_code])
            
            if full_code in tick_data:
                current_price = tick_data[full_code]['lastPrice']  # 最新价
                high_limit = tick_data[full_code]['highLimit']     # 涨停价
                
                # 如果最新价等于涨停价，则判断为涨停
                if current_price == high_limit and current_price > 0:
                    return True
            
            return False
            
        except Exception as e:
            print(f"查询涨停状态失败: {e}")
            return False

    def is_limit_down(self, stock_code):
        """查询股票是否跌停
        
        Args:
            stock_code: 6位股票代码，如'600000'
        
        Returns:
            bool: True表示跌停，False表示未跌停
        """
        try:
            # 补全股票代码后缀
            full_code = f"{stock_code}.SH" if stock_code.startswith('6') else f"{stock_code}.SZ"
            
            # 获取股票实时行情
            tick_data = xtdata.get_full_tick([full_code])
            
            if full_code in tick_data:
                current_price = tick_data[full_code]['lastPrice']  # 最新价
                low_limit = tick_data[full_code]['lowLimit']       # 跌停价
                
                # 如果最新价等于跌停价，则判断为跌停
                if current_price == low_limit and current_price > 0:
                    return True
            
            return False
            
        except Exception as e:
            print(f"查询跌停状态失败: {e}")
            return False
        
    def check_is_jhjj(self):
        '''
        检查是否集合竞价
        集合竞价不做撤单
        9点15到9点30不撤单
        14点57到59不撤单
        '''
        loc=time.localtime()
        tm_hour=loc.tm_hour
        tm_min=loc.tm_min
        wo=loc.tm_wday
        #早上集合竞价开始时间
        zs_start_hour=9
        zs_start_mini=15
        #早上集合竞价结束时间
        zs_end_hour=9
        zs_end_mini=30
        #下午时间
        xw_start_hour=14
        xw_start_mini=57
        #下午集合竞价结束时间
        xw_end_hour=14
        xw_end_mini=59
        if tm_hour==zs_start_hour and tm_hour==zs_end_hour and tm_min>=zs_start_mini and tm_min<zs_end_mini:
            print("早上集合竞价时间")
            return True
        elif tm_hour==xw_start_hour and tm_hour==xw_end_hour and tm_min>=xw_start_mini and tm_min<=xw_end_mini:
            print("下午集合竞价时间")
            return True
        else:
            #print('非集合竞价时间')
            return False
    # ==================== 交易方法 ====================
    
    
    def buy(self, stock_code, price, quantity, price_type=xtconstant.FIX_PRICE):

        return self.order_stock(stock_code, xtconstant.STOCK_BUY, quantity, price_type, price)
    
    def sell(self, stock_code, price, quantity, price_type=xtconstant.FIX_PRICE):
        """卖出股票"""
        return self.order_stock(stock_code, xtconstant.STOCK_SELL, quantity, price_type, price)
    
    def order_stock(self, stock_code, order_type, quantity, price_type, price, 
                   strategy_name='', remark=''):
        """下单交易"""
        if not self._check_connection():
            return None
            
        try:
            order_id = self.xt_trader.order_stock(
                self.account, stock_code, order_type, quantity, 
                price_type, price, strategy_name, remark
            )
            print(f" 下单成功，订单ID: {order_id}")
            return order_id
        except Exception as e:
            print(f"下单失败: {e}")
            return None
    
    def cancel_order(self, order_id):
        """撤单"""
        if not self._check_connection():
            return False
            
        try:
            result = self.xt_trader.cancel_order_stock(self.account, order_id)
            if result == 0:
                print(f"撤单请求已成功发送: {order_id}")
                return result
            else:
                print(f"撤单失败: {order_id}, 错误码: {result}")
                return result
        except Exception as e:
            print(f"撤单异常: {e}")
            return result
        
    def today_entrusts(self):
        """
        查询当日所有委托记录
        Returns:
            DataFrame: 包含当日所有委托记录的DataFrame
        """
        if not self._check_connection():
            return pd.DataFrame()

        try:
            # 查询所有委托记录（cancelable_only=False表示查询所有状态）
            orders = self.xt_trader.query_stock_orders(self.account, cancelable_only=False)
            if not orders:
                return pd.DataFrame()
            # 格式化委托记录
            entrusts_list = []
            for order in orders:
                entrust_data = {
                    '委托编号': order.order_id,
                    '证券代码': order.stock_code,
                    '委托状态': order.order_status,
                    '买卖方向': '买入' if order.order_type == xtconstant.STOCK_BUY else '卖出',
                    '委托价格': order.price,
                    '委托数量': order.order_volume,
                    '成交数量': order.traded_volume,
                    '未成交数量':order.order_volume-order.traded_volume,
                    '委托时间': order.order_time,
                    '策略名称': order.strategy_name,
                    '委托备注': order.order_remark
                }
                entrusts_list.append(entrust_data)
            
            df = pd.DataFrame(entrusts_list)
            return df  
        except Exception as e:
            print(f" 查询当日委托失败: {e}")
            return pd.DataFrame()
        
    def _get_order_status_desc(self, status_code):
        """获取委托状态描述"""
        status_map = {
            48: "未报",      
            49: "待报",   
            50: "已报",      
            51: "已报待撤",   
            52: "部成待撤",  
            53: "部撤（部分成交，剩下已撤单）",   
            54: "已撤",     
            55: "部成（部分成交，剩下的待成交）",  
            56: "已成",     
            57: "废单",  
            255: "未知" 
        }
        return status_map.get(status_code, f"未知状态({status_code})")
        
    def today_trades(self):
        if not self.is_connected:
            print(" 未连接交易系统，请先调用connect()方法")
            return False
        try:
            trades = self.xt_trader.query_stock_trades(self.account)
            if not trades:
                return pd.DataFrame()
            trades_list = []
            for trade in trades:
                trade_data = {
                    '成交编号':trade.traded_id,
                    '证券代码':trade.stock_code,
                    '买卖':'买入' if trade.order_type == xtconstant.STOCK_BUY else '卖出',
                    '成交均价':trade.traded_price,
                    '成交数量':trade.traded_volume,
                    '成交时间':datetime.fromtimestamp(trade.traded_time).strftime('%Y-%m-%d %H:%M:%S')
                }
                trades_list.append(trade_data)
            df = pd.DataFrame(trades_list)
            return df
        except Exception as e:
            print(f"查询当日成交失败：{e}")
            return pd.DataFrame()

    # ==================== 工具方法 ====================
    
    def _check_connection(self):
        """检查连接状态"""
        if not self.is_connected:
            print(" 未连接交易系统，请先调用connect()方法")
            return False
        return True
    
    def _format_position(self, position):
        """格式化持仓信息"""
        return {
            'stock_code': position.stock_code,
            'stock_name': getattr(position, 'stock_name', ''),
            'volume': position.volume,  # 当前持仓
            'can_use_volume': position.can_use_volume,  # 可用持仓
            'open_price': position.open_price,  # 开仓价
            'market_value': position.market_value  # 市值
        }
    
    def _format_order(self, order):
        """格式化委托信息"""
        return {
            'order_id': order.order_id,
            'stock_code': order.stock_code,
            'order_status': order.order_status,
            'order_type': '买入' if order.order_type == xtconstant.STOCK_BUY else '卖出',
            'order_volume': order.order_volume,  # 委托数量
            'traded_volume': order.traded_volume,  # 成交数量
            'price': order.price,  # 委托价格
            'order_time': order.order_time
        }
    
    def _format_trade(self, trade):
        """格式化成交信息"""
        return {
            'trade_id': trade.trade_id,
            'stock_code': trade.stock_code,
            'order_id': trade.order_id,
            'traded_price': trade.traded_price,  # 成交价格
            'traded_volume': trade.traded_volume,  # 成交数量
            'trade_time': trade.trade_time
        }
    
    def run_forever(self):
        """保持运行以接收推送"""
        if self.is_connected:
            print(" 开始接收交易推送，按Ctrl+C退出...")
            self.xt_trader.run_forever()
        else:
            print("❌ 未连接，无法运行")




# 使用示例
if __name__=='__main__':

    with open('分析配置.json','r+',encoding='utf-8') as f:
        com=f.read()
    text=json.loads(com)
    qq=text['发送qq'] 
    qmt_account=text['qmt账户']
    qmt_path=text['qmt路径']
    qmt_account_type=text['交易品种']
  
    trader=Trader(qmt_path=qmt_path,account_id=qmt_account)
    trader.connect()
    #打印账户信息
    print(trader.today_entrusts())