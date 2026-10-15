Page({
  data: {
    start: "",
    destination: "",
    startLocation: null,
    destinationLocation: null,  
    travelMode: "公交",
    directRoute: null,
    isDirectRouteLoading: false,
    intentText: "",
    submitted: false,
    isLoading: false,
    candidateCount: 0,
    restaurants: [],
  },

  onStartInput(event) {
    this.setData({
      start: event.detail.value,
      submitted: false,
      candidateCount: 0,
      restaurants: [],
      rejectedIds: [],
      startLocation: null,
      directRoute: null,
    })
  },

  onDestinationInput(event) {
    this.setData({
      destination: event.detail.value,
      destinationLocation: null,
      submitted: false,
      candidateCount: 0,
      restaurants: [],
      rejectedIds: [],
      DestinationLocation: null,
      directRoute: null,
    })
  },

chooseStartLocation() {
  this.chooseLocation("start")
},

chooseDestinationLocation() {
  this.chooseLocation("destination")
},

chooseLocation(locationType) {
  wx.chooseLocation({
    success: (location) => {
      const locationName =
        location.name || location.address || "已选择的位置"

      const selectedLocation = {
        name: locationName,
        address: location.address || "",
        latitude: location.latitude,
        longitude: location.longitude
      }

      const resetData = {
        submitted: false,
        candidateCount: 0,
        restaurants: [],
        rejectedIds: []
      }

      if (locationType === "start") {
        this.setData(
          Object.assign({}, resetData, {
            start: locationName,
            startLocation: selectedLocation,
            directRoute: null
          })
        )
      } else {
        this.setData(
          Object.assign({}, resetData, {
            destination: locationName,
            destinationLocation: selectedLocation,
            directRoute: null
          })
        )
      }
    },

    fail: (error) => {
      console.error("地图选点失败：", error)

      if (
        error.errMsg &&
        error.errMsg.includes("cancel")
      ) {
        return
      }

      wx.showToast({
        title: "暂时无法打开地图",
        icon: "none"
      })
    }
  })
},

  onIntentInput(event) {
    this.setData({
      intentText: event.detail.value,
      submitted: false,
      candidateCount: 0,
      restaurants: [],
      rejectedIds: []
    })
  },

  selectTravelMode(event) {
    wx.removeStorageSync(
      "selectedCommuteRoute"
    )
  
    this.setData({
      travelMode:
        event.currentTarget.dataset.mode,
      submitted: false,
      candidateCount: 0,
      restaurants: [],
      rejectedIds: [],
      directRoute: null
    })
  },

  openRouteSelection() {
    const {
      start,
      destination,
      startLocation,
      destinationLocation,
      travelMode
    } = this.data
  
    if (!startLocation) {
      wx.showToast({
        title: "请通过地图选择起点",
        icon: "none"
      })
      return
    }
  
    if (!destinationLocation) {
      wx.showToast({
        title: "请通过地图选择终点",
        icon: "none"
      })
      return
    }
  
    wx.setStorageSync(
      "routeDraft",
      {
        start,
        destination,
        startLocation,
        destinationLocation,
        travelMode
      }
    )
  
    wx.navigateTo({
      url: "/pages/routes/routes"
    })
  },

  formatRouteDuration(minutes) {
    const totalMinutes = Number(minutes) || 0
  
    if (totalMinutes < 60) {
      return `${totalMinutes}分钟`
    }
  
    const hours = Math.floor(totalMinutes / 60)
    const remainingMinutes = totalMinutes % 60
  
    if (remainingMinutes === 0) {
      return `${hours}小时`
    }
  
    return `${hours}小时${remainingMinutes}分钟`
  },
  
  loadDirectRoute() {
    const {
      startLocation,
      destinationLocation,
      travelMode
    } = this.data
  
    if (!startLocation || !destinationLocation) {
      return
    }
  
    this.setData({
      isDirectRouteLoading: true,
      directRoute: null
    })
  
    wx.request({
      url: "http://127.0.0.1:8000/map/direct-route",
      method: "POST",
  
      data: {
        start_location: startLocation,
        destination_location: destinationLocation,
        travel_mode: travelMode
      },
  
      success: (response) => {
        if (
          response.statusCode !== 200 ||
          !response.data ||
          response.data.success !== true
        ) {
          wx.showToast({
            title: "路线计算失败",
            icon: "none"
          })
          return
        }
  
        const distance =
          Number(response.data.distance_meters) || 0
  
        const distanceText = distance < 1000
          ? `${distance}米`
          : `${(distance / 1000).toFixed(1)}公里`
  
        const directRoute = Object.assign(
          {},
          response.data,
          {
            distance_text: distanceText,
            duration_text: this.formatRouteDuration(
              response.data.duration_minutes
            )
          }
        )
  
        this.setData({
          directRoute
        })
      },
  
      fail: (error) => {
        console.error("真实路线请求失败：", error)
  
        wx.showToast({
          title: "无法连接路线服务",
          icon: "none"
        })
      },
  
      complete: () => {
        this.setData({
          isDirectRouteLoading: false
        })
      }
    })
  },

  searchRestaurants() {
    const {
      start,
      destination,
      intentText,
      travelMode,
      startLocation,
      destinationLocation
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
  
    if (!startLocation || !destinationLocation) {
      wx.showToast({
        title: "请通过地图选择起点和终点",
        icon: "none"
      })
      return
    }
  
    const selectedCommuteRoute =
      wx.getStorageSync(
        "selectedCommuteRoute"
      )
  
    if (
      !selectedCommuteRoute ||
      !selectedCommuteRoute.route
    ) {
      wx.showToast({
        title: "请先确认一条通勤路线",
        icon: "none"
      })
      return
    }
  
    if (
      selectedCommuteRoute.start !== start ||
      selectedCommuteRoute.destination !==
        destination ||
      selectedCommuteRoute.travelMode !==
        travelMode
    ) {
      wx.showToast({
        title: "地点或出行方式已变化，请重新选择路线",
        icon: "none",
        duration: 2500
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
        rejected_ids:
          this.data.rejectedIds,
        start_location: startLocation,
        destination_location:
          destinationLocation
      },
  
      success: (response) => {
        if (
          response.statusCode === 200 &&
          response.data &&
          response.data.success === true
        ) {
          const restaurants =
            response.data.restaurants || []
  
          if (restaurants.length === 0) {
            wx.showToast({
              title: "没有找到符合条件的餐厅",
              icon: "none"
            })
            return
          }
  
          const lotterySession = {
            start,
            destination,
            intentText,
            travelMode,
            startLocation,
            destinationLocation,
            selectedCommuteRoute,
            candidateCount:
              response.data.candidate_count,
            restaurants,
            rejectedIds:
              this.data.rejectedIds
          }
  
          wx.setStorageSync(
            "lotterySession",
            lotterySession
          )
  
          wx.navigateTo({
            url: "/pages/lottery/lottery"
          })
        } else {
          const message =
            response.data &&
            response.data.detail
              ? response.data.detail
              : "没有找到符合条件的餐厅"
  
          wx.showToast({
            title: message,
            icon: "none",
            duration: 2500
          })
        }
      },
  
      fail: (error) => {
        console.error(
          "抽签请求失败：",
          error
        )
  
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

})