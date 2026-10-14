import re

from .models import DiningIntent


CUISINE_KEYWORDS = (
    "家常菜", "杭帮菜", "川菜", "湘菜", "东北菜", "西北菜", "粤菜",
    "日料", "火锅", "烧烤", "面馆", "小吃", "轻食", "西餐", "砂锅",
    "香锅", "东南亚菜", "简餐", "粥店",
)

FLAVOR_ALIASES = {
    "清淡": ("清淡", "清爽", "低脂"),
    "辣": ("辣", "火辣", "香辣"),
    "麻辣": ("麻辣",),
    "重口": ("重口", "重口味"),
    "热乎": ("热乎", "热的", "暖和"),
    "低脂": ("低脂", "减脂", "健康"),
}


def parse_intent(text: str) -> DiningIntent:
    normalized = text.strip().lower()
    intent = DiningIntent(raw_text=text)

    intent.cuisines = [word for word in CUISINE_KEYWORDS if word in normalized]

    for canonical, aliases in FLAVOR_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            intent.flavors.append(canonical)

    budget_patterns = (
        r"(?:人均|预算|最多|不超过|控制在)?\s*(\d{1,4})\s*元(?:以内|以下|可以搞定|能搞定)?",
        r"(\d{1,4})\s*块(?:以内|以下|可以搞定|能搞定)?",
    )
    for pattern in budget_patterns:
        match = re.search(pattern, normalized)
        if match:
            intent.budget_max = int(match.group(1))
            break

    detour_match = re.search(r"(?:绕路|多走|增加)\s*(?:不超过|最多)?\s*(\d{1,3})\s*分钟", normalized)
    if detour_match:
        intent.max_detour_minutes = int(detour_match.group(1))

    intent.solo_only = any(word in normalized for word in ("一个人", "一人食", "独自"))
    intent.avoid_queue = any(word in normalized for word in ("不排队", "别排队", "不用排队", "少排队"))
    return intent
