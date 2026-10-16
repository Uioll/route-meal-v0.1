import os
from functools import lru_cache
from typing import Literal
import math
import httpx
from dotenv import load_dotenv


load_dotenv()


TravelMode = Literal["公交", "骑行", "步行"]

TENCENT_MAP_BASE_URL = (
    "https://apis.map.qq.com/ws/direction/v1"
)

ROUTE_ENDPOINTS = {
    "公交": "transit",
    "骑行": "bicycling",
    "步行": "walking",
}


class MapServiceError(RuntimeError):
    """腾讯地图服务调用失败。"""


def get_map_key() -> str:
    key = os.getenv("TENCENT_MAP_KEY", "").strip()

    if not key:
        raise MapServiceError(
            "没有找到 TENCENT_MAP_KEY，"
            "请检查项目根目录的 .env 文件"
        )

    return key


def decode_polyline(
    compressed_polyline: list,
) -> list[dict]:
    """
    将腾讯地图压缩坐标转换为微信地图可以使用的坐标点。

    腾讯地图格式：
    [第一个纬度, 第一个经度, 纬度差值, 经度差值, ...]

    微信地图格式：
    [
        {"latitude": 30.1, "longitude": 120.1},
        ...
    ]
    """
    if (
        not isinstance(compressed_polyline, list)
        or len(compressed_polyline) < 2
    ):
        return []

    coordinates = list(compressed_polyline)

    for index in range(2, len(coordinates)):
        coordinates[index] = (
            coordinates[index - 2]
            + coordinates[index] / 1_000_000
        )

    points = []

    for index in range(0, len(coordinates) - 1, 2):
        latitude = float(coordinates[index])
        longitude = float(coordinates[index + 1])

        points.append(
            {
                "latitude": round(latitude, 6),
                "longitude": round(longitude, 6),
            }
        )

    return points


def append_unique_points(
    target: list[dict],
    new_points: list[dict],
) -> None:
    """
    拼接多段路线，同时避免相邻路线段的连接点重复。
    """
    for point in new_points:
        if target and target[-1] == point:
            continue

        target.append(point)


def extract_normal_route_points(
    route: dict,
) -> list[dict]:
    """
    提取骑行、步行路线坐标。
    """
    return decode_polyline(
        route.get("polyline", [])
    )


def extract_transit_route_points(
    route: dict,
) -> list[dict]:
    """
    提取公交路线的完整坐标。

    公交路线由步行段和公交/地铁段共同组成，
    所以需要把每一段的坐标依次拼起来。
    """
    route_points = []

    for step in route.get("steps", []):
        step_mode = step.get("mode")

        if step_mode == "WALKING":
            walking_points = decode_polyline(
                step.get("polyline", [])
            )

            append_unique_points(
                route_points,
                walking_points,
            )

        elif step_mode == "TRANSIT":
            lines = step.get("lines", [])

            if not lines:
                continue

            # 同一个路段可能列出多个可乘线路，
            # 但这些线路的行驶轨迹相同，只取第一条。
            selected_line = lines[0]

            transit_points = decode_polyline(
                selected_line.get("polyline", [])
            )

            append_unique_points(
                route_points,
                transit_points,
            )

    return route_points


def build_transit_summary(route: dict) -> str:
    """
    生成公交路线摘要，例如：
    步行 → 地铁1号线 → 12路
    """
    descriptions = []

    for step in route.get("steps", []):
        step_mode = step.get("mode")

        if step_mode == "WALKING":
            if not descriptions or descriptions[-1] != "步行":
                descriptions.append("步行")

        elif step_mode == "TRANSIT":
            lines = step.get("lines", [])

            if not lines:
                continue

            line = lines[0]
            title = str(line.get("title", "")).strip()
            vehicle = line.get("vehicle", "")

            if title:
                descriptions.append(title)
            elif vehicle == "SUBWAY":
                descriptions.append("地铁")
            elif vehicle == "BUS":
                descriptions.append("公交")
            elif vehicle == "RAIL":
                descriptions.append("铁路")

    if not descriptions:
        return "公交推荐路线"

    return " → ".join(descriptions)


