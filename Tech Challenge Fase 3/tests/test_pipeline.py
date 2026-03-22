"""Testes de integração — explainability e pipeline (sem LLM real)."""
from src.security.explainability import ExplainabilityModule


def test_attribution_with_overlap():
    module = ExplainabilityModule()
    docs = [{
        "page_content": "The protocol for sepsis recommends antibiotic within 1 hour.",
        "metadata": {"source_id": "medquad-001", "title": "Sepsis Treatment"},
        "score": 0.9,
    }]
    response = "Sepsis protocol: administer antibiotic promptly within the first hour."
    result = module.build_attribution(docs, response)
    assert len(result.attributions) > 0
    assert result.confidence > 0.5


def test_no_attribution_for_unrelated_docs():
    module = ExplainabilityModule()
    docs = [{
        "page_content": "Equipment sterilization procedures for surgical tools.",
        "metadata": {"source_id": "medquad-002", "title": "Sterilization"},
        "score": 0.3,
    }]
    response = "Diabetes is managed with insulin and lifestyle changes."
    result = module.build_attribution(docs, response)
    assert len(result.attributions) == 0
