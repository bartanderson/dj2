# tools/analysis/contracts/load_contract.py

from pathlib import Path
import json
from typing import Any, Dict, List

from .contract_types import (
    SystemContract,
    DomainContract,
    OutputContract,
    DependencyRules,
    CoreInvariants,
    StabilityPrinciple,
)

_CONTRACT_PATH = (
    Path(__file__).resolve().parents[1]
    / "specification"
    / "tool_system_contract.json"
)


class ContractLoadError(Exception):
    pass


# CONTRACT LOADER BOUNDARY:
# This module is responsible for:
# - loading JSON contract data
# - performing shallow structural validation (required top-level keys only)
# - constructing typed SystemContract objects
#
# It MUST NOT:
# - perform semantic validation or dependency analysis
# - enforce deep schema correctness beyond top-level presence checks
# - evolve into a rules/validation engine
#
# All deeper validation responsibilities belong to a separate validation layer.
#
# This module is stable and intentionally limited in scope.


# -----------------------------
# PUBLIC ENTRYPOINT
# -----------------------------

def load_system_contract() -> SystemContract:
    data = _load_raw_json()
    _validate_required_structure(data)
    return _build_system_contract(data)


# -----------------------------
# IO LAYER
# -----------------------------

def _load_raw_json() -> Dict[str, Any]:
    try:
        with open(_CONTRACT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise ContractLoadError(f"Failed to load system contract: {e}") from e


# -----------------------------
# STRUCTURE VALIDATION (SHALLOW ONLY)
# -----------------------------

def _validate_required_structure(data: Dict[str, Any]) -> None:
    required_top_level = {
        "system",
        "version",
        "domains",
        "core_invariants",
        "output_contract",
        "dependency_rules",
        "stability_principle",
    }

    missing = required_top_level - set(data.keys())
    if missing:
        raise ContractLoadError(f"Missing required contract fields: {missing}")


# -----------------------------
# SAFE FIELD ACCESS
# -----------------------------

def _require(obj: Dict[str, Any], key: str, context: str):
    if not isinstance(obj, dict):
        raise ContractLoadError(f"{context} is not an object")

    if key not in obj:
        raise ContractLoadError(f"Missing '{key}' in {context}")

    return obj[key]


def _require_list(obj: Dict[str, Any], key: str, context: str) -> List[Any]:
    value = _require(obj, key, context)

    if not isinstance(value, list):
        raise ContractLoadError(f"'{key}' in {context} must be a list")

    return value


def _require_dict(obj: Dict[str, Any], key: str, context: str) -> Dict[str, Any]:
    value = _require(obj, key, context)

    if not isinstance(value, dict):
        raise ContractLoadError(f"'{key}' in {context} must be an object")

    return value


# -----------------------------
# DOMAIN BUILDER
# -----------------------------

def _build_domains(raw_domains: Dict[str, Any]) -> Dict[str, DomainContract]:
    domains: Dict[str, DomainContract] = {}

    for name, dom in raw_domains.items():
        if not isinstance(dom, dict):
            raise ContractLoadError(f"Invalid domain (not object): {name}")

        definition = _require(dom, "definition", f"domains.{name}")
        rules = _require_list(dom, "rules", f"domains.{name}")

        domains[name] = DomainContract(
            definition=definition,
            rules=rules,
        )

    return domains


# -----------------------------
# SYSTEM CONTRACT BUILDER
# -----------------------------

def _build_system_contract(data: Dict[str, Any]) -> SystemContract:
    output = _require_dict(data, "output_contract", "output_contract")
    deps = _require_dict(data, "dependency_rules", "dependency_rules")
    stability = _require_dict(data, "stability_principle", "stability_principle")

    return SystemContract(
        system=data["system"],
        version=data["version"],

        domains=_build_domains(_require_dict(data, "domains", "domains")),

        output_contract=OutputContract(
            required_fields=_require_list(output, "required_fields", "output_contract"),
            rules=_require_list(output, "rules", "output_contract"),
        ),

        dependency_rules=DependencyRules(
            allowed=_require_dict(deps, "allowed", "dependency_rules"),
            forbidden=_require_list(deps, "forbidden", "dependency_rules"),
        ),

        core_invariants=CoreInvariants(
            invariants=_require_list(data, "core_invariants", "core_invariants"),
        ),

        stability_principle=StabilityPrinciple(
            definition=_require(stability, "definition", "stability_principle"),
            constraints=_require_list(stability, "constraints", "stability_principle"),
        ),
    )