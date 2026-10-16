from datetime import datetime
import random
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .data import RESTAURANTS
from .models import VisitRecord
from .storage import VisitHistory

from .parser import parse_intent
from .service import (
    draw_two,
    filter_restaurants,
    recommendation_reason,
    simulated_route,
)

from .map_service import (
    MapServiceError,
    geocode_address,
    plan_route,
    plan_route_via_restaurant,
    search_restaurants_along_route,
)

app = FastAPI(
    title="顺路去哪吃 API",
    description="为微信小程序提供餐厅筛选和抽签服务",
    version="0.2.0",
)


class IntentRequest(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=200,
        description="用户对今天想吃什么的自然语言描述",
        examples=["我今天想吃家常菜，辣一点，50元以内"],
    )

class LocationPoint(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=200,
        description="地点名称",
    )

    address: str = Field(
        default="",
        max_length=300,
        description="地点详细地址",
    )

    latitude: float = Field(
        ge=-90,
        le=90,
        description="纬度",
    )

    longitude: float = Field(
        ge=-180,
        le=180,
        description="经度",
    )

class DirectRouteRequest(BaseModel):
    start_location: LocationPoint
    destination_location: LocationPoint

    travel_mode: Literal["公交", "骑行", "步行"] = Field(
        default="公交",
        description="路线使用的出行方式",
    )

class RoutePoint(BaseModel):
    latitude: float = Field(
        ge=-90,
        le=90,
        description="路线点纬度",
    )

    longitude: float = Field(
        ge=-180,
        le=180,
        description="路线点经度",
    )


class RouteRestaurantSearchRequest(BaseModel):
    route_points: list[RoutePoint] = Field(
        min_length=2,
        description="用户确认路线的坐标点",
    )

    max_search_points: int = Field(
        default=3,
        ge=2,
        le=10,
        description="从路线中抽取的餐厅检索点数量",
    )

    radius_meters: int = Field(
        default=800,
        ge=1,
        le=1000,
        description="每个路线点的餐厅搜索半径",
    )

    page_size_per_point: int = Field(
        default=10,
        ge=1,
        le=20,
        description="每个路线点最多获取的餐厅数量",
    )

class RoutePoint(BaseModel):
    latitude: float = Field(
        ge=-90,
        le=90,
        description="路线点纬度",
    )

    longitude: float = Field(
        ge=-180,
        le=180,
        description="路线点经度",
    )


class RouteRestaurantSearchRequest(BaseModel):
    route_points: list[RoutePoint] = Field(
        min_length=2,
        description="用户确认路线的坐标点",
    )

    max_search_points: int = Field(
        default=3,
        ge=2,
        le=10,
        description="从路线中抽取的餐厅检索点数量",
    )

    radius_meters: int = Field(
        default=800,
        ge=1,
        le=1000,
        description="每个路线点的餐厅搜索半径",
    )

    page_size_per_point: int = Field(
        default=10,
        ge=1,
        le=20,
        description="每个路线点最多获取的餐厅数量",
    )

    
    keyword: str = Field(
        default="餐厅",
        min_length=1,
        max_length=50,
        description="餐厅搜索关键词，例如家常菜、火锅、川菜",
    )

class RealLotteryRequest(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=200,
        description="用户今天想吃什么",
    )

    route_points: list[RoutePoint] = Field(
        min_length=2,
        description="用户确认的通勤路线坐标点",
    )

    rejected_ids: list[str] = Field(
        default_factory=list,
        description="本轮已经拒绝的腾讯地图餐厅 POI ID",
    )

    max_search_points: int = Field(
        default=5,
        ge=2,
        le=10,
        description="从路线中抽取的餐厅检索点数量",
    )

    radius_meters: int = Field(
        default=800,
        ge=100,
        le=1000,
        description="每个路线采样点的检索半径",
    )

    page_size_per_point: int = Field(
        default=10,
        ge=1,
        le=20,
        description="每个路线采样点最多获取的餐厅数量",
    )

