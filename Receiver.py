import json
import logging
import time
from collections import defaultdict
from datetime import datetime
from flask import Flask, request, jsonify
import os
import pandas as pd
import cryptor
import base_func

# 抑制 Werkzeug 噪音日志（扫描产生的 400/404/505 等）
logging.getLogger('werkzeug').setLevel(logging.ERROR)


class LocalJQDataReceiver:
    """本地聚宽交易信号接收服务
    
    安全特性：
    - 仅接受 POST/GET /api/order 路径，其余路径静默返回 404
    - POST 请求必须包含 Content-Type: application/json 和 encrypted_order 字段
    - 简单 IP 速率限制（可配置窗口和阈值）
    """

    def __init__(self, local_port=8888, password='jq2local',
                 decrypt_key='', strategy_names=None, signal_queue=None,
                 rate_limit=60):
        """
        Args:
            local_port: 监听端口
            password: 连接密码
            decrypt_key: 解密令牌（必须与聚宽发送端一致）
            strategy_names: 策略名称列表
            signal_queue: queue.Queue 实例，收到有效信号后将 DataFrame 放入队列
            rate_limit: 每分钟最大请求数（防扫描），默认 60
        """
        self.local_port = local_port
        self.password = password
        self.strategy_names = strategy_names or []
        self.signal_queue = signal_queue
        self.decryptor = cryptor.SimpleDecryptor(decrypt_key)
        self.base_func_instance = base_func.base_func()

        # 速率限制：每 IP 在窗口期内最多 rate_limit 次
        self._rate_window = 60       # 秒
        self._rate_max_requests = rate_limit
        self._request_log = defaultdict(list)

        # 创建 Flask app 并注册路由
        self.app = Flask(__name__)
        self._register_routes()

    # ==================== 安全中间件 ====================

    def _check_rate_limit(self, client_ip):
        """简单滑动窗口速率限制，返回 True 表示放行"""
        now = time.time()
        # 清除过期记录
        self._request_log[client_ip] = [
            t for t in self._request_log[client_ip]
            if now - t < self._rate_window
        ]
        if len(self._request_log[client_ip]) >= self._rate_max_requests:
            return False
        self._request_log[client_ip].append(now)
        return True

    # ==================== 路由注册 ====================

    def _register_routes(self):
        """通过闭包注册路由，使路由函数可以访问 self"""

        @self.app.before_request
        def security_filter():
            """安全过滤器 — 静默拒绝所有非法请求"""
            client_ip = request.remote_addr

            # 速率限制
            if not self._check_rate_limit(client_ip):
                return '', 429

            # 只放行 /api/order 路径
            if request.path != '/api/order':
                return '', 404

            # POST 请求必须是 JSON
            if request.method == 'POST':
                if not request.is_json:
                    return '', 400

        @self.app.route('/api/order', methods=['POST', 'GET'])
        def receive_order():
            # GET 健康检查
            if request.method == 'GET':
                return jsonify({
                    'status': 'success',
                    'message': '服务正常运行',
                })

            # POST 处理交易信号
            data = request.json
            if not data or 'encrypted_order' not in data:
                return jsonify({'status': 'error', 'message': '缺少加密数据'}), 400

            # 解密数据
            decrypted_data = self.decryptor.decrypt(data['encrypted_order'])
            if not decrypted_data:
                print("解密失败，拒绝使用该条数据")
                return jsonify({'status': 'error', 'message': '解密失败'}), 403

            print("成功接收并解密交易信号")

            # 解析为 DataFrame
            df = self._parse_order_data(decrypted_data)

            if df.shape[0] > 0:
                # 写入摘要 CSV（供日终 trade_summary 使用）
                self._save_summary(df)

                # 放入信号队列（事件驱动触发下单）
                if self.signal_queue is not None:
                    self.signal_queue.put(df)
                    print("交易信号已推入队列等待执行")
                else:
                    # 兼容模式：仍写入原始数据 CSV
                    self._save_raw_data(df)

            return jsonify({
                'status': 'success',
                'message': '信号已接收',
            })

    # ==================== 数据处理 ====================

    def _parse_order_data(self, order_info):
        """将解密后的原始数据解析为标准化 DataFrame"""
        df = pd.DataFrame([order_info])
        if df.shape[0] == 0:
            return df

        df['数据长度'] = df['股票代码'].apply(lambda x: len(str(x)))
        df['订单添加时间'] = df['订单添加时间'].apply(lambda x: str(x)[:10])
        df = df[df['数据长度'] >= 6]
        df['交易类型'] = df['买卖'].apply(
            lambda x: 'buy' if x == True or x == 'True' or x == 'true' else 'sell'
        )
        df = (df.drop_duplicates(subset=['股票代码', '下单数量', '买卖', '多空'], keep='last')
              if '股票代码' in df.columns else df.drop_duplicates())
        df['证券代码'] = df['股票代码'].apply(lambda x: str(x)[:6])
        df['订单ID'] = df['订单ID'].astype(str)
        df['密码'] = df['密码'].astype(str)

        st_name = self.strategy_names[0] if self.strategy_names else ''
        df['投资备注'] = (str(st_name) + ',' +
                       df['股票代码'].apply(lambda x: str(x)[:6]) + ',' +
                       df['订单ID'].astype(str) + ',' + '0')
        return df

    def _save_summary(self, df):
        """保存摘要数据（供日终汇总）"""
        file_path = './摘要数据/摘要数据.csv'
        os.makedirs('摘要数据', exist_ok=True)
        copy_df = df[['证券代码', '买卖', '下单数量', '平均成交价格', '订单添加时间']].copy()
        copy_df['证券代码'] = copy_df['证券代码'].apply(
            lambda x: self.base_func_instance.adjust_stock(x)
        )
        copy_df['类型'] = '聚宽模拟信号'
        copy_df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)

    def _save_raw_data(self, df):
        """保存原始数据 CSV（兼容模式，仅在无 Queue 时使用）"""
        file_path = './原始数据/原始数据.csv'
        os.makedirs('原始数据', exist_ok=True)
        df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)

    # ==================== 启动服务 ====================

    def start_server(self):
        """启动 Flask 接收服务"""
        port = self.local_port or 8888
        print(f"🚀 启动本地交易接收服务，端口: {port}")
        print(f"📡 服务地址: http://127.0.0.1:{port}")
        print(f"🛡️ 安全策略: 仅接受 /api/order，速率限制 {self._rate_max_requests}次/{self._rate_window}秒")
        print("等待聚宽交易信号...")
        self.app.run(host='0.0.0.0', port=port, debug=False, threaded=True)


# 向后兼容：保留旧类名的别名
local_jq_data_receiver = LocalJQDataReceiver