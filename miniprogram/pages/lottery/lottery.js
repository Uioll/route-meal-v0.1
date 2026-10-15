Page({
  data: {
    start: "",
    destination: "",
    intentText: "",
    travelMode: "公交",
    startLocation: null,
    destinationLocation: null,
    selectedCommuteRoute: null,

    candidateCount: 0,
    restaurants: [],
    rejectedIds: [],

    isLoading: false,
    selectedRestaurantId: null
  },

  onLoad() {
    const session = wx.getStorageSync("lotterySession")

    if (
      !session ||
      !Array.isArray(session.restaurants)
    ) {
      wx.showToast({
        title: "没有找到抽签结果",
        icon: "none"
      })

      setTimeout(() => {
        wx.navigateBack()
      }, 1200)

      return
    }

    this.setData({
      start: session.start || "",
      destination: session.destination || "",
      intentText: session.intentText || "",
      travelMode: session.travelMode || "公交",
      startLocation: session.startLocation || null,
      destinationLocation:
        session.destinationLocation || null,
      selectedCommuteRoute:
        session.selectedCommuteRoute || null,
      candidateCount:
        Number(session.candidateCount) || 0,
      restaurants: session.restaurants || [],
      rejectedIds: session.rejectedIds || []
    })
  },

  redrawRestaurants() {
    if (this.data.isLoading) {
      return
    }

    const displayedIds = this.data.restaurants.map(
      restaurant => restaurant.id
    )

    const rejectedIds = this.data.rejectedIds.concat(
      displayedIds
    )

    this.setData({
      isLoading: true,
      restaurants: [],
      candidateCount: 0,
      rejectedIds
    })

    wx.request({
      url: "http://127.0.0.1:8000/lottery/draw",
      method: "POST",

      header: {
        "content-type": "application/json"
      },

      data: {
        text: this.data.intentText,
        travel_mode: this.data.travelMode,
        rejected_ids: rejectedIds,
        start_location: this.data.startLocation,
        destination_location:
          this.data.destinationLocation
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
              title: "没有更多符合条件的餐厅了",
              icon: "none",
              duration: 2500
            })

            return
          }

          this.setData({
            candidateCount:
              response.data.candidate_count || 0,
            restaurants
          })

          this.saveLotterySession()

          wx.showToast({
            title: "重新抽签完成",
            icon: "success"
          })
        } else {
          const message =
            response.data &&
            response.data.detail
              ? response.data.detail
              : "重新抽签失败"

          wx.showToast({
            title: message,
            icon: "none",
            duration: 2500
          })
        }
      },

      fail: (error) => {
        console.error("重新抽签请求失败：", error)

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

  saveLotterySession() {
    wx.setStorageSync("lotterySession", {
      start: this.data.start,
      destination: this.data.destination,
      intentText: this.data.intentText,
      travelMode: this.data.travelMode,
      startLocation: this.data.startLocation,
      destinationLocation:
        this.data.destinationLocation,
      selectedCommuteRoute:
        this.data.selectedCommuteRoute,
      candidateCount: this.data.candidateCount,
      restaurants: this.data.restaurants,
      rejectedIds: this.data.rejectedIds
    })
  },

  chooseRestaurant(event) {
    const restaurantId = Number(
      event.currentTarget.dataset.id
    )

    const selectedRestaurant =
      this.data.restaurants.find(
        restaurant => restaurant.id === restaurantId
      )

    if (!selectedRestaurant) {
      wx.showToast({
        title: "没有找到该餐厅",
        icon: "none"
      })

      return
    }

    this.setData({
      selectedRestaurantId: restaurantId
    })

    const selectedRestaurantSession = {
      start: this.data.start,
      destination: this.data.destination,
      intentText: this.data.intentText,
      travelMode: this.data.travelMode,
      startLocation: this.data.startLocation,
      destinationLocation:
        this.data.destinationLocation,
      selectedCommuteRoute:
        this.data.selectedCommuteRoute,
      restaurant: selectedRestaurant
    }

    wx.setStorageSync(
      "selectedRestaurantSession",
      selectedRestaurantSession
    )

    wx.navigateTo({
      url: "/pages/meal-route/meal-route"
    })
  }
})