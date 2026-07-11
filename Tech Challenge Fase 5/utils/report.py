"""Utilitários de formatação de relatório — enriquecimento em Markdown e helpers de exportação HTML/PDF."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from utils.knowledge import STRIDE_CATEGORIES

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def build_summary_table(threats: dict[str, list[dict]]) -> str:
    """Monta uma tabela Markdown com o resumo de todas as ameaças, ordenadas por severidade."""
    rows = []
    for component, comp_threats in threats.items():
        for t in comp_threats:
            rows.append({
                "component": component,
                "threat_id": t.get("threat_id", ""),
                "stride": f"{t.get('stride_letter', '')} - {t.get('stride_category', '')}",
                "severity": t.get("severity", "Medium"),
                "description": t.get("description", "")[:80] + "..." if len(t.get("description", "")) > 80 else t.get("description", ""),
                "cwe": t.get("cwe_reference", ""),
            })

    rows.sort(key=lambda r: SEVERITY_ORDER.get(r["severity"], 99))

    lines = [
        "| # | Componente | STRIDE | Severidade | Descrição | CWE |",
        "|---|-----------|--------|----------|-------------|-----|",
    ]
    for i, row in enumerate(rows, 1):
        lines.append(
            f"| {i} | {row['component']} | {row['stride']} | "
            f"{row['severity']} | {row['description']} | {row['cwe']} |"
        )

    return "\n".join(lines)


def build_risk_matrix(components: list[dict], threats: dict[str, list[dict]]) -> str:
    """Monta uma matriz de risco componente × STRIDE em Markdown."""
    stride_letters = list("STRIDE")
    stride_names = {s: STRIDE_CATEGORIES[s]["name"] for s in stride_letters}

    header = "| Componente | " + " | ".join(stride_names[s] for s in stride_letters) + " |"
    sep = "|---|" + "---|" * len(stride_letters)
    lines = [header, sep]

    for comp in components:
        name = comp["name"]
        comp_threats = threats.get(name, [])
        threat_map: dict[str, str] = {}
        for t in comp_threats:
            letter = t.get("stride_letter", "")
            sev = t.get("severity", "")
            if letter not in threat_map or SEVERITY_ORDER.get(sev, 99) < SEVERITY_ORDER.get(threat_map[letter], 99):
                threat_map[letter] = sev

        cells = []
        for letter in stride_letters:
            sev = threat_map.get(letter, "")
            cells.append(sev if sev else "-")

        lines.append(f"| **{name}** | " + " | ".join(cells) + " |")

    return "\n".join(lines)


def build_remediation_plan(threats: dict[str, list[dict]]) -> str:
    """Monta um plano de remediação priorizado a partir de todas as ameaças."""
    all_threats = []
    for component, comp_threats in threats.items():
        for t in comp_threats:
            all_threats.append({"component": component, **t})

    all_threats.sort(key=lambda t: SEVERITY_ORDER.get(t.get("severity", "Low"), 99))

    lines = []
    current_severity = None
    counter = 1

    for t in all_threats:
        sev = t.get("severity", "Medium")
        if sev != current_severity:
            current_severity = sev
            lines.append(f"\n### Prioridade {sev}\n")

        lines.append(f"**{counter}. [{t['threat_id']}] {t['component']} — {t.get('stride_category', '')}**")
        lines.append(f"- **Ameaça:** {t.get('description', '')}")
        lines.append(f"- **Contramedida:** {t.get('countermeasure', '')}")
        lines.append(f"- **CWE:** {t.get('cwe_reference', '')}")
        lines.append("")
        counter += 1

    return "\n".join(lines)


def enrich_report(
    report_markdown: str,
    components: list[dict],
    threats: dict[str, list[dict]],
    report_json: dict[str, Any],
) -> str:
    """Anexa tabelas geradas automaticamente e o plano de remediação ao relatório do LLM."""
    metadata = report_json.get("metadata", {})
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    header = f"""# Relatório de Modelagem de Ameaças STRIDE

> **Gerado em:** {timestamp}
> **Ferramenta:** STRIDE Threat Modeler — FIAP Hackaton Fase 5
> **Total de Componentes:** {metadata.get('total_components', len(components))}
> **Total de Ameaças:** {metadata.get('total_threats', sum(len(v) for v in threats.values()))}

---

"""

    summary_section = f"""
---

## Anexo A — Tabela Completa de Resumo de Ameaças

{build_summary_table(threats)}

---

## Anexo B — Matriz de Risco

{build_risk_matrix(components, threats)}

---

## Anexo C — Plano de Remediação Priorizado

{build_remediation_plan(threats)}

---

"""

    return header + report_markdown + summary_section


def threats_to_csv(threats: dict[str, list[dict]]) -> str:
    """Exporta todas as ameaças em formato CSV."""
    lines = [
        "ID da Ameaça,Componente,Letra STRIDE,Categoria STRIDE,Severidade,Descrição,Vetor de Ataque,Vulnerabilidade,Contramedida,CWE"
    ]
    for component, comp_threats in threats.items():
        for t in comp_threats:
            def esc(v: str) -> str:
                return f'"{str(v).replace(chr(34), chr(39))}"'
            lines.append(",".join([
                esc(t.get("threat_id", "")),
                esc(component),
                esc(t.get("stride_letter", "")),
                esc(t.get("stride_category", "")),
                esc(t.get("severity", "")),
                esc(t.get("description", "")),
                esc(t.get("attack_vector", "")),
                esc(t.get("vulnerability", "")),
                esc(t.get("countermeasure", "")),
                esc(t.get("cwe_reference", "")),
            ]))
    return "\n".join(lines)


def get_severity_stats(threats: dict[str, list[dict]]) -> dict[str, int]:
    stats = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for comp_threats in threats.values():
        for t in comp_threats:
            sev = t.get("severity", "Medium")
            if sev in stats:
                stats[sev] += 1
    return stats


def get_stride_stats(threats: dict[str, list[dict]]) -> dict[str, int]:
    stats = {letter: 0 for letter in "STRIDE"}
    for comp_threats in threats.values():
        for t in comp_threats:
            letter = t.get("stride_letter", "")
            if letter in stats:
                stats[letter] += 1
    return stats
