// components/lyx-modal/lyx-modal.js
const util = require('../../utils/util');
Component({
  options: {
    multipleSlots: true // 在组件定义时的选项中启用多slot支持
  },
  /**
   * 组件的属性列表
   */
  properties: {
    title: {
      type: String
    },
    hidden: {
      type: Boolean
    },
    noCancel: {
      type: Boolean
    },
    confirmText: {
      type: String
    },
    confirmColor: {
      type: String,
      observer: function (newValue) {
        this.setData({
          tintColor: 'color:' + newValue
        })
      }
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    noCancel: false,
    confirmText: '确认',
    cancelText: '取消',
    // tintColor: 'color:#00a48f',
    tintColor: 'color:#f7931e'
  },

  /**
   * 组件的方法列表
   */
  methods: {
    cancel: function () {
      this.triggerEvent('cancel')
    },
    confirm: function () {
      this.triggerEvent('confirm')
    }
  },

  ready: function () {
    let that = this
    util.wxPromisify(wx.getSystemInfo)().then(res => {
      that.setData({
        height: res.windowHeight + 'px'
      })
    })
  }
})
