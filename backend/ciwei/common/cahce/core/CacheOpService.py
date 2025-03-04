# encoding: utf-8
"""
@author: github/100101001
@contact: 17702113437@163.com
@time: 2020/4/12 下午11:52
@file: CacheOpService.py
@desc: 
"""
import json
import uuid

from application import APP_CONSTANTS
from common.cahce import CacheKeyReverse
from common.cahce.core import CacheKeyGetter, redis_conn_cache
from common.libs.Helper import queryToDict
from common.loggin.time import time_log
from common.models.ciwei.Goods import Good
from common.models.proxy.MemberProxy import MemberProxy
from common.models.proxy.UserProxy import UserProxy


@time_log
def setMemberCache(member_info=None):
    """
    从数据库获取到Member信息，或者更新了Member信息后设置缓存
    :param member_info:
    :return:
    """
    if not member_info:
        return
    mem_key = CacheKeyGetter.memberKey(member_info.id)
    if isinstance(member_info, dict):
        redis_conn_cache.set(mem_key, json.dumps(member_info))
    elif isinstance(member_info, MemberProxy):
        redis_conn_cache.set(mem_key, json.dumps(member_info.__dict__))
    else:
        redis_conn_cache.set(mem_key, json.dumps(queryToDict(member_info)))
    redis_conn_cache.expire(mem_key, 3600)


def setThankInfoCache(thank_info=None):
    thank_key = CacheKeyGetter.thankKey(thank_info.goods_id)
    redis_conn_cache.set(thank_key, json.dumps({'summary': thank_info.summary, 'thank_price': str(thank_info.thank_price),
                                    'nickname': thank_info.nickname, 'avatar': thank_info.avatar}))
    redis_conn_cache.expire(thank_key, 3600)


@time_log
def setMarkCache(goods_id=0, marks=None):
    """
    进入详情页面，会员查看记录，将每次都需要的认领者ID记录进缓存。方便后续查询使用。 v是set
    :param goods_id:
    :param marks: []
    :return:
    """
    mark_key = CacheKeyGetter.markKey(goods_id)
    mark_member_ids = set(str(i.member_id) for i in marks)
    mark_member_ids.add('-1')
    for m_id in mark_member_ids:
        redis_conn_cache.sadd(mark_key, m_id)
    redis_conn_cache.expire(mark_key, 3600)
    return mark_member_ids


@time_log
def addPreMarkCache(goods_id=0, member_id=0):
    """
    会员认领了good后，向cache中goods_id的认领集合中加入member_id
    保险起见，缓存命中才会进行操作。
    但因为会员只能进入详情认领，在详情接口中会设置该缓存(过期时间为2h)，一般都会缓存命中。
    :param goods_id:
    :param member_id:
    :return:
    """
    mark_key = CacheKeyGetter.markKey(goods_id)
    if redis_conn_cache.smembers(mark_key):
        redis_conn_cache.sadd(mark_key, member_id)
        redis_conn_cache.expire(mark_key, 3600)


@time_log
def removePreMarkCache(found_ids=None, member_id=0):
    """
    会员取消认领了good后，向cache中goods_id的认领集合中移除member_id
    如果缓存不命中，操作了也没有关系
    :param found_ids:
    :param member_id:
    :return:
    """
    for found_id in found_ids:
        m_key = CacheKeyGetter.markKey(found_id)
        redis_conn_cache.srem(m_key, member_id)
        redis_conn_cache.expire(m_key, 3600)


@time_log
def setUsersCache(users=None, is_all=False):
    all_user_key = CacheKeyGetter.allUserKey()
    for user in users:
        if user is not None:
            # 设置 user_id -> member_Id
            redis_conn_cache.hset(all_user_key, user.member_id, json.dumps(user.__dict__ if isinstance(user, UserProxy) else queryToDict(user)))
    if is_all:
        is_all_key = CacheKeyGetter.isAllUserKey()
        redis_conn_cache.hset(all_user_key, is_all_key, APP_CONSTANTS['is_all_user_val'])
    redis_conn_cache.expire(all_user_key, 3600)


@time_log
def setGoodsIncrReadCache(goods_id=0):
    """
    设置新增的阅读量
    :param goods_id:
    :return:
    """
    read_key = CacheKeyGetter.goodsReadKey(goods_id)
    redis_conn_cache.incr(read_key, 1)
    redis_conn_cache.expire(read_key, 3600 * 24 * 7)  # 一天内的累计阅读新增


def syncAndClearGoodsIncrReadCache():
    """
    把缓存中的阅读增量放至数据库
    :return:
    """
    from application import db
    # 获取所有阅读量的key
    read_key_pattern = CacheKeyGetter.goodsReadKeyPrefixPattern()
    keys = redis_conn_cache.keys(read_key_pattern)
    for k in keys:
        incr_views = int(redis_conn_cache.get(k))
        goods_id = CacheKeyReverse.goodsReadKey(read_key=k)
        # elastic search 可以不需要view count,避免更新ES的消耗
        # goods = Good.getById(goods_id)
        # goods.view_count += incr_views
        # db.session.add(goods)
        Good.query.filter_by(id=goods_id).update({'view_count': Good.view_count + incr_views},
                                                 synchronize_session=False)
    db.session.commit()
    # 全部同步后批量删除
    if keys:
        redis_conn_cache.delete(*keys)


def setWxToken(token_data=None):
    """
    设置微信token及过期时间
    :param token_data:
    :return:
    """
    wx_token_key = CacheKeyGetter.wxTokenKey()
    redis_conn_cache.set(wx_token_key, token_data.get('access_token'))
    redis_conn_cache.expire(wx_token_key, int(token_data.get('expires_in', 7200)) - 200)


def setSmsVerifyCode(member_id=None, mobile='', code=''):
    """
    验证码
    :param member_id:
    :param mobile:
    :param code:
    :return:
    """
    sms_key = CacheKeyGetter.smsVerifyKey(member_id)
    redis_conn_cache.hset(sms_key, mobile, code)
    redis_conn_cache.expire(sms_key, 300)


def setLoginSession(member=None):
    """
    登录身份令牌
    :param member:
    :return:
    """

    def __getUniqueLoginToken():
        while True:
            tmp_token = str(uuid.uuid4()).replace('-', '')
            tmp_key = CacheKeyGetter.sessionKey(tmp_token)
            if not redis_conn_cache.exists(tmp_key):
                break
        return tmp_token, tmp_key
    token, session_key = __getUniqueLoginToken()
    session_body = '{0}#{1}'.format(member.id, member.openid)
    redis_conn_cache.set(session_key, session_body)
    redis_conn_cache.expire(session_key, 1800)
    return token


def setFreqMobileCache():
    freq_key = CacheKeyGetter.freqMobileKey()
