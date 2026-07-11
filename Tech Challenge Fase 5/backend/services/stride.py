import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from models.schemas import Component, StrideReport, StrideThreat, ProviderType
from services.llm_factory import get_llm_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um especialista em cibersegurança. Realize a análise de ameaças STRIDE sobre os componentes fornecidos.

Retorne APENAS um objeto JSON válido com estas chaves exatas:
spoofing, tampering, repudiation, information_disclosure, denial_of_service, elevation_of_privilege

Cada valor é um array de:
{"component_id":"comp_1","component_name":"Nome","threat":"descrição curta em português do Brasil","risk_level":"low|medium|high|critical","countermeasures":["uma contramedida em português do Brasil"]}

Regras:
- No máximo 1 ameaça por componente por categoria STRIDE
- No máximo 30 ameaças no total, somando todas as categorias
- Apenas 1 contramedida por ameaça
- Mantenha os textos de ameaça e contramedida curtos (menos de 80 caracteres cada)
- Retorne APENAS o objeto JSON, sem markdown, sem explicação"""

VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}
CATEGORIES = [
    "spoofing", "tampering", "repudiation",
    "information_disclosure", "denial_of_service", "elevation_of_privilege"
]


def _build_components_text(components: list[Component]) -> str:
    lines = ["Componentes da arquitetura para analisar:"]
    for comp in components:
        lines.append(f"- id:{comp.id} name:{comp.name} type:{comp.type} desc:{comp.description}")
    return "\n".join(lines)


# ── Helpers de recuperação de JSON ───────────────────────────────────────────

def _repair_json(raw: str) -> str:
    """Recupera um JSON truncado.

    Passo 1 – se terminarmos dentro de uma string não fechada (corte por limite
              de tokens), trunca de volta até o último '}' que estava fora de uma string.
    Passo 2 – fecha todos os arrays/objetos ainda abertos.
    """
    last_obj_close = -1
    in_string = False
    escape = False

    for i, ch in enumerate(raw):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "}":
            last_obj_close = i

    if in_string:
        if last_obj_close >= 0:
            # Truncado além do último objeto completo — corta ali
            raw = raw[:last_obj_close + 1]
        else:
            # Nenhum objeto completo — fecha a string aberta para que o Passo 2
            # consiga ao menos fechar as chaves/colchetes do objeto parcial
            raw = raw + '"'

    raw = raw.rstrip().rstrip(",")
    depth: list[str] = []
    in_string = False
    escape = False

    for ch in raw:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth.append("}")
        elif ch == "[":
            depth.append("]")
        elif ch in "}]" and depth and depth[-1] == ch:
            depth.pop()

    return raw + "".join(reversed(depth))


def _extract_array(text: str, key: str) -> list:
    """Extrai o array JSON de `key` usando parsing de profundidade de colchetes.

    Funciona mesmo quando o JSON ao redor está malformado — encontramos o '['
    que pertence à chave e avançamos contando a profundidade até fechar (ou o
    texto acabar, caso em que reparamos e tentamos de novo).
    """
    marker = f'"{key}"'
    idx = text.find(marker)
    if idx < 0:
        return []

    colon = text.find(":", idx + len(marker))
    if colon < 0:
        return []

    bracket = text.find("[", colon)
    if bracket < 0:
        return []

    depth = 0
    in_string = False
    escape = False

    for i in range(bracket, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                chunk = text[bracket: i + 1]
                try:
                    return json.loads(chunk)
                except json.JSONDecodeError:
                    try:
                        return json.loads(_repair_json(chunk))
                    except (json.JSONDecodeError, ValueError):
                        return []

    # Array nunca fechou — usa o que tem e repara
    chunk = text[bracket:]
    try:
        return json.loads(_repair_json(chunk))
    except (json.JSONDecodeError, ValueError):
        return []


def _extract_per_category(raw: str) -> dict:
    """Recuperação de último recurso: extrai o array de cada categoria STRIDE independentemente."""
    logger.warning("[stride] Recorrendo à extração de array por categoria")
    result = {}
    for cat in CATEGORIES:
        result[cat] = _extract_array(raw, cat)
        if result[cat]:
            logger.info("[stride]   recuperado %-30s %d entradas", cat, len(result[cat]))
        else:
            logger.warning("[stride]   não foi possível recuperar %s", cat)
    return result


# ── Parse ─────────────────────────────────────────────────────────────────────

def _parse_stride_report(raw: str) -> StrideReport:
    raw = raw.strip()
    # Remove o bloco de código markdown, se houver
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    data: dict | None = None

    # Tentativa 1: parse direto
    try:
        data = json.loads(raw)
        logger.info("[stride] JSON parseado com sucesso")
    except json.JSONDecodeError as exc:
        logger.warning("[stride] Falha ao parsear JSON (%s) — tentando reparar", exc)

        # Tentativa 2: reparo (trata strings truncadas + colchetes não fechados)
        try:
            repaired = _repair_json(raw)
            data = json.loads(repaired)
            logger.info("[stride] JSON recuperado após reparo | chars_reparados=%d", len(repaired))
        except (json.JSONDecodeError, ValueError):
            pass

    # Tentativa 3: extração por categoria (trata vírgulas faltando, caracteres estranhos, etc.)
    if data is None:
        data = _extract_per_category(raw)
        total = sum(len(v) for v in data.values())
        if total == 0:
            logger.error("[stride] Todas as tentativas de recuperação falharam | primeiros 400 chars: %s", raw[:400])
            raise ValueError("Falha ao parsear o relatório STRIDE na resposta do LLM")

    parsed: dict[str, list[StrideThreat]] = {}
    for cat in CATEGORIES:
        threats: list[StrideThreat] = []
        for t in data.get(cat, []):
            if not isinstance(t, dict):
                continue
            if t.get("risk_level") not in VALID_RISK_LEVELS:
                t["risk_level"] = "medium"
            try:
                threats.append(StrideThreat(**t))
            except Exception:
                pass
        parsed[cat] = threats
        logger.info("[stride]   %-30s %d ameaças", cat, len(threats))

    return StrideReport(**parsed)


# ── API pública ───────────────────────────────────────────────────────────────

def analyze_stride(
    components: list[Component],
    provider: ProviderType | None = None,
    override_url: str | None = None,
    override_model: str | None = None,
) -> StrideReport:
    logger.info("[stride] Iniciando análise STRIDE | %d componentes | provider=%s",
                len(components), provider)

    llm, model = get_llm_client(provider, override_url, override_model)
    logger.info("[stride] Usando modelo=%s", model)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=_build_components_text(components)),
    ]

    logger.info("[stride] Chamando o LLM via LangChain...")
    response = llm.invoke(messages)
    content = response.content or ""

    logger.info("[stride] LLM respondeu | chars=%d", len(content))
    logger.debug("[stride] Resposta bruta (primeiros 300): %s", content[:300])

    return _parse_stride_report(content)
