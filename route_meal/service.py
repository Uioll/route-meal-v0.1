import random

from .models import DiningIntent, Restaurant


SUPPORTED_MODES = ("公交", "骑行", "步行")


def filter_restaurants(
    restaurants: list[Restaurant],
    intent: DiningIntent,
    travel_mode: str,
    rejected_ids: set[int] | None = None,
) -> list[Restaurant]:
    if travel_mode not in SUPPORTED_MODES:
        raise ValueError(f"暂不支持出行方式：{travel_mode}")

    rejected_ids = rejected_ids or set()
    candidates: list[Restaurant] = []

    for restaurant in restaurants:
        if restaurant.id in rejected_ids:
            continue
        if restaurant.detour_minutes.get(travel_mode, 999) > intent.max_detour_minutes:
            continue
        if intent.budget_max is not None and restaurant.average_price > intent.budget_max:
            continue
        if intent.solo_only and not restaurant.solo_friendly:
            continue
        if intent.avoid_queue and restaurant.queue_level == "高":
            continue
        if intent.cuisines and not set(intent.cuisines).intersection(restaurant.cuisine):
            continue
        if intent.flavors and not _flavor_match(intent.flavors, restaurant.flavors):
            continue
        candidates.append(restaurant)

    return candidates


def _flavor_match(requested: list[str], available: tuple[str, ...]) -> bool:
    available_set = set(available)
    for flavor in requested:
        if flavor == "辣" and available_set.intersection({"辣", "香辣", "麻辣", "酸辣"}):
            continue
        if flavor == "清淡" and available_set.intersection({"清淡", "清爽", "低脂"}):
            continue
        if flavor not in available_set:
            return False
    return True


def draw_two(candidates: list[Restaurant], rng: random.Random | None = None) -> list[Restaurant]:
    if len(candidates) < 2:
        return candidates.copy()
    rng = rng or random.Random()
    return rng.sample(candidates, 2)


def recommendation_reason(restaurant: Restaurant, intent: DiningIntent, travel_mode: str) -> str:
    reasons = []
    if intent.cuisines:
        matched = set(intent.cuisines).intersection(restaurant.cuisine)
        if matched:
            reasons.append("符合" + "、".join(sorted(matched)))
    if intent.flavors:
        reasons.append("口味接近“" + "、".join(intent.flavors) + "”")
    if intent.budget_max is not None:
        reasons.append(f"人均{restaurant.average_price}元，在{intent.budget_max}元预算内")
    reasons.append(f"按{travel_mode}计算预计只增加{restaurant.detour_minutes[travel_mode]}分钟")
    return "；".join(reasons)


def simulated_route(start: str, restaurant: Restaurant, destination: str, travel_mode: str) -> str:
    return f"{start} → {restaurant.name}（{restaurant.address}）→ {destination}｜全程保持{travel_mode}方式"
