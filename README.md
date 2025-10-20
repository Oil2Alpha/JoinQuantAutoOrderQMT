# 聚宽量化交易跟单系统

一个基于FRP技术的QMT交易平台跟单聚宽策略信号的自动化跟单系统，实现策略信号的自动接收、解析和交易执行。

## 技术原理

聚宽服务器--->您的公网服务器--FRP-->您的本地计算机（运行MiniQMT本系统）

## 功能特点

- 🔄 **自动跟单**：实时监听聚宽策略交易信号并自动执行
- 📊 **多策略支持**：支持多个策略同时运行，可配置独立跟单比例
- ⚡ **智能下单**：支持买入/卖出委托，自动处理整手和零股交易
- 🔄 **订单管理**：未成交订单自动撤单重试，支持最大重试次数配置
- 📱 **实时通知**：通过企业微信推送交易通知和摘要信息
- 🛡️ **风险控制**：涨停跌停检测、加密模块、交易时间验证等风控机制

## 环境要求

- Python 3.7+
- QMT交易终端
- 聚宽策略信号服务

## 安装依赖

pip install pandas tqdm numpy schedule xtquant flask json 

## 文件树

project/
├── 聚宽跟单设置.json          # 跟单系统配置
├── 分析配置.json              # 交易账户配置
├── main.py                   # 主程序
├── Trader.py                 # QMT交易接口
├── Receiver.py               # 数据接收服务
├── base_func.py              # 基础功能函数
├── send_trader_info.py       # 微信消息通知模块
├── 持股数据/                  # 持仓数据目录
├── 账户数据/                  # 账户信息目录
├── 原始数据/                  # 聚宽原始信号数据
├── 摘要数据/                  # 交易摘要数据
└── 下单股票池/                # 待交易股票池

## 如何开始

1.在聚宽策略服务器上您的策略代码最上面粘贴以下代码,并修改您的公网IP、端口和密钥（密钥需要与您本地“聚宽跟单设置.json”中的《解码令牌》保持一致，这是为了避免发送明文而被抓包攻击”）：
```python
#跟单代码
# 导入函数库
from jqdata import *
import requests
import json
import pandas as pd
import hashlib
import hmac
import base64

# 修改为您自己的服务器配置
url = 'http://xx.xxx.xx.xx'  # 您的云服务器公网IP
port = 6000  # 您设置的转发端口

# 加密配置
ENCRYPT_PASSWORD = "your secret"  # 加密密钥

class SimpleEncryptor:
    def __init__(self, password):
        self.password = password
        # 使用密码的SHA256哈希作为密钥
        self.key = hashlib.sha256(password.encode()).digest()
    def encrypt(self, data):
        """使用HMAC和简单异或加密"""
        if isinstance(data, dict):
            data = json.dumps(data, ensure_ascii=False)
        # 生成HMAC签名
        hmac_obj = hmac.new(self.key, data.encode('utf-8'), hashlib.sha256)
        signature = hmac_obj.hexdigest()
        # 简单异或加密（在聚宽环境中可用的轻量加密）
        encrypted = self._simple_xor_encrypt(data.encode('utf-8'))
        # 组合签名和加密数据
        result = {
            'signature': signature,
            'data': base64.b64encode(encrypted).decode('utf-8')
        }
        
        return base64.b64encode(json.dumps(result).encode('utf-8')).decode('utf-8')
    def _simple_xor_encrypt(self, data_bytes):
        """简单的异或加密"""
        key_bytes = self.key
        encrypted = bytearray()
        for i, byte in enumerate(data_bytes):
            encrypted.append(byte ^ key_bytes[i % len(key_bytes)])
        return bytes(encrypted)
# 初始化加密器
encryptor = SimpleEncryptor(ENCRYPT_PASSWORD)
# 发送函数
class simple_trader:
    def __init__(self, url='http://您的公网ip', port=6000):
        self.server_url = f'{url}:{port}'
    
    def send_simple_order(self, order_data):
        '''
        发送简化的交易数据，使用更通用的API格式
        '''
        endpoint = '/api/order'  # 更通用的endpoint
        request_url = f'{self.server_url}{endpoint}'
        encrypted_data = encryptor.encrypt(order_data)
        headers = {'Content-Type': 'application/json'}
        data = {
            'encrypted_order': encrypted_data,
            'timestamp': str(pd.Timestamp.now())
        }
        
        try:
            res = requests.post(url=request_url, json=data, headers=headers, timeout=10)
            print(f"简化交易信号已发送到: {request_url}")
            print(f"响应状态: {res.status_code}")
            return res.json() if res.status_code == 200 else None
        except Exception as e:
            print(f"发送简化交易信号失败: {e}")
            return None

# 可选：使用简化版本
simple_data = simple_trader(url=url, port=port)

def send_order(result):
    data = {}
    data['状态'] = str(result.status)
    data['订单添加时间'] = str(result.add_time)
    data['买卖'] = str(result.is_buy)
    data['下单数量'] = str(result.amount)
    data['已经成交'] = str(result.filled)
    data['股票代码'] = str(result.security)
    data['订单ID'] = str(result.order_id)
    data['平均成交价格'] = str(result.price)
    data['持仓成本'] = str(result.avg_cost)
    data['多空'] = str(result.side)
    data['交易费用'] = str(result.commission)
    data['时间戳'] = str(pd.Timestamp.now())
    data['密码'] = str("xxx")
    
    result_str = str(data)
    
    # 发送到您的服务器
    try:
        #xg_data.send_order(result_str)
        # 可选：同时使用简化版本发送
        simple_data.send_simple_order(data)
    except Exception as e:
        print(f"发送订单失败: {e}")
    
    return data

def xg_order(func):
    '''
    继承order对象 数据交易函数
    '''
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if result == None:
            return
        send_order(result)
        return result
    return wrapper

def xg_order_target(func):
    '''
    继承order_target对象 百分比
    '''
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if result == None:
            return        
        send_order(result)
        return result
    return wrapper
    
def xg_order_value(func):
    '''
    继承order_value对象 数量
    '''
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if result == None:
            return        
        send_order(result)
        return result
    return wrapper

def xg_order_target_value(func):
    '''
    继承order_target_value对象 数量
    '''
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if result == None:
            return        
        send_order(result)
        return result
    return wrapper

# from jqdata import *
order = xg_order(order)
order_target = xg_order_target(order_target)
order_value = xg_order_value(order_value)
order_target_value = xg_order_target_value(order_target_value)

```

2.购买任何一家云服务器供应商提供的云服务器和公用IP地址（最便宜的即可）

3.在您的服务器端安装FRP服务端（FRPS），并配制好端口和Token，然后启动FRPS服务。注：FRP开源，从Github下载

4.在您的本地电脑上安装FRP客户端(FRPC)，并配制好端口和Token，然后启动本地FRP服务

5.根据您本地电脑情况和策略情况自行填写分析配置.json和聚宽跟单设置.json

6.启动miniQMT服务后，使用Vscode运行该段代码，显示QMT连接成功,Flank服务成功，即说明您的系统运行正常

7.运行您的聚宽策略回测1-2天，可以看到交易系统收到订单并自动下单

## 版权与许可声明

### 使用限制

禁止开源：严禁其他人以任何形式将本代码公开、分发或作为开源项目发布

禁止商业用途：未经明确授权，禁止用于任何商业目的

禁止二次分发：禁止复制、修改后向第三方分发
