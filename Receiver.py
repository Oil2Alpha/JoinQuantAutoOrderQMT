import json
from datetime import datetime
from flask import Flask, request, jsonify
import os
import pandas as pd
import cryptor
import base_func

# 加密配置（必须与发送端相同）
with open('聚宽跟单设置.json','r+',encoding='utf-8') as f:
        com=f.read()
text=json.loads(com)
ENCRYPT_PASSWORD=text['解码令牌'] 
st_name=text['策略名称']
decryptor = cryptor.SimpleDecryptor(ENCRYPT_PASSWORD)

class local_jq_data_receiver:    
    def __init__(self, local_port=8888, password='jq2local'):
        self.local_port = local_port
        self.password = password
    app = Flask(__name__)
    @app.route('/api/order', methods=['POST', 'GET'])
    def receive_order():
        if request.method == 'GET':
            return jsonify({
                'status': 'success', 
                'message': '服务正常运行',
            })
        
        data = request.json
        # 解密数据
        if 'encrypted_order' in data:
            decrypted_data = decryptor.decrypt(data['encrypted_order'])
            if decrypted_data:
                order_info = decrypted_data
                print("成功接收并解密交易信号")
            else:
                print("解密失败，拒绝使用该条数据")
                order_info = []
        else:
            # 对未加密的数据不进行接受
            order_info = []
            print("接收到无效的未加密的交易信号，拒绝使用该条数据")   
        df = pd.DataFrame([order_info])
        if df.shape[0] > 0:
            df['数据长度'] = df['股票代码'].apply(lambda x: len(str(x)))
            df['订单添加时间'] = df['订单添加时间'].apply(lambda x: str(x)[:10])
            df = df[df['数据长度'] >= 6]
            df['交易类型'] = df['买卖'].apply(lambda x: 'buy' if x == True or x == 'True' or x == 'true' else 'sell')
            df = df.drop_duplicates(subset=['股票代码', '下单数量', '买卖', '多空'], keep='last') if '股票代码' in df.columns else df.drop_duplicates()
            df['证券代码'] = df['股票代码'].apply(lambda x: str(x)[:6])
            df['订单ID'] = df['订单ID'].astype(str)
            df['密码'] = df['密码'].astype(str)
            df['投资备注']=str(st_name[0])+','+df['股票代码'].apply(lambda x: str(x)[:6])+','+df['订单ID'].astype(str)+','+'0'  #0记录该信号未来会被反复挂单撤单了几次

        file_path = './原始数据/原始数据.csv'
        file_path_copy = './摘要数据/摘要数据.csv'
        os.makedirs('原始数据', exist_ok=True)
        copy_df = df[['证券代码', '买卖','下单数量', '平均成交价格', '订单添加时间']].copy()
        base_func_instance=base_func.base_func
        copy_df["证券代码"] = copy_df["证券代码"].apply(lambda x: base_func_instance.adjust_stock(x))
        copy_df['类型'] = '聚宽模拟信号'
        df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)
        copy_df.to_csv(file_path_copy, mode='a', header=not os.path.exists(file_path_copy), index=False)
        return jsonify({
            'status': 'success', 
            'message': '服务正常运行',
        })
    
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

    def start_server(self, port=8888):
        if self.local_port != None:
            port = self.local_port
        print(f"🚀 启动本地交易接收服务，端口: {port}")
        print(f"📡 服务地址: http://127.0.0.1:{port}")
        print("等待聚宽交易信号...")
        local_jq_data_receiver.app.run(host='0.0.0.0', port=port, debug=False, threaded=True)