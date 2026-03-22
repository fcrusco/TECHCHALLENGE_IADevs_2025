"""Testes unitários — guardrails de segurança."""
from src.security.guardrails import Guardrails


def setup():
    return Guardrails()


def test_blocks_prescription():
    g = setup()
    result = g.check("Por favor, prescreva amoxicilina 500mg")
    assert result.allowed is False


def test_blocks_definitive_diagnosis():
    g = setup()
    result = g.check("Faça um diagnóstico definitivo do paciente")
    assert result.allowed is False


def test_allows_normal_query():
    g = setup()
    result = g.check("Quais sintomas estão associados à pneumonia?")
    assert result.allowed is True


def test_warns_on_dosage():
    g = setup()
    result = g.check("Qual a dosagem recomendada de metformina?")
    assert result.allowed is True
    assert result.requires_human_validation is True
    assert len(result.warnings) > 0