def build_normal_summary(
    route: dict,
    travel_mode: TravelMode,
) -> str:
    """
    生成步行或骑行路线摘要。
    """
    road_names = []

    for step in route.get("steps", []):
        road_name = str(
            step.get("road_name", "")
        ).strip()

        if (
            road_name
            and road_name not in road_names
        ):
            road_names.append(road_name)

        if len(road_names) >= 2:
            break

    if road_names:
        return "经 " + "、".join(road_names)

    direction = str(
        route.get("direction", "")
    ).strip()

    if direction:
        return f"整体向{direction}"

    return f"{travel_mode}推荐路线"


def build_route_result(
    route: dict,
    route_index: int,
    travel_mode: TravelMode,
) -> dict:
    """
    将腾讯地图路线整理成小程序容易使用的统一格式。
    """
    if travel_mode == "公交":
        points = extract_transit_route_points(route)
        summary = build_transit_summary(route)
    else:
        points = extract_normal_route_points(route)
        summary = build_normal_summary(
            route,
            travel_mode,
        )

    return {
        "id": route_index,
        "distance_meters": route.get(
            "distance",
            0,
        ),
        "duration_minutes": route.get(
            "duration",
            0,
        ),
        "summary": summary,
        "points": points,
    }


def plan_route(
    start_latitude: float,
    start_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
    travel_mode: TravelMode,
) -> dict:
    endpoint = ROUTE_ENDPOINTS.get(travel_mode)

    if endpoint is None:
        raise MapServiceError(
            f"暂不支持出行方式：{travel_mode}"
        )

    url = (
        f"{TENCENT_MAP_BASE_URL}/{endpoint}/"
    )

    params = {
        "from": (
            f"{start_latitude},"
            f"{start_longitude}"
        ),
        "to": (
            f"{destination_latitude},"
            f"{destination_longitude}"
        ),
        "key": get_map_key(),
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                url,
                params=params,
            )
            response.raise_for_status()
            result = response.json()

    except httpx.HTTPError as error:
        raise MapServiceError(
            "连接腾讯地图路线服务失败"
        ) from error

    except ValueError as error:
        raise MapServiceError(
            "腾讯地图没有返回有效的 JSON 数据"
        ) from error

    if result.get("status") != 0:
        message = result.get(
            "message",
            "腾讯地图返回未知错误",
        )
        raise MapServiceError(message)

    original_routes = (
        result
        .get("result", {})
        .get("routes", [])
    )

    if not original_routes:
        raise MapServiceError(
            "没有找到可用路线"
        )

    route_results = []

    # 第一版最多展示三条，避免向小程序传输过多坐标。
    for route_index, route in enumerate(
        original_routes[:3]
    ):
        route_result = build_route_result(
            route=route,
            route_index=route_index,
            travel_mode=travel_mode,
        )

        # 没有轨迹点的路线无法画在地图上，暂不返回。
        if route_result["points"]:
            route_results.append(route_result)

    if not route_results:
        raise MapServiceError(
            "路线存在，但没有取得可绘制的轨迹坐标"
        )

    first_route = route_results[0]

    return {
        # 保留下面三个旧字段，
        # 确保现在的小程序页面仍然可以运行。
        "travel_mode": travel_mode,
        "distance_meters": first_route[
            "distance_meters"
        ],
        "duration_minutes": first_route[
            "duration_minutes"
        ],

        # 新增路线选择所需字段。
        "route_count": len(route_results),
        "routes": route_results,
    }


@lru_cache(maxsize=128)
def geocode_address(address: str) -> dict:
    """
    将文字地址转换为腾讯地图坐标。

    使用缓存避免同一家餐厅重复消耗地址解析额度。
    """
    normalized_address = address.strip()

    if not normalized_address:
        raise MapServiceError(
            "餐厅地址不能为空"
        )

    url = (
        "https://apis.map.qq.com/"
        "ws/geocoder/v1/"
    )

    params = {
        "address": normalized_address,
        "key": get_map_key(),
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                url,
                params=params,
            )
            response.raise_for_status()
            result = response.json()

    except httpx.HTTPError as error:
        raise MapServiceError(
            "连接腾讯地图地址解析服务失败"
        ) from error

    except ValueError as error:
        raise MapServiceError(
            "腾讯地图没有返回有效的地址解析数据"
        ) from error

    if result.get("status") != 0:
        message = result.get(
            "message",
            "腾讯地图地址解析失败",
        )
        raise MapServiceError(message)

    geocode_result = result.get(
        "result",
        {},
    )

    location = geocode_result.get(
        "location",
        {},
    )

    latitude = location.get("lat")
    longitude = location.get("lng")

    if latitude is None or longitude is None:
        raise MapServiceError(
            "腾讯地图没有返回餐厅坐标"
        )

    return {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "title": geocode_result.get(
            "title",
            normalized_address,
        ),
        "address": geocode_result.get(
            "address",
            normalized_address,
        ),
    }


