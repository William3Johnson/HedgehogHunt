var goodsData = require("../../data/posts-data.js");
var util = require("../../utils/util.js");
var app = getApp();
Page({
  data: {
    banners: ["/images/goods/camera.jpg", "/images/goods/ear_phone.jpg"],
    activeCategoryId: -1,
    categories: [{
        id: -1,
        name: '全部',
      },
      {
        id: 0,
        name: '待认领'
      },
      {
        id: 1,
        name: '预认领'
      },
      {
        id: 2,
        name: '已认领'
      },
    ],
  },
  catClick: function(e) {
    //选择一次分类时返回选中值
    this.setData({
      activeCategoryId: e.currentTarget.id,
    });
    this.onPullDownRefresh();
  },
  //点击信息卡查看详情
  onDetailTap: function(event) {
    var id = event.currentTarget.dataset.id;
    wx.navigateTo({
      url: 'info/info？goods_id=' + id,
    })
  },
  //下拉刷新
  onPullDownRefresh: function(event) {
    this.setData({
      p: 1,
      goods_list: [],
      loadingMoreHidden: true
    });
    this.getGoodsList();
  },
  //下拉刷新
  onRefresh: function (event) {
    this.setData({
      p: 1,
      goods_list: [],
      loadingMoreHidden: true
    });
    this.getGoodsList();
  },
  //点击导航图标
  onNavigateTap: function(event) {
    var id = event.currentTarget.dataset.id * 1; //乘1强制转换成数字
    var [isSelecteds, urls] = util.onNavigateTap(id, 2);
    this.setData({
      isSelecteds: isSelecteds
    })
    wx.redirectTo({
      url: urls[id],
    })
  },
  onLoad: function(options) {
    var [isSelecteds, urls] = util.onNavigateTap(1);
    // var business_type = options.business_type;
    var business_type=1;
    if (business_type == 0) {
      var categories=[{
          id: -1,
          name: '全部',
        },
        {
          id: 0,
          name: '待找回'
        },
        {
          id: 1,
          name: '预找回'
        },
        {
          id: 2,
          name: '已找回'
        },
      ]
    }
    else {
     var categories=[{
          id: -1,
          name: '全部',
        },
        {
          id: 0,
          name: '待领取'
        },
        {
          id: 1,
          name: '预领取'
        },
        {
          id: 2,
          name: '已领取'
        },
      ]

    }
    this.setData({
      isSelecteds: isSelecteds,
      filter_address: '',
      business_type: business_type,
      categories: categories,
      goods_name: '',
      owner_name: '',
      filter_address: '',
    });
    this.onRefresh();
  },
  onShow: function() {
    var regFlag = app.globalData.regFlag;
    this.setData({
      regFlag: regFlag
    });
    this.setInitData();
    // this.getBanners();
  },
  onShareAppMessage: function(Options) {
    return {
      title: '我在刺猬寻物找东西，你也快来看看吧~',
      path: '/pages/index/index',
      success: function(res) {
        wx.request({
          url: app.buildUrl('/member/share'),
          success: function(res) {
            var resp = res.data;
            if (resp.code != 200) {
              app.alert({
                'content': resp.msg
              });
              return;
            }
            wx.showToast({
              title: '分享成功！',
              icon: 'success',
              content: '积分+5',
              duration: 3000
            })
          },
          fail: function(res) {
            app.serverBusy();
            return;
          }
        })
      }
    }
  },
  scroll: function(e) {
    var that = this,
      scrollTop = that.data.scrollTop;
    that.setData({
      scrollTop: e.detail.scrollTop
    });
  },
  //查看导航栏信息
  goAdvInfo: function(e) {
    var adv_id = e.currentTarget.dataset.id;
    console.log(adv_id);
    wx.navigateTo({
      url: '../adv/info/adv-info?id=' + adv_id,
    })
  },
  toSearch: function(e) {
    this.onPullDownRefresh();
  },
  //举报按钮
  toReport: function(e) {
    var regFlag = app.globalData.regFlag;
    if (!regFlag) {
      app.loginTip();
      return;
    }
    var id = e.currentTarget.dataset.id;
    var that = this;
    wx.showModal({
      title: "违规举报",
      content: "为维护平台环境，欢迎举报色情及诈骗、恶意广告等违规信息！同时，恶意举报将会被封号，请谨慎操作，确认举报？",
      success: function(res) {
        if (res.confirm) { //点击确定,获取操作用户id以及商品id,从用户token里面获取id
          wx.showLoading({
            title: '信息提交中..'
          });
          wx.request({
            url: app.buildUrl("/goods/report"),
            header: app.getRequestHeader(),
            data: {
              id: id
            },
            success: function(res) {
              var resp = res.data;
              if (resp.code != 200) {
                app.alert({
                  'content': resp.msg
                });
                return
              }
              wx.hideLoading();
              wx.showToast({
                title: '举报成功，感谢！',
                icon: 'success',
                duration: 2000
              });
            },
            fail: function(res) {
              wx.hideLoading();
              wx.showToast({
                title: '系统繁忙，反馈失败，还是感谢！',
                duration: 2000
              });
            },
            complete: function() {
              wx.hideLoading();
              that.onPullDownRefresh();
            }
          });
        }
      }
    });
  },
  setInitData: function() {
    this.setData({
      goods_list: [],
      loadingMoreHidden: true,
      p: 1,
      activeCategoryId: -1,
      loadingHidden: true, // loading
      swiperCurrent: 0,
      goods: [],
      scrollTop: "0",
      processing: false,
      items:[{
          name: 'owner_name',
          placeholder: '姓名',
          icons: 'search_icon',
        },
        {
          name: "goods_name",
          placeholder: "物品",
        },
        {
          name: "filter_address",
          placeholder: "地址",
        }
      ]
    });
  },
  //获取轮播图
  getBanners: function() {
    var that = this;
    if (!that.data.loadingMoreHidden) {
      return;
    }
    if (that.data.processing) {
      return;
    }
    that.setData({
      processing: true,
      loadingHidden: false
    });
    wx.request({
      url: app.buildUrl("/adv/search"),
      header: app.getRequestHeader(),
      success: function(res) {
        var resp = res.data;
        if (resp.code !== 200) {
          app.alert({
            'content': resp.msg
          });
          return
        }
        var banners = resp.data.list;
        that.setData({
          banners: banners,
        });
      },
      fail: function(res) {
        app.serverBusy();
        return;
      },
      complete: function(res) {
        that.setData({
          processing: false,
          loadingHidden: true
        });
        //获取商品信息
        that.getGoodsList();
      },
    })
  },
  onReachBottom: function(e) {
    var that = this;
    //延时500ms处理函数
    setTimeout(function() {
      that.setData({
        loadingHidden: true
      });
      that.getGoodsList();
    }, 500);
  },
  onBindConfirm: function (e) {
    var data = e.detail.value;
    this.setData({
      owner_name: data['owner_name'],
      goods_name: data['goods_name'],
      filter_address: date['filter_address']
    })
    this.onPullDownRefresh();
  },
  //获取信息列表
  getGoodsList: function(e) {
    var that = this;
    if (!that.data.loadingMoreHidden) {
      return;
    }

    if (that.data.processing) {
      return;
    }
    that.setData({
      processing: true,
      loadingHidden: false
    });
    wx.request({
      url: app.buildUrl("/goods/search"),
      header: app.getRequestHeader(),
      data: {
        status: that.data.activeCategoryId,
        mix_kw: that.data.owner_name,
        goods_name:that.data.goods_name,
        p: that.data.p,
        business_type: that.data.business_type,
        filter_address: that.data.filter_address
      },
      success: function(res) {
        var resp = res.data;
        if (resp.code !== 200) {
          app.alert({
            'content': resp.msg
          });
          return
        }
        var goods_list = resp.data.list;
        goods_list = app.cutStr(goods_list);
        that.setData({
          goods_list: that.data.goods_list.concat(goods_list),
          p: that.data.p + 1,
        });
        if (resp.data.has_more === 0) {
          that.setData({
            loadingMoreHidden: false,
          })
        }
      },
      fail: function(res) {
        app.serverBusy();
        return;
      },
      complete: function(res) {
        that.setData({
          processing: false,
          loadingHidden: true
        });
      },
    })
  },
})