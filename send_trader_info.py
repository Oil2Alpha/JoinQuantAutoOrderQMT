import time
import pyautogui as pa
import pywinauto as pw
import schedule
import yagmail
import requests
import json
import random
from datetime import datetime
class send_info:
    '''
    qmt自动登录
    '''
    def __init__(self,
                wx_token_list=['22222']):

        self.wx_token_list=wx_token_list
    def seed_wechat(self, msg='买卖交易成功,'):
        '''
        发送企业微信
        '''
        access_token=random.choice(self.wx_token_list)
        url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=' + access_token
        headers = {'Content-Type': 'application/json;charset=utf-8'}
        data = {
            "msgtype": "text",  # 发送消息类型为文本
            "at": {
                # "atMobiles": reminders,
                "isAtAll": False,  # 不@所有人
            },
            "text": {
                "content": msg,  # 消息正文
            }
        }
        r = requests.post(url, data=json.dumps(data), headers=headers)
        text = r.json()
        errmsg = text['errmsg']
        if errmsg == 'ok':
            print('wechat发生成功')
            return text
        else:
            print(text)
            return text
        