# encoding: utf-8
"""
@author: github/100101001
@contact: 17702113437@163.com
@time: 2020/4/30 下午4:31
@file: listeners.py
@desc: 
"""
from sqlalchemy import event

from common.libs import LogService
from common.models.ciwei.Member import Member
from common.models.ciwei.logs.change.MemberSmsPkgChangeLog import MemberSmsPkgChangeLog


@event.listens_for(Member.left_notify_times, 'set')
def memberSmsChangeLog(target, new_val, old_val, *args):
    LogService.setMemberNotifyTimesChange(member_info=target, unit=new_val - old_val, old_times=old_val)


@event.listens_for(Member.balance, 'set')
def memberBalanceChangeLog(target, new_val, old_val, *args):
    LogService.setMemberBalanceChange(member_info=target, unit=new_val - old_val, old_balance=old_val)


@event.listens_for(MemberSmsPkgChangeLog.notify_times, 'set')
def memberSmPkgChangeLog(target, new_val, old_val, *args):
    LogService.setMemberSmsPkgChange(sms_pkg=target, unit=new_val - old_val, old_times=old_val)