class MealRouteRestaurant(BaseModel):
    id: str = Field(
        min_length=1,
        description="腾讯地图餐厅 POI ID",
    )

    name: str = Field(
        min_length=1,
        max_length=200,
        description="餐厅名称",
    )

    address: str = Field(
        default="",
        max_length=300,
        description="餐厅地址",
    )

    latitude: float = Field(
        ge=-90,
        le=90,
        description="餐厅纬度",
    )

    longitude: float = Field(
        ge=-180,
        le=180,
        description="餐厅经度",
    )

    telephone: str = Field(
        default="",
        max_length=200,
        description="餐厅联系电话",
    )

class MealRouteRequest(BaseModel):
    start_location: LocationPoint
    destination_location: LocationPoint
    restaurant: MealRouteRestaurant

    travel_mode: Literal[
        "公交",
        "骑行",
        "步行",
    ] = Field(
        default="公交",
        description="保持不变的出行方式",
    )

    original_duration_minutes: float = Field(
        default=0,
        ge=0,
        description="用户确认的原通勤路线时间",
    )

class RestaurantFilterRequest(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=200,
        description="用户对今天想吃什么的自然语言描述",
    )

    travel_mode: Literal["公交", "骑行", "步行"] = Field(
        default="公交",
        description="用户已经选择的出行方式",
    )

    start_location: LocationPoint | None = Field(
        default=None,
        description="地图选择的起点",
    )

    destination_location: LocationPoint | None = Field(
        default=None,
        description="地图选择的终点",
    )

    rejected_ids: list[int] = Field(
        default_factory=list,
        description="本次抽签中已经拒绝的餐厅ID",
    )

class RoutePreviewRequest(BaseModel):
    start: str = Field(
        min_length=1,
        max_length=100,
        description="出发地点",
    )

    destination: str = Field(
        min_length=1,
        max_length=100,
        description="最终目的地",
    )

    start_location: LocationPoint | None = Field(
        default=None,
        description="地图选择的起点",
    )

    destination_location: LocationPoint | None = Field(
        default=None,
        description="地图选择的终点",
    )

    restaurant_id: int = Field(
        gt=0,
        description="用户选中的餐厅ID",
    )

    travel_mode: Literal["公交", "骑行", "步行"] = Field(
        default="公交",
        description="保持不变的出行方式",
    )

class VisitCreateRequest(BaseModel):
    restaurant_id: int | str = Field(
        description="餐厅ID或腾讯地图POI ID",
    )

    restaurant_name: str = Field(
        min_length=1,
        max_length=200,
        description="餐厅名称",
    )

    restaurant_address: str = Field(
        default="",
        max_length=300,
        description="餐厅地址",
    )

    personal_rating: float = Field(
        ge=1,
        le=5,
        description="个人评分，1到5分，最多一位小数",
    )

    comment: str = Field(
        default="",
        max_length=500,
        description="用户的简短评价",
    )

    willing_to_return: bool = Field(
        description="用户是否愿意再次前往",
    )

@app.get("/")
def root():
    return {
        "message": "欢迎使用顺路去哪吃 API",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "0.2.0",
    }


@app.post("/intent/parse")
def parse_dining_intent(request: IntentRequest):
    intent = parse_intent(request.text)

    return {
        "success": True,
        "intent": intent.to_dict(),
    }


@app.post("/restaurants/filter")
def filter_dining_restaurants(request: RestaurantFilterRequest):
    intent = parse_intent(request.text)

    candidates = filter_restaurants(
        restaurants=RESTAURANTS,
        intent=intent,
        travel_mode=request.travel_mode,
        rejected_ids=set(request.rejected_ids),
    )

    restaurant_results = []

    for restaurant in candidates:
        restaurant_results.append(
            {
                "id": restaurant.id,
                "name": restaurant.name,
                "cuisine": restaurant.cuisine,
                "flavors": restaurant.flavors,
                "average_price": restaurant.average_price,
                "rating": restaurant.rating,
                "solo_friendly": restaurant.solo_friendly,
                "queue_level": restaurant.queue_level,
                "detour_minutes": restaurant.detour_minutes[
                    request.travel_mode
                ],
                "address": restaurant.address,
                "reason": recommendation_reason(
                    restaurant,
                    intent,
                    request.travel_mode,
                ),
            }
        )

    return {
        "success": True,
        "intent": intent.to_dict(),
        "travel_mode": request.travel_mode,
        "candidate_count": len(restaurant_results),
        "restaurants": restaurant_results,
    }

