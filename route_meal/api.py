from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .data import RESTAURANTS
from .parser import parse_intent
from .service import (
    draw_two,
    filter_restaurants,
    recommendation_reason,
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

    rejected_ids: list[int] = Field(
        default_factory=list,
        description="本次抽签中已经拒绝的餐厅ID",
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