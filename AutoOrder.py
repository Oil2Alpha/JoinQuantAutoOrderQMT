import pandas as pd
from tqdm import tqdm
import numpy as np
import json
import os
from xtquant import xtconstant
import pandas as pd
import schedule
from datetime import datetime
import time
import Trader 
import Receiver
import threading
import base_func
import send_trader_info
from tabulate import tabulate

# 创建实例
with open('聚宽跟单设置.json','r+',encoding='utf-8') as f:
        com=f.read()
text=json.loads(com)
password=text['密码'] 
local_receiver_port=text['端口']
receiver = Receiver.local_jq_data_receiver(local_port=local_receiver_port,password=password)
def start_server_in_thread():
    """在单独线程中启动服务器"""
    def run_server():
        receiver.start_server()   
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()



class joinquant_trader:
    def __init__(self, qmt_path='D:/国金QMT交易端/userdata_mini',
                qmt_account='88888535', qmt_account_type='STOCK',  st_name='小市值组合策略',
                local_receiver_port=8888, max_retry='20', forced_sell='8'):

        self.qmt_path = qmt_path
        self.qmt_account = qmt_account
        self.qmt_account_type = qmt_account_type
        self.st_name = st_name
        self.local_receiver_port = local_receiver_port
        self.trader = Trader.Trader(self.qmt_path, self.qmt_account)
        self.path=os.path.dirname(os.path.abspath(__file__))
        self.base_func = base_func.base_func()
        self.max_retry = max_retry
        self.forced_sell= forced_sell
        #滑点
        #self.trader.slippage=0.01
        #交易记录,补单
        self.base_func = base_func.base_func()
        self.id_log=[]


        if not self.trader.connect():
            print(" QMT交易系统连接失败，请检查配置")

    def save_position(self):
        df=self.trader.get_positions()
        df=pd.DataFrame(df)
        if df is None:
            print('获取持股失败')
        elif isinstance(df, pd.DataFrame) and df.empty:
            print('当前空仓')
        if df.shape[0]>0:
            df.to_excel(r'持股数据\持股数据.xlsx')
            return df
    def save_balance(self):
        df=self.trader.get_account_info()
        df.to_excel(r'账户数据\账户数据.xlsx')
        return df
    
    def get_trader_data(self,name='测试1',zh_ratio=1):
        with open(r'{}\聚宽跟单设置.json'.format(self.path),encoding='utf-8') as f:
            com=f.read()
        text=json.loads(com)
        try:
            if os.path.exists(r'{}\原始数据\原始数据.csv'.format(self.path)):
                time.sleep(2)
            df = pd.read_csv(r'{}\原始数据\原始数据.csv'.format(self.path))
            self.cls_file()
        except FileNotFoundError:
            df = pd.DataFrame()
        except pd.errors.EmptyDataError:
            df = pd.DataFrame()
        except Exception as e:
            print(f"读取CSV文件出错: {e}")
            df = pd.DataFrame()
        try:
            df['证券代码']=df['证券代码'].apply(lambda x: '0'*(6-len(str(x)))+str(x))
        except:
            pass
        try:
            del df['Unnamed: 0']
        except:
            pass
        trader_log=self.trader.today_entrusts()
        if trader_log.shape[0]>0:
            #废单，撤单
            del_list=[54,57]
            trader_log['废单']=trader_log['委托状态'].apply(lambda x: '是' if x in del_list else '不是')
            trader_log=trader_log[trader_log['废单']=='不是']
            if trader_log.shape[0]>0:
                trader_id_list=trader_log['委托备注'].tolist()
            else:
                trader_id_list=[]
            trader_id_list=trader_log['证券代码'].tolist()
        else:
            trader_id_list=[]
        if df.shape[0]>0:
            df['订单ID ']=df['订单ID'].astype(str)
            if df.shape[0]>0:
                df['组合跟单比例']=zh_ratio
                df['交易检查']=df['投资备注'].apply(lambda x: '已经交易' if x in trader_id_list else '没有交易')
                df=df[df['交易检查']=='没有交易']
                amount_list=[]
                if df.shape[0]>0:
                    for stock,amount,trader_type in zip(df['证券代码'].tolist(),df['下单数量'].tolist(),df['交易类型'].tolist()):
                        try:
                            amount=amount*zh_ratio
                            if trader_type=='buy':
                                try:
                                    if amount>=100:
                                        amount_list.append(amount)
                                    else:
                                        amount_list.append(0)
                                except Exception as e:
                                    print(e,'组合{} 买入有问题****************'.format(name))
                                    amount_list.append(0)
                            elif trader_type=='sell':
                                try:
                                    if amount>=100:
                                        amount_list.append(amount)
                                    else:
                                        amount_list.append(0)
                                except Exception as e:
                                    print('组合{} {}卖出有问题可能没有持股'.format(name,stock))
                                    amount_list.append(0)
                            else:
                                print('组合{} {}未知的交易类型'.format(name,stock))
                                amount_list.append(0)
                        except Exception as e:
                            print(e,stock,'有问题*************')
                            amount_list.append(0)
                    df['数量']=amount_list
                    #数量为0的不进入下单记录
                    df=df[df['数量']>=10]
                    print('下单股票池））））））））））））））））））））））））')
                    print(df)
                    df.to_excel(r'{}\下单股票池\下单股票池.xlsx'.format(self.path))
                else:
                    print('{}组合没有需要下单标的******************'.format(name))
                    df=pd.DataFrame()
                    df.to_excel(r'{}\下单股票池\下单股票池.xlsx'.format(self.path))
            else:
                print('{}没有这个组合*************'.format(name))
                df=pd.DataFrame()
                df.to_excel(r'{}\下单股票池\下单股票池.xlsx'.format(self.path))
        else:
            #print('{}交易股票池没有数据*************'.format(name))
            df=pd.DataFrame()
            df.to_excel(r'{}\下单股票池\下单股票池.xlsx'.format(self.path))

    def start_trader_on(self,name='测试1',password='123456'):
        with open(r'{}\聚宽跟单设置.json'.format(self.path),encoding='utf-8') as f:
            com=f.read()
        text=json.loads(com)
        df=pd.read_excel(r'{}\下单股票池\下单股票池.xlsx'.format(self.path))
        try:
            df['证券代码']=df['证券代码'].apply(lambda x: '0'*(6-len(str(x)))+str(x))
        except:
            pass
        try:
            del df['Unnamed: 0 ']
        except:
            pass
        if df.shape[0]>0:
            df['证券代码']=df['证券代码'].astype(str)
            df['证券代码']=df['证券代码'].apply(lambda x: '0'*(6-len(str(x)))+str(x))
            #先卖在买
            sell_df=df[df['交易类型']=='sell']
            if sell_df.shape[0]>0:
                for stock,amount,maker, in zip(sell_df['证券代码'].tolist(),sell_df['数量'].tolist(),sell_df['投资备注'].tolist()):
                    if maker not in self.id_log:    
                        try:
                            stock_price=self.base_func.get_stock_spot_data(stock=stock)
                            price = stock_price['最新价'] if stock_price is not None else None
                            if price is None:
                                raise ValueError("非交易时间，无法获取有效价格")
                            stock = self.base_func.adjust_stock(stock)
                            self.trader.order_stock(stock_code=stock,order_type=xtconstant.STOCK_SELL,quantity=amount,price_type = xtconstant.FIX_PRICE,price=price,strategy_name=str(self.st_name[0]),remark=str(maker))
                            self.id_log.append(maker)
                            msg="""策略:{}\n股票:{}\n操作:卖出\n价格:{}\n数量:{}\n时间:{}""".format(self.st_name,stock,price,amount,datetime.now())
                            self.seed_msg(text=msg)
                        except Exception as e:
                            print(e)
                            print('组合{} {}卖出有问题'.format(name,stock))
                    else:
                        print('{} 在订单id等待卖出监测'.format(maker))
            else:
                print('{}组合没有符合调参的卖出数据'.format(name))
            buy_df=df[df['交易类型']=='buy']
            if buy_df.shape[0]>0:
                for stock,amount,maker in zip(buy_df['证券代码'].tolist(),buy_df['数量'].tolist(),buy_df['投资备注'].tolist()):
                    if maker not in self.id_log:
                        try:
                            stock_price=self.base_func.get_stock_spot_data(stock=stock)
                            price = stock_price['最新价'] if stock_price is not None else None
                            if price is None:
                                raise ValueError("非交易时间，无法获取有效价格")
                            stock = self.base_func.adjust_stock(stock)
                            self.trader.order_stock(stock_code=stock,order_type=xtconstant.STOCK_BUY,quantity=amount,price_type = xtconstant.FIX_PRICE,price=price,strategy_name=str(self.st_name[0]),remark=str(maker))
                            self.id_log.append(maker)
                            msg = """策略:{strategy}\n股票:{stock}\n操作:{action}\n价格:{price}\n数量:{amount}\n时间:{time}""".format(
                                    strategy=self.st_name,
                                    stock=stock,
                                    action="买入", 
                                    price=price,
                                    amount=amount,
                                    time=datetime.now())
                            self.seed_msg(text=msg)
                        except Exception as e:
                            print(e)
                            print('组合{} {}买入有问题'.format(name,stock))
                    else:
                        print('{} 在订单id等待买入检查'.format(maker))
            else:
                print('{}组合没有符合调参的买入数据'.format(name))
        else:
            #print('{}组合没有符合调参数据'.format(name))
            return True

    def update_all_data(self):
        '''
        更新策略数据
        '''
        if 1>0:
            with open(r'{}\聚宽跟单设置.json'.format(self.path),encoding='utf-8') as f:
                com=f.read()
            text=json.loads(com)
            name_list=text['策略名称']
            ratio_list=text['策略跟单比例']
            password=['密码']
            for name,ratio in zip(name_list,ratio_list):
                self.get_trader_data(name=name,zh_ratio=ratio)
                self.start_trader_on(name=name,password=password)
        else:
            print('跟单{} 目前不是交易时间***************'.format(datetime.now()))

    def get_remove_maker_id(self):
        '''
        检查交易记录
        '''
        trader_log=self.trader.today_entrusts()
        if trader_log.shape[0]>0:
            #废单，撤单
            del_list=[54,57]
            trader_log['废单']=trader_log['委托状态'].apply(lambda x: '是' if x in del_list else '不是')
            trader_log=trader_log[trader_log['废单']=='不是']
            if trader_log.shape[0]>0:
                trader_id_list=trader_log['委托备注'].tolist()
            else:
                trader_id_list=[]
        else:
            trader_id_list=[]
        if len(self.id_log)>0:
            for maker in self.id_log:
                if  maker not in trader_id_list:
                    self.id_log.remove(maker)
                    print(maker,'不在委托记录移除交易记录')
                else:
                    print(maker,'在委托记录不移除交易记录')
        else:
            #print('没有问题交易记录数据')
            return True

    def run_order_trader_func(self):
        '''
        下单不成交撤单在下单
        '''
        if self.trader.check_is_jhjj():
            print('集合竞价时间不撤单')
        else:
            if self.base_func.check_is_trader_date_1():
                time.sleep(10)
                trader_log=self.trader.today_entrusts()
                #不成交代码,注意57这个是策略下的废单，看个人是否需要
                not_list=[49,50,51,52]
                if trader_log.shape[0]>0:
                    trader_log['不成交']=trader_log['委托状态'].apply(lambda x: '是' if x in not_list else '不是')
                    trader_log=trader_log[trader_log['不成交']=='是']
                else:
                    trader_log=trader_log
                name_list=[self.st_name]
                try:
                    trader_log['去重键'] = trader_log['委托备注'].apply(lambda x:get_remark_key(x))
                    trader_log = trader_log.drop_duplicates(subset=['去重键'], keep='last')
                    trader_log = trader_log.drop('去重键', axis=1)  # 删除临时列
                    #trader_log=trader_log.drop_duplicates(subset=['委托备注'], keep='last')
                except Exception as e:
                    trader_log=pd.DataFrame()
                    print(e)
                if trader_log.shape[0]>0:
                    trader_log['证券代码']=trader_log['证券代码'].apply(lambda x: '0'*(6-len(str(x)))+str(x))
                    trader_log['策略'] = trader_log['委托备注'].apply(lambda x: str(x).split(',')[0] if x else '')
                    trader_log['本策略']=trader_log['策略'].apply(lambda x: '是' if x in name_list[0] else '不是')
                    trader_log['挂单次数']=trader_log['委托备注'].apply(lambda x: str(x).split(',')[-1] if x else '0')
                    trader_log=trader_log[trader_log['本策略']=='是']
                    if trader_log.shape[0]>0:
                        for stock,amount,trader_type,maker,order_id,name,times in zip(trader_log['证券代码'].tolist(),
                                trader_log['未成交数量'].tolist(),trader_log['买卖方向'].tolist(),
                                trader_log['委托备注'].tolist(),trader_log['委托编号'].tolist(),
                                trader_log['策略名称'].tolist(),trader_log['挂单次数'].tolist()):
                            stock=self.base_func.adjust_stock(stock=stock)
                            if self.trader.is_limit_down(stock_code=stock) or self.trader.is_limit_up(stock_code=stock):
                                print('{}涨停/跌停不撤单*******'.format(stock))
                            else:
                                price=self.base_func.get_stock_spot_data(stock=stock)['最新价']
                                #未成交卖出
                                print('未成交订单：')
                                print('证券代码：{} 未成交数量{}交易类型{} 投资备注{} 订单id{} 撤单次数{}'.format(stock,amount,trader_type,maker,order_id,times))
                                times = int(times)
                                times = times + 1   #每次申请撤单都增加一次撤单次数
                                #卖出
                                if times > self.max_retry:
                                    msg = "股票{}本次订单挂单次数超过最大次数,已不再尝试交易".format(stock)
                                    self.seed_msg(text=msg)
                                    continue   #该股票不再继续挂单
                                if trader_type=='卖出':
                                    cancel_order_result=self.trader.cancel_order(order_id=order_id)
                                    time.sleep(5)     #等待5秒再检查是否撤单成功，给系统反应时间
                                    trader_log=self.trader.today_entrusts()
                                    #不成交代码,注意57这个是策略下的废单，看个人是否需要
                                    not_list=[49,50,51,52]
                                    if trader_log.shape[0]>0:
                                        trader_log['不成交']=trader_log['委托状态'].apply(lambda x: '是' if x in not_list else '不是')
                                        trader_log=trader_log[trader_log['不成交']=='是']
                                        maker_list=trader_log['委托备注'].tolist()
                                    else:
                                        maker_list=[]
                                    if maker in maker_list or cancel_order_result !=0:
                                        print(maker,"委托编号"+str(order_id),'卖出撤单没有成功,等待继续撤单')
                                    else:
                                        parts = maker.split(',')
                                        parts[-1] = str(times)  # 更新备注中的撤单次数
                                        maker = ','.join(parts)
                                        if amount<100:
                                            if times<self.forced_sell:  #挂普通限价单
                                                self.trader.order_stock(stock_code=stock,order_type=xtconstant.STOCK_SELL,quantity=amount,price_type = xtconstant.FIX_PRICE,price=price,strategy_name=str(self.st_name[0]),remark=str(maker))
                                                msg="""策略：{}\n股票：{}\n操作:卖出\n价格:{}\n数量:{}\n订单号:{}\n时间:{}\n备注:第{}次卖出未成交撤单再次挂单""".format(self.st_name, stock, price, amount,order_id ,datetime.now(),times)
                                                self.seed_msg(text=msg)
                                            else:        #直接挂卖一档强制卖出
                                                self.trader.order_stock(stock_code=stock,order_type=xtconstant.STOCK_SELL,quantity=amount,price_type = xtconstant.MARKET_PEER_PRICE_FIRST,price=price,strategy_name=str(self.st_name[0]),remark=str(maker))
                                                msg="""策略：{}\n股票：{}\n操作:卖出\n价格:{}\n数量:{}\n订单号:{}\n时间:{}\n备注:第{}次卖出未成交撤单再次挂对手方最优价格强制卖出""".format(self.st_name, stock, price, amount,order_id ,datetime.now(),times)
                                                self.seed_msg(text=msg)
                                        elif amount%100==0:
                                            if times<self.forced_sell:
                                                self.trader.order_stock(stock_code=stock,order_type=xtconstant.STOCK_SELL,quantity=amount,price_type = xtconstant.FIX_PRICE,price=price,strategy_name=str(self.st_name[0]),remark=str(maker))
                                                msg="""策略：{}\n股票：{}\n操作:卖出\n价格:{}\n数量:{}\n订单号:{}\n时间:{}\n备注:第{}卖出未成交撤单再次挂单""".format(self.st_name, stock, price, amount,order_id ,datetime.now(),times)
                                                self.seed_msg(text=msg)
                                            else:
                                                self.trader.order_stock(stock_code=stock,order_type=xtconstant.STOCK_SELL,quantity=amount,price_type = xtconstant.MARKET_PEER_PRICE_FIRST,price=price,strategy_name=str(self.st_name[0]),remark=str(maker))
                                                msg="""策略：{}\n股票：{}\n操作:卖出\n价格:{}\n数量:{}\n订单号:{}\n时间:{}\n备注:第{}卖出未成交撤单再次挂对手方最优价格强制卖出""".format(self.st_name, stock, price, amount,order_id ,datetime.now(),times)
                                                self.seed_msg(text=msg)
                                        else:
                                            round_lots = (amount // 100) * 100  # 整手部分
                                            odd_lots = amount % 100            # 零股部分
                                            self.trader.order_stock(stock_code=stock,order_type=xtconstant.STOCK_SELL,quantity=round_lots,price_type = xtconstant.FIX_PRICE,price=price,strategy_name=str(self.st_name[0]),remark=str(maker))
                                            self.trader.order_stock(stock_code=stock,order_type=xtconstant.STOCK_SELL,quantity=odd_lots,price_type = xtconstant.FIX_PRICE,price=price,strategy_name=str(self.st_name[0]),remark=str(maker))
                                            msg="""策略：{}\n股票：{}\n操作:卖出\n价格:{}\n数量:{}\n订单号:{}\n时间:{}\n备注:卖出部成交，撤单拆分零整手再次挂单""".format(self.st_name, stock, price, amount,order_id ,datetime.now())
                                            self.seed_msg(text=msg)
                                elif trader_type=='买入':
                                    cancel_order_result=self.trader.cancel_order(order_id=order_id)
                                    time.sleep(5)
                                    #检查是否撤单成功
                                    trader_log=self.trader.today_entrusts()
                                    #不成交代码,注意57这个是策略下的废单，看个人是否需要
                                    not_list=[49,50,51,52]
                                    if trader_log.shape[0]>0:
                                        trader_log['不成交']=trader_log['委托状态'].apply(lambda x: '是' if x in not_list else '不是')
                                        trader_log=trader_log[trader_log['不成交']=='是']
                                        maker_list=trader_log['委托备注'].tolist()
                                    else:
                                        maker_list=[]
                                    if maker in maker_list or cancel_order_result !=0:
                                        print(maker,"委托编号"+str(order_id),'买入撤单没有成功,等待继续撤单')
                                    else:
                                        parts = maker.split(',')
                                        parts[-1] = str(times)  # 更新备注中的撤单次数
                                        maker = ','.join(parts)
                                        if amount>100 and amount%100==0:
                                            self.trader.order_stock(stock_code=stock,order_type=xtconstant.STOCK_BUY,quantity=amount,price_type = xtconstant.FIX_PRICE,price=price,strategy_name=str(self.st_name[0]),remark=str(maker))
                                            msg="""策略：{}\n股票：{}\n操作:买入\n价格:{}\n数量:{}\n订单号:{}\n时间:{}\n备注:第{}买入未成交撤单再次挂单""".format(self.st_name, stock, price, amount,order_id ,datetime.now(),times)
                                            self.seed_msg(text=msg)
                                        else:
                                            self.seed_msg(text="存在异常数量的股票无法有效挂买入单")
                                            print("存在小于100手数量的股票无法有效挂买入单")
                                else:
                                    print('组合{} 撤单重新交易未知的交易类型'.format(name))
                    else:
                        print('本策略撤单了没有需要重新下单的委托数据')
                else:
                    #print('没有需要重新下单的委托数据')
                    return True
            else:
                #print(datetime.now(),'目前不是交易时间')
                return True

    def trade_summary(self):
        if self.base_func.check_is_trader_date_1():
            try:
                df_joinquant = pd.read_csv(r'.\摘要数据\摘要数据.csv')
                self.cls_summary_file()
                df_qmt = self.trader.today_trades()
            except Exception as e:
                print(f"查询当日成交失败：{e}")
                df_joinquant = pd.DataFrame()
            try:
                if df_joinquant.shape[0]>0 and df_qmt.shape[0]>0:
                    msg_joinquant = "聚宽交易信号摘要\n"
                    df_joinquant['交易类型'] = df_joinquant['买卖'].apply(lambda x: '买入' if x == True or x == 'True' or x == 'true' else '卖出')
                    for index,row in df_joinquant.iterrows():
                        msg_joinquant += f"证券:{row['证券代码']}\n"
                        msg_joinquant += f"操作:{row['交易类型']}{row['下单数量']}股\n"
                        msg_joinquant += f"价格:{row['平均成交价格']}元\n"
                        msg_joinquant += f"时间:{str(row['订单添加时间'])}\n"  # 只显示时分秒
                        msg_joinquant += "---\n"
                    buy_count_jq = len(df_joinquant[df_joinquant['交易类型'] == '买入'])
                    sell_count_jq = len(df_joinquant[df_joinquant['交易类型'] == '卖出'])
                    msg_joinquant += f"买入:{buy_count_jq}\n卖出:{sell_count_jq}\n"
                    msg_joinquant += f"合计:{len(df_joinquant)}条交易记录"
                    self.seed_msg(text=msg_joinquant)
                    msg_qmt = "当日真实交易摘要\n"  
                    for index,row in df_qmt.iterrows():
                        msg_qmt += f"证券:{row['证券代码']}\n"
                        msg_qmt += f"操作:{row['买卖']}{row['成交数量']}股\n"
                        msg_qmt += f"价格:{row['成交均价']}元\n"
                        msg_qmt += f"时间:{str(row['成交时间'])}\n"  # 只显示时分秒
                        msg_qmt += "---\n"
                    buy_count_qmt = len(df_qmt[df_qmt['买卖'] == '买入'])
                    sell_count_qmt = len(df_qmt[df_qmt['买卖'] == '卖出'])
                    msg_qmt += f"买入:{buy_count_qmt}\n卖出:{sell_count_qmt}\n"
                    msg_qmt += f"合计:{len(df_qmt)}条交易记录\n"
                    self.seed_msg(text=msg_qmt)
                elif df_joinquant.shape[0]>0 and df_qmt.shape[0]==0:
                    self.seed_msg(text="跟单程序可能出现意外，收到交易信号但无成交记录")
                else:
                    self.seed_msg(text="心跳信号：交易时间，今日无交易信号")
            except Exception as e:
                print(f"发送当日交易摘要失败：{e}")
        else:
            self.seed_msg(text="心跳信号：非交易时间，程序正常运行")

    def cls_file(self):
        file_path = './原始数据/原始数据.csv'
        os.makedirs('原始数据', exist_ok=True)
        os.remove(file_path)
        return True
    
    def cls_summary_file(self):
        file_path = './摘要数据/摘要数据.csv'
        os.makedirs('摘要数据', exist_ok=True)
        os.remove(file_path)
        return True

    def seed_msg(self,text=','):
        '''
        发生交易通知,发送至企业微信
        '''
        msg=text
        msg+=','
        with open('分析配置.json','r+',encoding='utf-8') as f:
            com=f.read()
        text=json.loads(com)
        wx_token_list=text['微信token']
        seed=send_trader_info.send_info(wx_token_list)
        seed.seed_wechat(msg)

def is_trading_time():
    """判断是否在交易时间段内"""
    now = datetime.now()
    current_time = now.time()
    
    # 检查是否是周末
    if now.weekday() >= 5:  # 5=周六, 6=周日
        return False
    current_hour = now.hour
    current_minute = now.minute
    # 交易时间段：8:40-16:00（包含16:00整点）
    if current_hour == 8 and current_minute >= 40:
        return True
    elif 9 <= current_hour < 16:
        return True
    elif current_hour == 16 and current_minute == 0:
        return True
    
def get_remark_key(remark):
    """从备注中提取去重关键信息（排除挂单次数）"""
    if pd.isna(remark) or remark == '':
        return remark
    parts = str(remark).split(',')
    # 取前3个部分：策略名,股票代码,订单ID
    return ','.join(parts[:3]) if len(parts) >= 3 else remark

if __name__=='__main__':
    with open('分析配置.json','r+',encoding='utf-8') as f:
        com=f.read()
    text=json.loads(com)
    qmt_account=text['qmt账户']
    qmt_path=text['qmt路径']
    qmt_account_type=text['交易品种']
    summary_message=text['发送摘要时间']
    with open('聚宽跟单设置.json','r+',encoding='utf-8') as f:
        com=f.read()
    text_a=json.loads(com)
    st_name=text_a['策略名称']
    max_retry=int(text_a['最大重新下单次数'])
    forced_sell=int(text_a['触发强制卖出次数'])
    

  
    trader=joinquant_trader(qmt_path=qmt_path,qmt_account=qmt_account,st_name=st_name,qmt_account_type=qmt_account_type,
                            local_receiver_port=local_receiver_port,max_retry=max_retry, forced_sell=forced_sell)
    #打印账户信息
    print(trader.save_balance())
    print(trader.save_position())
    #启动监听服务
    start_server_in_thread()
    #检查交易信号
    schedule.every(0.05).minutes.do(trader.update_all_data)
    #10秒检查一下订单
    schedule.every(0.2).minutes.do(trader.get_remove_maker_id)
    #45秒撤单了在下单(检查挂单未交易前sleep(15)避免刚挂单就撤单)
    schedule.every(0.5).minutes.do(trader.run_order_trader_func)
    #对应时间发送一下摘要
    schedule.every().day.at(summary_message).do(trader.trade_summary)
    #开板卖出
    #schedule.every(0.06).minutes.do(trader.run_get_check_open_zt)
    while True:
        schedule.run_pending()
        if is_trading_time():
            time.sleep(1)   # 交易时间段：1秒间隔
        else:
            time.sleep(360) # 非交易时间：10分钟间隔
