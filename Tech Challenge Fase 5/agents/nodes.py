"""Nós do LangGraph para o pipeline de modelagem de ameaças STRIDE."""

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
    """Invoca o LLM e registra tempo de execução + tamanho da resposta."""
    # Estima o tamanho do prompt (chars ÷ 4 ≈ tokens)
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


# Modelo STRIDE fine-tuned (Qwen2.5-3B LoRA, ver training/), servido localmente
# via Ollama. Não tem capacidade de visão, então só substitui a etapa de
# análise STRIDE — a etapa de visão continua usando o provider selecionado.
STRIDE_MODEL_PROVIDER = "ollama"
STRIDE_MODEL_URL = "http://localhost:11434"
STRIDE_MODEL_NAME = "stride-qwen2.5-3b"

# O modelo foi fine-tuned exclusivamente sobre o prompt/schema de
# backend/services/stride.py (JSON agrupado por categoria STRIDE, vocabulário
# de tipos de backend/models/schemas.py). O pipeline agents/ usa outro prompt e
# outro schema (agrupado por nome de componente, com attack_vector/vulnerability/
# cwe_reference) — por isso a chamada ao modelo treinado precisa replicar o
# prompt exato do treino e depois converter a resposta para o formato nativo
# deste pipeline (ver _call_stride_model abaixo).
_STRIDE_MODEL_SYSTEM_PROMPT = """Você é um especialista em cibersegurança. Realize a análise de ameaças STRIDE sobre os componentes fornecidos.

Retorne APENAS um objeto JSON válido com estas chaves exatas:
spoofing, tampering, repudiation, information_disclosure, denial_of_service, elevation_of_privilege

Cada valor é um array de:
{"component_id":"comp_1","component_name":"Name","threat":"descrição curta em português do Brasil","risk_level":"low|medium|high|critical","countermeasures":["uma contramedida em português do Brasil"]}

Regras:
- No máximo 1 ameaça por componente por categoria STRIDE
- No máximo 30 ameaças no total, somando todas as categorias
- Apenas 1 contramedida por ameaça
- Mantenha os textos de ameaça e contramedida curtos (menos de 80 caracteres cada)
- Retorne APENAS o objeto JSON, sem markdown, sem explicação"""

# Vocabulário de tipos usado por utils/knowledge.py -> vocabulário mais restrito
# em que o Modelo treinado STRIDE foi fine-tuned (ver training/seed_kb.py)
_STRIDE_MODEL_TYPE_MAP = {
    "load_balancer": "api_gateway",
    "application_server": "microservice",
    "authentication_service": "auth_service",
    "external_service": "external_api",
    "container": "cloud_service",
    "function": "cloud_service",
    "network": "cloud_service",
    "dns": "cloud_service",
    "vpn": "cloud_service",
}

_STRIDE_MODEL_CATEGORY_TO_LETTER = {
    "spoofing": "S",
    "tampering": "T",
    "repudiation": "R",
    "information_disclosure": "I",
    "denial_of_service": "D",
    "elevation_of_privilege": "E",
}

_STRIDE_MODEL_RISK_TO_SEVERITY = {"low": "Low", "medium": "Medium", "high": "High", "critical": "Critical"}


def _call_stride_model(components: list[dict]) -> tuple[dict, Any]:
    """Chama o Modelo treinado STRIDE com o prompt/schema exatos do treino e
    converte a resposta para o formato nativo deste pipeline (agrupado por
    nome de componente, com threat_id/stride_letter/severity/etc)."""
    llm, _ = _get_llm(STRIDE_MODEL_PROVIDER, STRIDE_MODEL_URL, STRIDE_MODEL_NAME, max_tokens=2048)

    capped = components[:15]
    id_to_name = {}
    lines = ["Componentes da arquitetura para analisar:"]
    for i, c in enumerate(capped, 1):
        comp_id = f"comp_{i}"
        id_to_name[comp_id] = c["name"]
        mapped_type = _STRIDE_MODEL_TYPE_MAP.get(c.get("type", "default"), c.get("type", "default"))
        lines.append(f"- id:{comp_id} name:{c['name']} type:{mapped_type} desc:{c.get('description', '')}")
    components_text = "\n".join(lines)

    messages = [SystemMessage(content=_STRIDE_MODEL_SYSTEM_PROMPT), HumanMessage(content=components_text)]
    response = _llm_call(llm, messages, "analyze_stride_node → Modelo STRIDE treinado")

    data = json.loads(_extract_json(response.content))

    threats: dict[str, list] = {}
    for category, items in data.items():
        letter = _STRIDE_MODEL_CATEGORY_TO_LETTER.get(category)
        if not letter or not isinstance(items, list):
            continue
        for idx, item in enumerate(items, 1):
            comp_name = id_to_name.get(item.get("component_id"), item.get("component_name", "?"))
            countermeasures = item.get("countermeasures") or [""]
            threats.setdefault(comp_name, []).append({
                "threat_id": f"{comp_name.replace(' ', '_').upper()}-{letter}{idx:02d}",
                "stride_letter": letter,
                "stride_category": STRIDE_CATEGORIES[letter]["name"],
                "description": item.get("threat", ""),
                "severity": _STRIDE_MODEL_RISK_TO_SEVERITY.get(item.get("risk_level", "medium"), "Medium"),
                "attack_vector": "Não detalhado pelo modelo treinado — ver descrição",
                "vulnerability": "Não detalhado pelo modelo treinado — ver descrição",
                "countermeasure": countermeasures[0] if countermeasures else "",
                "cwe_reference": "N/A",
            })

    return threats, response


