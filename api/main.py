from collections import Counter
from contextlib import asynccontextmanager
from bundle import verify_bundle
from csv import DictReader
from functools import lru_cache
from pathlib import Path
from statistics import mean
from typing import Any, Annotated, Literal
from datetime import date
from fastapi.responses import Response
from client_query import ClientFilters, select_clients, export_csv

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from prediction import load_model, predict


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


# Diagnostics produits par le notebook, consultables sans réentraîner de modèle.
for name, description in {
    "evaluation_k": "Métriques de clustering pour chaque valeur de k.",
    "choix_k": "Choix statistiques et choix commercial de k.",
    "profils_k_candidats": "Profils RFM des segmentations candidates.",
    "comparaison_k4_k5": "Correspondance des clients entre k=4 et k=5.",
    "audit_retours": "Périmètre et bilan monétaire des retours.",
    "sensibilite_retours": "Comparaison des partitions achats positifs et montant net.",
    "migrations_retours": "Migrations après appariement optimal des groupes.",
    "retours_par_segment": "Effet des retours par segment initial.",
    "profils_politiques_retours": "Profils des groupes selon la politique de retours.",
    "stabilite_sensibilite_retours": "Sensibilité aux retours sur plusieurs graines.",
}.items():
    DATASETS[name] = {"file": DATA_DIR / f"{name}.csv", "description": description}

@asynccontextmanager
async def lifespan(application):
    # Refuser le démarrage sur un mélange de modèles, tables ou documentation.
    application.state.bundle = verify_bundle(DATA_DIR)
    for name in DATASETS:
        load_dataset(name)
    load_model()
    yield


app = FastAPI(
    title="API Segmentation Marketing",
    description="Expose les resultats RFM/segments en JSON pour n8n et les futurs assistants marketing.",
    version="0.3.0",
    lifespan=lifespan,
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


def read_dataset(dataset_name: str) -> list[dict[str, Any]]:
    try:
        return load_dataset(dataset_name)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Fichier introuvable: {DATASETS[dataset_name]['file'].name}",
        ) from exc


def resolve_segment(segment: str) -> str:
    normalized = segment.strip().casefold()
    for row in read_dataset("tableau_synthese_segments"):
        name = row["Segment"]
        if name.casefold() == normalized:
            return name
    raise HTTPException(status_code=404, detail=f"Segment inconnu: {segment}")


def dataset_response(
    dataset_name: str,
    limit: int | None,
    offset: int,
    segment: str | None = None,
) -> dict[str, Any]:
    rows = read_dataset(dataset_name)
    if segment is not None:
        canonical_segment = resolve_segment(segment)
        rows = [row for row in rows if row.get("segment_name") == canonical_segment]

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
            "/evaluation-k",
            "/choix-k",
            "/comparaison-segmentations",
            "/sensibilite-retours",
            "/segments/{segment}",
            "/model-info",
            "/bundle-info",
            "/predict",
            "/clients/export",
            "/clients/filters",
        ],
    }


