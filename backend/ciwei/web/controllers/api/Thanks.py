# -*- coding:utf-8 -*-
import datetime
from decimal import Decimal

from flask import request, jsonify, g
from sqlalchemy import or_

from application import app, db
from common.libs import LogService
from common.libs.Helper import getCurrentDate, selectFilterObj, getDictFilterField
from common.models.ciwei.Goods import Good
from common.models.ciwei.Mark import Mark
from common.models.ciwei.Member import Member
from common.models.ciwei.Report import Report
from common.models.ciwei.Thanks import Thank
from common.models.ciwei.User import User
from web.controllers.api import route_api


@route_api.route("/thanks/create", methods=['GET', 'POST'])
def thanksCreate():
    try:
        resp = {'code': 200, 'msg': 'create thanks record successfully(search)', 'data': {}}
        req = request.values

        member_info = g.member_info
        if not member_info:
            resp['code'] = -1
            resp['msg'] = "请先登录"
            return jsonify(resp)

        thanks_model = Thank()
        thanks_model.member_id = member_info.id  # 发出答谢的人
        thanks_model.nickname = member_info.nickname  # 发出答谢的人
        thanks_model.avatar = member_info.avatar  # 发出答谢的人
        target_member_id = int(req['auther_id']) if 'auther_id' in req else 0
        thanks_model.target_member_id = target_member_id
        business_type = int(req['business_type'])

        thanks_model.business_desc = "拾到" if business_type == 1 else "丢失"
        goods_id = int(req['goods_id']) if 'goods_id' in req else 0
        goods_name = req['goods_name'] if 'goods_name' in req else '你捡到的东西'
        owner_name = req['owner_name'] if 'owner_name' in req else '无名'
        thanks_model.goods_name = goods_name
        thanks_model.owner_name = owner_name
        target_price = Decimal(req['target_price']).quantize(Decimal('0.00')) if 'target_price' in req else 0.00
        thanks_model.thank_price = target_price
        if target_price > 0.00:
            # 金额转入目标用户余额
            thanks_model.order_sn = req['order_sn']
            target_member_info = Member.query.filter_by(id=target_member_id).first()
            LogService.setMemberBalanceChange(member_info=target_member_info, unit=target_price,
                                              old_balance=member_info.balance,
                                              note='答谢收款')
            target_member_info.balance += target_price
            db.session.add(target_member_info)

        thanks_model.summary = req['thanks_text']  # 前端已判空
        thanks_model.goods_id = goods_id  # 答谢的物品
        db.session.add(thanks_model)
        # 标记goods方便详情帖子获取是否已经答谢过（答谢接口频率低于详情），和记录接口查看已答谢记录
        # 标记认领记录已经OK了
        now = datetime.datetime.now()
        if business_type == 1:
            # 帖子和认领记录一起更新
            Good.query.filter_by(id=goods_id, status=3).with_for_update().update({'status': 4, 'thank_time': now},
                                                                                 synchronize_session=False)
            Mark.query.filter(Mark.member_id == member_info.id,
                              Mark.goods_id == goods_id,
                              Mark.status == 1).update({'status': 2}, synchronize_session=False)
        if business_type == 2:
            # 归还和寻物帖子一起更新
            lost_goods_id = Good.query.filter_by(id=goods_id).with_entities(Good.return_goods_id).first()
            Good.query.filter(or_(Good.id == goods_id, Good.id == lost_goods_id[0]),
                              Good.status == 3).with_for_update().update({'status': 4, 'thank_time': now},
                                                                         synchronize_session=False)
        db.session.commit()
        resp['data']['id'] = thanks_model.id
        res = jsonify(resp)
    except Exception as e:
        app.logger.error(request.path + ': ' + e)
        db.session.rollback()
        resp = {'code': -1, 'msg': '服务器内部异常', 'data': {}}
        return jsonify(resp)
    try:
        # 即使发生了异常也不会影响已经支付答谢过的
        from common.libs import SubscribeService
        SubscribeService.send_thank_subscribe(thanks_model)
    except Exception as e:
        app.logger.error(request.path + ': ' + e)
    return res