def plan_route_via_restaurant(
    start_latitude: float,
    start_longitude: float,
    restaurant_latitude: float,
    restaurant_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
    travel_mode: TravelMode,
) -> dict:
    """
    规划经过餐厅的新路线。

    非驾车路线没有通用途经点参数，因此分成：
    1. 起点到餐厅
    2. 餐厅到终点
    """
    first_result = plan_route(
        start_latitude=start_latitude,
        start_longitude=start_longitude,
        destination_latitude=(
            restaurant_latitude
        ),
        destination_longitude=(
            restaurant_longitude
        ),
        travel_mode=travel_mode,
    )

    second_result = plan_route(
        start_latitude=(
            restaurant_latitude
        ),
        start_longitude=(
            restaurant_longitude
        ),
        destination_latitude=(
            destination_latitude
        ),
        destination_longitude=(
            destination_longitude
        ),
        travel_mode=travel_mode,
    )

    first_route = first_result["routes"][0]
    second_route = second_result["routes"][0]

    return {
        "travel_mode": travel_mode,
        "distance_meters": (
            first_route["distance_meters"]
            + second_route["distance_meters"]
        ),
        "duration_minutes": (
            first_route["duration_minutes"]
            + second_route["duration_minutes"]
        ),
        "segments": [
            {
                "key": "to_restaurant",
                "label": "起点到餐厅",
                "distance_meters": (
                    first_route[
                        "distance_meters"
                    ]
                ),
                "duration_minutes": (
                    first_route[
                        "duration_minutes"
                    ]
                ),
                "summary": first_route[
                    "summary"
                ],
                "points": first_route[
                    "points"
                ],
            },
            {
                "key": "to_destination",
                "label": "餐厅到终点",
                "distance_meters": (
                    second_route[
                        "distance_meters"
                    ]
                ),
                "duration_minutes": (
                    second_route[
                        "duration_minutes"
                    ]
                ),
                "summary": second_route[
                    "summary"
                ],
                "points": second_route[
                    "points"
                ],
            },
        ],
    }

def search_nearby_restaurants(
    latitude: float,
    longitude: float,
    radius_meters: int = 800,
    page_size: int = 20,
    keyword: str = "餐厅",
) -> list[dict]:
    if not 1 <= radius_meters <= 1000:
        raise MapServiceError(
            "餐厅搜索半径必须在1到1000米之间"
        )

    if not 1 <= page_size <= 20:
        raise MapServiceError(
            "每次搜索数量必须在1到20之间"
        )

    keyword = keyword.strip()

    if not keyword:
        keyword = "餐厅"

    url = "https://apis.map.qq.com/ws/place/v1/search"

    params = {
        "keyword": keyword,
        "boundary": (
            f"nearby("
            f"{latitude},"
            f"{longitude},"
            f"{radius_meters},"
            f"0)"
        ),
        "filter": "category=美食",
        "orderby": "_distance",
        "page_size": page_size,
        "page_index": 1,
        "output": "json",
        "key": get_map_key(),
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                url,
                params=params,
            )
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPError as error:
        raise MapServiceError(
            "连接腾讯地图餐厅搜索服务失败"
        ) from error
    except ValueError as error:
        raise MapServiceError(
            "腾讯地图没有返回有效的JSON数据"
        ) from error

    if result.get("status") != 0:
        message = result.get(
            "message",
            "腾讯地图餐厅搜索返回未知错误",
        )
        raise MapServiceError(message)

    restaurants = []

    for item in result.get("data", []):
        location = item.get("location") or {}

        latitude_value = location.get("lat")
        longitude_value = location.get("lng")

        if (
            latitude_value is None
            or longitude_value is None
        ):
            continue

        restaurants.append(
            {
                "poi_id": item.get("id", ""),
                "name": item.get(
                    "title",
                    "未命名餐厅",
                ),
                "address": item.get(
                    "address",
                    "",
                ),
                "telephone": item.get(
                    "tel",
                    "",
                ),
                "category": item.get(
                    "category",
                    "",
                ),
                "latitude": latitude_value,
                "longitude": longitude_value,
            }
        )

    return restaurants

