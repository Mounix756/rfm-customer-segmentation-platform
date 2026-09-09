"""Même sélection pour la liste, ses statistiques et l'export global."""
import csv
import io
import unicodedata
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value).casefold()) if not unicodedata.combining(c)).strip()


class ClientFilters(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    segment: str | None = Field(default=None, min_length=1)
    q: str | None = Field(default=None, max_length=150)
    country: str | None = Field(default=None, max_length=100)
    recency_min: int | None = Field(default=None, ge=0)
    recency_max: int | None = Field(default=None, ge=0)
    frequency_min: int | None = Field(default=None, ge=1)
    frequency_max: int | None = Field(default=None, ge=1)
    monetary_min: float | None = Field(default=None, ge=0)
    monetary_max: float | None = Field(default=None, ge=0)
    sort_by: Literal['CustomerID','Recency','Frequency','Monetary','CountryMode','segment_name'] = 'CustomerID'
    order: Literal['asc','desc'] = 'asc'
    limit: int = Field(default=25, ge=1, le=500)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode='after')
    def ordered_ranges(self):
        for field in ['recency','frequency','monetary']:
            lo, hi = getattr(self, field+'_min'), getattr(self, field+'_max')
            if lo is not None and hi is not None and lo > hi:
                raise ValueError(f'{field}_min doit être inférieur ou égal à {field}_max')
        return self


def select_clients(rows, filters):
    if filters.segment and not any(normalize(r['segment_name']) == normalize(filters.segment) for r in rows):
        raise HTTPException(status_code=404, detail='Segment inconnu')
    selected = []
    for row in rows:
        if filters.segment and normalize(row['segment_name']) != normalize(filters.segment): continue
        if filters.country and normalize(row['CountryMode']) != normalize(filters.country): continue
        if filters.q and normalize(filters.q) not in normalize(' '.join(str(row[k]) for k in ['CustomerID','CountryMode','segment_name'])): continue
        keep = True
        for field, column in [('recency','Recency'),('frequency','Frequency'),('monetary','Monetary')]:
            lo, hi = getattr(filters, field+'_min'), getattr(filters, field+'_max')
            if (lo is not None and row[column] < lo) or (hi is not None and row[column] > hi): keep = False
        if keep: selected.append(row)
    # Le second critère rend les pages reproductibles en cas d'égalité.
    selected.sort(key=lambda r: r['CustomerID'])
    selected.sort(key=lambda r: normalize(r[filters.sort_by]) if isinstance(r[filters.sort_by], str) else r[filters.sort_by], reverse=filters.order == 'desc')
    return selected


def export_csv(rows, columns):
    output = io.StringIO(newline='')
    writer = csv.writer(output, delimiter=';')
    writer.writerow(columns)
    for row in rows:
        values = []
        for column in columns:
            value = row.get(column, '')
            # Les champs texte ne doivent pas devenir des formules de tableur.
            if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')):
                value = "'" + value
            values.append(value)
        writer.writerow(values)
    return '\ufeff' + output.getvalue()
