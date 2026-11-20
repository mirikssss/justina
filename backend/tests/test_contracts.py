"""Контракт = код. Падает, если openapi.yaml, JSON Schema и Pydantic-модели разъехались."""

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from storozh.main import app
from storozh.shared.contracts import NormalizedDocument, SourceSnapshot
from storozh.shared.events import TOPICS, Event

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"
METHODS = {"get", "post", "put", "patch", "delete"}


def _registry() -> Registry:
    resources = []
    for path in [*CONTRACTS.glob("schemas/*.json"), *CONTRACTS.glob("events/*.json")]:
        schema = json.loads(path.read_text())
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads(next(CONTRACTS.glob(f"*/{name}")).read_text())
    return Draft202012Validator(schema, registry=_registry())


def _load(name: str) -> dict:
    return json.loads((CONTRACTS / "examples" / name).read_text())


def test_openapi_paths_match_fastapi():
    spec = yaml.safe_load((CONTRACTS / "openapi.yaml").read_text())
    in_contract = {(m.upper(), p) for p, ops in spec["paths"].items() for m in ops if m in METHODS}
    generated = app.openapi()["paths"]  # то, что реально объявлено в FastAPI-роутерах
    in_code = {(m.upper(), p) for p, ops in generated.items() for m in ops if m in METHODS}
    assert in_contract - in_code == set(), "есть в openapi.yaml, нет в коде"
    assert in_code - in_contract == set(), "есть в коде, нет в openapi.yaml"


def test_normalized_document_example():
    doc = _load("normalized_document.poa_car.json")
    _validator("normalized_document.schema.json").validate(doc)
    NormalizedDocument.model_validate(doc)


def test_source_snapshot_example():
    snap = _load("source_snapshot.json")
    _validator("source_snapshot.schema.json").validate(snap)
    SourceSnapshot.model_validate(snap)


@pytest.mark.parametrize("name", sorted(p.name for p in (CONTRACTS / "examples").glob("event.*.json")))
def test_event_examples(name: str):
    ev = _load(name)
    _validator(f"{ev['type']}.v1.schema.json").validate(ev)
    assert Event.model_validate(ev).to_json()["schema"] == ev["schema"]


def test_every_topic_has_schema():
    files = {p.name.removesuffix(".v1.schema.json") for p in (CONTRACTS / "events").glob("*.v1.schema.json")}
    assert files == set(TOPICS)
