"""URI документа: uz:{реестр}:{тип}:{номер}. Не меняется никогда, даже когда меняется статус."""

import re
from dataclasses import dataclass

REGISTRIES = {"notarius", "kadastr", "mvd", "katm", "mib", "mehnat", "mygov", "soliq", "birdarcha"}
TYPES = {"act", "poa", "ban", "object", "vehicle", "loan", "case", "contract", "request", "notice", "company", "tax"}

_RE = re.compile(r"^uz:(?P<registry>[a-z]+):(?P<type>[a-z]+):(?P<number>[^\s:][^\s]*)$")


@dataclass(frozen=True, slots=True)
class DocumentURI:
    registry: str
    type: str
    number: str

    def __str__(self) -> str:
        return f"uz:{self.registry}:{self.type}:{self.number}"


def build(registry: str, type_: str, number: str) -> str:
    uri = DocumentURI(registry, type_, number.strip())
    validate(str(uri))
    return str(uri)


def parse(uri: str) -> DocumentURI:
    m = _RE.match(uri)
    if not m:
        raise ValueError(f"bad document URI: {uri!r}")
    if m["registry"] not in REGISTRIES:
        raise ValueError(f"unknown registry in URI: {m['registry']!r}")
    if m["type"] not in TYPES:
        raise ValueError(f"unknown type in URI: {m['type']!r}")
    return DocumentURI(m["registry"], m["type"], m["number"])


def validate(uri: str) -> str:
    parse(uri)
    return uri
