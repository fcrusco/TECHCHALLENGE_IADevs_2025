"""Monta o dataset de fine-tuning STRIDE (JSONL em formato chat).

Combina as instâncias de arquitetura sintéticas (architectures.py) com as
ameaças-semente grounded (seed_kb.py), e usa um modelo LM Studio local para
parafrasear o texto de ameaça/contramedida, dando diversidade lexical mas
mantendo fixos a categoria STRIDE, o risk_level e a cwe_reference (grounded,
não alucinado).

O formato de saída é idêntico ao que backend/services/stride.py envia/espera,
de forma que o modelo treinado seja um substituto direto (drop-in) daquela
chamada de LLM:
  messages = [system(SYSTEM_PROMPT), user(components_text)] -> assistant(json)

Uso:
    python build_dataset.py [--no-augment] [--limit N]
"""

import argparse
import json
import logging
import random
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from architectures import build_instances
from seed_kb import CATEGORIES, SEED_THREATS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("build_dataset")

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
LM_STUDIO_MODEL = "google/gemma-4-12b-qat"  # já carregado/rápido nesta GPU para augmentation de dados

# Mantido idêntico a backend/services/stride.py
SYSTEM_PROMPT = """Você é um especialista em cibersegurança. Realize a análise de ameaças STRIDE sobre os componentes fornecidos.

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


def _build_components_text(components: list[dict]) -> str:
    lines = ["Componentes da arquitetura para analisar:"]
    for c in components:
        lines.append(f"- id:{c['id']} name:{c['name']} type:{c['type']} desc:{c['description']}")
    return "\n".join(lines)


def _draft_report(components: list[dict]) -> dict:
    """Rascunho ground-truth extraído direto da base semente (sem paráfrase)."""
    report = {cat: [] for cat in CATEGORIES}
    for c in components:
        for entry in SEED_THREATS.get(c["type"], []):
            report[entry["category"]].append({
                "component_id": c["id"],
                "component_name": c["name"],
                "threat": entry["threat"],
                "risk_level": entry["risk_level"],
                "countermeasures": [entry["countermeasure"]],
            })
    return report


AUGMENT_SYSTEM = """Você reescreve dados de treinamento para um modelo de modelagem de ameaças STRIDE.
Reescreva os campos "threat" e cada item de "countermeasures" com palavras diferentes,
adaptando levemente ao nome/contexto do componente citado. NÃO mude "component_id",
"component_name", "risk_level", nem a categoria/estrutura do JSON. NÃO adicione nem
remova nenhuma entrada. Mantenha cada texto com menos de 80 caracteres.
Retorne APENAS o objeto JSON reescrito, no mesmo formato de entrada, sem markdown."""


def _call_lm_studio(system: str, user: str, max_tokens: int = 4096) -> str:
    payload = json.dumps({
        "model": LM_STUDIO_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.5,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(
        LM_STUDIO_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=240) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return text.strip()


def _augment(draft: dict) -> dict:
    total = sum(len(v) for v in draft.values())
    max_tokens = min(8192, 1200 + total * 220)
    for attempt in range(2):
        try:
            raw = _call_lm_studio(AUGMENT_SYSTEM, json.dumps(draft, ensure_ascii=False), max_tokens=max_tokens)
            rewritten = json.loads(_clean_json(raw))
            for cat in CATEGORIES:
                if cat not in rewritten or len(rewritten[cat]) != len(draft[cat]):
                    raise ValueError(f"shape mismatch in category {cat}")
            return rewritten
        except Exception as exc:
            logger.warning("  tentativa %d de augmentation falhou (%s)", attempt + 1, exc)
    logger.warning("  desistindo — usando rascunho sem augmentation")
    return draft


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-augment", action="store_true", help="pula a paráfrase via LM Studio")
    parser.add_argument("--limit", type=int, default=None, help="limita o número de instâncias (debug)")
    args = parser.parse_args()

    instances = build_instances()
    random.Random(42).shuffle(instances)
    if args.limit:
        instances = instances[: args.limit]

    out_path = Path(__file__).parent / "data" / "stride_sft.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with out_path.open("w", encoding="utf-8") as f:
        for i, inst in enumerate(instances, 1):
            components = inst["components"]
            draft = _draft_report(components)
            total_threats = sum(len(v) for v in draft.values())
            if total_threats == 0:
                continue

            t0 = time.time()
            report = draft if args.no_augment else _augment(draft)
            elapsed = time.time() - t0

            user_msg = _build_components_text(components)
            assistant_msg = json.dumps(report, ensure_ascii=False)

            example = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": assistant_msg},
                ]
            }
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
            written += 1
            logger.info("[%d/%d] %-45s %2d componentes | %2d ameaças | %.1fs",
                        i, len(instances), inst["domain"], len(components), total_threats, elapsed)

    logger.info("Dataset escrito em %s (%d exemplos)", out_path, written)


if __name__ == "__main__":
    main()
