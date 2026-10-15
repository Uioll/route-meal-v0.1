Page({
  data: {
    start: "",
    destination: "",
    travelMode: "公交",
    intentText: "",
    submitted: false,
    isLoading: false,
    candidateCount: 0,
    restaurants: [],
    isRouteLoading: false,
    selectedRestaurantId: null,
    routePreview: null,
    rejectedIds: []
  },

  onStartInput(event) {
    this.setData({
      start: event.detail.value,
      submitted: false,
      candidateCount: 0,
      restaurants: [],
      routePreview: null,
      rejectedIds: []
    })
  },

  onDestinationInput(event) {
    this.setData({
      destination: event.detail.value,
      submitted: false,
      candidateCount: 0,
      restaurants: [],
      routePreview: null,
      rejectedIds: []
    })
  },

  onIntentInput(event) {
    this.setData({
      intentText: event.detail.value,
      submitted: false,
      candidateCount: 0,
      restaurants: [],
      routePreview: null,
      rejectedIds: []
    })
  },

  selectTravelMode(event) {
    this.setData({
      travelMode: event.currentTarget.dataset.mode,
      submitted: false,
      candidateCount: 0,
      restaurants: [],
      routePreview: null,
      rejectedIds: []
    })
  },

  searchRestaurants() {
    const {
      start,
      destination,
      intentText,
      travelMode
    } = this.data

    if (!start.trim()) {
      wx.showToast({
        title: "请填写起点",
        icon: "none"
      })
      return
    }

    if (!destination.trim()) {
      wx.showToast({
        title: "请填写终点",
        icon: "none"
      })
      return
    }

    if (!intentText.trim()) {
      wx.showToast({
        title: "请填写想吃什么",
        icon: "none"
      })
      return
    }

    this.setData({
      isLoading: true,
      submitted: false,
      candidateCount: 0,
      restaurants: [],
      routePreview: null
    })

    wx.request({
      url: "http://127.0.0.1:8000/lottery/draw",
      method: "POST",

      header: {
        "content-type": "application/json"
      },

      data: {
        text: intentText,
        travel_mode: travelMode,
        rejected_ids: this.data.rejectedIds
      },

      success: (response) => {
        if (
          response.statusCode === 200 &&
          response.data.success === true
        ) {
          this.setData({
            submitted: true,
            candidateCount: response.data.candidate_count,
            restaurants: response.data.restaurants
          })

          wx.showToast({
            title: "抽签完成",
            icon: "success"
          })
        } else {
          const message =
            response.data.detail || "没有找到符合条件的餐厅"

          wx.showToast({
            title: message,
            icon: "none",
            duration: 2500
          })
        }
      },

      fail: (error) => {
        console.error("抽签请求失败：", error)

        wx.showToast({
          title: "无法连接后端",
          icon: "none"
        })
      },

      complete: () => {
        this.setData({
          isLoading: false
        })
      }
    })
  },

  redrawRestaurants() {
    const displayedIds = this.data.restaurants.map(
      restaurant => restaurant.id
    )
  
    const rejectedIds = [
      ...this.data.rejectedIds,
      ...displayedIds
    ]
  
    this.setData({
      rejectedIds: rejectedIds,
      restaurants: [],
      candidateCount: 0,
      routePreview: null,
      selectedRestaurantId: null
    }, () => {
      this.searchRestaurants()
    })
  },


  chooseRestaurant(event) {
    const restaurantId = Number(event.currentTarget.dataset.id)

    this.setData({
      isRouteLoading: true,
      selectedRestaurantId: restaurantId,
      routePreview: null
    })

    wx.request({
      url: "http://127.0.0.1:8000/route/preview",
      method: "POST",

      header: {
        "content-type": "application/json"
      },

      data: {
        start: this.data.start,
        destination: this.data.destination,
        restaurant_id: restaurantId,
        travel_mode: this.data.travelMode
      },

      success: (response) => {
        if (
          response.statusCode === 200 &&
          response.data.success === true
        ) {
          this.setData({
            routePreview: response.data
          })

          wx.showToast({
            title: "新路线已生成",
            icon: "success"
          })
        } else {
          const message =
            response.data.detail || "生成路线失败"

          wx.showToast({
            title: message,
            icon: "none"
          })
        }
      },

      fail: (error) => {
        console.error("路线请求失败：", error)

        wx.showToast({
          title: "无法生成路线",
          icon: "none"
        })
      },

      complete: () => {
        this.setData({
          isRouteLoading: false
        })
      }
    })
  }
})