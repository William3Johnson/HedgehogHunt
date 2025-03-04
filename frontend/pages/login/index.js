/**@module **/

const app = getApp();
const globalData = app.globalData;

//TODO cb_fail
const getNewSessionKey = function (cb_success=(session_key)=>{}) {
  wx.login({
    success: res => {
      let code = res.code;
      if (!code) {
        app.alert({content: '网络开小差了，请稍后重试'});
        return
      }
      //成功拿到code
      wx.request({
        method: 'POST',
        url: app.buildUrl('/member/renew/session'),
        header: {
          'content-type': 'application/json',
        },
        data: {code: code},
        success: res => {
          let resp = res.data;
          if(resp['code'] !== 200){
            app.alert({content: resp['msg']});
            return
          }
          //成功拿到新的session_key
          let info = resp['data'];
          cb_success(info['session_key']);
          globalData.session_key = info.session_key;
        },
        fail: (res) =>{
          app.serverBusy()
        }
      })
    },
    fail: (res) =>{
      app.alert({content: '网络开小差了，请稍后重试'})
    }
  })
};


const checkReg = function (cb_comp = (isReg) => {}) {
  if (app.globalData.regFlag && app.getCache("token")) {
    //已注册且已登录
    app.alert({title: '登录提示', content: '已登录过，勿重复登录！', cb_confirm: wx.navigateBack});
    cb_comp(true)
  }
  wx.request({
    url: app.buildUrl("/member/is-reg"),
    data: {
      openid: globalData.openid
    },
    success: (res) => {
      let resp = res.data;
      if (resp['code'] !== 200) {
        app.alert({content: resp['msg']});
        return;
      }
      let is_reg = resp['data']['is_reg'];
      if (is_reg) {
        //未登录的注册用户，直接登录
        app.login();
      }
      cb_comp(is_reg);
    },
    fail: (res)=>{
      app.serverBusy()
    }
  })
};

Page({
  data: {
    //判断小程序的API，回调，参数，组件等是否在当前版本可用。
    canIUse: wx.canIUse('button.open-type.getUserInfo') && wx.canIUse('button.open-type.getPhoneNumber'),
    isHide: false,
    getUserInfo: false,
    getPhone: true,
    loginInfo: null,
    dataReady: false
  },
  /**
   * 进入页面时检查用户是否已注册或者已经登录，使得话返回
   * 如果进入页面时没有手机号，则先获取用户的手机号
   * 否则再获取用户微信公开信息后去后台注册登录
   * @param options 页面参数
   */
  onLoad: function (options) {
    let phone = decodeURIComponent(options.phone);
    if (phone === 'undefined') {
      //刚进入获取手机页面，检查是否已注册过，已注册过就回退
      //已注册未登录的还会自动登录
      checkReg((isReg) => {
        if (!isReg) {
          // 显示页面
          this.setData({dataReady: true})
        }
      })
    } else {
      //已经获取到手机号，并进入了获取用户信息页面
      //显示页面
      this.setData({
        getUserInfo: true,
        getPhone: false,
        mobile: phone,
        dataReady: true
      })
    }
  },
  //如果进入页面时，已经登陆，就回退
  onShow: function () {

  },
  /**
   * @name registerUnload
   */
  onUnload: function() {
    if (!globalData.regFlag && globalData.isScanQrcode && this.data.getPhone) {
      //如果扫码后选择先注册再发布，但因为注册失败而中途退出了注册的第一个页面
      if (!globalData.isFreqScanQrcode) {
        //非频繁扫码，支持发布
        app.toConfirmUnRegRelease()
      } else {
        //算扫码失败，涉嫌频繁扫码
        app.cancelQrcodeScan()
      }
    }
  },
  //微信用户授权后,获取公开用户信息
  getInfo: function (e) {
    this.toRegister(e.detail.userInfo, this.data.mobile)
  },
  /**
   * @name registerHandler 注册处理函数
   * @param userInfo 用户授权的身份信息
   * @param mobile 用户授权的手机号
   */
  toRegister: function (userInfo, mobile) {
    //向注册用户信息userInfo中加入手机号
    if (userInfo) {
      wx.showLoading({
        title: '登陆中',
        mask: true
      })
      setTimeout(function () {
        wx.hideLoading()
      }, 1500)
      userInfo['mobile'] = mobile
    }
    app.register(userInfo)
  },
  //微信用户授权后,获取加密的手机号
  getPhoneNumber(e) {
    //获取加密手机的结果
    let msg = e.detail.errMsg;
    //加密的信息和解密信息
    let encryptedData = e.detail.encryptedData;
    let iv = e.detail.iv;
    //session_key和openid
    let session_key = globalData.session_key;
    if (msg === 'getPhoneNumber:ok') {
      //成功获取
      wx.showToast({
        title: '请稍等',
        icon: 'loading',
        duration: 1000,
        mask: true
      })
      // session_key过期，重新续命
      wx.checkSession({
        // 没过期
        success: (res) => {
          this.decrypt(session_key, encryptedData, iv)
        },
        //过期续命
        fail: (res) => {
          getNewSessionKey((session_key) => {
            this.decrypt(session_key, encryptedData, iv)
          })
        }
      })
    }
  },
  //解码手机号
  decrypt: function(session_key, encryptedData, iv) {
    wx.request({
      method: 'POST',
      url: app.buildUrl('/member/phone/decrypt'),
      header: {
        'content-type': 'application/json',
      },
      data: {
        session_key: session_key,
        encrypted_data: encryptedData,
        iv: iv
      },
      success:  (res) => {
        let resp = res.data;
        if (resp['code'] !== 200) {
          app.alert({content: resp['msg']});
          return
        }
        let mobile = resp['data'];
        //未获得用户授权信息，进入按钮弹窗授权
        wx.navigateTo({
          url: '/pages/login/index?phone=' + encodeURIComponent(mobile)
        })
      },
      fail: (res)=>{
        app.serverBusy()
      }
    })
  }
})