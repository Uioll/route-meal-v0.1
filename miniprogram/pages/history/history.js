const BASE_URL = 'http://127.0.0.1:8000'

Page({
  data: {
    visits: [],
    visitCount: 0,
    isLoading: true,
    loadFailed: false,
    deletingRecordId: null
  },

  onShow() {
    this.loadVisits()
  },

  onPullDownRefresh() {
    this.loadVisits(true)
  },

  formatVisitDate(value) {
    if (!value) {
      return ''
    }

    const [date, time = ''] = value.split('T')
    const [year, month, day] = date.split('-')

    return `${year}年${Number(month)}月${Number(day)}日 ${time.slice(0, 5)}`
  },

  deleteVisit(event) {
    const recordId = event.currentTarget.dataset.recordId
    const restaurantName =
      event.currentTarget.dataset.restaurantName

    wx.showModal({
      title: '删除用餐记录',
      content: `确定删除“${restaurantName}”的这条记录吗？`,
      confirmText: '删除',
      confirmColor: '#e35d43',

      success: (modalResult) => {
        if (!modalResult.confirm) {
          return
        }

        this.setData({
          deletingRecordId: recordId
        })

        wx.request({
          url: `${BASE_URL}/visits/${recordId}`,
          method: 'DELETE',

          success: (response) => {
            if (
              response.statusCode !== 200 ||
              !response.data ||
              response.data.success !== true
            ) {
              wx.showToast({
                title: '删除失败',
                icon: 'none'
              })
              return
            }

            wx.showToast({
              title: '删除成功',
              icon: 'success'
            })

            this.loadVisits()
          },

          fail: (error) => {
            console.error('删除用餐记录失败：', error)

            wx.showToast({
              title: '删除请求失败',
              icon: 'none'
            })
          },

          complete: () => {
            this.setData({
              deletingRecordId: null
            })
          }
        })
      }
    })
  },

  loadVisits(fromPullDown = false) {
    if (!fromPullDown) {
      this.setData({
        isLoading: true,
        loadFailed: false
      })
    }

    wx.request({
      url: `${BASE_URL}/visits`,
      method: 'GET',

      success: (response) => {
        if (
          response.statusCode !== 200 ||
          !response.data ||
          response.data.success !== true
        ) {
          this.setData({
            isLoading: false,
            loadFailed: true
          })
          return
        }

        const visits = (response.data.visits || [])
          .map((item) => ({
            ...item,
            display_time: this.formatVisitDate(item.visited_at)
          }))
          .reverse()

        this.setData({
          visits,
          visitCount: response.data.visit_count || visits.length,
          isLoading: false,
          loadFailed: false
        })
      },

      fail: (error) => {
        console.error('获取用餐记录失败：', error)

        this.setData({
          isLoading: false,
          loadFailed: true
        })

        wx.showToast({
          title: '历史记录加载失败',
          icon: 'none'
        })
      },

      complete: () => {
        wx.stopPullDownRefresh()
      }
    })
  }
})