import json
from datetime import datetime
from flask import Flask, request, jsonify
import os
import pandas as pd
import base64
import hashlib
import hmac

class SimpleDecryptor:
    def __init__(self, password):
        self.password = password
        # 使用密码的SHA256哈希作为密钥
        self.key = hashlib.sha256(password.encode()).digest()
    
    def decrypt(self, encrypted_data):
        """解密并验证数据"""
        try:
            # 解码外层base64
            decoded_data = base64.b64decode(encrypted_data).decode('utf-8')
            encrypted_info = json.loads(decoded_data)
            
            signature = encrypted_info['signature']
            encrypted_bytes = base64.b64decode(encrypted_info['data'])
            
            # 解密数据
            decrypted_bytes = self._simple_xor_decrypt(encrypted_bytes)
            decrypted_str = decrypted_bytes.decode('utf-8')
            
            # 验证HMAC签名
            hmac_obj = hmac.new(self.key, decrypted_str.encode('utf-8'), hashlib.sha256)
            expected_signature = hmac_obj.hexdigest()
            
            if hmac.compare_digest(signature, expected_signature):
                return json.loads(decrypted_str)
            else:
                print("签名验证失败")
                return None
                
        except Exception as e:
            print(f"解密失败: {e}")
            return None
    
    def _simple_xor_decrypt(self, data_bytes):
        """简单的异或解密（与加密相同）"""
        key_bytes = self.key
        decrypted = bytearray()
        for i, byte in enumerate(data_bytes):
            decrypted.append(byte ^ key_bytes[i % len(key_bytes)])
        return bytes(decrypted)