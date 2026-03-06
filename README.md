# 聚宽量化交易跟单系统

一个基于FRP技术的QMT交易平台跟单聚宽策略信号的自动化跟单系统，实现策略信号的自动接收、解析和交易执行。

## 技术原理

```
聚宽服务器 → HTTP POST → 公网服务器 → FRP → 本地 Receiver(Flask) → Queue → AutoOrder(QMT)
```

## 功能特点

- 🔄 **事件驱动下单**：Receiver 收到信号后通过 Queue 立即触发下单，替代传统 CSV 轮询，延迟 <100ms
- 📊 **多策略支持**：支持多个策略同时运行，可配置独立跟单比例
- ⚡ **智能下单**：支持买入/卖出委托，自动处理整手和零股交易
- 🔄 **订单管理**：未成交订单自动撤单重试，支持最大重试次数和强制卖出配置
- 📱 **实时通知**：通过企业微信推送交易通知和摘要信息
- 🛡️ **安全防护**：请求过滤、IP 速率限制、加密传输、交易时间验证
- 🔇 **静默防扫描**：自动过滤外网扫描和嗅探流量，不影响正常日志

## 环境要求

- Python 3.7+
- QMT 交易终端（MiniQMT 模式）
- 聚宽策略信号服务
- 公网服务器 + FRP 内网穿透

## 安装依赖

```bash
pip install pandas numpy schedule flask requests xtquant
```

## 文件结构

```
project/
├── 聚宽跟单设置.json          # 跟单系统配置（策略、端口、速率限制等）
├── 分析配置.json              # 交易账户配置（QMT路径、微信token等）
├── AutoOrder.py              # 主程序（事件驱动下单 + 定时撤单重挂）
├── Trader.py                 # QMT 交易接口封装
├── Receiver.py               # Flask 信号接收服务（含安全中间件）
├── base_func.py              # 基础功能（行情获取、交易时间判断等）
├── cryptor.py                # 信号加解密模块
├── send_trader_info.py       # 企业微信通知模块
├── 持股数据/                  # 持仓数据目录
├── 账户数据/                  # 账户信息目录
├── 原始数据/                  # 聚宽原始信号数据
├── 摘要数据/                  # 交易摘要数据
└── 下单股票池/                # 待交易股票池
```

## 配置说明

### 聚宽跟单设置.json

```json
{
    "服务器": "http://your-server-ip",
    "密码": "",
    "端口": "8888",
    "策略跟单比例": [1],
    "策略名称": ["小市值策略"],
    "解码令牌": "your-secret-key",
    "最大重新下单次数": "5",
    "触发强制卖出次数": "3",
    "每分钟最大请求数": "60"
}
```

| 字段 | 说明 |
|------|------|
| 策略跟单比例 | 跟单数量乘数，`[1]` 表示 1:1 跟单 |
| 解码令牌 | 与聚宽端加密密钥保持一致 |
| 最大重新下单次数 | 未成交撤单后最多重新挂单次数 |
| 触发强制卖出次数 | 超过此次数后以对手方最优价强制卖出 |
| 每分钟最大请求数 | IP 速率限制阈值，多单场景适当调高 |

### 分析配置.json

```json
{
    "交易品种": "STOCK",
    "qmt路径": "D:/国金QMT交易端模拟/userdata_mini",
    "qmt账户": "your-account",
    "是否参加集合竞价": "否",
    "发送摘要时间": "09:55:00",
    "微信token": ["your-wechat-webhook-key"]
}
```

## 快速开始

### 1. 聚宽端配置

在聚宽策略代码最上面粘贴以下代码，并修改您的公网 IP、端口和密钥：