def _get_llm(
    provider: str | None = None,
    override_url: str | None = None,
    override_model: str | None = None,
    max_tokens: int | None = None,
) -> tuple[ChatOpenAI, str]:
    """Cria um client ChatOpenAI para o provider selecionado (openai/ollama/lmstudio).

    Retorna (llm, nome_do_modelo). override_url/model têm precedência sobre as
    variáveis de ambiente, permitindo escolher o provider/modelo na interface.
    """
    provider = provider or os.environ.get("LLM_PROVIDER", "lmstudio")

    # LM_STUDIO_MAX_TOKENS só se aplica ao LM Studio — não contamina OpenAI/Ollama
    lm_max = int(os.environ.get("LM_STUDIO_MAX_TOKENS", max_tokens or 1024))

    if provider == "openai":
        model = override_model or os.environ.get("OPENAI_MODEL", "gpt-4o")
        llm = ChatOpenAI(
            model=model,
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            temperature=0.1,
            # Sem max_tokens: deixa o modelo usar o limite padrão da API
        )
        return llm, model

    if provider == "ollama":
        base = (override_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        url = base if base.endswith("/v1") else f"{base}/v1"
        model = override_model or os.environ.get("OLLAMA_MODEL", "gemma3:4b")
        ollama_max = max_tokens or int(os.environ.get("OLLAMA_MAX_TOKENS", lm_max))
        llm = ChatOpenAI(
            base_url=url,
            model=model,
            api_key="ollama",
            max_tokens=ollama_max,
            temperature=0.1,
        )
        return llm, model

    # lmstudio (padrão)
    base_url = override_url or os.environ.get("LM_STUDIO_URL", "http://localhost:1234/v1")
    model = override_model or os.environ.get("LM_STUDIO_MODEL", "google/gemma-4-e4b")
    llm = ChatOpenAI(
        base_url=base_url,
        model=model,
        api_key="lm-studio",
        max_tokens=lm_max,
        temperature=0.1,
    )
    return llm, model

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
    """Carrega um arquivo de imagem e o retorna como uma string base64."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Imagem não encontrada: {image_path}")
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
    """Remove os blocos de código markdown, caso o modelo envolva o JSON com eles."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json(text: str) -> str:
    """Extrai JSON de texto arbitrário (o GPT-4o frequentemente adiciona prosa ao redor).
    Tenta em ordem: bloco de código, objeto bare, array bare."""
    text = text.strip()
    # 1. Bloco de código markdown: ```json ... ``` ou ``` ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        return m.group(1).strip()
    # 2. Objeto JSON (prioridade: pega o maior bloco { ... })
    m = re.search(r"(\{[\s\S]*\})", text)
    if m:
        return m.group(1)
    # 3. Array JSON
    m = re.search(r"(\[[\s\S]*\])", text)
    if m:
        return m.group(1)
    return text


def analyze_image_node(state: ThreatModelState) -> dict[str, Any]:
    """Nó 1: usa um LLM com capacidade de visão para analisar o diagrama de arquitetura."""
    provider = state.get("provider")
    override_url = state.get("override_url")
    override_model = state.get("override_model")

    llm, model = _get_llm(provider, override_url, override_model, max_tokens=4096)
    logger.info("  provider: %s | modelo: %s", provider or os.environ.get("LLM_PROVIDER", "lmstudio"), model)

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
        "model_used": model,
        "provider_used": provider or os.environ.get("LLM_PROVIDER", "lmstudio"),
    }