def sample_route_points(
    route_points: list[dict],
    max_points: int = 5,
) -> list[dict]:
    if not route_points:
        return []

    if not 2 <= max_points <= 10:
        raise MapServiceError(
            "路线检索点数量必须在2到10之间"
        )

    point_count = len(route_points)

    if point_count <= max_points:
        selected_points = route_points
    else:
        selected_points = []

        for index in range(max_points):
            point_index = round(
                index
                * (point_count - 1)
                / (max_points - 1)
            )

            selected_points.append(
                route_points[point_index]
            )

    normalized_points = []

    for point in selected_points:
        latitude = point.get(
            "latitude",
            point.get("lat"),
        )
        longitude = point.get(
            "longitude",
            point.get("lng"),
        )

        if latitude is None or longitude is None:
            continue

        normalized_point = {
            "latitude": float(latitude),
            "longitude": float(longitude),
        }

        if normalized_point not in normalized_points:
            normalized_points.append(
                normalized_point
            )

    return normalized_points
def straight_line_distance_meters(
    start_latitude: float,
    start_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
) -> int:
    earth_radius_meters = 6371000

    start_latitude_radians = math.radians(
        start_latitude
    )
    destination_latitude_radians = math.radians(
        destination_latitude
    )

    latitude_difference = math.radians(
        destination_latitude
        - start_latitude
    )
    longitude_difference = math.radians(
        destination_longitude
        - start_longitude
    )

    value = (
        math.sin(latitude_difference / 2) ** 2
        + math.cos(start_latitude_radians)
        * math.cos(destination_latitude_radians)
        * math.sin(longitude_difference / 2) ** 2
    )

    angle = 2 * math.atan2(
        math.sqrt(value),
        math.sqrt(1 - value),
    )

    return round(
        earth_radius_meters * angle
    )


def search_restaurants_along_route(
    route_points: list[dict],
    max_search_points: int = 5,
    radius_meters: int = 800,
    page_size_per_point: int = 10,
    keyword: str = "餐厅",
) -> dict:
    search_points = sample_route_points(
        route_points=route_points,
        max_points=max_search_points,
    )

    restaurants_by_id = {}

    for point_index, point in enumerate(
        search_points
    ):
        nearby_restaurants = (
            search_nearby_restaurants(
                latitude=point["latitude"],
                longitude=point["longitude"],
                radius_meters=radius_meters,
                page_size=page_size_per_point,
                keyword=keyword,
            )
        )

        for restaurant in nearby_restaurants:
            poi_id = restaurant.get("poi_id")

            if not poi_id:
                poi_id = (
                    f'{restaurant["name"]}|'
                    f'{restaurant["latitude"]}|'
                    f'{restaurant["longitude"]}'
                )

            distance_to_sample = (
                straight_line_distance_meters(
                    start_latitude=(
                        point["latitude"]
                    ),
                    start_longitude=(
                        point["longitude"]
                    ),
                    destination_latitude=(
                        restaurant["latitude"]
                    ),
                    destination_longitude=(
                        restaurant["longitude"]
                    ),
                )
            )

            existing = restaurants_by_id.get(
                poi_id
            )

            if (
                existing is None
                or distance_to_sample
                < existing[
                    "distance_to_route_sample_meters"
                ]
            ):
                restaurant_result = dict(
                    restaurant
                )

                restaurant_result[
                    "route_sample_index"
                ] = point_index

                restaurant_result[
                    "distance_to_route_sample_meters"
                ] = distance_to_sample

                restaurants_by_id[
                    poi_id
                ] = restaurant_result

    restaurants = list(
        restaurants_by_id.values()
    )

    restaurants.sort(
        key=lambda item: item[
            "distance_to_route_sample_meters"
        ]
    )

    return {
        "search_point_count": len(
            search_points
        ),
        "search_points": search_points,
        "restaurant_count": len(
            restaurants
        ),
        "restaurants": restaurants,
    }