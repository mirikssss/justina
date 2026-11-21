"""Общие модели данных. Зеркало contracts/schemas/*.schema.json — меняются только вместе с контрактом.

tests/test_contracts.py проверяет, что примеры из contracts/examples проходят и JSON Schema, и эти модели.
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from storozh.shared import uri as uri_mod


class Lang(StrEnum):
    uz = "uz"
    ru = "ru"


class DocumentKind(StrEnum):
    notarial_act = "notarial_act"
    poa_notarial = "poa_notarial"
    poa_car = "poa_car"
    ban = "ban"
    real_estate_right = "real_estate_right"
    vehicle = "vehicle"
    loan = "loan"
    enforcement_case = "enforcement_case"
    labor_contract = "labor_contract"
    application = "application"
    notification = "notification"
    company = "company"
    tax_assessment = "tax_assessment"


class DocumentStatus(StrEnum):
    active = "active"
    completed = "completed"
    revoked = "revoked"
    expired = "expired"
    unknown = "unknown"


class OwnerRole(StrEnum):
    """Роль владельца кабинета в документе. На ней стоят правила «Сторожа»."""

    principal = "principal"
    agent = "agent"
    party = "party"
    debtor = "debtor"
    employee = "employee"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Party(_Strict):
    role: str
    name_masked: str
    pinfl_hash: str | None = None  # HMAC, не сам ПИНФЛ


class DocumentObject(_Strict):
    type: str
    id_masked: str | None = None
    label: str | None = None


class Issuer(_Strict):
    type: str
    name: str | None = None


class SourceRef(_Strict):
    external_id: str
    url: str | None = None  # не входит в хеш версии


class NormalizedDocument(_Strict):
    """Документ в одном виде для всех источников. ПИНФЛ, паспорт, номер авто и телефон — только маски."""

    uri: str
    kind: DocumentKind
    source: str = Field(pattern=r"^[a-z0-9_]+\.[a-z0-9_]+$")  # "mygov.car_poa"
    title: str
    status: DocumentStatus
    owner_role: OwnerRole
    parties: list[Party] = []
    object: DocumentObject | None = None
    issued_at: date | None = None
    valid_until: date | None = None
    issuer: Issuer | None = None
    fields: dict[str, Any] = {}
    source_ref: SourceRef

    @field_validator("uri")
    @classmethod
    def _uri(cls, v: str) -> str:
        return uri_mod.validate(v)


class SourceSnapshot(_Strict):
    """Единственный вход данных: POST /internal/ingest/snapshots (подпись HMAC в X-Signature)."""

    snapshot_id: UUID
    citizen_id: UUID
    source: str
    fetched_at: datetime
    complete: bool  # True — в снимке весь список; только тогда пропажа записи = событие
    documents: list[NormalizedDocument]
