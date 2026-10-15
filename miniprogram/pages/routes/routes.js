Page({
  data: {
    isLoading: false,
    errorMessage: "",

    start: "",
    destination: "",
    travelMode: "公交",

    startLocation: null,
    destinationLocation: null,

    routes: [],
    selectedRouteId: 0,

    mapLatitude: 30.2741,
    mapLongitude: 120.1551,
    mapScale: 13,

    mapPolylines: [],
    mapIncludePoints: [],
    mapCircles: []
  },

  onLoad() {
    const routeDraft = wx.getStorageSync("routeDraft")

    if (
      !routeDraft ||
      !routeDraft.startLocation ||
      !routeDraft.destinationLocation
    ) {
      wx.showModal({
        title: "缺少地点信息",
        content: "请返回首页，通过地图选择起点和终点。",
        showCancel: false,
        success: () => {
          wx.navigateBack()
        }
      })
      return
    }

    const startLocation = Object.assign(
      {},
      routeDraft.startLocation,
      {
        name:
          routeDraft.startLocation.name ||
          routeDraft.start ||
          "起点"
      }
    )

    const destinationLocation = Object.assign(
      {},
      routeDraft.destinationLocation,
      {
        name:
          routeDraft.destinationLocation.name ||
          routeDraft.destination ||
          "终点"
      }
    )

    this.setData({
      start: routeDraft.start || startLocation.name,
      destination:
        routeDraft.destination ||
        destinationLocation.name,
      travelMode: routeDraft.travelMode || "公交",
      startLocation,
      destinationLocation,
      mapLatitude: startLocation.latitude,
      mapLongitude: startLocation.longitude,
      mapCircles: this.buildLocationCircles(
        startLocation,
        destinationLocation
      )
    })

    this.loadRouteOptions()
  },

  onReady() {
    this.mapContext = wx.createMapContext(
      "routeMap",
      this
    )
  
    this.fitSelectedRoute()
  },

  buildLocationCircles(
    startLocation,
    destinationLocation
  ) {
    return [
      {
        latitude: startLocation.latitude,
        longitude: startLocation.longitude,
        color: "#ffffff",
        fillColor: "#22b573",
        radius: 18,
        strokeWidth: 4
      },
      {
        latitude: destinationLocation.latitude,
        longitude: destinationLocation.longitude,
        color: "#ffffff",
        fillColor: "#ff7043",
        radius: 18,
        strokeWidth: 4
      }
    ]
  },

  loadRouteOptions() {
    if (this.data.isLoading) {
      return
    }

    this.setData({
      isLoading: true,
      errorMessage: "",
      routes: [],
      mapPolylines: [],
      mapIncludePoints: []
    })

    wx.request({
      url: "http://127.0.0.1:8000/map/direct-route",
      method: "POST",

      header: {
        "content-type": "application/json"
      },

      data: {
        start_location: this.data.startLocation,
        destination_location:
          this.data.destinationLocation,
        travel_mode: this.data.travelMode
      },

      success: (response) => {
        if (
          response.statusCode !== 200 ||
          !response.data ||
          response.data.success !== true
        ) {
          const detail =
            response.data && response.data.detail
              ? response.data.detail
              : "路线规划失败"

          this.setData({
            errorMessage: detail
          })

          return
        }

        const originalRoutes =
          response.data.routes || []

        const routes = originalRoutes.map(
          (route, index) => {
            return Object.assign({}, route, {
              id:
                route.id === undefined
                  ? index
                  : route.id,
              displayDistance:
                this.formatDistance(
                  route.distance_meters
                ),
              displayDuration:
                this.formatDuration(
                  route.duration_minutes
                )
            })
          }
        )

        if (routes.length === 0) {
          this.setData({
            errorMessage: "没有取得可显示的路线"
          })
          return
        }

        this.setData({
          routes,
          selectedRouteId: routes[0].id
        })

        this.updateMapRoutes()
      },

      fail: (error) => {
        console.error("路线请求失败：", error)

        this.setData({
          errorMessage:
            "无法连接后端，请确认 FastAPI 服务正在运行"
        })
      },

      complete: () => {
        this.setData({
          isLoading: false
        })
      }
    })
  },

  formatDistance(distanceMeters) {
    const distance = Number(distanceMeters || 0)

    if (distance < 1000) {
      return `${Math.round(distance)} 米`
    }

    return `${(distance / 1000).toFixed(1)} 公里`
  },

  formatDuration(durationMinutes) {
    const minutes = Math.round(
      Number(durationMinutes || 0)
    )

    if (minutes < 60) {
      return `${minutes} 分钟`
    }

    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60

    if (remainingMinutes === 0) {
      return `${hours} 小时`
    }

    return `${hours} 小时 ${remainingMinutes} 分钟`
  },

  selectRoute(event) {
    const routeId = Number(
      event.currentTarget.dataset.routeId
    )

    this.setData({
      selectedRouteId: routeId
    })

    this.updateMapRoutes()
  },

  updateMapRoutes() {
    const selectedRouteId =
      this.data.selectedRouteId

    const normalPolylines = []
    const selectedPolylines = []
    let selectedPoints = []

    this.data.routes.forEach((route) => {
      const polyline = {
        points: route.points || [],
        color:
          route.id === selectedRouteId
            ? "#ff7043"
            : "#5f6773",
        width:
          route.id === selectedRouteId
            ? 8
            : 6,
        borderColor:
          route.id === selectedRouteId
            ? "#ffffff"
            : "#ffffff88",
        borderWidth: 2
      }

      if (route.id === selectedRouteId) {
        selectedPolylines.push(polyline)
        selectedPoints = route.points || []
      } else {
        normalPolylines.push(polyline)
      }
    })
    const viewportPoints =
      selectedPoints.concat([
        {
          latitude:
            this.data.startLocation.latitude,
          longitude:
            this.data.startLocation.longitude
        },
        {
          latitude:
            this.data.destinationLocation.latitude,
          longitude:
            this.data.destinationLocation.longitude
        }
      ])

    this.setData(
      {
        mapPolylines:
          normalPolylines.concat(
            selectedPolylines
          ),
        mapIncludePoints: viewportPoints
      },
      () => {
        this.fitSelectedRoute()
      })
  },

  fitSelectedRoute() {
    if (
      !this.mapContext ||
      !this.data.mapIncludePoints ||
      this.data.mapIncludePoints.length === 0
    ) {
      return
    }
  
    this.mapContext.includePoints({
      points: this.data.mapIncludePoints,
  
      /*
       * 上方有起终点卡片，底部有路线面板。
       * 底部留出更大空间，将路线向地图可见区域上方移动。
       */
      padding: [170, 35, 270, 35]
    })
  },

  confirmSelectedRoute() {
    const selectedRoute = this.data.routes.find(
      (route) => {
        return (
          route.id ===
          this.data.selectedRouteId
        )
      }
    )

    if (!selectedRoute) {
      wx.showToast({
        title: "请先选择路线",
        icon: "none"
      })
      return
    }

    wx.setStorageSync(
      "selectedCommuteRoute",
      {
        route: selectedRoute,
        start: this.data.start,
        destination: this.data.destination,
        startLocation:
          this.data.startLocation,
        destinationLocation:
          this.data.destinationLocation,
        travelMode: this.data.travelMode,
        confirmedAt: new Date().toISOString()
      }
    )

    wx.showToast({
      title: "路线已确认",
      icon: "success"
    })

    setTimeout(() => {
      wx.navigateBack()
    }, 500)
  },

  retryLoadRoutes() {
    this.loadRouteOptions()
  }
})