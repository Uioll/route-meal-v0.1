import json
from pathlib import Path

from .models import VisitRecord


class VisitHistory:
    def __init__(
        self,
        path: str | Path = "data/visit_history.json",
    ) -> None:
        self.path = Path(path)

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []

        content = self.path.read_text(
            encoding="utf-8",
        ).strip()

        if not content:
            return []

        return json.loads(content)

    def save(self, history: list[dict]) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.path.write_text(
            json.dumps(
                history,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def append(self, record: VisitRecord) -> None:
        history = self.load()
        history.append(record.to_dict())
        self.save(history)

    def delete(self, record_id: int) -> dict:
        history = self.load()

        if record_id < 0 or record_id >= len(history):
            raise IndexError("用餐记录不存在")

        deleted_record = history.pop(record_id)
        self.save(history)

        return deleted_record