"""
Parecer médico via IA — Tech Challenge Fase 4

Envia os resultados de detecção do(s) modelo(s) YOLOv8 para o GPT-4o
e retorna um parecer médico completo e profissional em português.

Requer: OPENAI_API_KEY no .env
"""

import os


def generate_medical_opinion(model_results, video_name="vídeo cirúrgico"):
    """
    Gera um parecer médico via GPT-4o com base nos resultados de detecção.

    Returns:
        (opinion: str | None, error: str | None)
    """
    try:
        from openai import OpenAI
    except ImportError:
        return None, "Dependência 'openai' não instalada. Execute: pip install openai"

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, "OPENAI_API_KEY não configurada no .env"

    client  = OpenAI(api_key=api_key)
    context = _build_context(model_results, video_name)

    system_msg = (
        "Você é um médico especialista em ginecologia e obstetrícia com ampla experiência "
        "em cirurgia laparoscópica. Sua função é elaborar pareceres médicos técnicos e "
        "profissionais em português com base em dados gerados por sistemas de visão "
        "computacional aplicados a vídeos cirúrgicos ginecológicos."
    )

    user_msg = f"""Analise os resultados abaixo de um sistema de visão computacional (YOLOv8) \
aplicado a um vídeo de cirurgia ginecológica laparoscópica e elabore um parecer médico \
completo, técnico e profissional.

{context}

Estruture o parecer com as seguintes seções:

1. **Resumo Executivo**
   Síntese objetiva dos principais achados da análise computacional.

2. **Análise dos Achados por Modelo de Detecção**
   Interpretação clínica dos resultados de cada detector (instrumentos, \
áreas críticas, sangramento), com correlação ao procedimento cirúrgico.

3. **Avaliação de Risco Clínico**
   Nível de risco global, justificativa e implicações para a segurança do procedimento.

4. **Eventos e Anomalias Relevantes**
   Análise detalhada das principais anomalias detectadas, sua localização temporal \
no procedimento e significância clínica.

5. **Recomendações**
   Ações clínicas indicadas com base nos achados, incluindo protocolos de \
monitoramento, encaminhamentos ou revisões necessárias.

6. **Considerações Finais**
   Observações complementares para a equipe médica, limitações do sistema e \
orientações para o acompanhamento do caso.

Use linguagem médica profissional adequada para prontuário clínico. Seja técnico, \
objetivo e baseado estritamente nos dados apresentados.

Este documento é gerado por um sistema de apoio à decisão clínica baseado em \
inteligência artificial. A validação e responsabilidade clínica são exclusivas do \
médico responsável pelo caso."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=2500,
        )
        return response.choices[0].message.content, None
    except Exception as e:
        return None, f"Erro na API OpenAI: {e}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ts(frame, fps):
    sec = int(frame) // max(int(fps), 1)
    return f"{sec // 60:02d}:{sec % 60:02d}"


def _build_context(model_results, video_name):
    fps          = model_results[0]["fps"]          if model_results else 20
    total_frames = model_results[0]["frame_count"]  if model_results else 0
    total_anom   = sum(len(r["anomalies"]) for r in model_results)
    dur_sec      = int(total_frames) // max(int(fps), 1)
    duration     = f"{dur_sec // 60:02d}:{dur_sec % 60:02d}"
    overall_rate = total_anom / max(total_frames, 1) * 100

    lines = [
        "=== DADOS DO VÍDEO ===",
        f"Arquivo              : {video_name}",
        f"Duração              : {duration}",
        f"Frames analisados    : {total_frames}",
        f"FPS                  : {fps:.1f}",
        f"Modelos executados   : {len(model_results)}",
        f"Total de anomalias   : {total_anom} ({overall_rate:.1f}% dos frames)",
        "",
    ]

    for r in model_results:
        folder = r["model_folder"]
        lines.append(f"=== MODELO: {folder.upper().replace('_', ' ')} ===")
        lines.append(f"Detecções totais: {r['detections']}")

        if folder == "instrumentos":
            lines.append("Comportamento: rastreamento de instrumentos cirúrgicos (modo tracking, sem anomalias)")
            timeline = r.get("instrument_timeline", {})
            detected = [(n, i) for n, i in timeline.items() if i["count"] > 0]
            if detected:
                lines.append("Instrumentos identificados no procedimento:")
                for name, info in sorted(detected, key=lambda x: -x[1]["count"]):
                    first = _ts(info["first_frame"], fps) if info.get("first_frame") else "—"
                    last  = _ts(info["last_frame"],  fps) if info.get("last_frame")  else "—"
                    segs  = len(info.get("segments", []))
                    lines.append(
                        f"  - {name}: {info['count']} detecções | "
                        f"{info['frames_pct']:.1f}% do vídeo | "
                        f"{segs} segmento(s) | {first} → {last}"
                    )
            else:
                lines.append("  Nenhum instrumento detectado no vídeo.")

        else:
            anom  = r["anomalies"]
            rate  = len(anom) / max(r["frame_count"], 1) * 100
            crit  = sum(1 for a in anom if isinstance(a, dict) and a.get("severity") == "CRÍTICO")
            alto  = sum(1 for a in anom if isinstance(a, dict) and a.get("severity") == "ALTO")
            medio = sum(1 for a in anom if isinstance(a, dict) and a.get("severity") == "MÉDIO")

            lines.append(f"Anomalias detectadas : {len(anom)} ({rate:.1f}% dos frames)")
            lines.append(f"  CRÍTICO: {crit} | ALTO: {alto} | MÉDIO: {medio}")

            cs = r.get("class_summary", {})
            if cs:
                lines.append("Objetos/classes identificados:")
                for cls_name, info in sorted(cs.items(), key=lambda x: -x[1]["count"]):
                    first = _ts(info["first_frame"], fps) if info.get("first_frame") else "—"
                    last  = _ts(info["last_frame"],  fps) if info.get("last_frame")  else "—"
                    lines.append(
                        f"  - {cls_name}: {info['count']} detecções | "
                        f"{info['frames_pct']:.1f}% dos frames | {first} → {last}"
                    )

            if anom:
                lines.append("Linha do tempo de anomalias (até 25 eventos):")
                for a in anom[:25]:
                    if isinstance(a, dict):
                        fr  = a.get("frame", 0)
                        lines.append(
                            f"  [{_ts(fr, fps)}] {a.get('severity','?')} — "
                            f"{a.get('type','?')}: {a.get('description','')}"
                        )
                if len(anom) > 25:
                    lines.append(f"  ... e mais {len(anom) - 25} anomalias (ver relatório completo)")

        lines.append("")

    return "\n".join(lines)
