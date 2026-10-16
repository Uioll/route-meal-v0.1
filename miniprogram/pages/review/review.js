Page({
  data: {
    restaurant: null,
    route: null,

    personalRating: "",
    visitComment: "",
    willingToReturn: true,

    isSaving: false,
    savedVisit: null
  },

  onLoad() {
    const session = wx.getStorageSync("reviewSession")

    if (!session) {
      wx.showToast({
        title: "没有找到餐厅信息",
        icon: "none"
      })

      setTimeout(() => {
        wx.navigateBack()
      }, 1200)

      return
    }

    const restaurant =
      session.restaurant ||
      (
        session.route &&
        session.route.restaurant
      ) ||
      (
        session.mealRoute &&
        session.mealRoute.restaurant
      )

    if (!restaurant || !restaurant.id) {
      wx.showToast({
        title: "餐厅信息不完整",
        icon: "none"
      })

      setTimeout(() => {
        wx.navigateBack()
      }, 1200)

      return
    }

    this.setData({
      restaurant,
      route:
        session.route ||
        session.mealRoute ||
        null
    })
  },

  onRatingInput(event) {
    this.setData({
      personalRating: event.detail.value
    })
  },

  onCommentInput(event) {
    this.setData({
      visitComment: event.detail.value
    })
  },

  selectReturnChoice(event) {
    this.setData({
      willingToReturn:
        event.currentTarget.dataset.value === "true"
    })
  },

  saveVisit() {
    if (this.data.isSaving) {
      return
    }

    const ratingText = String(
      this.data.personalRating
    ).trim()

    const rating = Number(ratingText)

    if (!ratingText || Number.isNaN(rating)) {
      wx.showToast({
        title: "请输入个人评分",
        icon: "none"
      })
      return
    }

    if (rating < 1 || rating > 5) {
      wx.showToast({
        title: "评分必须在1到5分之间",
        icon: "none"
      })
      return
    }

    if (
      Math.abs(
        rating - Math.round(rating * 10) / 10
      ) > 0.000001
    ) {
      wx.showToast({
        title: "评分最多保留一位小数",
        icon: "none"
      })
      return
    }

    this.setData({
      isSaving: true
    })

    wx.request({
      url: "http://127.0.0.1:8000/visits",
      method: "POST",

      header: {
        "content-type": "application/json"
      },

      data: {
        restaurant_id: String(
          this.data.restaurant.id
        ),
        restaurant_name:
          this.data.restaurant.name,
        restaurant_address:
          this.data.restaurant.address || "",
        personal_rating: rating,
        comment:
          this.data.visitComment.trim(),
        willing_to_return:
          this.data.willingToReturn
      },

      success: (response) => {
        if (
          response.statusCode === 200 &&
          response.data &&
          response.data.success === true
        ) {
          this.setData({
            savedVisit: response.data.visit
          })

          wx.showToast({
            title: "用餐记录已保存",
            icon: "success"
          })
        } else {
          const message =
            response.data &&
            response.data.detail
              ? response.data.detail
              : "保存用餐记录失败"

          wx.showToast({
            title: message,
            icon: "none",
            duration: 2500
          })
        }
      },

      fail: (error) => {
        console.error("保存用餐记录失败：", error)

        wx.showToast({
          title: "无法连接后端",
          icon: "none"
        })
      },

      complete: () => {
        this.setData({
          isSaving: false
        })
      }
    })
  },

  goToHistory() {
    wx.switchTab({
      url: "/pages/history/history"
    })
  },

  backToHome() {
    wx.switchTab({
      url: "/pages/index/index"
    })
  }
})