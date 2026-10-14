from datetime import datetime
import re
from .data import RESTAURANTS
from .models import VisitRecord
from .parser import parse_intent
from .service import (
    SUPPORTED_MODES,
    draw_two,
    filter_restaurants,
    recommendation_reason,
    simulated_route,
)
from .storage import VisitHistory


def _choose_mode() -> str:
    while True:
        mode = input("出行方式（公交/骑行/步行，默认公交）：").strip() or "公交"
        if mode in SUPPORTED_MODES:
            return mode
        print("目前请选择公交、骑行或步行。")


def main() -> None:
    print("\n=== 顺路去哪吃 V0.1 ===")
    print("当前使用模拟餐厅和模拟绕路时间，用来验证产品逻辑。\n")

    start = input("请输入起点（默认：公司）：").strip() or "公司"
    destination = input("请输入终点（默认：家）：").strip() or "家"
    travel_mode = _choose_mode()
    text = input("今天想吃什么？\n> ").strip()
    if not text:
        text = "50元以内，一个人吃，最多绕路10分钟"

    intent = parse_intent(text)
    print("\n解析结果：", intent.to_dict())

    rejected_ids: set[int] = set()
    selected = None

    while selected is None:
        candidates = filter_restaurants(RESTAURANTS, intent, travel_mode, rejected_ids)
        options = draw_two(candidates)

        if not options:
            print("\n没有符合全部条件的餐厅。请放宽预算、口味或绕路时间后重新运行。")
            return

        print(
            f"\n筛选后候选池共有 {len(candidates)} 家餐厅，"
            f"本轮随机展示 {len(options)} 家："
        )
        labels = ("A", "B")
        for index, restaurant in enumerate(options):
            print(f"\n{labels[index]}：{restaurant.name}｜评分 {restaurant.rating}｜人均 {restaurant.average_price} 元")
            print("原因：" + recommendation_reason(restaurant, intent, travel_mode))

        allowed = "/".join(labels[: len(options)]) + "/R/Q"
        answer = input(f"\n选择餐厅，R=都不喜欢并重抽，Q=退出（{allowed}）：").strip().upper()
        if answer == "Q":
            return
        if answer == "R":
            rejected_ids.update(item.id for item in options)
            continue
        if answer in labels[: len(options)]:
            selected = options[labels.index(answer)]
        else:
            print("输入无效，请重新选择。")

    print("\n已选择：" + selected.name)
    print("新路线：" + simulated_route(start, selected, destination, travel_mode))

    arrived = input("\n模拟到店并写入记录吗？（y/N）：").strip().lower()
    if arrived != "y":
        return

    while True:
        rating_text = input("个人评分（1-5，最多一位小数）：").strip()

        if re.fullmatch(r"[1-4](?:\.\d)?|5(?:\.0)?", rating_text):
            rating = float(rating_text)
            break

        print("请输入1到5之间的数字，最多一位小数，例如4、4.3或4.5。")

    comment = input("简短评价：").strip()
    willing = input("愿意再去吗？（y/N）：").strip().lower() == "y"
    record = VisitRecord(
        restaurant_id=selected.id,
        restaurant_name=selected.name,
        visited_at=datetime.now().isoformat(timespec="seconds"),
        personal_rating=rating,
        comment=comment,
        willing_to_return=willing,
    )
    VisitHistory().append(record)
    print("\n记录已保存到 data/visit_history.json。")