@app.post("/lottery/draw")
def draw_restaurant_lottery(request: RestaurantFilterRequest):
    intent = parse_intent(request.text)

    candidates = filter_restaurants(
        restaurants=RESTAURANTS,
        intent=intent,
        travel_mode=request.travel_mode,
        rejected_ids=set(request.rejected_ids),
    )

    selected_restaurants = draw_two(candidates)

    lottery_results = []

    for restaurant in selected_restaurants:
        lottery_results.append(
            {
                "id": restaurant.id,
                "name": restaurant.name,
                "cuisine": restaurant.cuisine,
                "flavors": restaurant.flavors,
                "average_price": restaurant.average_price,
                "rating": restaurant.rating,
                "solo_friendly": restaurant.solo_friendly,
                "queue_level": restaurant.queue_level,
                "detour_minutes": restaurant.detour_minutes[
                    request.travel_mode
                ],
                "address": restaurant.address,
                "reason": recommendation_reason(
                    restaurant,
                    intent,
                    request.travel_mode,
                ),
            }
        )

    return {
        "success": True,
        "candidate_count": len(candidates),
        "displayed_count": len(lottery_results),
        "travel_mode": request.travel_mode,
        "rejected_ids": request.rejected_ids,
        "restaurants": lottery_results,
    }

@app.post("/map/direct-route")
def get_direct_route(request: DirectRouteRequest):
    try:
        route = plan_route(
            start_latitude=(
                request.start_location.latitude
            ),
            start_longitude=(
                request.start_location.longitude
            ),
            destination_latitude=(
                request.destination_location.latitude
            ),
            destination_longitude=(
                request.destination_location.longitude
            ),
            travel_mode=request.travel_mode,
        )
    except MapServiceError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    return {
        "success": True,
        "route_type": "real",
        "start": request.start_location.model_dump(),
        "destination": (
            request.destination_location.model_dump()
        ),
        **route,
    }

@app.post("/restaurants/route-search")
def search_real_restaurants_along_route(
    request: RouteRestaurantSearchRequest,
    ):
    route_points = [
        point.model_dump()
        for point in request.route_points
    ]

    try:
        result = search_restaurants_along_route(
            route_points=route_points,
            max_search_points=(
                request.max_search_points
            ),
            radius_meters=request.radius_meters,
            page_size_per_point=(
                request.page_size_per_point
            ),
            keyword=request.keyword,
        )
    except MapServiceError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    return {
        "success": True,
        **result,
    }

@app.post("/lottery/real-draw")
def draw_real_restaurant_lottery(
    request: RealLotteryRequest,
):
    intent = parse_intent(request.text)

    keyword = (
        intent.cuisines[0]
        if intent.cuisines
        else "餐厅"
    )

    route_search_result = (
        search_restaurants_along_route(
            route_points=[
                point.model_dump()
                for point in request.route_points
            ],
            max_search_points=(
                request.max_search_points
            ),
            radius_meters=request.radius_meters,
            page_size_per_point=(
                request.page_size_per_point
            ),
            keyword=keyword,
        )
    )

    rejected_ids = {
        str(poi_id)
        for poi_id in request.rejected_ids
    }

    candidates = [
        restaurant
        for restaurant
        in route_search_result["restaurants"]
        if str(restaurant["poi_id"])
        not in rejected_ids
    ]

    displayed_count = min(2, len(candidates))

    selected_restaurants = random.sample(
        candidates,
        displayed_count,
    )

    lottery_results = []

    for restaurant in selected_restaurants:
        category = restaurant.get(
            "category",
            "美食",
        )

        category_parts = [
            part
            for part in category.split(":")
            if part and part != "美食"
        ]

        distance = restaurant.get(
            "distance_to_route_sample_meters",
            0,
        )

        lottery_results.append(
            {
                "id": str(restaurant["poi_id"]),
                "poi_id": str(
                    restaurant["poi_id"]
                ),
                "name": restaurant["name"],
                "address": restaurant["address"],
                "telephone": restaurant.get(
                    "telephone",
                    "",
                ),
                "category": category,
                "cuisine": category_parts,
                "latitude": restaurant["latitude"],
                "longitude": restaurant["longitude"],
                "distance_to_route_meters": (
                    distance
                ),
                "is_real": True,
                "reason": (
                    f"腾讯地图分类为“{category}”；"
                    f"距离所选路线约{distance}米"
                ),
            }
        )

    return {
        "success": True,
        "data_source": "tencent_map",
        "keyword": keyword,
        "candidate_count": len(candidates),
        "displayed_count": len(
            lottery_results
        ),
        "rejected_ids": request.rejected_ids,
        "restaurants": lottery_results,
    }

