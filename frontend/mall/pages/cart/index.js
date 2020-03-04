//index.js
var app = getApp();
const navigate = require("../template/navigate-bar1/navigate-bar1-template.js")
const utils = require("../../utils/util.js")
Page({
    data: {
        dataReady: false,
        p: 1,
        list: [],
        loadingMoreHidden: false
    },
    onLoad: function () {
        //设置底部导航栏
        var [isSelecteds, urls] = utils.onNavigateTap(1);
        this.setData({
            isSelecteds: isSelecteds
        })
    },
    onShow: function () {
        this.setData({
            dataReady: false,
            p: 1,
            list: []
        })
        this.getCartList();
    },
    //每项前面的选中框
    selectTap: function (e) {
        var index = e.currentTarget.dataset.index;
        var list = this.data.list;
        if (index !== "" && index != null) {
            list[parseInt(index)].active = !list[parseInt(index)].active;
            this.setPageData(this.getSaveHide(), this.totalPrice(), this.allSelect(), this.noSelect(), list);
        }
    },
    //计算是否全选了
    allSelect: function () {
        var list = this.data.list;
        var allSelect = false;
        for (var i = 0; i < list.length; i++) {
            var curItem = list[i];
            if (curItem.active) {
                allSelect = true;
            } else {
                allSelect = false;
                break;
            }
        }
        return allSelect;
    },
    //计算是否都没有选
    noSelect: function () {
        var list = this.data.list;
        var noSelect = 0;
        for (var i = 0; i < list.length; i++) {
            var curItem = list[i];
            if (!curItem.active) {
                noSelect++;
            }
        }
        if (noSelect == list.length) {
            return true;
        } else {
            return false;
        }
    },
    //全选和全部选按钮
    bindAllSelect: function () {
        var currentAllSelect = this.data.allSelect;
        var list = this.data.list;
        for (var i = 0; i < list.length; i++) {
            list[i].active = !currentAllSelect;
        }
        this.setPageData(this.getSaveHide(), this.totalPrice(), !currentAllSelect, this.noSelect(), list);
    },
    //加数量
    jiaBtnTap: function (e) {
        var that = this;
        var index = e.currentTarget.dataset.index;
        var list = that.data.list;
        list[parseInt(index)].number++;
        that.setPageData(that.getSaveHide(), that.totalPrice(), that.allSelect(), that.noSelect(), list);
        this.setCart(list[parseInt(index)].product_id, list[parseInt(index)].number);
    },
    //减数量
    jianBtnTap: function (e) {
        var index = e.currentTarget.dataset.index;
        var list = this.data.list;
        if (list[parseInt(index)].number > 1) {
            list[parseInt(index)].number--;
            this.setPageData(this.getSaveHide(), this.totalPrice(), this.allSelect(), this.noSelect(), list);

            this.setCart(list[parseInt(index)].product_id, list[parseInt(index)].number);
        }
    },
    //编辑默认全不选
    editTap: function () {
        var list = this.data.list;
        for (var i = 0; i < list.length; i++) {
            var curItem = list[i];
            curItem.active = false;
        }
        this.setPageData(!this.getSaveHide(), this.totalPrice(), this.allSelect(), this.noSelect(), list);
    },
    //选中完成默认全选
    saveTap: function () {
        var list = this.data.list;
        for (var i = 0; i < list.length; i++) {
            var curItem = list[i];
            curItem.active = true;
        }
        this.setPageData(!this.getSaveHide(), this.totalPrice(), this.allSelect(), this.noSelect(), list);
    },
    getSaveHide: function () {
        return this.data.saveHidden;
    },
    totalPrice: function () {
        var list = this.data.list;
        var totalPrice = 0.00;
        for (var i = 0; i < list.length; i++) {
            if (!list[i].active) {
                continue;
            }
            totalPrice = totalPrice + parseFloat(list[i].price) * list[i].number;
        }
        return totalPrice;
    },
    setPageData: function (saveHidden, total, allSelect, noSelect, list) {
        this.setData({
            list: list,
            saveHidden: saveHidden,
            totalPrice: total,
            allSelect: allSelect,
            noSelect: noSelect,
            dataReady: true
        });
    },
    //去结算
    toPayOrder: function () {
        var data = {
            type: "cart",
            goods: []
        };

        var list = this.data.list;
        for (var i = 0; i < list.length; i++) {
            if (!list[i].active) {
                continue;
            }
            data['goods'].push({
                "id": list[i].product_id,
                "price": list[i].price,
                "number": list[i].number
            });
        }

        wx.redirectTo({
            url: "/mall/pages/order/index?data=" + JSON.stringify(data)
        });
    },
    //如果没有显示去光光按钮事件
    toIndexPage: function () {
        var campus_name = app.globalData.campus_name
        var campus_id = app.globalData.campus_id
        wx.redirectTo({
            url: '/mall/pages/index?campus_id=' + campus_id +
                '&campus_name=' + encodeURIComponent(campus_name),
        })
    },
    //选中删除的数据
    deleteSelected: function () {
        var list = this.data.list;
        var goods = [];
        list = list.filter(function (item) {
            if (item.active) {
                goods.push({
                    "id": item.product_id
                })
            }

            return !item.active;
        });

        this.setPageData(this.getSaveHide(), this.totalPrice(), this.allSelect(), this.noSelect(), list);
        //发送请求到后台删除数据
        wx.request({
            url: app.buildUrl("/cart/del"),
            header: app.getRequestHeader(),
            method: 'POST',
            data: {
                goods: JSON.stringify(goods)
            },
            success: function (res) {
            }
        });
    },
    getCartList: function () {
        var that = this;
        wx.request({
            url: app.buildUrl("/cart/index"),
            data: {
                p: that.data.p
            },
            header: app.getRequestHeader(),
            success: function (res) {
                var resp = res.data;
                if (resp.code != 200) {
                    app.alert({ "content": resp.msg });
                    return;
                }
                that.setData({
                    list: that.data.list.concat(resp.data.list),
                    saveHidden: true,
                    totalPrice: 0.00,
                    allSelect: true,
                    noSelect: false,
                    p: that.data.p + 1,
                    loadingMoreHidden: resp.data.has_more
                });

                that.setPageData(that.getSaveHide(), that.totalPrice(), that.allSelect(), that.noSelect(), that.data.list);
            }
        });
    },
    setCart: function (product_id, number) {
        var that = this;
        var data = {
            "id": product_id,
            "number": number
        };
        wx.request({
            url: app.buildUrl("/cart/set"),
            header: app.getRequestHeader(),
            method: 'POST',
            data: data,
            success: function (res) {
            }
        });
    },
    //点击导航
    onNavigateTap: function (event) {
        navigate.onNavigateTap(event, this)
    },
    onReachBottom: function () {
        var that = this;
        console.log("onreach")
        setTimeout(function () {
            that.getCartList();
        }, 500);
    },
});
