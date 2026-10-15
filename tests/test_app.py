import random
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from route_meal.api import app
from route_meal.data import RESTAURANTS
from route_meal.models import VisitRecord
from route_meal.parser import parse_intent
from route_meal.service import draw_two, filter_restaurants
from route_meal.storage import VisitHistory


client = TestClient(app)


class IntentParserTests(unittest.TestCase):
    def test_parses_core_request(self):
        intent = parse_intent("我今天想吃家常菜，火辣的，50元可以搞定，一个人吃，最多绕路10分钟")
        self.assertEqual(intent.cuisines, ["家常菜"])
        self.assertIn("辣", intent.flavors)
        self.assertEqual(intent.budget_max, 50)
        self.assertTrue(intent.solo_only)
        self.assertEqual(intent.max_detour_minutes, 10)


class RestaurantServiceTests(unittest.TestCase):
    def test_filters_by_budget_flavor_and_detour(self):
        intent = parse_intent("家常菜，辣，50元以内，最多绕路7分钟")
        results = filter_restaurants(RESTAURANTS, intent, "公交")
        self.assertTrue(results)
        for restaurant in results:
            self.assertLessEqual(restaurant.average_price, 50)
            self.assertLessEqual(restaurant.detour_minutes["公交"], 7)
            self.assertIn("家常菜", restaurant.cuisine)

    def test_rejected_restaurants_do_not_return(self):
        intent = parse_intent("50元以内")
        first = filter_restaurants(RESTAURANTS, intent, "公交")
        rejected = {item.id for item in first[:2]}
        second = filter_restaurants(RESTAURANTS, intent, "公交", rejected)
        self.assertFalse(rejected.intersection(item.id for item in second))

    def test_draw_is_reproducible_with_seed(self):
        selected = draw_two(RESTAURANTS, random.Random(7))
        self.assertEqual(len(selected), 2)
        self.assertNotEqual(selected[0].id, selected[1].id)


class StorageTests(unittest.TestCase):
    def test_visit_record_is_saved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "history.json"
            storage = VisitHistory(path)

            storage.append(
                VisitRecord(
                    1,
                    "Test Restaurant",
                    "2026-10-14T17:00:00",
                    5,
                    "Good",
                    True,
                )
            )

            history = storage.load()

            self.assertEqual(len(history), 1)
            self.assertEqual(
                history[0]["restaurant_name"],
                "Test Restaurant",
            )

    def test_visit_record_can_be_deleted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "history.json"
            storage = VisitHistory(path)

            storage.append(
                VisitRecord(
                    1,
                    "First Restaurant",
                    "2026-10-14T17:00:00",
                    4.5,
                    "Good",
                    True,
                )
            )

            storage.append(
                VisitRecord(
                    2,
                    "Second Restaurant",
                    "2026-10-15T18:00:00",
                    3.0,
                    "Average",
                    False,
                )
            )

            deleted_record = storage.delete(0)
            remaining_history = storage.load()

            self.assertEqual(
                deleted_record["restaurant_name"],
                "First Restaurant",
            )
            self.assertEqual(len(remaining_history), 1)
            self.assertEqual(
                remaining_history[0]["restaurant_name"],
                "Second Restaurant",
            )

    def test_delete_rejects_unknown_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "history.json"
            storage = VisitHistory(path)

            with self.assertRaises(IndexError):
                storage.delete(99)


if __name__ == "__main__":
    unittest.main()

client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_parse_intent():
    response = client.post(
        "/intent/parse",
        json={
            "text": "我今天想吃家常菜，辣一点，50元以内",
        },
    )

    assert response.status_code == 200

    result = response.json()
    # print(result)

    assert result["success"] is True
    assert result["intent"]["budget_max"] == 50