def extract_components_node(state: ThreatModelState) -> dict[str, Any]:
    """Nó 2: converte a descrição bruta em dados estruturados de componentes."""
    llm, _ = _get_llm(state.get("provider"), state.get("override_url"), state.get("override_model"), max_tokens=1024)

    # Trunca apenas para modelos locais menores; OpenAI suporta contextos longos
    raw = state.get("raw_description") or ""
    description = raw[:2000] if (state.get("provider") or os.environ.get("LLM_PROVIDER", "lmstudio")) != "openai" else raw[:8000]

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
        data = json.loads(_extract_json(response.content))
        logger.info("  JSON parseado com sucesso")
    except json.JSONDecodeError as e:
        logger.warning("  Falha ao parsear JSON: %s — usando estrutura vazia", e)
        logger.warning("  Resposta bruta (primeiros 500): %s", (response.content or "")[:500])
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
    """Nó 3: gera ameaças STRIDE para cada componente usando LLM + base de conhecimento."""
    components = state.get("components", [])
    if not components:
        return {"threats": {}, "current_step": "stride_analyzed", "stride_model_used": None}

    # Monta ameaças de fallback vindas da base de conhecimento (usadas se o LLM falhar ao parsear)
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

    if state.get("use_stride_model"):
        logger.info("  usando modelo STRIDE treinado: %s/%s", STRIDE_MODEL_PROVIDER, STRIDE_MODEL_NAME)
        try:
            threats, response = _call_stride_model(components)
            total = sum(len(v) for v in threats.values())
            logger.info("  Modelo treinado: %d ameaças em %d componentes", total, len(threats))
            if total == 0:
                threats = kb_threats
        except Exception as e:
            logger.warning("  Modelo treinado falhou (%s) — usando kb_threats como fallback", e)
            threats = kb_threats
            response = None

        return {
            "threats": threats,
            "current_step": "stride_analyzed",
            "messages": [response] if response else [],
            "stride_model_used": STRIDE_MODEL_NAME,
        }

    llm, model = _get_llm(state.get("provider"), state.get("override_url"), state.get("override_model"), max_tokens=2048)

    # Lista compacta de componentes — evita que um JSON enorme estoure a janela de contexto
    comp_lines = "\n".join(
        f"- {c['name']} ({c.get('type','')}, boundary={c.get('trust_boundary','')}, "
        f"external={c.get('is_external',False)})"
        for c in components[:15]  # limite de 15 componentes
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
        threats = json.loads(_extract_json(response.content))
        total = sum(len(v) for v in threats.values())
        logger.info("  JSON parseado: %d ameaças em %d componentes", total, len(threats))
        if total == 0:
            logger.warning("  Nenhuma ameaça no JSON — usando kb_threats como fallback")
            threats = kb_threats
    except json.JSONDecodeError as e:
        logger.warning("  Falha ao parsear JSON: %s — usando kb_threats como fallback", e)
        logger.warning("  Resposta bruta (primeiros 500): %s", (response.content or "")[:500])
        threats = kb_threats

    return {
        "threats": threats,
        "current_step": "stride_analyzed",
        "messages": [response],
        "stride_model_used": None,
    }


def generate_report_node(state: ThreatModelState) -> dict[str, Any]:
    """Nó 4: gera o relatório final de modelagem de ameaças STRIDE."""
    llm, _ = _get_llm(state.get("provider"), state.get("override_url"), state.get("override_model"), max_tokens=2048)

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

    # Bullets compactos de ameaças — evita mandar o JSON inteiro no prompt do relatório
    threat_lines = []
    for comp_name, comp_threats in threats.items():
        for t in comp_threats[:3]:  # top 3 por componente mantém o prompt pequeno
            sev = t.get("severity", "")
            threat_lines.append(
                f"[{sev}] [{t.get('threat_id','')}] {comp_name} — "
                f"{t.get('stride_letter','')}/{t.get('stride_category','')}: "
                f"{t.get('description','')[:80]} | Correção: {t.get('countermeasure','')[:60]}"
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
Não use emojis ou ícones — apenas texto. Indique a severidade de cada ameaça escrevendo a palavra
(Crítico, Alto, Médio ou Baixo) em negrito. Escreva o relatório inteiro em português do Brasil."""

    logger.info("  %d ameaças no resumo | %d componentes", len(threat_lines), len(components))
    messages = [SystemMessage(content=_REPORT_SYSTEM), HumanMessage(content=prompt)]
    response = _llm_call(llm, messages, "generate_report_node → LLM")

    report_json = {
        "metadata": {
            "generated_by": "STRIDE Threat Modeler - FIAP Hackaton",
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
