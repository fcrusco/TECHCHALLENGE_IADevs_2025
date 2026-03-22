"""Testes unitários — anonimização de dados médicos."""
from src.preprocessing.anonymizer import anonymize_text, anonymize_record


def test_removes_cpf():
    result = anonymize_text("CPF do paciente: 123.456.789-00")
    assert "123.456.789-00" not in result
    assert "<CPF>" in result


def test_removes_crm():
    result = anonymize_text("Médico responsável: CRM 12345/SP")
    assert "CRM 12345/SP" not in result


def test_medical_terms_preserved():
    result = anonymize_text("Diagnóstico: diabetes mellitus tipo 2")
    assert "diabetes mellitus" in result


def test_record_preserves_non_text_fields():
    record = {"instruction": "teste clínico", "label": 1, "score": 0.9}
    result = anonymize_record(record)
    assert result["label"] == 1
    assert result["score"] == 0.9
