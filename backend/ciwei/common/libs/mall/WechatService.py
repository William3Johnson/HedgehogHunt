# encoding: utf-8
"""
@author: github/100101001
@contact: 17702113437@163.com
@time: 2020/2/12 下午2:32
@file: WeChatService.py
@desc:
"""
import hashlib
import uuid
import xml.etree.ElementTree as ET

import requests

from application import app
from common.cahce.core import CacheQueryService, CacheOpService
import base64
import json
from Crypto.Cipher import AES
import urllib.parse as parser


class WeChatService:

    def __init__(self, merchant_key=None):
        self.merchant_key = merchant_key

    def create_sign(self, pay_data):
        """
        生成签名
        :param pay_data:
        :return:
        """
        stringA = '&'.join(["{0}={1}".format(k, pay_data.get(k)) for k in sorted(pay_data)])
        stringSignTemp = '{0}&key={1}'.format(stringA, self.merchant_key)
        sign = hashlib.md5(stringSignTemp.encode("utf-8")).hexdigest()
        return sign.upper()

    def get_pay_info(self, pay_data=None):
        """
        获取wx支付信息
        :param pay_data:
        :return:
        """
        sign = self.create_sign(pay_data)
        pay_data['sign'] = sign
        xml_data = self.dict_to_xml(pay_data)
        headers = {'Content-Type': 'application/xml'}
        url = "https://api.mch.weixin.qq.com/pay/unifiedorder"
        r = requests.post(url=url, data=xml_data.encode('utf-8'), headers=headers)
        r.encoding = "utf-8"
        app.logger.info(r.text)
        if r.status_code == 200:
            prepay_id = self.xml_to_dict(r.text).get('prepay_id')
            if prepay_id:
                pay_sign_data = {
                    'appId': pay_data.get('appid'),
                    'timeStamp': pay_data.get('out_trade_no'),
                    'nonceStr': pay_data.get('nonce_str'),
                    'package': 'prepay_id={0}'.format(prepay_id),
                    'signType': 'MD5'
                }
                pay_sign = self.create_sign(pay_sign_data)
                pay_sign_data.pop('appId')
                pay_sign_data['paySign'] = pay_sign
                pay_sign_data['prepay_id'] = prepay_id
                return pay_sign_data
            return False

        return False

    def dict_to_xml(self, dict_data):
        """
        把字典数据转成xml格式
        :rtype: object
        :param dict_data:
        :return:
        """
        xml = ["<xml>"]
        for k, v in dict_data.items():
            xml.append("<{0}>{1}</{0}>".format(k, v))
        xml.append("</xml>")
        return "".join(xml)

    def xml_to_dict(self, xml_data):
        """
        解析xml数据成 k-v字典
        :param xml_data:
        :return:
        """
        xml_dict = {}
        root = ET.fromstring(xml_data)
        for child in root:
            xml_dict[child.tag] = child.text
        return xml_dict

    def get_nonce_str(self):
        """
        获取随机字符串
        :return:
        """
        return str(uuid.uuid4()).replace('-', '')

    @staticmethod
    def getAccessToken():
        """
        从缓存获取token并返回，过期获取新的返回，并设置缓存
        :return:
        """
        token = CacheQueryService.getWxToken()
        if not token:
            # get new token
            url = "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}".format(
                app.config['OPENCS_APP']['appid'], app.config['OPENCS_APP']['appkey'])

            wxResp = requests.get(url).json()
            if 'access_token' not in wxResp.keys():
                app.logger.error("failed to get token! Errcode: %s, Errmsg:%s", wxResp['errcode'], wxResp['errmsg'])
                return None
            else:
                CacheOpService.setWxToken(wxResp)
                return wxResp.get('access_token')
        else:
            return token

    @classmethod
    def getMimiProgramQrcode(cls, openid=''):
        token = cls.getAccessToken()
        if not token:
            return None

        # 无限API上线可用(体验版)
        # [2019-12-10 16:06:50,066] ERROR in QrCode: failed to get qr code. Errcode: 41030, Errmsg:invalid page hint: [6qqTta0210c393]
        wx_resp = requests.post(
            "https://api.weixin.qq.com/wxa/getwxacodeunlimit?access_token={}".format(token),
            json={"scene": parser.quote(str(openid)), "width": 280, "page": "pages/index/index"})

        if len(wx_resp.content) < 80:
            data = wx_resp.json()
            app.logger.error("没拿到二维码. 错误码: %s, 错误信息:%s", data['errcode'], data['errmsg'])
            return None
        else:
            return wx_resp.content

    @classmethod
    def getWeChatOpenId(cls, code, get_session_key=False):
        """
        通过code在微信登录获取openid, session_key
        :param code:
        :param get_session_key:
        :return:
        """
        openid = None
        session_key = None
        if code:
            app_id = app.config['OPENCS_APP']['appid']
            app_key = app.config['OPENCS_APP']['appkey']
            url = 'https://api.weixin.qq.com/sns/jscode2session?appid={0}&secret={1}&' \
                  'js_code={2}&grant_type=authorization_code'.format(app_id, app_key, code)

            r = requests.get(url, headers={'Connection': 'close'})
            res = json.loads(r.text)
            if 'openid' in res:
                openid = res['openid']
            if 'session_key' in res:
                session_key = res['session_key']

        if get_session_key:
            return openid, session_key
        else:
            return openid


class WXBizDataCrypt:
    """
    微信手机AES解密
    """

    def __init__(self, appId, sessionKey):
        self.appId = appId
        self.sessionKey = sessionKey

    def decrypt(self, encryptedData, iv):
        # base64 decode
        sessionKey = base64.b64decode(self.sessionKey)
        encryptedData = base64.b64decode(encryptedData)
        iv = base64.b64decode(iv)

        cipher = AES.new(sessionKey, AES.MODE_CBC, iv)

        decrypted = json.loads(self._unpad(cipher.decrypt(encryptedData)))

        if decrypted['watermark']['appid'] != self.appId:
            raise Exception('Invalid Buffer')
        app.logger.info(decrypted)
        return decrypted

    def _unpad(self, s):
        # 最后一个字符的ASCII值为c,截掉最后c位字符
        return s[:-ord(s[len(s) - 1:])]
