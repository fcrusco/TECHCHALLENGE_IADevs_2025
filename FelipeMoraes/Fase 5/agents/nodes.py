"""LangGraph nodes for the STRIDE threat modeling pipeline."""

import base64
import json
import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

from agents.state import ArchitectureComponent, STRIDEThreat, ThreatModelState
from utils.knowledge import (
    STRIDE_CATEGORIES,
    classify_component_type,
    get_threats_for_component,
)


def _llm_call(llm: ChatOpenAI, messages: list, label: str) -> Any:
    """Invoke the LLM and log timing + response size."""
    # Estimate prompt size (chars ÷ 4 ≈ tokens)
    prompt_chars = sum(
        len(m.content) if isinstance(m.content, str)
        else sum(p.get("text", "").__len__() for p in m.content if isinstance(p, dict) and "text" in p)
        for m in messages
    )
    logger.info("  %-35s prompt ~%d chars (~%d tokens)", label, prompt_chars, prompt_chars // 4)
    t0 = time.time()
    response = llm.invoke(messages)
    elapsed = time.time() - t0
    resp_chars = len(response.content) if isinstance(response.content, str) else 0
    logger.info("  %-35s resposta %d chars (~%d tokens) em %.1fs",
                label, resp_chars, resp_chars // 4, elapsed)
    return response


def _get_llm(max_tokens: int | None = None) -> ChatOpenAI:
    """Build a ChatOpenAI client pointed at the local LM Studio server."""
    base_url = os.environ.get("LM_STUDIO_URL", "http://localhost:1234/v1")
    model = os.environ.get("LM_STUDIO_MODEL", "google/gemma-4-e4b")
    # Honour env override; fall back to caller's suggestion, then a safe default
    out_tokens = int(os.environ.get("LM_STUDIO_MAX_TOKENS", max_tokens or 1024))
    return ChatOpenAI(
        base_url=base_url,
        model=model,
        api_key="lm-studio",
        max_tokens=out_tokens,
        temperature=0.1,
    )

_IMAGE_ANALYSIS_SYSTEM = """Você é um arquiteto de software e analista de segurança especialista.
Sua tarefa é analisar diagramas de arquitetura e extrair informações detalhadas sobre os
componentes, seus relacionamentos, limites de confiança (trust boundaries) e fluxos de dados.

Ao analisar um diagrama de arquitetura, identifique:
1. Todos os componentes (serviços, servidores, bancos de dados, usuários, gateways, etc.)
2. As conexões e fluxos de dados entre os componentes
3. Limites de confiança (ex.: internet pública, DMZ, rede privada, VPC de nuvem)
4. Componentes externos vs internos
5. O tipo de cada componente (servidor web, banco de dados, API gateway, load balancer, etc.)

Seja minucioso e preciso. Inclua todos os componentes visíveis, mesmo que pequenos ou auxiliares.
Responda sempre em português do Brasil.
"""

_COMPONENT_EXTRACTION_SYSTEM = """Você é um arquiteto de segurança especializado em modelagem de ameaças.
Dada a descrição de uma arquitetura de software, extraia todos os componentes em formato JSON estruturado.
Retorne APENAS um objeto JSON válido — sem blocos de código markdown, sem texto extra.
Escreva os valores de texto (como "description") em português do Brasil; mantenha as chaves do JSON em inglês.
"""

_STRIDE_ANALYSIS_SYSTEM = """Você é um engenheiro de segurança sênior especializado em modelagem de ameaças
usando a metodologia STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure,
Denial of Service, Elevation of Privilege).

Para cada componente de arquitetura fornecido, gere ameaças STRIDE específicas e acionáveis
relevantes para aquele componente exato e seu contexto na arquitetura.
Considere o tipo do componente, suas conexões e limites de confiança.

Retorne APENAS um objeto JSON válido com sua análise — sem blocos de código markdown, sem texto extra.
Escreva os valores de texto (description, attack_vector, vulnerability, countermeasure) em português do Brasil;
mantenha as chaves do JSON e os valores de "severity"/"stride_letter" em inglês.
"""

_REPORT_SYSTEM = """Você é um analista de segurança especialista que escreve relatórios formais de modelagem de ameaças.
Gere um relatório de modelagem de ameaças em Markdown abrangente e profissional, seguindo a metodologia STRIDE.
O relatório deve ser claro, acionável e adequado para apresentação a uma equipe de segurança ou engenharia.
Escreva o relatório inteiro em português do Brasil.
"""


def _load_image_base64(image_path: str) -> str:
    """Load an image file and return it as a base64 string."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def _get_image_media_type(image_path: str) -> str:
    suffix = Path(image_path).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(suffix, "image/png")


def _clean_json(text: str) -> str:
    """Strip markdown code fences if the model wraps JSON in them."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def analyze_image_node(state: ThreatModelState) -> dict[str, Any]:
    """Node 1: Use a vision-capable local LLM to analyze the architecture diagram."""
    logger.info("  modelo: %s | max_tokens: %s",
                os.environ.get("LM_STUDIO_MODEL", "?"),
                os.environ.get("LM_STUDIO_MAX_TOKENS", "?"))

    llm = _get_llm(max_tokens=4096)

    image_base64 = state.get("image_base64")
    if not image_base64 and state.get("image_path"):
        image_base64 = _load_image_base64(state["image_path"])
        logger.info("  imagem carregada do disco: %s", state.get("image_path"))

    media_type = _get_image_media_type(state.get("image_path", "diagram.png"))
    img_kb = len(image_base64) * 3 / 4 / 1024  # base64 → bytes aproximado
    logger.info("  imagem: %s | tamanho aprox.: %.1f KB", media_type, img_kb)

    messages = [
        SystemMessage(content=_IMAGE_ANALYSIS_SYSTEM),
        HumanMessage(
            content=[
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{media_type};base64,{image_base64}"},
                },
                {
                    "type": "text",
                    "text": (
                        "Analise este diagrama de arquitetura de software em detalhes.\n\n"
                        "Forneça uma descrição abrangente que inclua:\n"
                        "1. Todos os componentes visíveis (nomeie cada um)\n"
                        "2. O tipo de cada componente (servidor web, banco de dados, API gateway, "
                        "load balancer, serviço de autenticação, CDN, firewall/WAF, storage, "
                        "fila de mensagens, cache, microsserviço, container, função serverless, "
                        "serviço externo, monitoramento, usuário/ator, limite de rede)\n"
                        "3. Todas as conexões/fluxos de dados entre os componentes\n"
                        "4. Limites de confiança (internet pública, DMZ, sub-rede privada, VPC, etc.)\n"
                        "5. Quais componentes são externos vs internos\n"
                        "6. O padrão geral de arquitetura (ex.: microsserviços, monolito, serverless, "
                        "três camadas, orientado a eventos)\n\n"
                        "Seja minucioso e específico. Nomeie cada componente exatamente como aparece no diagrama."
                    ),
                },
            ]
        ),
    ]

    response = _llm_call(llm, messages, "analyze_image_node → LLM")

    return {
        "image_base64": image_base64,
        "raw_description": response.content,
        "current_step": "image_analyzed",
        "messages": [response],
    }


def extract_components_node(state: ThreatModelState) -> dict[str, Any]:
    """Node 2: Parse the raw description into structured component data."""
    llm = _get_llm(max_tokens=1024)

    # Truncate to avoid exceeding context limits on small local models
    description = (state.get("raw_description") or "")[:2000]

    prompt = f"""Com base nesta descrição de arquitetura, extraia todos os componentes como um objeto JSON.

Descrição da arquitetura:
{description}

Retorne um objeto JSON com esta estrutura exata:
{{
  "components": [
    {{
      "name": "Nome do Componente",
      "type": "component_type",
      "description": "O que este componente faz",
      "trust_boundary": "public_internet | dmz | private | vpc | external",
      "connections": ["ComponenteA", "ComponenteB"],
      "is_external": true ou false
    }}
  ],
  "trust_boundaries": ["lista de nomes distintos de limites de confiança"],
  "data_flows": [
    {{
      "from": "ComponenteA",
      "to": "ComponenteB",
      "protocol": "HTTPS/TCP/etc",
      "description": "Que dado flui"
    }}
  ],
  "architecture_pattern": "Descrição do padrão geral de arquitetura"
}}

Tipos de componente válidos: user, web_server, api_gateway, load_balancer, application_server,
database, cache, message_queue, authentication_service, cdn, firewall, storage,
microservice, container, function, network, external_service, monitoring, dns, vpn.

Se um tipo não estiver claro, use a correspondência mais próxima da lista acima.
"""

    messages = [SystemMessage(content=_COMPONENT_EXTRACTION_SYSTEM), HumanMessage(content=prompt)]
    response = _llm_call(llm, messages, "extract_components_node → LLM")

    try:
        data = json.loads(_clean_json(response.content))
        logger.info("  JSON parseado com sucesso")
    except json.JSONDecodeError as e:
        logger.warning("  Falha ao parsear JSON: %s — usando estrutura vazia", e)
        data = {"components": [], "trust_boundaries": [], "data_flows": []}

    components = data.get("components", [])
    for comp in components:
        if not comp.get("type"):
            comp["type"] = classify_component_type(comp.get("name", ""), comp.get("description", ""))
        comp.setdefault("connections", [])
        comp.setdefault("trust_boundary", "private")
        comp.setdefault("is_external", False)

    return {
        "components": components,
        "trust_boundaries": data.get("trust_boundaries", []),
        "data_flows": data.get("data_flows", []),
        "current_step": "components_extracted",
        "messages": [response],
    }


def analyze_stride_node(state: ThreatModelState) -> dict[str, Any]:
    """Node 3: Generate STRIDE threats for each component using LLM + knowledge base."""
    llm = _get_llm(max_tokens=2048)

    components = state.get("components", [])
    if not components:
        return {"threats": {}, "current_step": "stride_analyzed"}

    # Build knowledge-base fallback threats (used if LLM fails to parse)
    kb_threats: dict[str, list] = {}
    for comp in components:
        comp_type = comp.get("type", "default")
        base_threats = get_threats_for_component(comp_type)
        threats_with_ids = []
        for i, threat in enumerate(base_threats, 1):
            t = dict(threat)
            stride_letter = t["stride_letter"]
            t["threat_id"] = f"{comp['name'].replace(' ', '_').upper()}-{stride_letter}{i:02d}"
            t["stride_category"] = STRIDE_CATEGORIES[stride_letter]["name"]
            threats_with_ids.append(t)
        kb_threats[comp["name"]] = threats_with_ids

    # Compact component list — avoid huge JSON blowing the context window
    comp_lines = "\n".join(
        f"- {c['name']} ({c.get('type','')}, boundary={c.get('trust_boundary','')}, "
        f"external={c.get('is_external',False)})"
        for c in components[:15]  # cap at 15 components
    )

    prompt = f"""Aplique a modelagem de ameaças STRIDE a cada componente listado abaixo.
Retorne APENAS um objeto JSON válido — sem blocos de código markdown, sem texto extra.

Componentes:
{comp_lines}

Esquema JSON por componente (gere de 2 a 3 ameaças cada):
{{
  "ComponentName": [
    {{
      "threat_id": "NAME-S01",
      "stride_letter": "S",
      "stride_category": "Spoofing",
      "description": "Ameaça específica",
      "severity": "Critical|High|Medium|Low",
      "attack_vector": "Como o atacante explora isso",
      "vulnerability": "Fraqueza raiz",
      "countermeasure": "Passos de mitigação",
      "cwe_reference": "CWE-XXX"
    }}
  ]
}}"""

    logger.info("  %d componentes enviados ao LLM (cap: 15)", len(components[:15]))
    messages = [SystemMessage(content=_STRIDE_ANALYSIS_SYSTEM), HumanMessage(content=prompt)]
    response = _llm_call(llm, messages, "analyze_stride_node → LLM")

    try:
        threats = json.loads(_clean_json(response.content))
        total = sum(len(v) for v in threats.values())
        logger.info("  JSON parseado: %d ameaças em %d componentes", total, len(threats))
    except json.JSONDecodeError as e:
        logger.warning("  Falha ao parsear JSON: %s — usando kb_threats como fallback", e)
        threats = kb_threats

    return {
        "threats": threats,
        "current_step": "stride_analyzed",
        "messages": [response],
    }


def generate_report_node(state: ThreatModelState) -> dict[str, Any]:
    """Node 4: Generate the final STRIDE threat modeling report."""
    llm = _get_llm(max_tokens=2048)

    components = state.get("components", [])
    threats = state.get("threats", {})
    trust_boundaries = state.get("trust_boundaries", [])
    data_flows = state.get("data_flows", [])
    raw_description = state.get("raw_description", "")

    severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    stride_counts = {letter: 0 for letter in "STRIDE"}
    for comp_threats in threats.values():
        for t in comp_threats:
            sev = t.get("severity", "Medium")
            if sev in severity_counts:
                severity_counts[sev] += 1
            letter = t.get("stride_letter", "")
            if letter in stride_counts:
                stride_counts[letter] += 1

    # Compact threat bullets — avoids sending the full JSON to the report prompt
    threat_lines = []
    for comp_name, comp_threats in threats.items():
        for t in comp_threats[:3]:  # top 3 per component keeps prompt small
            sev = t.get("severity", "")
            emoji = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}.get(sev, "")
            threat_lines.append(
                f"{emoji} [{t.get('threat_id','')}] {comp_name} — "
                f"{t.get('stride_letter','')}/{t.get('stride_category','')}: "
                f"{t.get('description','')[:80]} | Fix: {t.get('countermeasure','')[:60]}"
            )

    comp_summary = ", ".join(
        f"{c['name']} ({c.get('type','')})" for c in components
    )

    prompt = f"""Escreva um Relatório de Modelagem de Ameaças STRIDE profissional em Markdown.

Arquitetura: {raw_description[:800]}
Componentes ({len(components)}): {comp_summary}
Limites de confiança: {', '.join(trust_boundaries) if trust_boundaries else 'N/A'}

Resumo de ameaças ({sum(len(v) for v in threats.values())} no total — Critical:{severity_counts['Critical']} High:{severity_counts['High']} Medium:{severity_counts['Medium']} Low:{severity_counts['Low']}):
{chr(10).join(threat_lines[:25])}

Escreva as seções: Resumo Executivo, Visão Geral da Arquitetura, Análise STRIDE, Principais Recomendações, Conclusão.
Use os selos de severidade 🔴🟠🟡🟢. Escreva o relatório inteiro em português do Brasil."""

    logger.info("  %d ameaças no resumo | %d componentes", len(threat_lines), len(components))
    messages = [SystemMessage(content=_REPORT_SYSTEM), HumanMessage(content=prompt)]
    response = _llm_call(llm, messages, "generate_report_node → LLM")

    report_json = {
        "metadata": {
            "generated_by": "STRIDE Threat Modeler - FIAP Hackathon",
            "total_components": len(components),
            "total_threats": sum(len(v) for v in threats.values()),
            "severity_distribution": severity_counts,
            "stride_distribution": stride_counts,
        },
        "components": components,
        "trust_boundaries": trust_boundaries,
        "data_flows": data_flows,
        "threats": threats,
    }

    return {
        "report_markdown": response.content,
        "report_json": report_json,
        "current_step": "report_generated",
        "messages": [response],
    }