```python
#跟单代码
from jqdata import *
import requests
import json
import pandas as pd
import hashlib
import hmac
import base64

# 修改为您自己的服务器配置
url = 'http://xx.xxx.xx.xx'  # 您的云服务器公网IP
port = 6000                   # 您设置的转发端口
ENCRYPT_PASSWORD = "your secret"  # 加密密钥（需与聚宽跟单设置.json中的"解码令牌"一致）

class SimpleEncryptor:
    def __init__(self, password):
        self.password = password
        self.key = hashlib.sha256(password.encode()).digest()
    def encrypt(self, data):
        if isinstance(data, dict):
            data = json.dumps(data, ensure_ascii=False)
        hmac_obj = hmac.new(self.key, data.encode('utf-8'), hashlib.sha256)
        signature = hmac_obj.hexdigest()
        encrypted = self._simple_xor_encrypt(data.encode('utf-8'))
        result = {
            'signature': signature,
            'data': base64.b64encode(encrypted).decode('utf-8')
        }
        return base64.b64encode(json.dumps(result).encode('utf-8')).decode('utf-8')
    def _simple_xor_encrypt(self, data_bytes):
        key_bytes = self.key
        encrypted = bytearray()
        for i, byte in enumerate(data_bytes):
            encrypted.append(byte ^ key_bytes[i % len(key_bytes)])
        return bytes(encrypted)

encryptor = SimpleEncryptor(ENCRYPT_PASSWORD)

class simple_trader:
    def __init__(self, url='http://您的公网ip', port=6000):
        self.server_url = f'{url}:{port}'
    def send_simple_order(self, order_data):
        endpoint = '/api/order'
        request_url = f'{self.server_url}{endpoint}'
        encrypted_data = encryptor.encrypt(order_data)
        headers = {'Content-Type': 'application/json'}
        data = {
            'encrypted_order': encrypted_data,
            'timestamp': str(pd.Timestamp.now())
        }
        try:
            res = requests.post(url=request_url, json=data, headers=headers, timeout=10)
            print(f"交易信号已发送: {res.status_code}")
            return res.json() if res.status_code == 200 else None
        except Exception as e:
            print(f"发送失败: {e}")
            return None

simple_data = simple_trader(url=url, port=port)

def send_order(result):
    data = {
        '状态': str(result.status), '订单添加时间': str(result.add_time),
        '买卖': str(result.is_buy), '下单数量': str(result.amount),
        '已经成交': str(result.filled), '股票代码': str(result.security),
        '订单ID': str(result.order_id), '平均成交价格': str(result.price),
        '持仓成本': str(result.avg_cost), '多空': str(result.side),
        '交易费用': str(result.commission), '时间戳': str(pd.Timestamp.now()),
        '密码': str("xxx"),
    }
    try:
        simple_data.send_simple_order(data)
    except Exception as e:
        print(f"发送订单失败: {e}")
    return data

def xg_order(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if result is None:
            return
        send_order(result)
        return result
    return wrapper

def xg_order_target(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if result is None:
            return
        send_order(result)
        return result
    return wrapper

def xg_order_value(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if result is None:
            return
        send_order(result)
        return result
    return wrapper

def xg_order_target_value(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if result is None:
            return
        send_order(result)
        return result
    return wrapper

order = xg_order(order)
order_target = xg_order_target(order_target)
order_value = xg_order_value(order_value)
order_target_value = xg_order_target_value(order_target_value)
```

### 2. 服务器端配置

1. 购买云服务器（最低配即可）并获取公网 IP
2. 安装 FRP 服务端（FRPS），配置端口和 Token，启动服务

### 3. 本地配置

1. 安装 FRP 客户端（FRPC），配好端口和 Token，启动客户端
2. 填写 `分析配置.json` 和 `聚宽跟单设置.json`
3. 启动 MiniQMT 交易终端

### 4. 运行

```bash
python AutoOrder.py
```

启动成功后您会看到：
```
QMT交易系统连接成功
🚀 启动本地交易接收服务，端口: 8888
🛡️ 安全策略: 仅接受 /api/order，速率限制 60次/60秒
✅ 系统就绪，下单链路已切换为事件驱动模式
```

## 工作流程

```
信号接收（事件驱动）                    定时任务（轮询）
━━━━━━━━━━━━━━━━━━                    ━━━━━━━━━━━━━━
聚宽信号 → Receiver                    每12秒: 检查订单ID记录
         ↓ 解密+验证                   每30秒: 撤单未成交重新挂单
         ↓ Queue.put()                 每  天: 发送交易摘要
         ↓ 主循环 Queue.get()
         ↓ process_signal()
         → QMT 下单
```

## 版权与许可声明

### 使用限制

禁止开源：严禁其他人以任何形式将本代码公开、分发或作为开源项目发布

禁止商业用途：未经明确授权，禁止用于任何商业目的

禁止二次分发：禁止复制、修改后向第三方分发