@app.get("/recommandations-segments")
def get_recommandations_segments(
    limit: int | None = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return dataset_response("recommandations_segments", limit, offset)


@app.get("/rfm-clients-segments")
def get_rfm_clients_segments(filters: Annotated[ClientFilters, Query()]):
    rows = select_clients(read_dataset('rfm_clients_segments'), filters)
    return {
        'dataset': 'rfm_clients_segments', 'source_file': 'rfm_clients_segments.csv',
        'description': 'Clients filtrés et triés avant pagination.',
        'statistics': build_statistics(rows),
        'pagination': {'offset': filters.offset, 'limit': filters.limit, 'total': len(rows), 'returned': len(rows[filters.offset:filters.offset+filters.limit])},
        'data': rows[filters.offset:filters.offset+filters.limit],
    }


@app.get('/clients/export')
def export_clients(filters: Annotated[ClientFilters, Query()]):
    all_rows = read_dataset('rfm_clients_segments')
    rows = select_clients(all_rows, filters)
    content = export_csv(rows, list(all_rows[0]) if all_rows else [])
    return Response(content, media_type='text/csv; charset=utf-8', headers={
        'Content-Disposition': 'attachment; filename="clients-selection.csv"',
        'X-Total-Count': str(len(rows)), 'Cache-Control': 'no-store',
    })


@app.get('/clients/filters')
def client_filter_options():
    rows = read_dataset('rfm_clients_segments')
    return {'countries': sorted({r['CountryMode'] for r in rows}), 'segments': sorted({r['segment_name'] for r in rows})}


@app.get("/tableau-synthese-segments")
def get_tableau_synthese_segments(
    limit: int | None = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return dataset_response("tableau_synthese_segments", limit, offset)


@app.get("/evaluation-k")
def get_evaluation_k(
    limit: int | None = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return dataset_response("evaluation_k", limit, offset)


@app.get("/choix-k")
def get_choix_k(
    limit: int | None = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return dataset_response("choix_k", limit, offset)


def grouped_response(sections: dict[str, str]) -> dict[str, Any]:
    # Chaque section conserve son fichier source et expose toute sa petite table.
    return {key: dataset_response(dataset, None, 0) for key, dataset in sections.items()}


@app.get("/comparaison-segmentations")
def get_comparaison_segmentations() -> dict[str, Any]:
    return grouped_response({
        "profils": "profils_k_candidats",
        "correspondance_k4_k5": "comparaison_k4_k5",
    })


@app.get("/sensibilite-retours")
def get_sensibilite_retours() -> dict[str, Any]:
    return grouped_response({
        "audit": "audit_retours",
        "comparaison": "sensibilite_retours",
        "migrations": "migrations_retours",
        "par_segment": "retours_par_segment",
        "profils": "profils_politiques_retours",
        "stabilite": "stabilite_sensibilite_retours",
    })


@app.get("/segments/{segment}")
def get_segment(segment: str) -> dict[str, Any]:
    canonical_segment = resolve_segment(segment)
    sections = {
        "synthese": ("tableau_synthese_segments", "Segment"),
        "recommandation": ("recommandations_segments", "Segment"),
        "effet_retours": ("retours_par_segment", "Segment_gross"),
    }
    response: dict[str, Any] = {"segment": canonical_segment, "sources": {}}
    for key, (dataset, column) in sections.items():
        matching = [row for row in read_dataset(dataset) if row[column] == canonical_segment]
        if not matching:
            raise HTTPException(status_code=404, detail=f"Information absente pour {canonical_segment}: {key}")
        response[key] = matching[0]
        response["sources"][key] = DATASETS[dataset]["file"].name
    response['definition'] = prediction_model()['segment_definitions'][canonical_segment]
    response['sources']['definition'] = 'rfm_model.json'
    return response


# L'inférence utilise uniquement des paramètres numériques JSON, sans pickle.


class ClientRFM(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    recency: int = Field(ge=0, le=1000000, description='Jours depuis le dernier achat valide à la date de référence.')
    frequency: int = Field(ge=1, le=1000000000, description='Factures distinctes sur la fenêtre observée.')
    monetary: float = Field(gt=0, le=1e15, description='Montant des achats positifs en GBP sur cette fenêtre.')
    observation_start: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$', description='Début inclus de la fenêtre, AAAA-MM-JJ.')
    observation_end: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$', description='Fin incluse de la fenêtre, AAAA-MM-JJ.')
    reference_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$', description='Date à laquelle la récence est mesurée, AAAA-MM-JJ.')
    mode: Literal['historical', 'simulation'] = 'historical'

    @model_validator(mode='after')
    def validate_period(self):
        start, end, reference = [date.fromisoformat(v) for v in [self.observation_start, self.observation_end, self.reference_date]]
        if start > end or reference <= end:
            raise ValueError('La fenêtre doit être ordonnée et la référence postérieure à sa fin.')
        # La date du dernier achat doit appartenir à la fenêtre déclarée.
        if not (reference-end).days <= self.recency <= (reference-start).days:
            raise ValueError('La récence place le dernier achat hors de la fenêtre déclarée.')
        return self


def prediction_model():
    try:
        return load_model()
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(status_code=503, detail='Modèle de classement indisponible ou invalide.')


@app.get('/model-info')
def get_model_info():
    model = prediction_model()
    return {**{key: model[key] for key in ['model_id', 'algorithm', 'k', 'features', 'currency', 'policy', 'training', 'segment_definitions']}, 'bundle_id': app.state.bundle['bundle_id'], 'temporal_contract': {'required': ['observation_start', 'observation_end', 'reference_date'], 'modes': ['historical', 'simulation'], 'rule': 'historical exige les dates du modèle ; toute autre période exige simulation'}}


@app.post('/predict')
def predict_client(client: ClientRFM):
    model = prediction_model()
    expected = {name: str(model['training'][key])[:10] for name, key in [('observation_start','window_start'), ('observation_end','window_end'), ('reference_date','reference_date')]}
    supplied = {name: getattr(client, name) for name in expected}
    same_period = supplied == expected
    if not same_period and client.mode != 'simulation':
        raise HTTPException(status_code=422, detail='Période différente de l’entraînement : utiliser explicitement le mode simulation. Aucune extrapolation validée ni annualisation automatique.')
    result = predict([client.recency, client.frequency, client.monetary], model)
    result['temporal_context'] = {'mode': client.mode, 'matches_training': same_period, **supplied,
        'observation_days': (date.fromisoformat(client.observation_end)-date.fromisoformat(client.observation_start)).days+1}
    result['notice'] = ('Simulation hors du périmètre validé : aucune garantie de pertinence pour cette période. ' if not same_period else '') + result['notice']
    result['bundle_id'] = app.state.bundle['bundle_id']
    result['segment_definition'] = model['segment_definitions'][result['segment']]
    result['recommendation'] = next((row['Recommandation marketing'] for row in read_dataset('recommandations_segments') if row['Segment'] == result['segment']), None)
    return result


@app.get('/bundle-info')
def get_bundle_info():
    return app.state.bundle
