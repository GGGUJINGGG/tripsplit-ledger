import json
from pathlib import Path

from app.models import DataStore


DATA_FILE = Path(__file__).parent / "data" / "trips.json"


def load_data() -> DataStore:
    if not DATA_FILE.exists():
        return DataStore()

    with DATA_FILE.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    return DataStore.model_validate(raw_data)


def save_data(data: DataStore) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data.model_dump(mode="json"), file, indent=2)
