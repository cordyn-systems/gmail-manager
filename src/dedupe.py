from __future__ import annotations

import csv
from pathlib import Path


class ProcessedLog:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ids = self.load_ids()

    def load_ids(self) -> set[str]:
        if not self.path.exists():
            return set()
        with self.path.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            return {
                row["gmail_message_id"]
                for row in reader
                if row.get("gmail_message_id")
            }

    def has_seen(self, message_id: str) -> bool:
        return message_id in self._ids

    def add_many(self, message_ids: list[str]) -> None:
        new_ids = [message_id for message_id in message_ids if message_id and message_id not in self._ids]
        if not new_ids:
            return

        file_exists = self.path.exists()
        with self.path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["gmail_message_id"])
            if not file_exists or self.path.stat().st_size == 0:
                writer.writeheader()
            for message_id in new_ids:
                writer.writerow({"gmail_message_id": message_id})
                self._ids.add(message_id)

