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

_IMAGE_ANALYSIS_SYSTEM = """You are an expert software architect and security analyst.
Your task is to analyze architecture diagrams and extract detailed information about the
components, their relationships, trust boundaries, and data flows.

When analyzing an architecture diagram, identify:
1. All components (services, servers, databases, users, gateways, etc.)
2. The connections and data flows between components
3. Trust boundaries (e.g., public internet, DMZ, private network, cloud VPC)
4. External vs internal components
5. The type of each component (web server, database, API gateway, load balancer, etc.)

Be thorough and precise. Include all visible components even if small or auxiliary.
"""

_COMPONENT_EXTRACTION_SYSTEM = """You are a security architect specializing in threat modeling.
Given a description of a software architecture, extract all components in structured JSON format.
Return ONLY a valid JSON object — no markdown fences, no extra text.
"""

_STRIDE_ANALYSIS_SYSTEM = """You are a senior security engineer specializing in threat modeling
using the STRIDE methodology (Spoofing, Tampering, Repudiation, Information Disclosure,
Denial of Service, Elevation of Privilege).

For each architecture component provided, generate specific, actionable STRIDE threats
relevant to that exact component and its context in the architecture.
Consider the component type, its connections, and trust boundaries.

Return ONLY a valid JSON object with your analysis — no markdown fences, no extra text.
"""

_REPORT_SYSTEM = """You are an expert security analyst writing formal threat modeling reports.
Generate a comprehensive, professional Markdown threat modeling report following STRIDE methodology.
The report should be clear, actionable, and suitable for presentation to a security or engineering team.
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
                        "Analyze this software architecture diagram in detail.\n\n"
                        "Provide a comprehensive description that includes:\n"
                        "1. All components visible (name each one)\n"
                        "2. The type of each component (web server, database, API gateway, "
                        "load balancer, authentication service, CDN, firewall/WAF, storage, "
                        "message queue, cache, microservice, container, serverless function, "
                        "external service, monitoring, user/actor, network boundary)\n"
                        "3. All connections/data flows between components\n"
                        "4. Trust boundaries (public internet, DMZ, private subnet, VPC, etc.)\n"
                        "5. Which components are external vs internal\n"
                        "6. The overall architecture pattern (e.g., microservices, monolith, serverless, "
                        "three-tier, event-driven)\n\n"
                        "Be thorough and specific. Name each component exactly as shown in the diagram."
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

    prompt = f"""Based on this architecture description, extract all components as a JSON object.

Architecture description:
{description}

Return a JSON object with this exact structure:
{{
  "components": [
    {{
      "name": "Component Name",
      "type": "component_type",
      "description": "What this component does",
      "trust_boundary": "public_internet | dmz | private | vpc | external",
      "connections": ["ComponentA", "ComponentB"],
      "is_external": true or false
    }}
  ],
  "trust_boundaries": ["list of distinct trust boundary names"],
  "data_flows": [
    {{
      "from": "ComponentA",
      "to": "ComponentB",
      "protocol": "HTTPS/TCP/etc",
      "description": "What data flows"
    }}
  ],
  "architecture_pattern": "Description of overall architecture pattern"
}}

Valid component types: user, web_server, api_gateway, load_balancer, application_server,
database, cache, message_queue, authentication_service, cdn, firewall, storage,
microservice, container, function, network, external_service, monitoring, dns, vpn.

If a type is unclear, use the closest match from the list above.
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

    prompt = f"""Apply STRIDE threat modeling to each component listed below.
Return ONLY a valid JSON object — no markdown fences, no extra text.

Components:
{comp_lines}

JSON schema per component (generate 2-3 threats each):
{{
  "ComponentName": [
    {{
      "threat_id": "NAME-S01",
      "stride_letter": "S",
      "stride_category": "Spoofing",
      "description": "Specific threat",
      "severity": "Critical|High|Medium|Low",
      "attack_vector": "How attacker exploits it",
      "vulnerability": "Root weakness",
      "countermeasure": "Mitigation steps",
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

    prompt = f"""Write a professional STRIDE Threat Modeling Report in Markdown.

Architecture: {raw_description[:800]}
Components ({len(components)}): {comp_summary}
Trust boundaries: {', '.join(trust_boundaries) if trust_boundaries else 'N/A'}

Threat summary ({sum(len(v) for v in threats.values())} total — Critical:{severity_counts['Critical']} High:{severity_counts['High']} Medium:{severity_counts['Medium']} Low:{severity_counts['Low']}):
{chr(10).join(threat_lines[:25])}

Write sections: Executive Summary, Architecture Overview, STRIDE Analysis, Key Recommendations, Conclusion.
Use 🔴🟠🟡🟢 severity badges."""

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
