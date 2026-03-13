"""
Ferramentas LangChain para o assistente medico.

Cada funcao decorada com @tool e uma ferramenta que o LLM pode chamar
automaticamente quando precisar de informacoes externas ao contexto do RAG.

Funcoes de consulta (query_*):
- Sao stubs que simulam um sistema hospitalar real.
- Em producao, devem ser substituidas por integracao real com o banco
  de dados do hospital (ex: via HL7 FHIR, API REST interna, SQLAlchemy).
- Retornam dados ficticios para fins de demonstracao academica.

Ferramentas (@tool):
- get_pending_exams: retorna exames pendentes de um paciente
- get_patient_summary: retorna resumo clinico anonimizado
- search_protocol: busca protocolos clinicos por palavra-chave
- emit_alert: registra alertas para a equipe medica

Nota sobre seguranca:
- Todas as ferramentas que envolvem dados de pacientes trabalham apenas
  com dados anonimizados, em conformidade com a LGPD.
- A ferramenta emit_alert exige validacao humana antes de qualquer acao.
"""
from __future__ import annotations
from langchain_core.tools import tool


# -----------------------------------------------------------------
# Stubs de consulta ao banco de dados hospitalar
# Em producao: substituir por chamadas reais ao sistema do hospital
# -----------------------------------------------------------------

def query_pending_exams(patient_id: str) -> list[dict]:
    """
    Stub que simula consulta de exames pendentes de um paciente.
    
    Em producao: conectar ao sistema de LIS (Laboratory Information System)
    do hospital via API ou banco de dados.
    """
    return [
        {"exam_type": "Hemograma completo", "requested_at": "2025-01-10"},
        {"exam_type": "Glicemia de jejum",  "requested_at": "2025-01-10"},
    ]


def query_patient(patient_id: str) -> dict:
    """
    Stub que simula consulta de dados basicos anonimizados do paciente.
    
    Em producao: conectar ao prontuario eletronico (PEP) do hospital.
    Dados retornados devem ser sempre anonimizados (sem nome, CPF, etc).
    """
    return {"age": 52, "gender": "M", "diagnosis_codes": "E11, I10"}


def query_protocols(keyword: str) -> list[dict]:
    """
    Stub que simula busca nos protocolos clinicos internos do hospital.
    
    Em producao: conectar ao sistema de gestao de protocolos do hospital
    ou a um banco vetorial de documentos internos.
    """
    return [
        {
            "title":      f"Protocolo {keyword.title()}",
            "content":    f"Diretrizes internas para manejo de {keyword}.",
            "version":    "1.2",
            "updated_at": "2024-12-01",
        }
    ]


# -----------------------------------------------------------------
# Ferramentas LangChain (@tool)
# -----------------------------------------------------------------

@tool
def get_pending_exams(patient_id: str) -> str:
    """
    Retorna a lista de exames pendentes de um paciente.
    Use quando o medico perguntar sobre exames em aberto ou resultados aguardados.

    Args:
        patient_id: Identificador unico do paciente no sistema hospitalar.
    """
    exams = query_pending_exams(patient_id)
    if not exams:
        return f"Nenhum exame pendente para o paciente {patient_id}."
    lines = [f"- {e['exam_type']} (solicitado em {e['requested_at']})" for e in exams]
    return f"Exames pendentes para paciente {patient_id}:\n" + "\n".join(lines)


@tool
def get_patient_summary(patient_id: str) -> str:
    """
    Retorna um resumo clinico anonimizado do paciente.
    Use para contextualizar a consulta com informacoes basicas do paciente.

    Args:
        patient_id: Identificador unico do paciente no sistema hospitalar.
    """
    data = query_patient(patient_id)
    if not data:
        return f"Paciente {patient_id} nao encontrado."
    return (
        f"Paciente {patient_id}: "
        f"Idade={data.get('age', 'N/D')}, "
        f"Sexo={data.get('gender', 'N/D')}, "
        f"CID-10={data.get('diagnosis_codes', 'N/D')}"
    )


@tool
def search_protocol(keyword: str) -> str:
    """
    Busca protocolos clinicos internos do hospital por palavra-chave.
    Use quando o medico perguntar sobre condutas, protocolos ou diretrizes internas.

    Args:
        keyword: Termo de busca (ex: 'sepse', 'antibiotico', 'AVC').
    """
    protocols = query_protocols(keyword)
    if not protocols:
        return f"Nenhum protocolo encontrado para '{keyword}'."
    results = []
    for p in protocols[:3]:
        snippet = p["content"][:300] + "..." if len(p["content"]) > 300 else p["content"]
        results.append(f"[{p['title']} v{p['version']}]: {snippet}")
    return "\n\n".join(results)


@tool
def emit_alert(patient_id: str, alert_type: str, message: str) -> str:
    """
    Registra um alerta para a equipe medica sobre um paciente.
    ATENCAO: Requer validacao humana antes de qualquer acao clinica.

    Args:
        patient_id: Identificador do paciente.
        alert_type: Tipo do alerta ('urgente', 'informativo', 'critico').
        message: Descricao do alerta.
    """
    print(f"[ALERTA {alert_type.upper()}] Paciente {patient_id}: {message}")
    return (
        f"Alerta '{alert_type}' registrado para paciente {patient_id}. "
        "A equipe medica sera notificada. REQUER VALIDACAO HUMANA."
    )


# Lista de todas as ferramentas disponíveis para uso pelo LLM
ALL_TOOLS = [get_pending_exams, get_patient_summary, search_protocol, emit_alert]