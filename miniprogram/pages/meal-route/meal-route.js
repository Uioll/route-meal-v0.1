Page({
  data: {
    session: null,
    isLoading: false,
    errorMessage: "",

    routeData: null,
    restaurant: null,

    displayDuration: "",
    displayDistance: "",
    displayDetour: "",

    mapLatitude: 30.2741,
    mapLongitude: 120.1551,
    mapPolylines: [],
    mapIncludePoints: [],
    mapCircles: []
  },

  onLoad() {
    const session = wx.getStorageSync(
      "selectedRestaurantSession"
    )

    if (
      !session ||
      !session.restaurant ||
      !session.startLocation ||
      !session.destinationLocation
    ) {
      wx.showModal({
        title: "缺少路线信息",
        content: "请返回抽签页面重新选择餐厅。",
        showCancel: false,
        success: () => {
          wx.navigateBack()
        }
      })
      return
    }

    this.setData({
      session,
      restaurant: session.restaurant,
      mapLatitude:
        session.startLocation.latitude,
      mapLongitude:
        session.startLocation.longitude
    })

    this.loadMealRoute()
  },

  onReady() {
    this.mapContext = wx.createMapContext(
      "mealRouteMap",
      this
    )

    this.fitRoute()
  },

  loadMealRoute() {
    if (this.data.isLoading) {
      return
    }

    const session = this.data.session

    const selectedRoute =
      session.selectedCommuteRoute &&
      session.selectedCommuteRoute.route
        ? session.selectedCommuteRoute.route
        : null

    const originalDuration =
      selectedRoute
        ? Number(
            selectedRoute.duration_minutes
          ) || 0
        : 0

    this.setData({
      isLoading: true,
      errorMessage: "",
      routeData: null
    })

    wx.request({
      url: "http://127.0.0.1:8000/map/meal-route",
      method: "POST",

      header: {
        "content-type": "application/json"
      },

      data: {
        start_location:
          session.startLocation,
        destination_location:
          session.destinationLocation,
        restaurant_id:
          session.restaurant.id,
        travel_mode:
          session.travelMode,
        original_duration_minutes:
          originalDuration
      },

      success: (response) => {
        if (
          response.statusCode !== 200 ||
          !response.data ||
          response.data.success !== true
        ) {
          const detail =
            response.data &&
            response.data.detail
              ? response.data.detail
              : "新路线生成失败"

          this.setData({
            errorMessage: detail
          })
          return
        }

        this.applyRouteData(
          response.data
        )
      },

      fail: (error) => {
        console.error(
          "新路线请求失败：",
          error
        )

        this.setData({
          errorMessage:
            "无法连接后端，请确认 FastAPI 正在运行"
        })
      },

      complete: () => {
        this.setData({
          isLoading: false
        })
      }
    })
  },

  applyRouteData(routeData) {
    const segments =
      routeData.segments || []

    const mapPolylines = []
    let includePoints = []

    segments.forEach(
      (segment, index) => {
        const points =
          segment.points || []

        includePoints =
          includePoints.concat(points)

        mapPolylines.push({
          points,
          color:
            index === 0
              ? "#ff7043"
              : "#3478f6",
          width: 8,
          borderColor: "#ffffff",
          borderWidth: 2
        })
      }
    )

    const restaurantLocation =
      routeData.restaurant.location

    const mapCircles = [
      {
        latitude:
          routeData.start.latitude,
        longitude:
          routeData.start.longitude,
        color: "#ffffff",
        fillColor: "#22b573",
        radius: 18,
        strokeWidth: 4
      },
      {
        latitude:
          restaurantLocation.latitude,
        longitude:
          restaurantLocation.longitude,
        color: "#ffffff",
        fillColor: "#ffb13b",
        radius: 24,
        strokeWidth: 5
      },
      {
        latitude:
          routeData.destination.latitude,
        longitude:
          routeData.destination.longitude,
        color: "#ffffff",
        fillColor: "#ff7043",
        radius: 18,
        strokeWidth: 4
      }
    ]

    includePoints =
      includePoints.concat([
        {
          latitude:
            routeData.start.latitude,
          longitude:
            routeData.start.longitude
        },
        {
          latitude:
            restaurantLocation.latitude,
          longitude:
            restaurantLocation.longitude
        },
        {
          latitude:
            routeData.destination.latitude,
          longitude:
            routeData.destination.longitude
        }
      ])

    this.setData(
      {
        routeData,
        restaurant:
          routeData.restaurant,
        mapPolylines,
        mapCircles,
        mapIncludePoints:
          includePoints,
        displayDuration:
          this.formatDuration(
            routeData.duration_minutes
          ),
        displayDistance:
          this.formatDistance(
            routeData.distance_meters
          ),
        displayDetour:
          `${routeData.detour_minutes} 分钟`
      },
      () => {
        this.fitRoute()
      }
    )
  },

  fitRoute() {
    if (
      !this.mapContext ||
      !this.data.mapIncludePoints ||
      this.data.mapIncludePoints.length === 0
    ) {
      return
    }

    this.mapContext.includePoints({
      points:
        this.data.mapIncludePoints,
      padding: [130, 35, 310, 35]
    })
  },

  formatDistance(distanceMeters) {
    const distance = Number(
      distanceMeters || 0
    )

    if (distance < 1000) {
      return `${Math.round(distance)} 米`
    }

    return `${
      (distance / 1000).toFixed(1)
    } 公里`
  },

  formatDuration(durationMinutes) {
    const minutes = Math.round(
      Number(durationMinutes || 0)
    )

    if (minutes < 60) {
      return `${minutes} 分钟`
    }

    const hours = Math.floor(
      minutes / 60
    )

    const remainingMinutes =
      minutes % 60

    if (remainingMinutes === 0) {
      return `${hours} 小时`
    }

    return (
      `${hours} 小时 ` +
      `${remainingMinutes} 分钟`
    )
  },

  retryLoadRoute() {
    this.loadMealRoute()
  },

  goToReview() {
    if (!this.data.routeData) {
      wx.showToast({
        title: "路线尚未生成",
        icon: "none"
      })
      return
    }

    wx.setStorageSync(
      "reviewSession",
      {
        restaurant:
          this.data.restaurant,
        routeData:
          this.data.routeData,
        travelMode:
          this.data.session.travelMode,
        route: 
          this.data.mealRoute
      }
    )

    wx.navigateTo({
      url: "/pages/review/review"
    })
  }
})