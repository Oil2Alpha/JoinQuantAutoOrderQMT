import random
import json
import time
import math
import pandas as pd
import xtquant.xtdata as xtdata
import os
import requests

class base_func:
    def __init__(self):
        pass
    def random_session_id(self):
        '''
        随机id
        '''
        session_id=''
        for i in range(0,9):
            session_id+=str(random.randint(1,9))
        return session_id

    def check_is_trader_date_1(self):
        '''
        检测是不是交易时间
        '''
        with open('分析配置.json','r+',encoding='utf-8') as f:
            com=f.read()
        text=json.loads(com)
        jhjj=text['是否参加集合竞价']
        loc=time.localtime()
        tm_hour=loc.tm_hour
        tm_min=loc.tm_min
        wo=loc.tm_wday
        if wo >= 5:
            return False
        if jhjj == '是':
            # 参加集合竞价
            # 上午 9:15-11:30
            is_morning = ((tm_hour == 9 and tm_min >= 15) or 
                        (tm_hour == 10) or
                        (tm_hour == 11 and tm_min <= 30))
            # 下午 13:00-15:00
            is_afternoon = ((tm_hour == 13) or
                        (tm_hour == 14) or
                        (tm_hour == 15 and tm_min == 0))
        else:
            # 不参加集合竞价  
            # 上午 9:30-11:30
            is_morning = ((tm_hour == 9 and tm_min >= 30) or 
                        (tm_hour == 10) or
                        (tm_hour == 11 and tm_min <= 30))
            # 下午 13:00-15:00
            is_afternoon = ((tm_hour == 13) or
                        (tm_hour == 14) or
                        (tm_hour == 15 and tm_min == 0))
        return is_morning or is_afternoon
        
    def select_data_type(self,stock='600031'):
        '''
        选择数据类型
        '''
        if stock[:3] in ['110','113','123','127','128','111','118']:
            return 'bond'
        elif stock[:3] in ['510','511','512','513','514','515','516','517','518','588','159','501','164'] or stock[:2] in ['16']:
            return 'fund'
        else:
            return 'stock'
    def adjust_stock(self,stock='600031.SH'):
        '''
        调整代码
        '''
        if stock[-2:]=='SH' or stock[-2:]=='SZ' or stock[-2:]=='sh' or stock[-2:]=='sz':
            stock=stock.upper()
        else:
            if stock[:3] in ['600','601','603','688','510','511',
                             '512','513','515','113','110','118','501'] or stock[:2] in ['11']:
                stock=stock+'.SH'
            else:
                stock=stock+'.SZ'
        return stock
    def adjust_amount(self,stock='',amount=''):
        '''
        调整数量
        '''           
        if stock[:3] in ['110','113','123','127','128','111']:
            amount=math.floor(amount/10)*10
        else:
            amount=math.floor(amount/100)*100
        return amount
    def check_stock_is_av_buy(self,stock='128036',price='156.700',amount=10,hold_limit=100):
        '''
        检查是否可以买入
        '''
        stock=self.adjust_stock(stock=stock)
        price=float(price)
        buy_value=price*amount
        try:
            cash_df=pd.read_excel(r'账户数据\账户数据.xlsx',dtype='object')
            del cash_df['Unnamed: 0'] 
        except:
            try:
                cash_df=pd.read_excel(r'账户数据.xlsx',dtype='object')
            except:   
                cash_df=self.balance()
        stock=self.adjust_stock(stock=stock)
        try:
            hold_data=self.position()
        except:
            try:
                hold_data=pd.read_excel(r'持股数据.xlsx',dtype='object')
            except:
                hold_data=pd.read_excel(r'持股数据\持股数据.xlsx',dtype='object')
        av_user_cash=cash_df['可用金额'].tolist()[-1]
        if stock in hold_data['证券代码'].tolist():
            hold_num=hold_data[hold_data['证券代码']==stock]['股票余额'].tolist()[-1]
        else:
            hold_num=0
        if hold_num>=hold_limit:
            print('不允许买入超过持股: 代码{} 可用资金{} 买入价值{}'.format(stock,av_user_cash,buy_value))
        elif av_user_cash>=buy_value and hold_num<hold_limit:
            print('允许买入: 代码{} 可用资金{} 买入价值{}'.format(stock,av_user_cash,buy_value))
            return True
        else:
            print('不允许买入可用资金不足: 代码{} 可用资金{} 买入价值{}'.format(stock,av_user_cash,buy_value))
            return False
    def check_stock_is_av_sell(self,stock='128036',amount=10):
        '''
        检查是否可以卖出
        '''
        stock=self.adjust_stock(stock=stock)
        try:
            hold_data=pd.read_excel(r'持股数据\持股数据.xlsx',dtype='object')
        except:
            try:
                hold_data=pd.read_excel(r'持股数据.xlsx',dtype='object')
            except:
                hold_data=self.position()
        stock_list=hold_data['证券代码'].tolist()
        if stock in stock_list:
            hold_num=hold_data[hold_data['证券代码']==stock]['可用余额'].tolist()[-1]
            if hold_num>=amount:
                print('允许卖出：{} 持股{} 卖出{}'.format(stock,hold_num,amount))
                return True
            else:
                print('不允许卖出持股不足：{} 持股{} 卖出{}'.format(stock,hold_num,amount))
                return False
        else:
            print('不允许卖出没有持股：{} 持股{} 卖出{}'.format(stock,0,amount))
            return False
    def adjust_hold_data(self,stock='603918',trader_type='sell',price=12,amount=100):
        '''
        模拟持股数据
        '''
        price=float(price)
        amount=float(amount)
        df=pd.read_excel(r'持股数据\持股数据.xlsx',dtype='object')
        del df['Unnamed: 0']
        df.index=df['证券代码']
        df1=df[df['证券代码']==stock]
        if df1.shape[0]>0:
            #可用余额
            available_balance=df1['可用余额'].tolist()[-1]
            #股票余额
            stock_balance=df1['股票余额'].tolist()[-1]
            if trader_type=='buy':
                stock_balance+=float(amount)
                available_balance+=float(amount)
            elif trader_type=='sell':
                available_balance-=float(amount)
                stock_balance-=float(amount)
                if available_balance<=0:
                    available_balance=0
                if stock_balance<=0:
                    stock_balance=0
            else:
                pass
            df1['可用余额']=[available_balance]
            df1['股票余额']=[stock_balance]
            data=df.drop(stock,axis=0)
            data=pd.concat([data,df1],ignore_index=True)
            data.to_excel(r'持股数据\持股数据.xlsx')
            print('持股数据调整成功')
        else:
            df2=pd.DataFrame()
            df2['明细']=['0']
            df2['证券代码']=[stock]
            df2['证券名称']=['0']
            df2['股票余额']=[amount]
            df2['可用余额']=[amount]
            df2['冻结数量']=[0]
            df2['成本价']=[price]
            df2['市价']=[price]
            df2['盈亏']=[0]
            df2['盈亏比(%)']=[0]
            df2['市值']=[amount*price]
            df2['当日买入']=[0]
            df2['当日卖出']=[0]
            df2['交易市场']=[0]
            df2['持股天数']=[0]
            data=pd.concat([df,df2],ignore_index=True)
            data.to_excel(r'持股数据\持股数据.xlsx')
            print('持股数据调整成功')													
            print('{}没有持股'.format(stock))
    def adjust_account_cash(self,stock='128036',trader_type='buy',price=123,amount=10):
        '''
        调整账户资金
        '''
        price=float(price)
        amount=float(amount)
        df=pd.read_excel(r'账户数据\账户数据.xlsx',dtype='object')
        try:
            del df['Unnamed: 0']
        except:
            pass
        value=price*amount
        #可用余额
        av_user_cash=float(df['可用金额'].tolist()[-1])
        if trader_type=='buy':
            av_user_cash-=value
        elif trader_type=='sell':
            av_user_cash+=value
        else:
            av_user_cash=av_user_cash
        df['可用金额']=[av_user_cash]
        df.to_excel(r'账户数据\账户数据.xlsx')
        print('账户资金调整完成')
        return df
 
    def adjust_stock(self,stock='600031.SH'):
        '''
        调整代码
        '''
        if stock[-2:]=='SH' or stock[-2:]=='SZ' or stock[-2:]=='sh' or stock[-2:]=='sz':
            stock=stock.upper()
        else:
            if stock[:3] in ['110','113','118','510','519',
                            "900",'200'] or stock[:2] in ['11','51','60','68'] or stock[:1] in ['5']:
                stock=stock+'.SH'
            else:
                stock=stock+'.SZ'
        return stock
    


    def get_stock_spot_data(self,stock):
        '''
        获取股票实时数据
        '''
        if self.check_is_trader_date_1()==False:
            return None
        try:
            stock_1=self.adjust_stock(stock=stock)
            tick=xtdata.get_full_tick(code_list=[stock_1])
            tick=tick[stock_1]
            if len(tick)>0:
                result={}
                result['证券代码']=stock
                result['时间']=tick['timetag']
                result['最新价']=tick['lastPrice']
                result['今开']=tick['open']
                result['最高价']=tick['high']
                result['最低价']=tick['low']
                result['昨收']=tick['lastClose']
                result['成交量']=tick['amount']
                result['成交额']=tick['volume']
                result['涨跌幅']=((tick['lastPrice']-tick['lastClose'])/tick['lastClose'])*100
                return result
            else:
                try:
                    stock=str(stock)[:6]
                    secid='{}.{}'.format(0,stock)
                    params={
                        'invt':'2',
                        'fltt':'1',
                        'cb':'jQuery3510180390237681324_1685191053405',
                        'fields':'f58,f107,f57,f43,f59,f169,f170,f152,f46,f60,f44,f45,f47,f48,f161,f49,f171,f50,f86,f177,f111,f51,f52,f168,f116,f117,f167,f162,f262',
                        'secid': secid,
                        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                        'wbp2u': '1452376043169950|0|1|0|web',
                        '_': '1685191053406',
                    }
                    url='http://push2.eastmoney.com/api/qt/stock/get?'
                    res=requests.get(url=url,params=params)
                    text=res.text
                    text=text[40:len(text)-2]
                    json_text=json.loads(text)
                    data=json_text['data']
                    result={}
                    result['最新价']=data['f43']/100
                    result['最高价']=data['f44']/100
                    result['最低价']=data['f45']/100
                    result['今开']=data['f46']/100
                    result['成交量']=data['f47']
                    result['成交额']=data['f48']
                    result['量比']=data['f50']/100
                    result['涨停']=data['f51']/100
                    result['跌停']=data['f52']/100
                    result['证券代码']=data['f57']
                    result['股票名称'] = data['f58']
                    result['昨收']=data['f60']/100
                    result['总市值']=data['f116']
                    result['流通市值']=data['f117']
                    result['换手率']=data['f168']/100
                    result['涨跌幅']=data['f170']/100
                    return result
                except:
                    
                    stock=str(stock)[:6]
                    secid='{}.{}'.format(1,stock)
                    params={
                            'invt':'2',
                            'fltt':'1',
                            'cb':'jQuery3510180390237681324_1685191053405',
                            'fields':'f58,f107,f57,f43,f59,f169,f170,f152,f46,f60,f44,f45,f47,f48,f161,f49,f171,f50,f86,f177,f111,f51,f52,f168,f116,f117,f167,f162,f262',
                            'secid': secid,
                            'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                            'wbp2u': '1452376043169950|0|1|0|web',
                            '_': '1685191053406',
                    }
                    url='http://push2.eastmoney.com/api/qt/stock/get?'
                    res=requests.get(url=url,params=params)
                    text=res.text
                    text=text[40:len(text)-2]
                    json_text=json.loads(text)
                    data=json_text['data']
                    result={}
                    result['最新价']=data['f43']/100
                    result['最高价']=data['f44']/100
                    result['最低价']=data['f45']/100
                    result['今开']=data['f46']/100
                    result['成交量']=data['f47']
                    result['成交额']=data['f48']
                    result['量比']=data['f50']/100
                    result['涨停']=data['f51']/100
                    result['跌停']=data['f52']/100
                    result['证券代码']=data['f57']
                    result['股票名称'] = data['f58']
                    result['昨收']=data['f60']/100
                    result['总市值']=data['f116']
                    result['流通市值']=data['f117']
                    result['换手率']=data['f168']/100
                    result['涨跌幅']=data['f170']/100
                    return result
        except Exception as e:
            print(e,stock,'qmt实时数据获取有问题切换到东方财富')
            try:
                stock=str(stock)[:6]
                secid='{}.{}'.format(0,stock)
                params={
                    'invt':'2',
                    'fltt':'1',
                    'cb':'jQuery3510180390237681324_1685191053405',
                    'fields':'f58,f107,f57,f43,f59,f169,f170,f152,f46,f60,f44,f45,f47,f48,f161,f49,f171,f50,f86,f177,f111,f51,f52,f168,f116,f117,f167,f162,f262',
                    'secid': secid,
                    'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                    'wbp2u': '1452376043169950|0|1|0|web',
                    '_': '1685191053406',
                }
                url='http://push2.eastmoney.com/api/qt/stock/get?'
                res=requests.get(url=url,params=params)
                text=res.text
                text=text[40:len(text)-2]
                json_text=json.loads(text)
                data=json_text['data']
                result={}
                result['最新价']=data['f43']/100
                result['最高价']=data['f44']/100
                result['最低价']=data['f45']/100
                result['今开']=data['f46']/100
                result['成交量']=data['f47']
                result['成交额']=data['f48']
                result['量比']=data['f50']/100
                result['涨停']=data['f51']/100
                result['跌停']=data['f52']/100
                result['证券代码']=data['f57']
                result['股票名称'] = data['f58']
                result['昨收']=data['f60']/100
                result['总市值']=data['f116']
                result['流通市值']=data['f117']
                result['换手率']=data['f168']/100
                result['涨跌幅']=data['f170']/100
                return result
            except:
                
                stock=str(stock)[:6]
                secid='{}.{}'.format(1,stock)
                params={
                        'invt':'2',
                        'fltt':'1',
                        'cb':'jQuery3510180390237681324_1685191053405',
                        'fields':'f58,f107,f57,f43,f59,f169,f170,f152,f46,f60,f44,f45,f47,f48,f161,f49,f171,f50,f86,f177,f111,f51,f52,f168,f116,f117,f167,f162,f262',
                        'secid': secid,
                        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                        'wbp2u': '1452376043169950|0|1|0|web',
                        '_': '1685191053406',
                }
                url='http://push2.eastmoney.com/api/qt/stock/get?'
                res=requests.get(url=url,params=params)
                text=res.text
                text=text[40:len(text)-2]
                json_text=json.loads(text)
                data=json_text['data']
                result={}
                result['最新价']=data['f43']/100
                result['最高价']=data['f44']/100
                result['最低价']=data['f45']/100
                result['今开']=data['f46']/100
                result['成交量']=data['f47']
                result['成交额']=data['f48']
                result['量比']=data['f50']/100
                result['涨停']=data['f51']/100
                result['跌停']=data['f52']/100
                result['证券代码']=data['f57']
                result['股票名称'] = data['f58']
                result['昨收']=data['f60']/100
                result['总市值']=data['f116']
                result['流通市值']=data['f117']
                result['换手率']=data['f168']/100
                result['涨跌幅']=data['f170']/100
                return result