# 查询所有记录
@route_api.route("/thanks/search", methods=['GET', 'POST'])
def thanksSearch():
    resp = {'code': 200, 'msg': 'search thanks successfully(thanks)', 'data': {}}
    req = request.values

    member_info = g.member_info
    if not member_info:
        resp['code'] = -1
        resp['msg'] = "没有相关用户信息"
        return jsonify(resp)

    p = int(req['p']) if ('p' in req and req['p']) else 1
    if p < 1:
        p = 1

    page_size = 10
    offset = (p - 1) * page_size

    # 获取用户的发布信息
    query = Thank.query.filter(Thank.status != 7)
    query = query.filter(Thank.status != 6)
    query = query.filter(Thank.status != 5)
    query = query.filter(Thank.status != 4)

    owner_name = req['owner_name'] if 'owner_name' in req else ''
    if owner_name:
        rule = or_(Thank.owner_name.ilike("%{0}%".format(owner_name)))
        query = query.filter(rule)

    mix_kw = str(req['mix_kw']) if 'mix_kw' in req else ''
    if mix_kw:
        fil_str = "%{0}%".format(mix_kw[0])
        for i in mix_kw[1:]:
            fil_str = fil_str + "%{0}%".format(i)
        rule = or_(Thank.goods_name.ilike("%{0}%".format(fil_str)), Thank.member_id.ilike("%{0}%".format(mix_kw)))
        query = query.filter(rule)

    # 获取操作值，看用户是查看收到的还是发出的答谢信息
    status = int(req['status']) if 'status' in req else ''
    if status == 0:
        query = query.filter_by(target_member_id=member_info.id)
    elif status == 1:
        query = query.filter_by(member_id=member_info.id)
    elif status == 2:
        pass

    only_new = req['only_new']
    if only_new == "true":
        query = query.filter_by(status=0)
    goods_list = query.order_by(Thank.id.desc()).offset(offset).limit(10).all()
    # 将对应的用户信息取出来，组合之后返回
    data_goods_list = []
    if goods_list:
        for item in goods_list:
            # 发出：我感谢的人
            # 收到：感谢我的人
            tmp_data = {
                "id": item.id,
                "status": item.status,  # 不存在时置1
                "goods_name": item.goods_name,
                "owner_name": item.owner_name,
                "updated_time": str(item.updated_time),
                "business_desc": item.business_desc,
                "summary": item.summary,
                "reward": str(item.thank_price),
                "auther_name": item.nickname,
                "avatar": item.avatar,
                "selected": False,
            }
            data_goods_list.append(tmp_data)

    resp['data']['list'] = data_goods_list
    resp['data']['has_more'] = len(data_goods_list) >= page_size
    return jsonify(resp)


@route_api.route("/thanks/update-status", methods=['GET', 'POST'])
def updateStatus():
    req = request.values
    member_info = g.member_info
    if not member_info:
        return ""
    query = Thank.query.filter(Thank.status != 7)
    query = query.filter(Thank.status != 6)
    query = query.filter(Thank.status != 5)
    query = query.filter(Thank.status != 4)
    all = req['all'] if 'all' in req else ''
    if all == "true":
        _rule = or_(Thank.target_member_id == member_info.id, Thank.member_id == member_info.id)
        goods_list = query.filter(_rule).all()
    else:
        goods_list = query.filter_by(target_member_id=member_info.id).all()
    if goods_list:
        for item in goods_list:
            if item.status == 0:
                item.status = 1
                item.updated_time = getCurrentDate()
                db.session.add(item)
                db.session.commit()
    return ""


# 查询所有记录
@route_api.route("/thanks/reports-search", methods=['GET', 'POST'])
def thanksReportSearch():
    resp = {'code': 200, 'msg': 'search thanks successfully(thanks)', 'data': {}}
    req = request.values

    member_info = g.member_info
    if not member_info:
        resp['code'] = -1
        resp['msg'] = "没有相关用户信息"
        return jsonify(resp)

    p = int(req['p']) if ('p' in req and req['p']) else 1
    if p < 1:
        p = 1

    page_size = 10
    offset = (p - 1) * page_size

    # 获取操作值，看用户是查看收到的还是发出的答谢信息
    report_status = int(req['report_status']) if 'report_status' in req else ''
    query = Report.query.filter_by(status=report_status)
    query = query.filter_by(record_type=0)
    report_list = query.order_by(Report.id.desc()).all()
    report_ids = selectFilterObj(report_list, 'record_id')

    # 获取举报列表的感谢信息
    query = Thank.query.filter(Thank.id.in_(report_ids))
    # owner_name = req['owner_name'] if 'owner_name' in req else ''
    # if owner_name:
    #     rule = or_(Thank.owner_name.ilike("%{0}%".format(owner_name)))
    #     query = query.filter(rule)
    #
    # mix_kw = str(req['mix_kw']) if 'mix_kw' in req else ''
    # if mix_kw:
    #     fil_str = "%{0}%".format(mix_kw[0])
    #     for i in mix_kw[1:]:
    #         fil_str = fil_str + "%{0}%".format(i)
    #     rule = or_(Thank.name.ilike("%{0}%".format(fil_str)), Thank.member_id.ilike("%{0}%".format(mix_kw)))
    #     query = query.filter(rule)

    thanks_list = query.order_by(Thank.id.desc()).offset(offset).limit(10).all()
    # #将对应的用户信息取出来，组合之后返回
    data_goods_list = []
    if thanks_list:
        for item in thanks_list:
            item_auther_info = Member.query.filter_by(id=item.member_id).first()
            item_report_info = Report.query.filter_by(record_id=item.id).filter_by(record_type=0).first()
            item_report_member_info = Member.query.filter_by(id=item_report_info.report_member_id).first()
            tmp_data = {
                "id": item.id,
                "status": item.status,  # 不存在时置1
                "goods_name": item.goods_name,
                "owner_name": item.owner_name,
                "updated_time": str(item.updated_time),
                "business_desc": item.business_desc,
                "summary": item.summary,
                "reward": "0.00",
                "auther_name": item_auther_info.nickname,
                "avatar": item_auther_info.avatar,
                "selected": False,

                "report_member_avatar": item_report_member_info.avatar,
                "report_member_name": item_report_member_info.nickname,
                "report_updated_time": str(item_report_info.updated_time),

                "report_id": item_report_info.id,
                "member_id": item_auther_info.id,
                "report_member_id": item_report_info.id,
            }
            data_goods_list.append(tmp_data)

    resp['data']['list'] = data_goods_list
    resp['data']['has_more'] = len(data_goods_list) >= page_size
    return jsonify(resp)


