# tools/analysis/tests/core/test_contract_loading.py

from tools.analysis.contracts.load_contract import load_system_contract
from tools.analysis.contracts.contract_types import SystemContract


def test_contract_loads():
    contract = load_system_contract()

    assert contract is not None
    assert isinstance(contract, SystemContract)


def test_domains_exist():
    contract = load_system_contract()

    assert "ingestion" in contract.domains
    assert "representation" in contract.domains
    assert "analysis" in contract.domains
    assert "orchestration" in contract.domains


def test_ingestion_rules_present():
    contract = load_system_contract()

    ingestion = contract.domains["ingestion"]

    assert ingestion.rules
    assert isinstance(ingestion.rules, list)
    assert len(ingestion.rules) > 0


def test_dependency_rules_structure():
    contract = load_system_contract()

    deps = contract.dependency_rules

    assert deps.allowed is not None
    assert isinstance(deps.allowed, dict)
    assert isinstance(deps.forbidden, list)


def test_output_contract_fields():
    contract = load_system_contract()

    output = contract.output_contract

    assert "entities" in output.required_fields
    assert "relationships" in output.required_fields