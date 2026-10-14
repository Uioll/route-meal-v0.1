from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Restaurant:
    id: int
    name: str
    cuisine: tuple[str, ...]
    flavors: tuple[str, ...]
    average_price: int
    rating: float
    solo_friendly: bool
    queue_level: str
    detour_minutes: dict[str, int]
    address: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DiningIntent:
    raw_text: str
    cuisines: list[str] = field(default_factory=list)
    flavors: list[str] = field(default_factory=list)
    budget_max: Optional[int] = None
    solo_only: bool = False
    avoid_queue: bool = False
    max_detour_minutes: int = 10

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VisitRecord:
    restaurant_id: int
    restaurant_name: str
    visited_at: str
    personal_rating: float
    comment: str
    willing_to_return: bool

    def to_dict(self) -> dict:
        return asdict(self)