# 将商品移除自己的列表
@route_api.route("/thanks/delete", methods=['GET', 'POST'])
def thanksDelete():
    resp = {'code': 200, 'msg': 'delete record successfully', 'data': {}}
    req = request.values

    member_info = g.member_info
    if not member_info:
        resp['code'] = -1
        resp['msg'] = "没有相关用户信息"
        return jsonify(resp)

    """
    op_status=0,用户的发布记录
    op_statis=1,用户的认领记录
    op_status=2,用户的推荐列表
    """

    op_status = int(req['op_status']) if 'op_status' in req else ''
    id_list = req['id_list'][1:-1].split(',')
    if op_status == 4:
        id_list_int = [int(i) for i in id_list]
        goods_list = Thank.query.filter(Thank.id.in_(id_list_int)).all()
        report_map = getDictFilterField(Report, Report.record_id, "record_id", id_list_int)
        user_info = User.query.filter_by(member_id=member_info.id).first()
        if not user_info:
            resp['code'] = -1
            resp['msg'] = "没有相关管理员信息，如需操作请添加管理员"
            resp['data'] = str(member_info.id) + "+" + member_info.nickname
            return jsonify(resp)
        if goods_list:
            for item in goods_list:
                report_item = report_map[item.id]
                report_item.user_id = user_info.uid
                report_item.status = 5

                item.user_id = user_info.uid
                item.report_status = 5
                item.updated_time = report_item.updated_time = getCurrentDate()
                db.session.add(item)
                db.session.add(report_item)
                db.session.commit()
    else:
        for i in id_list:
            goods_info = Thank.query.filter_by(id=int(i)).first()
            goods_info.status = 7
            db.session.add(goods_info)
            db.session.commit()

    return jsonify(resp)


# 拉黑发布者或者举报者
@route_api.route('/thanks/block')
def thanksBlock():
    resp = {'code': 200, 'msg': 'operate successfully(block)', 'data': {}}
    req = request.values

    member_info = g.member_info
    if not member_info:
        resp['code'] = -1
        resp['msg'] = "用户信息异常"
        return jsonify(resp)

    user_info = User.query.filter_by(member_id=member_info.id).first()
    if not user_info:
        resp['code'] = -1
        resp['msg'] = "没有相关管理员信息，如需操作请添加管理员"
        resp['data'] = str(member_info.id) + "+" + member_info.nickname
        return jsonify(resp)

    report_status = int(req['report_status']) if 'report_status' in req else "nonono"
    report_id = int(req['report_id'])

    report_info = Report.query.filter_by(id=report_id).first()

    auther_info = Member.query.filter_by(id=report_info.member_id).first()
    report_member_info = Member.query.filter_by(id=report_info.report_member_id).first()
    thanks_info = Thank.query.filter_by(id=report_info.record_id).first()

    report_info.status = report_status
    report_info.user_id = user_info.uid
    thanks_info.report_status = report_status
    thanks_info.user_id = user_info.uid
    # 拉黑举报者
    if report_status == 2:
        report_member_info.status = 0
    # 拉黑发布者
    elif report_status == 3:
        auther_info.status = 0
    # 没有违规
    else:
        pass

    auther_info.updated_time = report_info.updated_time = thanks_info.updated_time = report_info.updated_time = getCurrentDate()
    db.session.add(auther_info)
    db.session.add(report_info)
    db.session.add(report_member_info)
    db.session.add(thanks_info)
    db.session.commit()

    return jsonify(resp)
