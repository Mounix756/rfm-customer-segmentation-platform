from collections import Counter
from csv import DictReader
from functools import lru_cache
from pathlib import Path
from statistics import mean
from typing import Any

from fastapi import FastAPI, HTTPException, Query


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

DATASETS = {
    "recommandations_segments": {
        "file": DATA_DIR / "recommandations_segments.csv",
        "description": "Recommandations marketing par segment client.",
    },
    "rfm_clients_segments": {
        "file": DATA_DIR / "rfm_clients_segments.csv",
        "description": "Clients RFM avec segment attribue.",
    },
    "tableau_synthese_segments": {
        "file": DATA_DIR / "tableau_synthese_segments.csv",
        "description": "Synthese statistique des segments client.",
    },
}

app = FastAPI(
    title="API Segmentation Marketing",
    description="Expose les resultats RFM/segments en JSON pour n8n et les futurs assistants marketing.",
    version="0.1.0",
)


def parse_value(value: str) -> Any:
    value = value.strip()
    if value == "":
        return None

    try:
        int_value = int(value)
    except ValueError:
        pass
    else:
        return int_value

    try:
        return float(value)
    except ValueError:
        return value


@lru_cache(maxsize=len(DATASETS))
def load_dataset(dataset_name: str) -> list[dict[str, Any]]:
    dataset = DATASETS[dataset_name]
    csv_path = dataset["file"]

    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = DictReader(csv_file)
        return [
            {column: parse_value(value or "") for column, value in row.items()}
            for row in reader
        ]


def build_statistics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "row_count": 0,
            "columns": [],
            "numeric": {},
            "categorical": {},
        }

    columns = list(rows[0].keys())
    stats: dict[str, Any] = {
        "row_count": len(rows),
        "columns": columns,
        "numeric": {},
        "categorical": {},
    }

    for column in columns:
        values = [row.get(column) for row in rows if row.get(column) is not None]
        numeric_values = [
            value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)
        ]

        if numeric_values and len(numeric_values) == len(values):
            stats["numeric"][column] = {
                "count": len(numeric_values),
                "sum": round(sum(numeric_values), 4),
                "mean": round(mean(numeric_values), 4),
                "min": min(numeric_values),
                "max": max(numeric_values),
            }
            continue

        text_values = [str(value) for value in values if isinstance(value, str)]
        if text_values:
            counter = Counter(text_values)
            stats["categorical"][column] = {
                "count": len(text_values),
                "unique": len(counter),
                "top_values": [
                    {"value": value, "count": count}
                    for value, count in counter.most_common(10)
                ],
            }

    return stats


def dataset_response(
    dataset_name: str,
    limit: int | None,
    offset: int,
) -> dict[str, Any]:
    try:
        rows = load_dataset(dataset_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Fichier introuvable: {exc}") from exc

    end = None if limit is None else offset + limit
    return {
        "dataset": dataset_name,
        "description": DATASETS[dataset_name]["description"],
        "source_file": DATASETS[dataset_name]["file"].name,
        "statistics": build_statistics(rows),
        "pagination": {
            "offset": offset,
            "limit": limit,
            "returned": len(rows[offset:end]),
            "total": len(rows),
        },
        "data": rows[offset:end],
    }


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "message": "API Segmentation Marketing",
        "endpoints": [
            "/recommandations-segments",
            "/rfm-clients-segments",
            "/tableau-synthese-segments",
        ],
    }


@app.get("/recommandations-segments")
def get_recommandations_segments(
    limit: int | None = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return dataset_response("recommandations_segments", limit, offset)


@app.get("/rfm-clients-segments")
def get_rfm_clients_segments(
    limit: int | None = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return dataset_response("rfm_clients_segments", limit, offset)


@app.get("/tableau-synthese-segments")
def get_tableau_synthese_segments(
    limit: int | None = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return dataset_response("tableau_synthese_segments", limit, offset)