@app.post("/map/meal-route")
def get_meal_route(request: MealRouteRequest):
    restaurant = request.restaurant

    try:
        route = plan_route_via_restaurant(
            start_latitude=(
                request.start_location.latitude
            ),
            start_longitude=(
                request.start_location.longitude
            ),
            restaurant_latitude=(
                restaurant.latitude
            ),
            restaurant_longitude=(
                restaurant.longitude
            ),
            destination_latitude=(
                request.destination_location.latitude
            ),
            destination_longitude=(
                request.destination_location.longitude
            ),
            travel_mode=request.travel_mode,
        )

    except MapServiceError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    detour_minutes = max(
        0,
        round(
            route["duration_minutes"]
            - request.original_duration_minutes
        ),
    )

    return {
        "success": True,
        "route_type": "real_via_restaurant",
        "start": (
            request.start_location.model_dump()
        ),
        "restaurant": {
            "id": restaurant.id,
            "name": restaurant.name,
            "address": restaurant.address,
            "telephone": restaurant.telephone,
            "location": {
                "latitude": restaurant.latitude,
                "longitude": restaurant.longitude,
            },
        },
        "destination": (
            request
            .destination_location
            .model_dump()
        ),
        "original_duration_minutes": (
            request.original_duration_minutes
        ),
        "detour_minutes": detour_minutes,
        **route,
    }

@app.post("/route/preview")
def preview_route(request: RoutePreviewRequest):
    selected_restaurant = next(
        (
            restaurant
            for restaurant in RESTAURANTS
            if restaurant.id == request.restaurant_id
        ),
        None,
    )

    if selected_restaurant is None:
        raise HTTPException(
            status_code=404,
            detail="没有找到对应的餐厅",
        )

    route_text = simulated_route(
        start=request.start,
        restaurant=selected_restaurant,
        destination=request.destination,
        travel_mode=request.travel_mode,
    )

    return {
        "success": True,
        "route_type": "simulated",
        "start": request.start,
        "restaurant": {
            "id": selected_restaurant.id,
            "name": selected_restaurant.name,
            "address": selected_restaurant.address,
        },
        "destination": request.destination,
        "travel_mode": request.travel_mode,
        "detour_minutes": selected_restaurant.detour_minutes[
            request.travel_mode
        ],
        "route_text": route_text,
    }

@app.post("/visits")
def create_visit(request: VisitCreateRequest):
    if abs(
        request.personal_rating
        - round(request.personal_rating, 1)
    ) > 0.000001:
        raise HTTPException(
            status_code=422,
            detail="个人评分最多只能保留一位小数",
        )

    record = VisitRecord(
        restaurant_id=request.restaurant_id,
        restaurant_name=request.restaurant_name,
        visited_at=datetime.now().isoformat(
            timespec="seconds"
        ),
        personal_rating=request.personal_rating,
        comment=request.comment,
        willing_to_return=request.willing_to_return,
        restaurant_address=(
            request.restaurant_address
        ),
    )
    VisitHistory().append(record)

    return {
        "success": True,
        "message": "用餐记录保存成功",
        "visit": record.to_dict(),
    }

@app.get("/visits")
def get_visits():
    history = VisitHistory().load()

    visits = [
        {
            **record,
            "record_id": index,
        }
        for index, record in enumerate(history)
    ]

    return {
        "success": True,
        "visit_count": len(visits),
        "visits": visits,
    }


@app.delete("/visits/{record_id}")
def delete_visit(record_id: int):
    try:
        deleted_record = VisitHistory().delete(record_id)
    except IndexError as error:
        raise HTTPException(
            status_code=404,
            detail="用餐记录不存在",
        ) from error

    return {
        "success": True,
        "message": "用餐记录删除成功",
        "deleted_visit": deleted_record,
    }

